#!/usr/bin/env python3
"""Compare legacy FO scores with published O*NET GPT exposure scores.

Only normalized exact-title matches are included; this avoids quietly
introducing uncertain mappings between Census and O*NET occupation taxonomies.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import unicodedata
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def pearson(xs: list[float], ys: list[float]) -> float:
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return cov / den if den else float("nan")


def ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        rank = (i + 1 + j) / 2
        for k in range(i, j):
            out[order[k]] = rank
        i = j
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy", type=Path, default=Path("data/ipums_variables.csv"))
    parser.add_argument("--published", type=Path, default=Path("extensions/onet_task_exposure/data/gpts_are_gpts_occ_level.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("extensions/onet_task_exposure/results"))
    args = parser.parse_args()

    old = read_csv(args.legacy)
    published = read_csv(args.published)
    by_title: dict[str, list[dict[str, str]]] = {}
    for row in published:
        by_title.setdefault(norm(row["Title"]), []).append(row)

    matched: list[tuple[dict[str, str], dict[str, str]]] = []
    ambiguous: list[str] = []
    for row in old:
        choices = by_title.get(norm(row["label"]), [])
        if len(choices) == 1:
            matched.append((row, choices[0]))
        elif len(choices) > 1:
            ambiguous.append(row["label"])
    if not matched:
        parser.error("No exact normalized title matches found")

    out_rows = []
    for legacy, current in matched:
        out_rows.append({
            "project_occ_id": legacy["id"],
            "project_occupation": legacy["label"],
            "onet_soc_code": current["O*NET-SOC Code"],
            "frey_osborne_probability": legacy["auto_prob_average"],
            "gpt4_direct_alpha": current["dv_rating_alpha"],
            "gpt4_direct_plus_half_tools_beta": current["dv_rating_beta"],
            "gpt4_direct_plus_all_tools_gamma": current["dv_rating_gamma"],
            "human_direct_plus_half_tools_beta": current["human_rating_beta"],
            "title_match_method": "normalized_exact",
        })

    args.output_dir.mkdir(parents=True, exist_ok=True)
    result_path = args.output_dir / "frey_osborne_vs_gpt4_exposure.csv"
    fields = list(out_rows[0])
    with result_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(out_rows)

    fo = [float(row["auto_prob_average"]) for row, _ in matched]
    beta = [float(current["dv_rating_beta"]) for _, current in matched]
    human_beta = [float(current["human_rating_beta"]) for _, current in matched]
    rho = pearson(ranks(fo), ranks(beta))
    mean_fo, mean_beta = sum(fo) / len(fo), sum(beta) / len(beta)
    ranked = sorted(zip(matched, fo, beta), key=lambda item: item[1], reverse=True)
    beta_ranked = sorted(zip(matched, fo, beta), key=lambda item: item[2], reverse=True)
    fo_rank = {item[0][0]["id"]: rank for rank, item in enumerate(ranked, 1)}
    beta_rank = {item[0][0]["id"]: rank for rank, item in enumerate(beta_ranked, 1)}
    top_fo = ranked[:10]
    rank_delta = lambda item: beta_rank[item[0][0]["id"]] - fo_rank[item[0][0]["id"]]
    rank_falls = sorted((item for item in top_fo if rank_delta(item) > 0), key=rank_delta, reverse=True)[:5]
    rank_rises = sorted((item for item in top_fo if rank_delta(item) < 0), key=rank_delta)[:5]

    report = [
        "# Frey–Osborne vs GPT-4 task exposure: exact-title comparison",
        "",
        "This is a descriptive comparison on normalized exact occupation-title matches only. The legacy score is Frey–Osborne computerisation probability; GPT-4 beta is the share of O*NET tasks classified as directly exposed plus half-weighted tool-enabled exposure (2023-era GPT-4 assessment). These are different constructs and should not be interpreted as interchangeable risk probabilities or job-loss forecasts.",
        "",
        f"- Legacy occupations: {len(old)}",
        f"- Published O*NET occupations: {len(published)}",
        f"- Exact normalized-title matches: {len(matched)} ({len(matched)/len(old):.1%} of legacy occupations)",
        f"- Unmatched legacy occupations: {len(old)-len(matched)}",
        f"- Ambiguous exact-title matches excluded: {len(ambiguous)}",
        f"- Matched sample mean Frey–Osborne probability: {mean_fo:.3f}",
        f"- Matched sample mean GPT-4 beta exposure: {mean_beta:.3f}",
        f"- Matched sample mean human beta exposure: {sum(human_beta)/len(human_beta):.3f}",
        f"- Spearman rank correlation, Frey–Osborne vs GPT-4 beta: {rho:.3f}",
        "",
        "## Largest rank falls among the 10 highest Frey–Osborne scores",
        "",
        "| Occupation | FO rank | GPT-4 beta rank | GPT-4 beta |",
        "|---|---:|---:|---:|",
    ]
    for (legacy, current), old_score, beta_score in rank_falls:
        old_rank = fo_rank[legacy["id"]]
        report.append(f"| {legacy['label']} | {old_rank} | {beta_rank[legacy['id']]} | {beta_score:.3f} |")
    report.extend(["", "## Largest rank rises among the 10 highest Frey–Osborne scores", "", "| Occupation | FO rank | GPT-4 beta rank | GPT-4 beta |", "|---|---:|---:|---:|"])
    for (legacy, current), old_score, beta_score in rank_rises:
        old_rank = fo_rank[legacy["id"]]
        report.append(f"| {legacy['label']} | {old_rank} | {beta_rank[legacy['id']]} | {beta_score:.3f} |")
    report.extend(["", "The rank correlation is Spearman's rho computed within this exact-title matched subset. Occupation matches that differ in naming or classification are intentionally left out pending a reviewed crosswalk.", ""])
    report_path = args.output_dir / "comparison_summary.md"
    report_path.write_text("\n".join(report), encoding="utf-8")
    print(f"Matched {len(matched)}/{len(old)} occupations; Spearman rho={rho:.3f}; mean FO={mean_fo:.3f}; mean GPT-4 beta={mean_beta:.3f}")
    print(f"Wrote {result_path} and {report_path}")


if __name__ == "__main__":
    main()
