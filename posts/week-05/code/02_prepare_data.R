# Prepare county inputs; this script does not yet generate maps.
root <- "posts/week-05"
out <- file.path(root, "data/processed")
dir.create(out, recursive = TRUE, showWarnings = FALSE)
read_counties <- function(table) {
  path <- file.path(root, "data/raw", paste0("acsdt5y2024-", tolower(table), ".dat"))
  if (!file.exists(path)) stop("Missing source file. Run code/01_get_data.R first.")
  x <- read.delim(path, sep = "|", colClasses = "character", check.names = FALSE,
                  quote = "", comment.char = "", na.strings = c("", "N", "null"))
  x <- x[grepl("^0500000US42[0-9]{3}$", x$GEO_ID), , drop = FALSE]
  stopifnot(nrow(x) == 67L, !anyDuplicated(x$GEO_ID))
  for (column in setdiff(names(x), "GEO_ID")) {
    x[[column]] <- as.numeric(x[[column]])
    # ACS negative sentinel values are not valid counts or dollar amounts.
    x[[column]][!is.na(x[[column]]) & x[[column]] < 0] <- NA_real_
  }
  x <- x[order(x$GEO_ID), ]
  write.csv(x, file.path(out, paste0(table, "_pa_counties.csv")), row.names = FALSE)
  x
}
rent <- read_counties("B25064")
burden <- read_counties("B25070")
income <- read_counties("B25119")
stopifnot(identical(rent$GEO_ID, income$GEO_ID), !anyNA(income$B25119_E003), all(income$B25119_E003 > 0))
stopifnot(identical(rent$GEO_ID, burden$GEO_ID))
needed <- sprintf("B25070_E%03d", 1:11)
stopifnot(!anyNA(burden[needed]), !anyNA(rent$B25064_E001))
# The universe is cash-rent renter-occupied housing units, not all households.
stopifnot(all(rowSums(burden[sprintf("B25070_E%03d", 2:11)]) == burden$B25070_E001))
eligible <- burden$B25070_E001 - burden$B25070_E011
cost_burdened <- rowSums(burden[sprintf("B25070_E%03d", 7:10)])
severe <- burden$B25070_E010
stopifnot(all(eligible > 0), all(cost_burdened <= eligible), all(severe <= cost_burdened))
county <- data.frame(
  GEOID = sub("^0500000US", "", rent$GEO_ID),
  renter_income = income$B25119_E003,
  renter_income_moe = income$B25119_M003,
  rent_to_income = 12 * rent$B25064_E001 / income$B25119_E003,
  median_gross_rent = rent$B25064_E001,
  median_gross_rent_moe = rent$B25064_M001,
  cash_rent_households = burden$B25070_E001,
  not_computed_households = burden$B25070_E011,
  eligible_households = eligible,
  burdened_households = cost_burdened,
  severely_burdened_households = severe,
  burden_rate = cost_burdened / eligible,
  severe_burden_rate = severe / eligible
)
write.csv(county, file.path(out, "pa_county_rental_inputs.csv"), row.names = FALSE)
writeLines(c("PASS: 67 unique Pennsylvania counties in each source table.",
  "PASS: geography IDs match across tables.",
  "PASS: all required estimates are present and nonnegative.",
  "PASS: B25070 component counts sum to the total.",
  "PASS: eligible denominators are positive and burden rates are within [0,1].",
  "NEXT: 03_analyze_and_map.R validates spatial joins and creates the maps; see analysis_checks.txt."),
  file.path(root, "results/data_checks.txt"))
message("Prepared 67 counties. Source margins of error are retained in the table extracts.")
