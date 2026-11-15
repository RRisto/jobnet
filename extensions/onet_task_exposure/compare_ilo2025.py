#!/usr/bin/env python3
"""Compare 2025 ILO task exposure means with project and GPT-4 scores.

Project occupations are matched to ISCO-08 titles using normalized exact
title equality only. This is conservative because IPUMS and ISCO are different
classification systems.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
import unicodedata
from pathlib import Path


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def pearson(xs: list[float], ys: list[float]) -> float:
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    den = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den if den else float("nan")


def ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    result = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        rank = (i + 1 + j) / 2
        for k in range(i, j):
            result[order[k]] = rank
        i = j
    return result


def collect_occupations(tree: dict) -> dict[str, dict]:
    result: dict[str, dict] = {}

    def visit(node: dict) -> None:
        name = str(node.get("name", ""))
        match = re.match(r"^\s*(\d{4})\s*-\s*(.+?)\s*$", name)
        if match:
            code, title = match.groups()
            task_scores = []
            for child in node.get("children", []):
                task = re.match(r"^\s*\(\s*([0-9]*\.?[0-9]+)\s*\)\s*-", str(child.get("name", "")))
                if task:
                    score = float(task.group(1))
                    if not 0 <= score <= 1:
                        raise ValueError(f"ILO task score out of range: {score}")
                    task_scores.append(score)
            if task_scores:
                result[code] = {
                    "code": code,
                    "title": title,
                    "task_count": len(task_scores),
                    "mean": statistics.fmean(task_scores),
                    "sd_population": statistics.pstdev(task_scores),
                    "risk": node.get("risk", ""),
                }
        else:
            for child in node.get("children", []):
                visit(child)

    visit(tree)
    return result


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy", type=Path, default=Path("data/ipums_variables.csv"))
    parser.add_argument("--gpt4", type=Path, default=Path("extensions/onet_task_exposure/data/gpts_are_gpts_occ_level.csv"))
    parser.add_argument("--ilo-tree", type=Path, default=Path("extensions/onet_task_exposure/data/ilo_2025_isco_exposure_tree.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("extensions/onet_task_exposure/results"))
    args = parser.parse_args()

    with args.ilo_tree.open(encoding="utf-8") as stream:
        ilodata = collect_occupations(json.load(stream))
    legacy = read_csv(args.legacy)
    gpt_rows = read_csv(args.gpt4)
    gpt_by_title: dict[str, list[dict[str, str]]] = {}
    for row in gpt_rows:
        gpt_by_title.setdefault(norm(row["Title"]), []).append(row)
    ilo_by_title: dict[str, list[dict]] = {}
    for row in ilodata.values():
        ilo_by_title.setdefault(norm(row["title"]), []).append(row)

    matches = []
    ambiguous = 0
    for row in legacy:
        title = norm(row["label"])
        ilo_hits = ilo_by_title.get(title, [])
        gpt_hits = gpt_by_title.get(title, [])
        if len(ilo_hits) > 1 or len(gpt_hits) > 1:
            ambiguous += 1
        if len(ilo_hits) == 1:
            gpt = gpt_hits[0] if len(gpt_hits) == 1 else {}
            matches.append((row, ilo_hits[0], gpt))
    if not matches:
        parser.error("No exact normalized title matches found")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / "frey_osborne_vs_gpt4_vs_ilo2025.csv"
    out = []
    for legacy_row, ilo, gpt in matches:
        out.append({
            "project_occ_id": legacy_row["id"],
            "project_occupation": legacy_row["label"],
            "isco08_code": ilo["code"],
            "isco08_title": ilo["title"],
            "ilo_2025_task_mean": f"{ilo['mean']:.8f}",
            "ilo_2025_task_sd_population": f"{ilo['sd_population']:.8f}",
            "ilo_2025_task_count": ilo["task_count"],
            "ilo_2025_gradient": ilo["risk"],
            "frey_osborne_probability": legacy_row["auto_prob_average"],
            "gpt4_beta": gpt.get("dv_rating_beta", ""),
            "gpt4_human_beta": gpt.get("human_rating_beta", ""),
            "title_match_method": "normalized_exact_isco_title",
        })
    fields = list(out[0])
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(out)

    fo = [float(r[0]["auto_prob_average"]) for r in matches]
    ilo_mean = [r[1]["mean"] for r in matches]
    valid_gpt = [(r[0], r[1], r[2]) for r in matches if r[2].get("dv_rating_beta")]
    report = [
        "# ILO 2025 GenAI task exposure comparison",
        "",
        "The ILO 2025 score is the equal-weight mean of the released task-level ISCO-08 scores for each occupation. It is a GenAI technical exposure measure, not a job-loss probability. The source index classifies occupations using task-score mean and variability; this report preserves its category labels and also reports the task mean. Population SD is calculated from released task scores for descriptive purposes.",
        "",
        f"- Project occupations: {len(legacy)}",
        f"- ILO ISCO-08 occupations extracted: {len(ilodata)}",
        f"- Exact normalized-title matches: {len(matches)} ({len(matches)/len(legacy):.1%} of project occupations)",
        f"- Matched occupations with GPT-4 beta also available: {len(valid_gpt)}",
        f"- Ambiguous title matches excluded: {ambiguous}",
        f"- Matched-sample mean Frey–Osborne probability: {statistics.fmean(fo):.3f}",
        f"- Matched-sample mean ILO 2025 task exposure: {statistics.fmean(ilo_mean):.3f}",
        f"- Spearman rank correlation, Frey–Osborne vs ILO 2025 mean: {pearson(ranks(fo), ranks(ilo_mean)):.3f}",
    ]
    if valid_gpt:
        gpt_beta = [float(r[2]["dv_rating_beta"]) for r in valid_gpt]
        ilo_for_gpt = [r[1]["mean"] for r in valid_gpt]
        report.extend([
            f"- Mean GPT-4 beta for those {len(valid_gpt)} occupations: {statistics.fmean(gpt_beta):.3f}",
            f"- Spearman rank correlation, GPT-4 beta vs ILO 2025 mean: {pearson(ranks(gpt_beta), ranks(ilo_for_gpt)):.3f}",
        ])
    report.extend(["", "## Highest ILO 2025 task means in the matched sample", "", "| Occupation | ILO task mean | ILO gradient | FO probability | GPT-4 beta |", "|---|---:|---|---:|---:|"])
    for legacy_row, ilo, gpt in sorted(matches, key=lambda x: x[1]["mean"], reverse=True)[:10]:
        gpt_score = f"{float(gpt['dv_rating_beta']):.3f}" if gpt.get("dv_rating_beta") else ""
        report.append(f"| {legacy_row['label']} | {ilo['mean']:.3f} | {ilo['risk']} | {float(legacy_row['auto_prob_average']):.3f} | {gpt_score} |")
    report.extend(["", "Matching uses normalized exact occupation titles only. Unmatched occupations are excluded pending an explicit crosswalk between the project’s IPUMS/Census classification and ISCO-08.", ""])
    report_path = args.output_dir / "ilo2025_comparison_summary.md"
    report_path.write_text("\n".join(report), encoding="utf-8")
    print(f"Extracted {len(ilodata)} ISCO occupations; matched {len(matches)}/{len(legacy)} project occupations")
    print(f"Spearman rho FO vs ILO={pearson(ranks(fo), ranks(ilo_mean)):.3f}")
    print(f"Wrote {csv_path} and {report_path}")


if __name__ == "__main__":
    main()
