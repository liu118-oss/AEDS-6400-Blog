# Blog 6 — Does One Year of Income Tell the Whole Story?

A reproducible Python/SQLite tutorial using public NLSY79 mothers and Child/Young Adult earnings. Article: `index.qmd`. All four regressions are descriptive, unweighted estimates of **mother–child wage-earnings elasticity**, not national family-income IGE estimates.

## Reproduce the published numbers and figures

Start in `posts/week-06` after cloning the repository. Python 3.11 or newer is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python code/analyze.py
python code/plot.py
```

On Windows, activate with `.venv\Scripts\activate`. No API key, private folder path, original multi-GB files, R, or Quarto is needed for these analysis commands. The compact extracts **contain real public observations**, not simulated data. All matching, grouping and averaging run in SQLite from Python. The generated database is disposable and is rebuilt on every run.

To render the article, additionally install Quarto, R, and the R packages `knitr` and `rmarkdown`. From the repository root:

```bash
quarto render posts/week-06/index.qmd
```

The article reads numeric results from saved CSVs. The Python scripts save both PNG figures and result tables; no coefficients are copied manually into the prose.

## Files

- `code/extract_inputs.py`: optional streamed extraction from the original wide CSVs.
- `code/analyze.py`: inflation adjustment, SQLite database, SQL matching/averaging, regressions, cluster uncertainty, and checks.
- `code/plot.py`: the two figures, reading `results/estimates.csv`.
- `data/mother_selected.csv`, `child_selected.csv`: compact extracts of official public variables.
- `data/*_variables.csv`: reference-number mapping for earnings and interview years.
- `data/*.NLSY79`, `data/*.NLSCYA`: small NLS Investigator tagsets, including ID and birth-year variables.
- `data/cpi_*.json`: original BLS API responses, with twelve monthly CPI-U observations per year.
- `data/cpi_annual.csv`: annual averages generated from those responses.
- `data/source_manifest.json`: source filenames, byte sizes, selected columns, extract hashes and official download URLs.
- `data/analysis.sqlite`, `data/matched_*.csv`: generated intermediates, excluded from Git.
- `results/`: coefficients and intervals, paired differences, sample flow, validation checks and figures.

## Recreate the compact extracts from official originals (optional)

The official [BLS access page](https://www.bls.gov/nls/getting-started/accessing-data.htm) provides these packaged files:

- [NLSY79, 1979–2018](https://www.bls.gov/nls/getting-started/nlsy79_all_1979-2018.zip)
- [Child/Young Adult, 1979–2018](https://www.bls.gov/nls/getting-started/nlscya_all_1979-2018.zip)

These are the 1979–2018 packages supplied for this project, not the latest survey release. Local files carry 2021 timestamps; this is not treated as a verified publication date. Unzip them to any directory, retaining the named subdirectories, then run:

```bash
python code/extract_inputs.py --raw-root "/your/path/to/downloads"
python code/analyze.py
python code/plot.py
```

The extraction reads only listed columns in chunks of 256 rows; it does not load the full wide files into memory. It overwrites the two compact inputs and regenerates the input manifest. Tagsets can also be uploaded to [NLS Investigator](https://www.nlsinfo.org/investigator/pages/login), but newer releases may revise values. Use the packaged vintage and recorded hashes for exact input matching.

The public ID variables are maternal `R0000100`, child `C0000100` and child's mother `C0000200`. Maternal birth year `R0000500` is two digits, so add 1900; child birth year `C0005700` is already four digits. `R0214800=2` identifies women. All 11,545 child IDs are unique and match a mother; all matched maternal records pass the sex check. [Official linking documentation](https://www.nlsinfo.org/content/cohorts/nlsy79-children/using-and-understanding-the-data/linking-children-young-adults-and).

## Income and timing rules

Rules were chosen after checking available observations and before fitting the regressions. They are fixed in `analyze.py`; they are not chosen to maximize a coefficient.

1. Use maternal `Q13-5`/`Q13-5_TRUNC` earnings from the 1988–2008 waves, and child `Q15-5-TOP` from the 2000–2018 waves. The supplied variable maps give every reference number. Public top-codes are retained, not treated as uncensored true amounts. Neither measure includes self-employment profits or a partner's earnings. Maternal questions exclude separately reported military pay, whereas the child item includes it from 2000. This small scope difference is a limitation; the post is about the reported wage-earnings measures, not an exact match of all income sources. [NLS income documentation](https://www.nlsinfo.org/content/cohorts/nlsy79-children/topical-guide/income/introduction).
2. For mothers through 2006, use the specific preceding calendar year named in the codebook. The 2008 item uses the year preceding the actual interview, from `T1200702`. For children through 2012, use the specified preceding survey year. In 2014, 2016 and 2018, use actual interview year minus one (`Y2990502`, `Y3360902`, `Y4000802`). Some interviews occur in the following year. Age is age at the end of the **income reference year**, not interview age.
3. Negative special codes are missing and excluded from averages; a reported zero remains zero. Do not interpret follow-up earnings brackets as dollar amounts or replace missing income with zero.
4. Convert nominal earnings into 2018 dollars before averaging: `earnings * CPI_2018 / CPI_reference_year`. CPI-U is U.S. city average, all items, not seasonally adjusted, series `CUUR0000SA0`. The annual index is the mean of all twelve published monthly indices. Original responses were obtained on October 20, 2026 using the [BLS public API](https://www.bls.gov/developers/). To refresh an input, POST to `https://api.bls.gov/publicAPI/v1/timeseries/data/` with JSON `{"seriesid":["CUUR0000SA0"],"startyear":"1987","endyear":"1996"}`; the other saved ranges are 1997–2006, 2007–2016 and 2017–2019. A key is not required for these short requests. Default reproduction uses the included snapshots and requires no network.
5. Maternal average: valid income observations at ages 30–44, at least three years, positive mean. Child average: ages 25–34, at least three years, positive mean. Average levels first and take the natural logarithm afterward. Years are available observations, not interpolated annual income histories.
6. Single-year measures: nearest valid observation to age 37 for mothers within 30–44, and age 30 for children within 25–34; earlier reference year breaks ties. Select before excluding zeros: do not search for a positive replacement. The averaging comparison uses only pairs with positive selected single-year earnings. Both regressions use the same 2,114 pairs. 756 of 2,870 average-eligible pairs are excluded by this rule; they are not absent from the original data.
7. Age comparison: nearest valid child earnings to age 27 within 25–29 and age 37 within 35–39, with the same tie rule. Hold the maternal average fixed. Require positive selected child earnings in both windows; both age regressions use the same 1,004 children (810 mothers). The older age interval has few repeated records because [interviews after 30 became quadrennial](https://www.nlsinfo.org/content/cohorts/nlsy79-children/intro-to-the-sample/sample-design). It is not appropriate to silently call one later observation a multi-year average.

## Estimation, uncertainty and limits

Each model is an OLS regression of log child earnings on an intercept and log maternal earnings. There are no survey weights or additional covariates. Standard errors use the mother-clustered sandwich estimator with correction `G/(G-1) * (N-1)/(N-2)`. Intervals use 1.96 times this standard error. The differences use the difference between the two models' cluster influence contributions, preserving the paired nature of each comparison. Do not infer significance just by inspecting overlapping individual intervals.

`results/differences.csv` shows that the older-minus-younger interval includes zero. The post therefore illustrates the lifecycle measurement problem and reports the observed age contrast, **without claiming it proves a statistically detectable difference or identifies lifetime-income bias**. Later income is not observed lifetime income; calendar time changes along with age. No alternative window was searched for a significant result.

The age-comparison sample was born in 1970–1982; the median maternal age at birth was 19. This sample especially reflects early childbearing. Selection into positive earnings, survey nonresponse, oversampling, public top-coding and changing employment patterns prevent interpreting these unweighted slopes as nationwide family-income mobility. Mothers' wages also omit other household resources.

## Validation

The pipeline checks unique IDs, a complete mother match, nonmissing CPI values and no duplicate person/reference-year earnings. Additional checks verify SQL means against direct calculations, the common sample, reported age windows and the OLS calculation. Results are saved in `results/checks.json` and `results/validation.txt`. The two PNGs are generated directly from the saved coefficient table.
