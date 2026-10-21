# Blog Post 3: Unemployment by education in the IPUMS CPS

How does unemployment vary by education among U.S. adults ages 25–64, and does the gap change when the labor market weakens?

## Start here

Run all commands from the repository root (the folder containing `_quarto.yml`). There are two routes. Neither requires an API key.

- **Route A: rebuild the figures and webpage** from the included weighted aggregate data. No IPUMS account or new download is needed. This does not independently repeat the microdata calculations.
- **Route B: repeat the complete analysis** from an IPUMS CPS extract, then rebuild the figures and webpage. This requires an IPUMS account and the matching data and XML files.

## Requirements

Use R 4.1 or later and Quarto. Install packages once:

```sh
Rscript -e 'install.packages(c("ipumsr", "dplyr", "tidyr", "readr", "haven", "ggplot2", "scales", "knitr", "rmarkdown"))'
```

## Route A: included aggregate data

```sh
Rscript posts/week-03/code/02_plot_cps.R
quarto render posts/week-03/index.qmd
```

The plotting script reads the three CSVs in `data/processed/` and saves the three PNG figures and `results/headline_rates.csv`. Quarto reads those results to populate the article; numbers are not copied manually. The rendered page is `docs/posts/week-03/index.html`. Optional local preview:

```sh
python3 -m http.server 8767 --directory docs
```

Open http://127.0.0.1:8767/posts/week-03/ (or use another free port).

## Route B: full analysis from microdata

At [IPUMS CPS](https://cps.ipums.org/cps/), register/sign in and create an extract:

1. Select **Basic Monthly** samples for **April in every year from 2000 through 2025**, inclusive: 26 samples. Do not select ASEC.
2. Include `YEAR`, `MONTH`, `AGE`, `EDUC`, `LABFORCE`, `EMPSTAT`, and `WTFINL`. Additional automatically included identifiers are fine.
3. Keep the full sample; do not apply person-level case selections or sample-size reductions. The analysis script applies age and labor-force filters.
4. Choose rectangular person-level data in fixed-width format. Download both the `.dat.gz` file and its matching `.xml` DDI/codebook.
5. Put exactly one matching pair in `posts/week-03/data/raw/`. Keep the data compressed. Move any other extracts outside this folder before running.

```sh
Rscript posts/week-03/code/01_analyze_cps.R
quarto render posts/week-03/index.qmd
```

The analysis imports the files, validates required variables and sample coverage, computes weighted estimates, saves aggregate CSVs, and calls `02_plot_cps.R`. An error about missing files or samples must be resolved before treating the full analysis as reproduced.

The supplied XML records an extract production date of September 29, 2026; the article cites IPUMS CPS Version 13.0 (2025). Newly downloaded releases may contain revisions; identical selection settings do not guarantee byte-identical inputs. Use the same local extract for exact comparisons. Raw person-level data are intentionally excluded from Git; download them through your own account. See [IPUMS CPS terms](https://cps.ipums.org/cps/terms.shtml).

## Repository contents

| Location | Contents |
|---|---|
| `index.qmd` | Article, with results read from CSVs |
| `code/01_analyze_cps.R` | Import, definitions, weights, aggregates; calls plotting script |
| `code/02_plot_cps.R` | Regenerates all three figures from saved aggregates |
| `data/raw/` | Local IPUMS `.xml` and `.dat.gz`; excluded from Git |
| `data/processed/annual_unemployment.csv` | April rates by year and education, including counts and weighted totals |
| `data/processed/education_gaps.csv` | Rate differences relative to bachelor's degree or higher |
| `data/processed/unemployment_by_age_2025.csv` | April 2025 rates by age and education |
| `results/` | Three PNGs and headline estimates |

The public repository must include the scripts, aggregate CSVs, PNGs, headline CSV, article source and this README. Raw microdata are not needed for Route A. The two routes use the same plotting code.

## Definitions and interpretation

All estimates use April Basic Monthly samples, not annual averages. April supplies a comparable month each year and includes the abrupt pandemic disruption in April 2020. The sample includes the civilian labor force ages 25–64. `LABFORCE == 2` selects labor-force participants; `EMPSTAT` codes 20–22 identify unemployment. The rate within each group is `sum(WTFINL * unemployed) / sum(WTFINL)`. Education categories are less than high school, high school/GED, some college/associate degree, and bachelor's degree or higher.

The figures show associations, not causal effects of education. The project does not calculate standard errors. Full reruns should reproduce the aggregate counts, weighted rates and gaps; font or graphics-library versions can affect PNG appearance without changing the statistics.

## Data source

Flood, Sarah, Miriam King, Renae Rodgers, Steven Ruggles, J. Robert Warren, Daniel Backman, Etienne Breton, Grace Cooper, Julia A. Rivera Drew, Stephanie Richards, David Van Riper, and Kari C. W. Williams. 2025. *IPUMS CPS: Version 13.0* [dataset]. Minneapolis, MN: IPUMS. https://doi.org/10.18128/D030.V13.0.
