#!/usr/bin/env python3
"""Prepare and aggregate an auditable O*NET task exposure dataset."""

from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import defaultdict
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError(f"{path} has no CSV header")
        return list(reader)


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def require_columns(rows: list[dict[str, str]], path: Path, columns: set[str]) -> None:
    actual = set(rows[0]) if rows else set()
    missing = columns - actual
    if missing:
        raise ValueError(f"{path} is missing required columns: {', '.join(sorted(missing))}")


def prepare(args: argparse.Namespace) -> None:
    tasks, crosswalk, occupations = (read_csv(args.onet_tasks), read_csv(args.crosswalk), read_csv(args.occupations))
    require_columns(tasks, args.onet_tasks, {"O*NET-SOC Code", "Task"})
    require_columns(crosswalk, args.crosswalk, {"project_occ_id", "onet_soc_code"})
    require_columns(occupations, args.occupations, {"id", "label"})

    labels = {row["id"].strip(): row["label"].strip() for row in occupations}
    mappings: dict[str, list[dict[str, str]]] = defaultdict(list)
    for mapping in crosswalk:
        project_id = mapping["project_occ_id"].strip()
        onet_code = mapping["onet_soc_code"].strip()
        if project_id not in labels:
            print(f"Skipping crosswalk id absent from occupations: {project_id}", file=sys.stderr)
            continue
        if onet_code:
            mappings[onet_code].append(mapping)

    output: list[dict[str, object]] = []
    for task_num, task in enumerate(tasks, start=1):
        code = task["O*NET-SOC Code"].strip()
        for mapping in mappings.get(code, []):
            project_id = mapping["project_occ_id"].strip()
            output.append({
                "task_id": f"{project_id}:{task_num}",
                "project_occ_id": project_id,
                "project_occupation": labels[project_id],
                "onet_soc_code": code,
                "task": task["Task"].strip(),
                "match_type": mapping.get("match_type", ""),
                "match_notes": mapping.get("match_notes", ""),
                "exposure_score": "",
                "task_weight": "",
                "assessment_source": "",
            })

    if not output:
        raise ValueError("No tasks matched. Check that the crosswalk O*NET-SOC codes match the O*NET task file.")
    fields = ["task_id", "project_occ_id", "project_occupation", "onet_soc_code", "task", "match_type", "match_notes", "exposure_score", "task_weight", "assessment_source"]
    write_csv(args.output, output, fields)
    print(f"Wrote {len(output)} task rows for {len({r['project_occ_id'] for r in output})} project occupations to {args.output}")


def number(value: str, *, default: float | None = None) -> float | None:
    value = value.strip()
    if not value:
        return default
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"Expected a number, received {value!r}") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"Expected a finite number, received {value!r}")
    return parsed


def aggregate(args: argparse.Namespace) -> None:
    rows = read_csv(args.scored_tasks)
    require_columns(rows, args.scored_tasks, {"project_occ_id", "project_occupation", "task", "exposure_score"})
    groups: dict[str, list[tuple[float, float | None, str]]] = defaultdict(list)
    for row in rows:
        score = number(row["exposure_score"])
        if score is None:
            continue
        if not 0 <= score <= 1:
            raise ValueError(f"Exposure score must be between 0 and 1 (occupation {row['project_occ_id']}, task {row['task']!r})")
        weight = number(row.get("task_weight", ""))
        if weight is not None and weight < 0:
            raise ValueError(f"Task weights cannot be negative (occupation {row['project_occ_id']})")
        groups[row["project_occ_id"].strip()].append((score, weight, row["project_occupation"].strip()))

    legacy: dict[str, str] = {}
    if args.legacy:
        legacy_rows = read_csv(args.legacy)
        require_columns(legacy_rows, args.legacy, {"id", "auto_prob_average"})
        legacy = {row["id"].strip(): row["auto_prob_average"].strip() for row in legacy_rows}

    results: list[dict[str, object]] = []
    total_by_occupation: dict[str, int] = defaultdict(int)
    incomplete = 0
    for row in rows:
        occ_id = row["project_occ_id"].strip()
        if not occ_id:
            incomplete += 1
        else:
            total_by_occupation[occ_id] += 1
    for occ_id, items in groups.items():
        weights = [(s, w) for s, w, _ in items if w is not None]
        weight_total = sum(w for _, w in weights)
        results.append({
            "project_occ_id": occ_id,
            "occupation": items[0][2],
            "task_count_scored": len(items),
            "task_count_total": total_by_occupation[occ_id],
            "score_coverage": len(items) / total_by_occupation[occ_id],
            "exposure_mean": sum(s for s, _, _ in items) / len(items),
            "exposure_weighted_mean": sum(s * w for s, w in weights) / weight_total if weight_total else "",
            "weighted_task_count": len(weights),
            "legacy_frey_osborne_probability": legacy.get(occ_id, ""),
        })

    fields = ["project_occ_id", "occupation", "task_count_scored", "task_count_total", "score_coverage", "exposure_mean", "exposure_weighted_mean", "weighted_task_count", "legacy_frey_osborne_probability"]
    write_csv(args.output, results, fields)
    missing_occ = len({r["project_occ_id"].strip() for r in rows if r["project_occ_id"].strip()}) - len(groups)
    print(f"Wrote exposure for {len(results)} occupations to {args.output}")
    if incomplete or missing_occ:
        print(f"Skipped {missing_occ} occupations with no scored tasks; {incomplete} rows had blank occupation ids.", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare", help="Join O*NET tasks with the reviewed occupation crosswalk")
    prep.add_argument("--onet-tasks", type=Path, required=True)
    prep.add_argument("--crosswalk", type=Path, required=True)
    prep.add_argument("--occupations", type=Path, required=True)
    prep.add_argument("--output", type=Path, required=True)
    prep.set_defaults(run=prepare)
    agg = commands.add_parser("aggregate", help="Aggregate reviewed 0–1 task scores by occupation")
    agg.add_argument("--scored-tasks", type=Path, required=True)
    agg.add_argument("--output", type=Path, required=True)
    agg.add_argument("--legacy", type=Path, help="Optional legacy CSV with id and auto_prob_average")
    agg.set_defaults(run=aggregate)
    args = parser.parse_args()
    try:
        args.run(args)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    main()
