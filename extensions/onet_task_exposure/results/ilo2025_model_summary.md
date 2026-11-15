# ILO exposure score model

A ridge regression uses occupation title unigram/bigram indicators, project occupation group, legacy Frey–Osborne probability, median education, log median earnings, and log employment. The target is the code-crosswalked ILO 2025 task mean. Five-fold cross-validation is deterministic. The model estimates the two unmatched occupations only; it does not estimate job loss.

- Crosswalked training occupations: 462
- Unmatched occupations estimated: 2
- Ridge alpha: 10.0
- 5-fold out-of-fold MAE: 0.0772
- 5-fold out-of-fold RMSE: 0.0984
- 5-fold out-of-fold R²: 0.5431
- Fold-mean baseline MAE: 0.1236
- Cross-validated MAE / target SD: 0.530

The 5-fold metrics measure prediction across held-out occupations, including rows with ambiguous crosswalk means. They are a sanity check, not external validation. With only two unmatched occupations, predictions for them are extrapolations and should be flagged in any downstream interpretation.

## Estimated unmatched occupations

- physical scientists, all other: 0.37254799
- counter and rental clerks: 0.37692058
