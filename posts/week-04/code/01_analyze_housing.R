# Blog Post 4: Housing prices, mortgage rates, and affordability
# Run from the repository root:
# Rscript posts/week-04/code/01_analyze_housing.R

library(dplyr)
library(tidyr)
library(readr)
library(ggplot2)
library(scales)

root <- "posts/week-04"
raw_dir <- file.path(root, "data", "raw")
processed_dir <- file.path(root, "data", "processed")
results_dir <- file.path(root, "results")
dir.create(raw_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(processed_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(results_dir, recursive = TRUE, showWarnings = FALSE)

# FRED's graph CSV endpoint provides reproducible downloads without an API key.
series <- c(
  MSPUS = "Median sales price of new houses sold",
  MORTGAGE30US = "30-year fixed mortgage rate",
  CPIAUCSL = "Consumer Price Index",
  MEHOINUSA646N = "Median household income"
)

download_fred <- function(id) {
  url <- paste0("https://fred.stlouisfed.org/graph/fredgraph.csv?id=", id)
  destination <- file.path(raw_dir, paste0(id, ".csv"))
  download.file(url, destination, mode = "wb", quiet = TRUE)

  read_csv(destination, na = c(".", ""), show_col_types = FALSE) |>
    rename(date = observation_date, value = all_of(id)) |>
    mutate(
      date = as.Date(date),
      year = as.integer(format(date, "%Y")),
      value = as.numeric(value)
    )
}

fred <- lapply(names(series), download_fred)
names(fred) <- names(series)

# Convert higher-frequency series to annual averages so they can be compared
# with annual median household income. The sample ends at the latest complete
# year shared by all four series.
price <- fred$MSPUS |>
  filter(year >= 2000, year <= 2025) |>
  group_by(year) |>
  summarise(home_price = mean(value, na.rm = TRUE), .groups = "drop")

mortgage <- fred$MORTGAGE30US |>
  filter(year >= 2000, year <= 2025) |>
  group_by(year) |>
  summarise(mortgage_rate = mean(value, na.rm = TRUE), .groups = "drop")

cpi <- fred$CPIAUCSL |>
  filter(year >= 2000, year <= 2025) |>
  group_by(year) |>
  summarise(cpi = mean(value, na.rm = TRUE), .groups = "drop")

income <- fred$MEHOINUSA646N |>
  filter(year >= 2000, year <= 2025) |>
  transmute(year, household_income = value)

annual <- price |>
  inner_join(mortgage, by = "year") |>
  inner_join(cpi, by = "year") |>
  inner_join(income, by = "year")

if (!identical(annual$year, 2000:2025)) {
  stop("Expected complete annual data for 2000-2025 from all four FRED series.")
}

monthly_payment <- function(principal, annual_rate, years = 30) {
  monthly_rate <- annual_rate / 100 / 12
  periods <- years * 12
  principal * monthly_rate * (1 + monthly_rate)^periods /
    ((1 + monthly_rate)^periods - 1)
}

cpi_2025 <- annual$cpi[annual$year == 2025]
rate_2021 <- annual$mortgage_rate[annual$year == 2021]

annual <- annual |>
  mutate(
    real_home_price_2025 = home_price * cpi_2025 / cpi,
    down_payment = 0.20 * home_price,
    loan_amount = 0.80 * home_price,
    monthly_payment = monthly_payment(loan_amount, mortgage_rate),
    payment_at_2021_rate = monthly_payment(loan_amount, rate_2021),
    monthly_income = household_income / 12,
    payment_burden = monthly_payment / monthly_income,
    burden_at_2021_rate = payment_at_2021_rate / monthly_income,
    price_to_income = home_price / household_income
  )

headline <- annual |>
  filter(year %in% c(2000, 2019, 2021, 2023, 2025))

write_csv(annual, file.path(processed_dir, "annual_housing_affordability.csv"))
write_csv(headline, file.path(results_dir, "headline_results.csv"))
write_lines(
  paste("FRED data downloaded", Sys.Date(), "from", paste(names(series), collapse = ", ")),
  file.path(raw_dir, "retrieval_note.txt")
)

colors <- c(
  "Nominal dollars" = "#A6A6A6",
  "2025 dollars" = "#2F6690",
  "Actual mortgage rate" = "#B33F40",
  "If the 2021 rate had continued" = "#6C8EAD"
)

theme_set(
  theme_minimal(base_size = 12) +
    theme(
      plot.title.position = "plot",
      legend.position = "bottom",
      panel.grid.minor = element_blank()
    )
)

# Figure 1: show why inflation adjustment changes the housing-price story.
price_long <- annual |>
  select(year, `Nominal dollars` = home_price, `2025 dollars` = real_home_price_2025) |>
  pivot_longer(-year, names_to = "measure", values_to = "price") |>
  mutate(measure = factor(measure, levels = c("Nominal dollars", "2025 dollars")))

p1 <- ggplot(price_long, aes(year, price, color = measure)) +
  geom_line(linewidth = 1.1) +
  scale_color_manual(values = colors) +
  scale_x_continuous(breaks = seq(2000, 2025, 5)) +
  scale_y_continuous(labels = dollar_format(scale = 1 / 1000, suffix = "K")) +
  labs(
    title = "Inflation explains part, but not all, of the rise in home prices",
    subtitle = "Annual average of quarterly median prices for new U.S. homes",
    x = NULL, y = "Median sales price", color = NULL,
    caption = "Source: Census/HUD MSPUS and BLS CPIAUCSL via FRED. Real values use 2025 dollars."
  )
ggsave(file.path(results_dir, "01_real_home_prices.png"), p1,
       width = 9, height = 5.7, dpi = 180, bg = "white")

# Figure 2: show the financing-cost reversal after the 2021 low.
rate_labels <- annual |> filter(year %in% c(2021, 2025))
p2 <- ggplot(annual, aes(year, mortgage_rate)) +
  geom_line(color = colors[["Actual mortgage rate"]], linewidth = 1.1) +
  geom_point(data = rate_labels, color = colors[["Actual mortgage rate"]], size = 2.8) +
  geom_text(
    data = rate_labels,
    aes(label = percent(mortgage_rate / 100, accuracy = 0.1)),
    nudge_y = 0.45, fontface = "bold"
  ) +
  scale_x_continuous(breaks = seq(2000, 2025, 5)) +
  scale_y_continuous(labels = label_percent(scale = 1, accuracy = 1),
                     limits = c(0, NA), expand = expansion(mult = c(0, 0.08))) +
  labs(
    title = "The era of exceptionally cheap mortgages ended after 2021",
    subtitle = "Annual average of weekly 30-year fixed mortgage rates",
    x = NULL, y = "Mortgage rate",
    caption = "Source: Freddie Mac MORTGAGE30US via FRED."
  )
ggsave(file.path(results_dir, "02_mortgage_rates.png"), p2,
       width = 9, height = 5.7, dpi = 180, bg = "white")

# Figure 3: combine prices, rates, and income in a household-relevant measure.
burden_long <- annual |>
  select(
    year,
    `Actual mortgage rate` = payment_burden,
    `If the 2021 rate had continued` = burden_at_2021_rate
  ) |>
  pivot_longer(-year, names_to = "scenario", values_to = "burden") |>
  mutate(
    burden = if_else(
      scenario == "If the 2021 rate had continued" & year < 2021,
      NA_real_, burden
    ),
    scenario = factor(
      scenario,
      levels = c("Actual mortgage rate", "If the 2021 rate had continued")
    )
  )

burden_labels <- burden_long |> filter(year == 2025)
burden_plot <- burden_long |> filter(!is.na(burden))

p3 <- ggplot(burden_plot, aes(year, burden, color = scenario)) +
  geom_line(linewidth = 1.1) +
  geom_point(data = burden_labels, size = 2.8) +
  geom_text(
    data = burden_labels,
    aes(label = percent(burden, accuracy = 0.1)),
    nudge_x = 0.35, fontface = "bold", show.legend = FALSE
  ) +
  scale_color_manual(values = colors) +
  scale_x_continuous(breaks = seq(2000, 2025, 5)) +
  scale_y_continuous(labels = percent_format(accuracy = 1)) +
  coord_cartesian(xlim = c(2000, 2026)) +
  labs(
    title = "Higher rates now account for much of the payment squeeze",
    subtitle = "Principal and interest on a median-priced new home with 20% down, as a share of median household income",
    x = NULL, y = "Share of gross monthly income", color = NULL,
    caption = "Sources: MSPUS, MORTGAGE30US, and MEHOINUSA646N via FRED. Counterfactual fixes the rate at its 2021 average."
  )
ggsave(file.path(results_dir, "03_payment_burden.png"), p3,
       width = 9, height = 5.9, dpi = 180, bg = "white")

cat("Downloaded four FRED series and analyzed", nrow(annual), "annual observations.\n")
print(headline)
