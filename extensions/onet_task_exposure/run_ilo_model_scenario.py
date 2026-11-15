#!/usr/bin/env python3
"""Run FO and ILO exposure scenarios on occupational and complete networks.

Uses the paper's labor update function and parameters. Long-term unemployment
is tracked exactly with short-duration cohorts plus a cumulative long-term
cohort, avoiding allocation of the full job-spell cube.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "code"))
import labornet as lbn  # noqa: E402


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def run_one(p: np.ndarray, employment0: np.ndarray, network: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    delta_u, delta_v = 0.01600001, 0.01200001
    gamma_u = gamma_v = 10 * delta_u
    sim_steps, shock_start = 600, 100
    shock_years = 30
    shock_duration = shock_years * 52 / 6.75
    unemployment0 = delta_u * employment0
    vacancies0 = delta_v * employment0
    demand0 = employment0 + unemployment0
    demand_final = lbn.labor_restructure(demand0, p)
    half_life, rate = lbn.calibrate_sigmoid(shock_duration)
    employment, unemployment, vacancies = employment0.copy(), unemployment0.copy(), vacancies0.copy()
    e_path = np.zeros((sim_steps, len(p)))
    u_path = np.zeros_like(e_path)
    v_path = np.zeros_like(e_path)
    d_path = np.zeros_like(e_path)
    ltu_path = np.zeros_like(e_path)
    # Exact aggregation of job-spell buckets for tau=3: retain durations 0, 1,
    # and 2 separately, and aggregate all durations >=3 into longterm.
    spell0 = np.zeros(len(p))
    spell1 = np.zeros(len(p))
    spell2 = np.zeros(len(p))
    longterm = np.zeros(len(p))
    e_path[0], u_path[0], v_path[0], d_path[0] = employment, unemployment, vacancies, demand0
    for t in range(1, sim_steps):
        demand = lbn.target_demand_automation(t, demand0, demand_final, shock_start, rate, half_life)
        unemployment_previous = unemployment.copy()
        unemployment, vacancies, employment, separated, exported = lbn.fire_and_hire_workers(
            delta_u, delta_v, gamma_u, gamma_v, employment, unemployment,
            vacancies, demand, network, lbn.matching_probability,
        )
        survival = 1 - exported / unemployment_previous
        longterm = (longterm + spell2) * survival
        spell2, spell1, spell0 = spell1 * survival, spell0 * survival, separated
        e_path[t], u_path[t], v_path[t], d_path[t] = employment, unemployment, vacancies, demand
        ltu_path[t] = longterm
    return e_path, u_path, v_path, d_path, ltu_path


def rate(e: np.ndarray, u: np.ndarray, start: int, end: int) -> float:
    return float(100 * u[start:end].sum() / (e[start:end] + u[start:end]).sum())


def occupation_rate(e: np.ndarray, u: np.ndarray, start: int, end: int) -> np.ndarray:
    return 100 * u[start:end].sum(axis=0) / (e[start:end] + u[start:end]).sum(axis=0)


def main() -> None:
    score_rows = read_rows(HERE / "results/ilo2025_model_inputs.csv")
    labels = [r["project_occupation"] for r in score_rows]
    fo = np.array([float(r["frey_osborne_probability"]) for r in score_rows])
    ilo = np.array([float(r["ilo_2025_score_for_model"]) for r in score_rows])
    exposure_rho = float(spearmanr(fo, ilo).statistic)
    emp_df = pd.read_csv(ROOT / "data/ipums_employment_2016.csv")
    employment = emp_df["IPUMS_CPS_av_monthly_employment_whole_period"].to_numpy(dtype=float)
    matrix_omn = np.genfromtxt(ROOT / "data/occupational_mobility_network.csv", delimiter=",")
    matrix_complete = np.ones_like(matrix_omn) / len(labels)
    if len(labels) != len(employment) or matrix_omn.shape != (len(labels), len(labels)):
        raise ValueError(f"dimension mismatch: scores={len(labels)}, employment={len(employment)}, network={matrix_omn.shape}")

    outdir = HERE / "results"
    summaries = []
    aggregate_stats = []
    scenario_inputs = (("Frey-Osborne", fo), ("ILO 2025 matched + model-filled", ilo))
    networks = (("occupational", matrix_omn), ("complete", matrix_complete))
    for name, exposure in scenario_inputs:
        for network_name, network in networks:
            e, u, v, demand, ltu = run_one(exposure, employment, network)
            base, transition = rate(e, u, 25, 75), rate(e, u, 100, 331)
            ltu_base, ltu_transition = rate(e, ltu, 25, 75), rate(e, ltu, 100, 331)
            aggregate_stats.append((name, network_name, base, transition, ltu_base, ltu_transition))
            u_base, u_transition = occupation_rate(e, u, 25, 75), occupation_rate(e, u, 100, 331)
            l_base, l_transition = occupation_rate(e, ltu, 25, 75), occupation_rate(e, ltu, 100, 331)
            u_pp, l_pp = u_transition-u_base, l_transition-l_base
            u_relative = np.divide(100*u_pp, u_base, out=np.full_like(u_pp,np.nan), where=u_base!=0)
            l_relative = np.divide(100*l_pp, l_base, out=np.full_like(l_pp,np.nan), where=l_base!=0)
            for i, row in enumerate(score_rows):
                summaries.append({
                    "project_occ_id": row["project_occ_id"], "occupation": labels[i],
                    "scenario": name, "network": network_name, "exposure_input": exposure[i],
                    "ilo_match_method": row["score_input_method"],
                    "unemployment_rate_initial_pct": u_base[i],
                    "unemployment_rate_transition_pct": u_transition[i],
                    "unemployment_change_percentage_points": u_pp[i],
                    "unemployment_rate_change_relative_pct": u_relative[i],
                    "ltu_rate_initial_pct": l_base[i], "ltu_rate_transition_pct": l_transition[i],
                    "ltu_change_percentage_points": l_pp[i],
                    "ltu_rate_change_relative_pct": l_relative[i],
                    "employment_initial": e[25:75, i].mean(),
                    "employment_transition": e[100:331, i].mean(),
                    "target_demand_initial": demand[25:75, i].mean(),
                    "target_demand_transition": demand[100:331, i].mean(),
                })
            aggregate = pd.DataFrame({
                "time_step": np.arange(len(e)), "employment_total": e.sum(axis=1),
                "unemployment_total": u.sum(axis=1), "longterm_unemployment_total": ltu.sum(axis=1),
                "unemployment_rate_pct": 100*u.sum(axis=1)/(e[0].sum()+u[0].sum()),
                "vacancy_rate_pct": 100*v.sum(axis=1)/(v.sum(axis=1)+e.sum(axis=1)),
                "longterm_unemployment_rate_pct": 100*ltu.sum(axis=1)/(e.sum(axis=1)+u.sum(axis=1)),
                "target_demand_total": demand.sum(axis=1),
            })
            suffix = "frey_osborne" if name == "Frey-Osborne" else "ilo_2025"
            aggregate.to_csv(outdir / f"timeseries_{suffix}_{network_name}.csv", index=False)
            print(f"{name} / {network_name}: unemployment {base:.3f}% to {transition:.3f}% ({transition-base:+.3f} pp); long-term {ltu_base:.3f}% to {ltu_transition:.3f}%")

    pd.DataFrame(summaries).to_csv(outdir / "ilo2025_vs_frey_osborne_simulation_by_occupation.csv", index=False)
    report = [
        "# Simulation using ILO 2025 exposure inputs", "",
        "This reruns the project's Python labor model on both the occupational mobility network and the complete network, with Frey–Osborne and matched ILO 2025 exposure vectors. Model parameters, initial employment, shock start, and 30-year duration are held fixed. For ILO, 462 inputs are crosswalk means and two are ridge estimates. Treating ILO task exposure as a demand-reduction fraction is a scenario assumption, not a forecast.", "",
        "The transition uses time steps 100–330 and baseline 25–74. Long-term unemployment is tracked with the exact job-spell recurrence using three short-duration buckets plus a cumulative duration-3-and-over bucket; this avoids allocating the original 600×600×464 spell array.", "",
        f"Across the 464 inputs, mean Frey–Osborne score is {fo.mean():.3f} and mean ILO exposure score is {ilo.mean():.3f}; their Spearman rank correlation is {exposure_rho:.3f}. These are different constructs, so this is a comparison of scenario inputs rather than a validation test.", "",
        "| Scenario | Network | Initial u | Transition u | Change (pp) | Initial LTU | Transition LTU |", "|---|---|---:|---:|---:|---:|---:|"]
    for scenario, net, b, tr, lb, lt in aggregate_stats:
        report.append(f"| {scenario} | {net} | {b:.3f}% | {tr:.3f}% | {tr-b:+.3f} | {lb:.3f}% | {lt:.3f}% |")
    report += ["", "Detailed occupation outcomes: `ilo2025_vs_frey_osborne_simulation_by_occupation.csv`. Four time series are saved as `timeseries_{frey_osborne,ilo_2025}_{occupational,complete}.csv`.", ""]
    (outdir / "ilo2025_simulation_summary.md").write_text("\n".join(report), encoding="utf-8")
    print(f"Wrote occupation outcomes to {outdir / 'ilo2025_vs_frey_osborne_simulation_by_occupation.csv'}")


if __name__ == "__main__":
    main()
