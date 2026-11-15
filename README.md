# Code and data for article "Occupational mobility and Automation: A data-driven network model"
## authors: R. Maria del Rio-Chanona, Penny Mealy, Mariano Beguerisse-Díaz, François Lafond, and J. Doyne Farmer

### Interactive Python setup (uv + Jupyter)

From the project root, run:

```powershell
uv sync --cache-dir .uv-cache
uv run --cache-dir .uv-cache jupyter lab notebooks/01_understand_model.ipynb
```

The project uses Python 3.12 in `.venv`; uv installs the required packages.
The starter notebook explains the numerical approximation with a small
three-occupation example, plots a demand shock against a baseline, and loads
the paper's data. Use **Run All Cells** or Shift+Enter to work through it.
The example is educational; it does not reproduce a calibrated paper figure.
The Julia simulation requires a separate Julia installation.

For VS Code, select `.venv/Scripts/python.exe` as the notebook kernel.
The dependency versions are recorded in `uv.lock` for reproducibility.


### Data
The adjacency matrix of the occupational mobility network is in the data folder. Please cite (Mealy et al. 2018) when using the occupational mobility network, where the construction methodology is explained. <br>
* "occupational_mobility_network.csv" <br>
The characteristics of occupations (e.g. employment, median wage, automation probability, etc.) are in the csv files <br>
 * "ipums_variables.csv" <br>
 * "ipums_lab_mSML_manual.csv"<br>
 * "ipums_employment_2016.csv"<br>
Randomizations or retrained version of the occupational mobility network are also in the data folder.

### Code
The code uses Python 3 (Version 3.8.3) and Julia (Version 1.0.4)<br>
The main functions of the code are in files labornet.py (for solving approximation) and AgentSimulation.jl (for running the agent-based model).<br>
Running the model (approximations). Most of the results presented in the paper originate from the approximations, which one can run using the file "RunNumericalShock.py" for automation shocks, "RunNumericalBeveridgeCurve.py" for the Beveridge curve, and "Calibrate_parameters_withBCurve_exhaustive" for calibration. The results from these files are saved in csv format in folder "results/csv".<br>
Running the agent-based model (simulations). To run the agent based model use file "RunAgentSimulation.jl"<br>

Plots. Once the model has run, the following files reproduce the main plots of the main text. <br>
* "Plotfiles_BeveridgeCurve.py"<br>
* "Plotfiles_aggregate_u_ltu_vs_sim.py"<br>
* "Plotfiles_long-term_unemployment.py"<br>
* "Plotfiles_network_effects_wage.py"<br>

### Results
Folder in which results are saved. The csv file contains the results of the numerical approximations, which we use for most plots. The simulations folder has the results of different runs on the agent-based model.


### References
del Rio-Chanona RM, MealyP, Beguerisse-Díaz M, Lafond F, Farmer JD. 2021 Occupational mobility and automation:a data-driven network model.  *J. R. Soc.Interface* 17: 20200898. https://doi.org/10.1098/rsif.2020.0898 <br>

Mealy P, del Rio-Chanona RM, Farmer JD. 2018 What you do at work matters: new lenses onlabour. *SSRN 3143064*. See SSRN:https://ssrn.com/abstract=3143064. (doi:10.2139/ssrn.3143064)




## ILO 2025 occupation exposure extension

The separate `extensions/onet_task_exposure/` directory adds an ILO 2025 task-exposure pipeline, occupation matching, comparisons with the paper's Frey–Osborne scores, and scenario simulations. It keeps new code, source data, and generated CSV results separate from the original authors' code and data. See [`extensions/onet_task_exposure/README.md`](extensions/onet_task_exposure/README.md) for setup and attribution.

The notebook `notebooks/02_ilo2025_exposure_analysis.ipynb` contains the interactive comparison. Run its cells from top to bottom; chart HTML files are generated under the extension results folder. Cached notebook outputs and the original `results/` simulation outputs are omitted from version control because they are reproducible and add substantial size. The original paper PDF is not bundled; see [the article DOI](https://doi.org/10.1098/rsif.2020.0898).

The paper is published under CC BY 4.0. Individual source datasets retain their own attribution and terms; consult the extension's attribution files and the cited sources before reusing data. No blanket license is declared for this combined repository.
