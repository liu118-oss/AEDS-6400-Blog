# Blog 5: Why Lower Rent Does Not Always Mean Less Housing Pressure

An analysis of median gross rent and rent burden across all 67 Pennsylvania counties, using 2020–2024 ACS five-year estimates. The article contains two maps and two scatterplots. No API key is required.

Repository: https://github.com/liu118-oss/AEDS-6400-Blog/tree/main/posts/week-05

## Read and inspect

- Article source: `index.qmd`
- Complete county results: `data/processed/pa_county_rental_analysis.csv`
- Figures: `results/01_median_rent_map.png`, `02_rent_burden_map.png`, `03_rent_vs_burden.png`, `04_income_vs_burden.png`
- Headline statistics: `results/headline_results.csv`
- Data and spatial checks: `results/data_checks.txt`, `results/analysis_checks.txt`
- One-file reproduction bundle: `results/replication.zip`

## Requirements

Install R and Quarto. In R, install:

```r
install.packages(c("sf", "ggplot2", "ggrepel", "scales", "readr", "dplyr", "knitr"))
```

On macOS/Windows, prefer available binary packages for `sf`. Linux installations may require GDAL, GEOS, PROJ, and udunits system libraries. The analysis records its actual package versions in `results/sessionInfo.txt`.

## Full reproduction from official downloads

Run these commands from the Git repository root, the folder containing `_quarto.yml`:

```sh
Rscript posts/week-05/code/01_get_data.R
Rscript posts/week-05/code/02_prepare_data.R
Rscript posts/week-05/code/03_analyze_and_map.R
Rscript posts/week-05/code/04_package_replication.R
quarto render posts/week-05/index.qmd
quarto render index.qmd
```

The first script downloads and caches the three official national tables and the county boundary archive. Subsequent runs reuse those files. The second extracts Pennsylvania's 67 counties and calculates inputs. The third joins geometry, assesses uncertainty, and generates the figures and results. The fourth creates the downloadable bundle. Rendering reads the generated CSVs, so headline numbers are not manually pasted into the article.

## Reproduce offline from the saved county snapshot

A clone contains the small Pennsylvania table extracts, calculated inputs, and boundary GeoJSON. With packages installed, the third command above can generate the analysis and figures without the national raw files or internet. It uses the saved GeoJSON if the national boundary ZIP is absent. Then run `04_package_replication.R` and render as above. The two raw-dependent commands are needed only to reconstruct the snapshot from the official national files.

The replication ZIP preserves paths beginning with `posts/week-05/`. Extract it into an empty folder and run the analysis and packaging commands from that folder. Without the full site's configuration, render the article standalone with `quarto render posts/week-05/index.qmd`; the page will have the same content but not the site's navigation.

## Sources and provenance

Official 2020–2024 ACS Table-Based Summary Files:

- [B25064](https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-b25064.dat)
- [B25070](https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-b25070.dat)
- [B25119](https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/acsdt5y2024-b25119.dat)
- [Summary File documentation](https://www.census.gov/programs-surveys/acs/data/summary-file.2024.html)
- [2024 county boundaries, 1:500,000](https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_county_500k.zip)

The national tables are approximately 81 MB together and are ignored by Git, as is the national boundary ZIP. Pennsylvania extracts and boundaries are small enough to commit. `data/raw/source_manifest.json` records the initial source download dates and SHA-256 hashes; the downloader logs cached reuse separately. `boundary_source.csv` records boundary provenance. Source revisions may change later reruns; retain the committed snapshot to reproduce this version.

## Definitions and geography

The ACS release describes the entire 2020–2024 period, not a single year or current asking rents. Gross rent includes contract rent and tenant-paid utilities; ACS dollar estimates are expressed in 2024 dollars. B25070's universe is renter-occupied housing units paying cash rent.

Select GEO_ID values matching `0500000US42xxx`. Use the five-character county GEOID to join the three tables to 2024 boundaries, requiring all 67 matches with no duplicates. Names come from the boundary file. The saved PA GeoJSON uses EPSG:4326; maps use CONUS Albers equal-area, EPSG:5070.

- Eligible denominator: B25070 E001 minus E011 (not computed), equivalently sum E002:E010.
- Burdened numerator: E007+E008+E009+E010, for rent/income at least 30%.
- Severely burdened numerator: E010, for rent/income at least 50%.
- Rates are numerator / eligible denominator, stored as fractions and displayed as percentages.
- Statewide summaries pool the county numerators and denominators, rather than averaging county percentages.
- Pearson correlation is descriptive and gives each of the 67 counties equal weight. It is not a household-level estimate or a causal effect.

No-cash-rent households are outside the source universe. Noncomputable ratios are excluded, not assigned zero burden. The script verifies that all component estimates sum to the total and that all required estimates and denominators are valid. Zero or negative household income produces a noncomputable ratio. The additional contextual measure is 12 * B25064 E001 / B25119 E003. B25119 E003 is median annual renter household income, covering all renter-occupied households, including those paying no cash rent. This ratio of medians is not a household-level burden statistic and never replaces B25070. Its correlation with burden is partly linked by construction because both involve rent and income. Income and rent MOEs are retained; no uncertainty interval or significance test is calculated for this ratio or either correlation.

## Uncertainty

Published ACS margins of error (M columns) are at 90% confidence. Following the Census approximation for derived estimates, a sum's MOE is the square root of the sum of squared component MOEs. The eligible denominator MOE uses components M002:M010; the burdened numerator uses M007:M010. For a subset proportion p = N/D, approximate MOE is sqrt(MOE_N^2 - p^2 * MOE_D^2)/D. If the expression under the square root is negative, use the ratio fallback with a plus sign. Severe burden uses the same method. These approximations do not recover full covariance information.

Intervals are bounded to [0,1]. Open circles on the burden map flag MOEs exceeding 5 percentage points, an explicit presentation rule rather than an official Census suppression threshold. Scatterplot vertical bars show those approximate intervals. Median-rent MOEs are preserved in the CSV; horizontal uncertainty bars are omitted for readability. Avoid interpreting close ranks or map shades as statistically significant differences.

Method reference: [Census ACS Accuracy Document, worked examples](https://www2.census.gov/programs-surveys/acs/tech_docs/accuracy/2023_ACS_Accuracy_Document_Worked_Examples.pdf).

## Scope and limitations

These are county-level descriptive comparisons. Differences in renter incomes, household composition, housing size and quality, and neighborhoods are not isolated. Renter income is included descriptively, without a causal model. The Centre County 2023 Housing Needs Assessment (pages 8 and 76) supplies independent background on Penn State and student renters, using an earlier period; it does not establish how much of the 2020–2024 county burden rate is attributable to students.

Context source: https://centrecountypa.gov/DocumentCenter/View/25310/Centre-County-2023-HNA_Final_6_20_2023 . Existing gross rents do not equal current listing prices. The maps identify differences for further investigation, not a recommendation to move or proof that a particular housing policy works.

## Folder structure

`code/` contains acquisition, preparation, mapping, and packaging scripts. `data/raw/` holds cached national sources and provenance; `data/processed/` holds reproducible county inputs, analysis, and boundaries. `results/` contains figures, summary tables, validation notes, package versions, and the replication ZIP. `index.qmd` reads the outputs to generate the article. The rendered page explicitly links to this README, code, data, and ZIP.

## Local website preview

After rendering from the full repository, run:

```sh
python3 -m http.server 8767 --bind 127.0.0.1 --directory docs
```

Open http://127.0.0.1:8767/posts/week-05/ . This serves only the local preview; it does not publish to GitHub.
