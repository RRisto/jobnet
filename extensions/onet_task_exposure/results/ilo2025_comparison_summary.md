# ILO 2025 GenAI task exposure comparison

The ILO 2025 score is the equal-weight mean of the released task-level ISCO-08 scores for each occupation. It is a GenAI technical exposure measure, not a job-loss probability. The source index classifies occupations using task-score mean and variability; this report preserves its category labels and also reports the task mean. Population SD is calculated from released task scores for descriptive purposes.

- Project occupations: 464
- ILO ISCO-08 occupations extracted: 427
- Exact normalized-title matches: 24 (5.2% of project occupations)
- Matched occupations with GPT-4 beta also available: 16
- Ambiguous title matches excluded: 0
- Matched-sample mean Frey–Osborne probability: 0.358
- Matched-sample mean ILO 2025 task exposure: 0.291
- Spearman rank correlation, Frey–Osborne vs ILO 2025 mean: -0.330
- Mean GPT-4 beta for those 16 occupations: 0.310
- Spearman rank correlation, GPT-4 beta vs ILO 2025 mean: 0.797

## Highest ILO 2025 task means in the matched sample

| Occupation | ILO task mean | ILO gradient | FO probability | GPT-4 beta |
|---|---:|---|---:|---:|
| financial analysts | 0.618 | Exposed: Gradient 4 | 0.230 |  |
| economists | 0.555 | Exposed: Gradient 3 | 0.430 | 0.500 |
| medical records and health information technicians | 0.516 | Exposed: Gradient 3 | 0.910 |  |
| psychologists | 0.391 | Exposed: Gradient 1 | 0.007 |  |
| photographers | 0.390 | Exposed: Gradient 1 | 0.021 | 0.385 |
| environmental engineers | 0.381 | Minimal Exposure | 0.018 | 0.556 |
| chemical engineers | 0.352 | Minimal Exposure | 0.017 | 0.462 |
| medical assistants | 0.346 | Exposed: Gradient 1 | 0.300 | 0.359 |
| construction managers | 0.338 | Minimal Exposure | 0.071 | 0.444 |
| pharmacists | 0.332 | Minimal Exposure | 0.012 | 0.429 |

Matching uses normalized exact occupation titles only. Unmatched occupations are excluded pending an explicit crosswalk between the project’s IPUMS/Census classification and ISCO-08.
