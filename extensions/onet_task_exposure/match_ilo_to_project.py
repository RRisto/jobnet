#!/usr/bin/env python3
"""Match ILO 2025 ISCO-08 task exposure to this project's Census occupations.

The crosswalk chain is Census 2010 -> SOC 2010 -> ISCO-08. A project's
occupation with multiple ILO candidates receives their unweighted mean, with
candidate-level uncertainty retained in the output. This is a classification
crosswalk, not a learned prediction model.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from compare_ilo2025 import collect_occupations, pearson, ranks, read_csv  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy", type=Path, default=ROOT / "data/ipums_variables.csv")
    parser.add_argument("--census-soc", type=Path, default=HERE / "data/census2010_soc2010_xw.csv")
    parser.add_argument("--soc-isco", type=Path, default=HERE / "data/soc2010_isco2008.csv")
    parser.add_argument("--ilo-tree", type=Path, default=HERE / "data/ilo_2025_isco_exposure_tree.json")
    parser.add_argument("--output-dir", type=Path, default=HERE / "results")
    args = parser.parse_args()

    with args.ilo_tree.open(encoding="utf-8") as f:
        ilo = collect_occupations(json.load(f))
    census_soc = read_csv(args.census_soc)
    soc_isco = read_csv(args.soc_isco)
    legacy = read_csv(args.legacy)

    census_to_soc: dict[str, set[str]] = {}
    for row in census_soc:
        census_to_soc.setdefault(row["census2010"].zfill(4), set()).add(row["soc2010"])
    soc_to_isco: dict[str, set[str]] = {}
    for row in soc_isco:
        soc_to_isco.setdefault(row["soc2010"], set()).add(row["isco2008"].zfill(4))
    crosswalk_titles = {r["isco2008"].zfill(4): r["isco2008_title"] for r in soc_isco}

    results = []
    for occupation in legacy:
        census_code = occupation["acs_occ_code"].zfill(4)
        soc_codes = sorted(census_to_soc.get(census_code, set()))
        candidates = sorted({isco for soc in soc_codes for isco in soc_to_isco.get(soc, set()) if isco in ilo})
        scores = [ilo[code] for code in candidates]
        if candidates:
            values = [x["mean"] for x in scores]
            mean = statistics.fmean(values)
            sd_between = statistics.pstdev(values)
            risks = sorted({str(x["risk"]) for x in scores})
            match_status = "unique_code_crosswalk" if len(candidates) == 1 else "ambiguous_code_crosswalk_mean"
        else:
            mean, sd_between, risks = "", "", []
            match_status = "unmatched"
        results.append({
            "project_occ_id": occupation["id"],
            "project_occupation": occupation["label"],
            "census2010_code": census_code,
            "soc2010_candidates": ";".join(soc_codes),
            "isco08_candidates": ";".join(candidates),
            "isco08_candidate_titles": ";".join(crosswalk_titles.get(c, "") for c in candidates),
            "candidate_count": len(candidates),
            "match_status": match_status,
            "ilo_2025_task_mean": f"{mean:.8f}" if candidates else "",
            "ilo_2025_candidate_min": f"{min(x['mean'] for x in scores):.8f}" if candidates else "",
            "ilo_2025_candidate_max": f"{max(x['mean'] for x in scores):.8f}" if candidates else "",
            "ilo_2025_candidate_sd": f"{sd_between:.8f}" if candidates else "",
            "ilo_2025_gradient_candidates": ";".join(risks),
            "frey_osborne_probability": occupation.get("auto_prob_average", ""),
        })

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_csv = args.output_dir / "ilo2025_project_occupation_scores.csv"
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)

    counts = {status: sum(r["match_status"] == status for r in results) for status in sorted({r["match_status"] for r in results})}
    matched = [r for r in results if r["ilo_2025_task_mean"]]
    matched_fo = [float(r["frey_osborne_probability"]) for r in matched]
    matched_ilo = [float(r["ilo_2025_task_mean"]) for r in matched]
    unique = counts.get("unique_code_crosswalk", 0)
    ambiguous = counts.get("ambiguous_code_crosswalk_mean", 0)
    report = [
        "# ILO 2025 scores matched to project occupations", "",
        "Scores are equal-weight means of the released ILO task-level GenAI exposure values. The crosswalk chain is Census 2010 occupation → SOC 2010 → ISCO-08. A one-to-many match uses the unweighted mean of eligible ILO occupations; candidate codes, score range, and between-candidate SD are retained. This score is technical GenAI task exposure, not a probability of job loss.", "",
        f"- Project occupations: {len(results)}", f"- Matched: {len(matched)} ({len(matched)/len(results):.1%})",
        f"- Unique code matches: {unique}", f"- Ambiguous code matches averaged: {ambiguous}",
        f"- Unmatched: {counts.get('unmatched', 0)}", f"- Mean ILO score across matched project occupations: {statistics.fmean(float(r['ilo_2025_task_mean']) for r in matched):.3f}",
        f"- Mean Frey–Osborne probability in the same matched sample: {statistics.fmean(matched_fo):.3f}",
        f"- Spearman rank correlation, Frey–Osborne vs ILO task mean: {pearson(ranks(matched_fo), ranks(matched_ilo)):.3f}",
        "", "## Crosswalk provenance", "",
        "The Census-to-SOC and SOC-to-ISCO mapping tables are the coding-systems repository mirror stored under `data/`; the latter is based on BLS SOC/ISCO crosswalk material. See [BLS SOC crosswalks](https://www.bls.gov/soc/soccrosswalks.htm) and [IPUMS OCC to OCCSOC crosswalk documentation](https://usa.ipums.org/usa/volii/occtooccsoc18.shtml). The ILO source dataset and attribution are documented in `data/ILO_2025_ATTRIBUTION.txt`.", "",
        "## Match counts", "", "| Match status | Occupations |", "|---|---:|"]
    report.extend(f"| {status} | {count} |" for status, count in counts.items())
    report += ["", f"Detailed rows: `{out_csv.name}`.", ""]
    out_md = args.output_dir / "ilo2025_project_occupation_summary.md"
    out_md.write_text("\n".join(report), encoding="utf-8")
    print(f"Matched {len(matched)}/{len(results)} occupations ({unique} unique, {ambiguous} ambiguous, {counts.get('unmatched', 0)} unmatched)")
    print(f"Wrote {out_csv} and {out_md}")


if __name__ == "__main__":
    main()
