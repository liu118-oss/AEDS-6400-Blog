# Blog 7: Finding Work After College: How Do Majors Compare?

## Reproduce this post

From this folder, with Python 3.10+:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python code/01_get_data.py
python code/02_make_figures.py
```

The first script preserves included snapshots. No account or API key is needed. The second regenerates processed CSVs, metrics, filter counts and both interactive HTML charts. It requires no network access. Open the HTML files from results directly, or render the article from the repository root:

```bash
quarto render posts/week-07/index.qmd
quarto render index.qmd
python -m http.server 8767 --directory docs
```

Rendering requires Quarto, R and the R packages knitr/rmarkdown, as for earlier posts. Open http://127.0.0.1:8767/posts/week-07/. Plotly JavaScript is bundled locally in results/plotly.min.js; no backend or CDN is needed. Do not commit the virtual environment.

## Structure

- `index.qmd`: article, with numeric results read from results/metrics.csv.
- `code/`: download and analysis/visualization scripts.
- `data/raw/`: unmodified official CSV files and source metadata JSON.
- `data/processed/`: numeric major data and chronologically sorted monthly data.
- `results/`: interactive figures, local Plotly library, filter counts and article metrics.

## Source and release

Federal Reserve Bank of New York, *The Labor Market for Recent College Graduates*, https://nyfed.org/collegelabor.

The download script lists the exact URLs. Snapshot assembled October 21, 2026. Source metadata identifies major outcomes as 2024 data released February 4, 2026, and monthly unemployment through June 2026 released August 6, 2026. Major figures derive from ACS/IPUMS; monthly figures from CPS/IPUMS. The preserved metadata contains the original definitions and source notices.

This post reorganizes and visualizes those files; it is my analysis, not a New York Fed endorsement. Source terms: https://www.newyorkfed.org/privacy/termsofuse. Retain attribution and original source notices when sharing the data. Plotly's bundled JavaScript retains its license header.

To fetch a newer release intentionally, run `python code/01_get_data.py --refresh`. This changes the snapshot: rerun analysis and review dates, definitions and narrative before publishing. The article is written for the preserved release, not automatically updated future observations.

## Definitions and calculations

- All source figures exclude current students. Recent graduates are ages 22–27, bachelor's or higher. Young non-graduates are ages 22–27 without a bachelor's; all workers are 16–65.
- Unemployment: unemployed / labor force. Underemployment: employed graduates in occupations typically not requiring a degree / employed graduates. It does not measure field-of-study mismatch.
- Major wages: median annual wages of full-time bachelor's-only workers ages 22–27. Employment rates also include higher-degree holders, so denominators differ. Wages are the dollar figures in the 2024 major release; no additional inflation adjustment is applied.
- Monthly rates are source-seasonally-adjusted three-month moving averages. October 2025 is estimated by the source. June values in the article are not quarterly averages.
- The Overall row is removed from the 73 plotted majors and retained as the benchmark. It is not an unweighted average of majors.
- Strict comparisons use full precision: wage > 58000; unemployment < 4.211; underemployment > 39.35 for the contrast group. Only display values are rounded.
- The four filters yield 73, 27, 12 and 17 majors. Of the 12 in filter three, 11 also have underemployment < 39.35. Engineering Technologies is the exception.
- Filter four is independent, not a fourth cumulative restriction. Both menus share one state update. A highlighted major outside the filter is hidden and explained in the status message. Plot axes and color limits stay fixed.
- No causal estimates or composite ranking are calculated. The supplied files do not include sampling uncertainty.

## Interaction checks

Check all four counts, highlight Computer Science then apply higher pay/lower unemployment (outside-filter message), switch back to All (highlight returns), and repeat in the opposite order. Check trend menu, slider, legend, hovering and narrow-screen layout. The text explains the patterns even without interacting; processed CSVs provide a tabular alternative.
