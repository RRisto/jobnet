# Simulation using ILO 2025 exposure inputs

This reruns the project's Python labor model on both the occupational mobility network and the complete network, with Frey–Osborne and matched ILO 2025 exposure vectors. Model parameters, initial employment, shock start, and 30-year duration are held fixed. For ILO, 462 inputs are crosswalk means and two are ridge estimates. Treating ILO task exposure as a demand-reduction fraction is a scenario assumption, not a forecast.

The transition uses time steps 100–330 and baseline 25–74. Long-term unemployment is tracked with the exact job-spell recurrence using three short-duration buckets plus a cumulative duration-3-and-over bucket; this avoids allocating the original 600×600×464 spell array.

Across the 464 inputs, mean Frey–Osborne score is 0.529 and mean ILO exposure score is 0.304; their Spearman rank correlation is -0.091. These are different constructs, so this is a comparison of scenario inputs rather than a validation test.

| Scenario | Network | Initial u | Transition u | Change (pp) | Initial LTU | Transition LTU |
|---|---|---:|---:|---:|---:|---:|
| Frey-Osborne | occupational | 5.233% | 5.485% | +0.251 | 2.082% | 2.198% |
| Frey-Osborne | complete | 4.103% | 4.219% | +0.115 | 1.039% | 1.017% |
| ILO 2025 matched + model-filled | occupational | 5.233% | 5.330% | +0.096 | 2.082% | 2.163% |
| ILO 2025 matched + model-filled | complete | 4.103% | 4.115% | +0.011 | 1.039% | 1.039% |

Detailed occupation outcomes: `ilo2025_vs_frey_osborne_simulation_by_occupation.csv`. Four time series are saved as `timeseries_{frey_osborne,ilo_2025}_{occupational,complete}.csv`.
