# ILO 2025 scores matched to project occupations

Scores are equal-weight means of the released ILO task-level GenAI exposure values. The crosswalk chain is Census 2010 occupation → SOC 2010 → ISCO-08. A one-to-many match uses the unweighted mean of eligible ILO occupations; candidate codes, score range, and between-candidate SD are retained. This score is technical GenAI task exposure, not a probability of job loss.

- Project occupations: 464
- Matched: 462 (99.6%)
- Unique code matches: 304
- Ambiguous code matches averaged: 158
- Unmatched: 2
- Mean ILO score across matched project occupations: 0.304
- Mean Frey–Osborne probability in the same matched sample: 0.528
- Spearman rank correlation, Frey–Osborne vs ILO task mean: -0.093

## Crosswalk provenance

The Census-to-SOC and SOC-to-ISCO mapping tables are the coding-systems repository mirror stored under `data/`; the latter is based on BLS SOC/ISCO crosswalk material. See [BLS SOC crosswalks](https://www.bls.gov/soc/soccrosswalks.htm) and [IPUMS OCC to OCCSOC crosswalk documentation](https://usa.ipums.org/usa/volii/occtooccsoc18.shtml). The ILO source dataset and attribution are documented in `data/ILO_2025_ATTRIBUTION.txt`.

## Match counts

| Match status | Occupations |
|---|---:|
| ambiguous_code_crosswalk_mean | 158 |
| unique_code_crosswalk | 304 |
| unmatched | 2 |

Detailed rows: `ilo2025_project_occupation_scores.csv`.
