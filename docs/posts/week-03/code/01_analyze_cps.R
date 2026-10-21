# Blog Post 3: Unemployment by education in the IPUMS CPS
# Run from the repository root:
# Rscript posts/week-03/code/01_analyze_cps.R

library(ipumsr)
library(dplyr)
library(tidyr)
library(readr)
library(haven)
library(ggplot2)
library(scales)

root <- "posts/week-03"
raw_dir <- file.path(root, "data", "raw")
processed_dir <- file.path(root, "data", "processed")
results_dir <- file.path(root, "results")
dir.create(processed_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(results_dir, recursive = TRUE, showWarnings = FALSE)

xml_files <- list.files(raw_dir, pattern = "\\.xml$", full.names = TRUE)
data_files <- list.files(raw_dir, pattern = "\\.dat(\\.gz)?$", full.names = TRUE)
if (length(xml_files) != 1 || length(data_files) != 1) {
  stop("Place exactly one matching IPUMS .xml file and one .dat.gz file in ", raw_dir)
}

ddi <- read_ipums_ddi(xml_files)
cps <- read_ipums_micro(ddi, data_file = data_files)
required <- c("YEAR", "MONTH", "AGE", "EDUC", "LABFORCE", "EMPSTAT", "WTFINL")
missing <- setdiff(required, names(cps))
if (length(missing)) stop("The IPUMS extract is missing: ", paste(missing, collapse = ", "))

# This project is designed for April Basic Monthly samples, 2000-2025.
if (any(unique(cps$MONTH) != 4)) stop("Extract must contain April samples only (MONTH = 4).")
if (!all(2000:2025 %in% unique(cps$YEAR))) {
  stop("Extract must contain every April Basic Monthly sample from 2000 through 2025.")
}

# Use labels to group post-1992 educational credentials. The unmatched check
# protects against silently dropping a new or unexpected IPUMS label.
cps_clean <- cps |>
  transmute(
    year = as.integer(YEAR), age = as.integer(AGE), weight = as.numeric(WTFINL),
    educ_label = as.character(as_factor(EDUC, levels = "labels")),
    in_labor_force = as.numeric(LABFORCE) == 2,
    unemployed = as.numeric(EMPSTAT) %in% 20:22
  ) |>
  filter(age >= 25, age <= 64, in_labor_force, is.finite(weight), weight > 0) |>
  mutate(
    education = case_when(
      grepl("bachelor|master|professional|doctor", educ_label, ignore.case = TRUE) ~ "Bachelor's or higher",
      grepl("some college|associate", educ_label, ignore.case = TRUE) ~ "Some college / associate",
      grepl("high school|GED", educ_label, ignore.case = TRUE) ~ "High school / GED",
      grepl("no schooling|none|preschool|nursery|kindergarten|grade|12th grade, no diploma",
            educ_label, ignore.case = TRUE) ~ "Less than high school",
      TRUE ~ NA_character_
    ),
    education = factor(education, levels = c(
      "Less than high school", "High school / GED",
      "Some college / associate", "Bachelor's or higher"
    )),
    age_group = cut(age, breaks = c(24, 34, 44, 54, 64),
                    labels = c("25-34", "35-44", "45-54", "55-64"))
  )

unmatched <- cps_clean |> filter(is.na(education)) |> distinct(educ_label)
if (nrow(unmatched)) {
  stop("Unmatched EDUC labels: ", paste(unmatched$educ_label, collapse = "; "))
}

weighted_rate <- function(data) {
  summarise(data,
            unemployed_population = sum(weight * unemployed),
            labor_force_population = sum(weight),
            unemployment_rate = unemployed_population / labor_force_population,
            observations = n(), .groups = "drop")
}

annual <- cps_clean |> group_by(year, education) |> weighted_rate()
age_2025 <- cps_clean |> filter(year == 2025) |>
  group_by(age_group, education) |> weighted_rate()
gaps <- annual |>
  select(year, education, unemployment_rate) |>
  pivot_wider(names_from = education, values_from = unemployment_rate) |>
  mutate(
    `Less than high school` = `Less than high school` - `Bachelor's or higher`,
    `High school / GED` = `High school / GED` - `Bachelor's or higher`,
    `Some college / associate` = `Some college / associate` - `Bachelor's or higher`
  ) |>
  select(-`Bachelor's or higher`) |>
  pivot_longer(-year, names_to = "education", values_to = "gap") |>
  mutate(education = factor(education, levels = c(
    "Less than high school", "High school / GED", "Some college / associate"
  )))

headline <- annual |> filter(year %in% c(2000, 2010, 2020, 2025))
write_csv(annual, file.path(processed_dir, "annual_unemployment.csv"))
write_csv(age_2025, file.path(processed_dir, "unemployment_by_age_2025.csv"))
write_csv(gaps, file.path(processed_dir, "education_gaps.csv"))
write_csv(headline, file.path(results_dir, "headline_rates.csv"))

# Rebuild figures through the same entry point used by the aggregate-data route.
source(file.path(root, "code", "02_plot_cps.R"))

cat("Analyzed", format(nrow(cps_clean), big.mark = ","), "labor-force records.\n")
print(headline)
