# AEDS 6400 Blog — Jin Liu

Blog posts for AEDS 6400 (Computational Methods for Economists), University of Pennsylvania, Fall 2026.

**Website:** https://liu118-oss.github.io/AEDS-6400-Blog/

## Posts

| # | Post | Folder | Language | Data |
|---|------|--------|----------|------|
| 1 | Eigenvalues and Eigenvectors: Why Systems Forget Where They Started | [`posts/week-01`](posts/week-01) | Python | None (simulated) |
| 2 | Which Tech Skills Should I Learn? Evidence from Arbeitnow Jobs | [`posts/week-02`](posts/week-02) | R (`rvest`) | Arbeitnow, scraped |
| 3 | Does Education Protect Workers from Unemployment? | [`posts/week-03`](posts/week-03) | R | IPUMS CPS |
| 4 | Why Lower New-Home Prices Have Not Restored Affordability | [`posts/week-04`](posts/week-04) | R | FRED |
| 5 | Why Lower Rent Does Not Always Mean Less Housing Pressure | [`posts/week-05`](posts/week-05) | R (`sf`) | Census ACS and county boundaries |

Each post folder (from Post 2 on) follows the same layout and has its own `README.md` with replication instructions:

```
posts/week-XX/
├── README.md          # question, data source, replication commands
├── code/              # numbered scripts, run in order
├── data/raw/          # downloaded or scraped inputs (or download instructions)
├── data/processed/    # cleaned, analysis-ready data written by the scripts
├── results/           # figures and tables written by the scripts
└── index.qmd          # the article; reads results/ rather than hard-coding numbers
```

## Reproducing the site

Requirements: [Quarto](https://quarto.org/), R (packages listed in each post's README), and Python 3 with `numpy`, `matplotlib`, and `jupyter` for Post 1.

```sh
# 1. Run a post's analysis scripts (see that post's README), e.g.
Rscript posts/week-04/code/01_analyze_housing.R
# 2. Render the website into docs/ (served by GitHub Pages)
quarto render
```

Other folders: `docs/` is the rendered website, `_freeze/` stores executed code output so the site re-renders without rerunning every analysis, and `_quarto.yml` configures the site.

Blog 5 includes [replication instructions](posts/week-05/README.md), county-level inputs, boundaries, and a downloadable replication ZIP. Official national source files can be downloaded without an API key; the saved county snapshot also supports offline analysis.
