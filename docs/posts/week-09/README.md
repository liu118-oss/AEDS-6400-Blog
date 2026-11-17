# Blog Post 9: Predicting Stock Returns with Gradient Boosting

Open **index.html** for the finished illustrated post. It is self-contained and can be opened without an internet connection. **article.md** is the editable prose version; **index.qmd** is its Quarto source. Both are generated from results, so make persistent prose changes in `code/blog_template.qmd`; `code/render_report.py` fills its numeric placeholders from saved results.

## Main finding

The regularized model improves forecast error relative to the class specification, but essentially ties a historical-average forecast. Both corrected model portfolios outperform the passive benchmarks in this test; the revised model earns less than the original. This retrospective experiment does not establish a persistent investment edge.

## Project structure

```text
index.html / .md / .qmd  Finished post and editable versions
README.md                     Replication instructions
METHODS.md                    Detailed design, corrections and limitations
analysis_plan.md              Choices fixed before final test inspection
requirements-lock.txt         Exact Python package versions used
styles.css                    Report styling
reference/original_class_model.R  Unmodified supplied class script
code/
  download_data.py             Explicit, optional acquisition step
  analyze.py                   Features, validation, models, portfolios, figures
  audit.py                     Independent checks and class-code diagnostics
  render_report.py             Generates prose and tables from saved outputs
  run_analysis.sh              Rebuilds analysis and report offline
data/raw/
  prices.csv                   Frozen Yahoo Finance historical snapshot
  metadata.json                Universe, dates, retrieval time and checksum
results/
  figures/                     Three labeled PNG figures
  validation.csv               Every candidate and fold, including sample sizes
  predictions.csv              All daily test forecasts and realized labels
  predictive_metrics*.csv       Scheduled and overlapping-daily accuracy
  investment_metrics.csv       Performance at three cost assumptions
  portfolio_weights.csv        Holdings at each rebalance
  holding_period_returns.csv   Returns and turnover for every holding period
  daily_wealth.csv              Daily portfolio paths
  calendar_year_returns.csv    Returns by available calendar-year window
  stock_contributions.csv      Descriptive, non-compounded contribution sums
  *_table.md                   Generated presentation tables
  summary.json                 Selected model, sample counts and uncertainty
  class_*diagnostic*            Invalid original accounting, clearly separated
  *.json                       Saved fitted XGBoost models and summaries
  *verification.txt            Executed checks
```

## Replicate from the saved snapshot (recommended)

Tested with Python 3.14 on macOS arm64, XGBoost 3.4.1 and Quarto. The lock file records the remaining versions. A different XGBoost version, platform or data vintage may change forecasts. A supported Python 3.14 environment is recommended for these pinned versions.

From the project directory:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
PYTHON=.venv/bin/python sh code/run_analysis.sh
```

The installation step needs network access; the analysis itself uses saved data and is offline. Install Quarto separately if it is unavailable. `run_analysis.sh` points XGBoost to scikit-learn's bundled OpenMP library on macOS. If your installation does not bundle that library, install the standard OpenMP runtime for your platform (for example, `brew install libomp` on macOS).

To regenerate only the text and HTML from existing results:

```sh
.venv/bin/python code/render_report.py
quarto render index.qmd
```

The preparation environment is not committed; create `.venv` for a portable copy. Within this website repository, render with `quarto render posts/week-09/index.qmd` from the repository root; output is written under `docs/posts/week-09/`. The public article is https://liu118-oss.github.io/AEDS-6400-Blog/posts/week-09/.

## Download a new vintage (optional; changes the experiment)

The delivered snapshot is sufficient for replication. To refresh, first preserve or move `data/raw/prices.csv` and `data/raw/metadata.json`, then run:

```sh
.venv/bin/python code/download_data.py
```

The downloader refuses to overwrite an existing snapshot and fails if a stock has no data. It requests the same fixed 2022–2025 period, but later corporate-action adjustments or provider revisions can change historical values. Do not describe refreshed results as exact replication of this vintage.

## Design and provenance

The supplied R script is the source of the universe, original predictors and original stated hyperparameters. This project reimplements its model in Python rather than claiming an identical R rerun. Main comparisons correct label leakage and accounting for **both** models. The test window and eight-candidate validation grid were fixed before test scores were inspected; subsequent changes were accounting/precision verification, documentation and presentation, not model selection.

The separate `Full_Results` classroom spreadsheet is not stock-price training data and is not used here. We do not invent what the original in-class run earned.

## Rubric coverage

1. Question and motivation: opening paragraphs.
2. Clear explanation: class experiment and model-improvement sections.
3. Interpretation and takeaway: accuracy/investment distinction and concluding section.
4. Data and presentation: source documentation, three figures and a compact investment table; detailed tables remain in the results folder.
5. Repository organization: folders above and these replication instructions.
6. Reproducibility: fixed snapshot, checksum, seed, package lock, generated outputs and checks.
7. Original experiment and prediction difficulty: class-model explanation, code audit, and discussion.
8. Substantive improvement: redesigned predictors and pre-test selection of regularized XGBoost.
9. Out-of-sample evaluation: common 2024–2025 test, original model and historical-mean forecast.
10. Economic performance: aligned trading portfolios, SPY/equal-weight benchmarks, risk and cost sensitivity.

## Sources

- User-supplied class script: `reference/original_class_model.R`.
- Yahoo Finance historical data, accessed through yfinance; see `data/raw/metadata.json`.
- tidyquant source documentation: https://business-science.github.io/tidyquant/reference/tq_get.html
- XGBoost parameter documentation: https://xgboost.readthedocs.io/en/stable/parameter.html
- Fama (1970): https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1970.tb00518.x
- Bailey et al., *The Probability of Backtest Overfitting*: https://escholarship.org/uc/item/4w1110bb
