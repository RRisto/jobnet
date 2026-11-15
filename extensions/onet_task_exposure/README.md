# O*NET task exposure extension

This is an independent research extension. It does not edit or replace the article authors' code, source data, or published Frey–Osborne scores.

## Purpose and limits

The pipeline prepares occupation task statements for scoring, then aggregates supplied task-level exposure scores into occupation-level measures. It does **not** automatically decide whether a task can be automated. Scores must come from a documented assessment method (for example, a published task score, a transparent human rubric, or a separately documented model assessment). Exposure is not a forecast of job loss.

## Reproduced published comparison

The extension also includes occupation-level replication data from Eloundou et al., **“GPTs are GPTs”** (2023/2024), stored as `data/gpts_are_gpts_occ_level.csv` under its MIT license. The GPT-4 `beta` measure is the share of O*NET tasks labeled directly exposed plus half-weighted tool-enabled exposure. It measures potential task-time savings, not automation probability or job loss.

Run the comparison against the article's Frey–Osborne values:

```powershell
python extensions/onet_task_exposure/compare_published.py
```

This uses normalized exact occupation-title matches only, avoiding an assumed equivalence between unlike Census and O*NET codes. It writes a matched occupation CSV and a summary with means, rank correlation, and examples of ranking changes into `results/`. Unmatched occupations are excluded pending a reviewed crosswalk.

## Newer ILO 2025 comparison

The extension also includes the public task-level score tree from Gmyrek et al.'s ILO 2025 GenAI exposure index and a separate comparison script:

```powershell
python extensions/onet_task_exposure/compare_ilo2025.py
```

This extracts 4-digit ISCO-08 occupation tasks, calculates the equal-weight task-score mean and population standard deviation, retains the ILO gradient label, and makes an exact-title comparison. For broader project coverage use the code-based match below; the title-only output is retained as a conservative comparison.

### Match ILO scores to project occupations

```powershell
python extensions/onet_task_exposure/match_ilo_to_project.py
python extensions/onet_task_exposure/train_exposure_model.py
python extensions/onet_task_exposure/run_ilo_model_scenario.py
```

The crosswalk chain is Census 2010 occupation code → SOC 2010 → ISCO-08. The 2025 ILO task means matched 462 of 464 project occupations: 304 unique code matches, 158 one-to-many matches averaged with candidate codes/range/spread retained, and 2 unmatched. Outputs remain in this extension's `results/` directory. The two unmatched scores are filled by a ridge regression using occupation-title unigram/bigram indicators, occupation group, and the existing education, earnings, employment, and Frey–Osborne variables. Its five-fold cross-validation is reported in `results/ilo2025_model_summary.md`; these are estimates of ILO exposure, not measured scores.

The final command runs the original Python model's labor update functions and parameters on both the occupational-mobility and complete networks for Frey–Osborne and ILO exposure inputs. It tracks unemployment and long-term unemployment with a compact cohort recurrence. Its outputs and limitations are in `results/ilo2025_simulation_summary.md`. The ILO score is a technical GenAI task-exposure measure; treating it as a demand-reduction fraction in the paper model is a scenario assumption, not a direct forecast of job loss.

The interactive notebook `notebooks/02_ilo2025_exposure_analysis.ipynb` reproduces the original notebook's occupation-network view, high/low exposure rankings, occupation-level unemployment comparisons, network effects by earnings, and potential-trap exploration using ILO scores alongside Frey–Osborne. Its Plotly charts are saved as standalone HTML files under `results/interactive/`.

The Census/SOC and SOC/ISCO crosswalk tables are stored under `data/` and mirrored from [danielruss/codingsystems](https://github.com/danielruss/codingsystems). The corresponding official reference is the [BLS SOC crosswalk page](https://www.bls.gov/soc/soccrosswalks.htm); IPUMS explains its Census occupation to OCCSOC mappings [here](https://usa.ipums.org/usa/volii/occtooccsoc18.shtml). Match counts, alternatives, and score ranges are included in `results/ilo2025_project_occupation_scores.csv`. The ILO source dataset and attribution are documented in `data/ILO_2025_ATTRIBUTION.txt`.

## Inputs

Download the O*NET database's task statements from the [O*NET database page](https://www.onetcenter.org/database.html). The task file must contain `O*NET-SOC Code` and `Task` columns (the standard O*NET Task Statements export does).

Create a project-to-O*NET crosswalk CSV with:

| Column | Meaning |
|---|---|
| `project_occ_id` | Occupation `id` from `data/ipums_variables.csv` |
| `onet_soc_code` | Matching O*NET-SOC occupation code |
| `match_type` | `exact`, `approximate`, or `manual`; document judgment in `match_notes` |
| `match_notes` | Optional explanation |

The legacy project's occupation codes are IPUMS codes, not O*NET-SOC codes, so this mapping is an explicit input and should be reviewed. Do not assume codes match just because their numbers look similar.

## Steps

1. Prepare a scoring sheet by joining task statements, an reviewed crosswalk, and the project's occupation names:

   ```powershell
   python extensions/onet_task_exposure/pipeline.py prepare `
     --onet-tasks path/to/Task Statements.csv `
     --crosswalk extensions/onet_task_exposure/data/occupation_crosswalk.csv `
     --occupations data/ipums_variables.csv `
     --output extensions/onet_task_exposure/data/tasks_to_score.csv
   ```

2. Fill `exposure_score` for each task with a value from 0 to 1, where 0 means no assessed exposure and 1 means the task could be fully performed by the assessed technology. Record `assessment_source` and optionally provide `task_weight` (such as O*NET task importance). Use one consistent scoring protocol and technology definition.

3. Aggregate scores:

   ```powershell
   python extensions/onet_task_exposure/pipeline.py aggregate `
     --scored-tasks extensions/onet_task_exposure/data/tasks_to_score.csv `
     --output extensions/onet_task_exposure/results/occupation_exposure.csv `
     --legacy data/ipums_variables.csv
   ```

The output reports the unweighted task mean, weighted mean when weights are present, task count, and score coverage. It includes the legacy Frey–Osborne value for side-by-side analysis only; it does not overwrite it. Occupations without a complete mapping or scored task set are omitted and reported to stderr.

## Provenance

O*NET task descriptions are maintained by the U.S. Department of Labor's O*NET program. Cite O*NET and the selected scoring source/method in any resulting analysis. Store downloaded and derived files only under this extension's `data/` and `results/` directories.

The included GPT-4 comparison data come from [OpenAI's public GPTs-are-GPTs replication repository](https://github.com/openai/GPTs-are-GPTs), `data/occ_level.csv`, distributed under the MIT license included beside the file. Cite Eloundou, Manning, Mishkin, and Rock, “GPTs are GPTs: Labor market impact potential of LLMs,” *Science* 384 (2024).

ILO 2025 task data are from the [authors' public repository](https://github.com/pgmyrek/2025_GenAI_scores_ISCO08) and are redistributed/adapted under CC BY 4.0 with attribution.

The included comparison data come from [OpenAI's public GPTs-are-GPTs replication repository](https://github.com/openai/GPTs-are-GPTs), `data/occ_level.csv`, distributed under the MIT license included beside the file. Cite Eloundou, Manning, Mishkin, and Rock, “GPTs are GPTs: Labor market impact potential of LLMs,” *Science* 384 (2024).
