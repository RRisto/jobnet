# Frey–Osborne vs GPT-4 task exposure: exact-title comparison

This is a descriptive comparison on normalized exact occupation-title matches only. The legacy score is Frey–Osborne computerisation probability; GPT-4 beta is the share of O*NET tasks classified as directly exposed plus half-weighted tool-enabled exposure (2023-era GPT-4 assessment). These are different constructs and should not be interpreted as interchangeable risk probabilities or job-loss forecasts.

- Legacy occupations: 464
- Published O*NET occupations: 923
- Exact normalized-title matches: 284 (61.2% of legacy occupations)
- Unmatched legacy occupations: 180
- Ambiguous exact-title matches excluded: 0
- Matched sample mean Frey–Osborne probability: 0.550
- Matched sample mean GPT-4 beta exposure: 0.349
- Matched sample mean human beta exposure: 0.291
- Spearman rank correlation, Frey–Osborne vs GPT-4 beta: -0.114

## Largest rank falls among the 10 highest Frey–Osborne scores

| Occupation | FO rank | GPT-4 beta rank | GPT-4 beta |
|---|---:|---:|---:|
| parts salespersons | 10 | 144 | 0.343 |
| photographic process workers and processing machine operators | 8 | 137 | 0.380 |
| cargo and freight agents | 6 | 99 | 0.470 |
| new accounts clerks | 5 | 53 | 0.560 |
| library technicians | 3 | 48 | 0.567 |

## Largest rank rises among the 10 highest Frey–Osborne scores

| Occupation | FO rank | GPT-4 beta rank | GPT-4 beta |
|---|---:|---:|---:|
| data entry keyers | 7 | 6 | 0.893 |

The rank correlation is Spearman's rho computed within this exact-title matched subset. Occupation matches that differ in naming or classification are intentionally left out pending a reviewed crosswalk.
