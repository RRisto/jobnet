#!/usr/bin/env python3
"""Fit and cross-validate a small ridge model for ILO exposure score filling.

The code crosswalk supplies scores for 462 occupations. This model estimates
only rows that the crosswalk cannot cover. It is not a model of realized job
loss or future automation.
"""
from __future__ import annotations

import csv
import math
import re
import statistics
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = HERE / "data"
RESULTS = HERE / "results"
RIDGE_ALPHA = 10.0
FOLDS = 5


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def raw_features(row: dict[str, str]) -> tuple[list[str], list[float]]:
    words = tokens(row["project_occupation"])
    text_features = [f"w:{w}" for w in words] + [f"b:{a}_{b}" for a, b in zip(words, words[1:])]
    text_features += [f"class:{row['classification']}"]
    numeric = [
        float(row["frey_osborne_probability"]),
        float(row["median_edu"]),
        math.log1p(float(row["median_earnings"])),
        math.log1p(float(row["total_employment_2010"])),
    ]
    return text_features, numeric


def design(train_rows: list[dict[str, str]], predict_rows: list[dict[str, str]]) -> tuple[np.ndarray, np.ndarray]:
    train_parts = [raw_features(r) for r in train_rows]
    pred_parts = [raw_features(r) for r in predict_rows]
    vocab = sorted({feature for text, _ in train_parts for feature in text})
    index = {feature: i for i, feature in enumerate(vocab)}
    n_text = len(vocab)
    x_train = np.zeros((len(train_rows), n_text + 4), dtype=float)
    x_pred = np.zeros((len(predict_rows), n_text + 4), dtype=float)
    for matrix, parts in ((x_train, train_parts), (x_pred, pred_parts)):
        for i, (text, numeric) in enumerate(parts):
            for feature in text:
                if feature in index:
                    matrix[i, index[feature]] = 1.0
            matrix[i, n_text:] = numeric
    mean = x_train.mean(axis=0)
    scale = x_train.std(axis=0)
    scale[scale == 0] = 1.0
    return (x_train - mean) / scale, (x_pred - mean) / scale


def fit_predict(train: list[dict[str, str]], predict: list[dict[str, str]]) -> np.ndarray:
    y = np.array([float(r["ilo_2025_task_mean"]) for r in train])
    xt, xp = design(train, predict)
    ym = float(y.mean())
    centered = y - ym
    beta = np.linalg.solve(xt.T @ xt + RIDGE_ALPHA * np.eye(xt.shape[1]), xt.T @ centered)
    return np.clip(xp @ beta + ym, 0.0, 1.0)


def main() -> None:
    matched = rows(RESULTS / "ilo2025_project_occupation_scores.csv")
    legacy_by_id = {r["id"]: r for r in rows(ROOT / "data/ipums_variables.csv")}
    for r in matched:
        legacy = legacy_by_id[r["project_occ_id"]]
        r["classification"] = legacy["classification"]
        r["median_edu"] = legacy["median_edu"]
        r["median_earnings"] = legacy["median_earnings"]
        r["total_employment_2010"] = legacy["total_employment_2010"]
    train = [r for r in matched if r["ilo_2025_task_mean"]]
    missing = [r for r in matched if not r["ilo_2025_task_mean"]]

    order = np.random.default_rng(20261115).permutation(len(train))
    fold_ids = np.empty(len(train), dtype=int)
    fold_ids[order] = np.arange(len(train)) % FOLDS
    oof = np.zeros(len(train), dtype=float)
    y = np.array([float(r["ilo_2025_task_mean"]) for r in train])
    for fold in range(FOLDS):
        tr = [r for i, r in enumerate(train) if fold_ids[i] != fold]
        va_indices = [i for i in range(len(train)) if fold_ids[i] == fold]
        va = [train[i] for i in va_indices]
        oof[va_indices] = fit_predict(tr, va)
    baseline = np.array([float(np.mean([y[i] for i in range(len(y)) if fold_ids[i] != fold_ids[j]])) for j in range(len(y))])
    model_mae = float(np.mean(np.abs(oof - y)))
    baseline_mae = float(np.mean(np.abs(baseline - y)))
    model_rmse = float(np.sqrt(np.mean((oof - y) ** 2)))
    ysd = float(y.std())
    model_r2 = 1.0 - float(np.mean((oof - y) ** 2)) / float(np.mean((y - y.mean()) ** 2))
    preds = fit_predict(train, missing) if missing else np.array([])

    for row, pred in zip(missing, preds):
        row["ilo_2025_model_estimate"] = f"{pred:.8f}"
        row["ilo_2025_score_for_model"] = f"{pred:.8f}"
        row["score_input_method"] = "ridge_model_estimate_unmatched"
    for row in train:
        row["ilo_2025_model_estimate"] = ""
        row["ilo_2025_score_for_model"] = row["ilo_2025_task_mean"]
        row["score_input_method"] = row["match_status"]

    RESULTS.mkdir(parents=True, exist_ok=True)
    output = RESULTS / "ilo2025_model_inputs.csv"
    fields = list(matched[0]) + ["ilo_2025_model_estimate", "ilo_2025_score_for_model", "score_input_method"]
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(matched)
    report = [
        "# ILO exposure score model", "",
        "A ridge regression uses occupation title unigram/bigram indicators, project occupation group, legacy Frey–Osborne probability, median education, log median earnings, and log employment. The target is the code-crosswalked ILO 2025 task mean. Five-fold cross-validation is deterministic. The model estimates the two unmatched occupations only; it does not estimate job loss.", "",
        f"- Crosswalked training occupations: {len(train)}",
        f"- Unmatched occupations estimated: {len(missing)}",
        f"- Ridge alpha: {RIDGE_ALPHA}", f"- 5-fold out-of-fold MAE: {model_mae:.4f}",
        f"- 5-fold out-of-fold RMSE: {model_rmse:.4f}", f"- 5-fold out-of-fold R²: {model_r2:.4f}",
        f"- Fold-mean baseline MAE: {baseline_mae:.4f}",
        f"- Cross-validated MAE / target SD: {model_mae / ysd:.3f}", "",
        "The 5-fold metrics measure prediction across held-out occupations, including rows with ambiguous crosswalk means. They are a sanity check, not external validation. With only two unmatched occupations, predictions for them are extrapolations and should be flagged in any downstream interpretation.", "",
        "## Estimated unmatched occupations", ""]
    report.extend(f"- {r['project_occupation']}: {r['ilo_2025_model_estimate']}" for r in missing)
    (RESULTS / "ilo2025_model_summary.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"5-fold MAE={model_mae:.4f}, RMSE={model_rmse:.4f}, R2={model_r2:.4f}; baseline MAE={baseline_mae:.4f}")
    print(f"Estimated {len(missing)} unmatched occupations; wrote {output}")


if __name__ == "__main__":
    main()
