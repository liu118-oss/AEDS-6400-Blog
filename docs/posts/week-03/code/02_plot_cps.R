# Run from the repository root. Uses only the published aggregate CSV files.
# Rscript posts/week-03/code/02_plot_cps.R
library(readr)
library(dplyr)
library(ggplot2)
library(scales)

root <- "posts/week-03"
processed_dir <- file.path(root, "data", "processed")
results_dir <- file.path(root, "results")
dir.create(results_dir, recursive = TRUE, showWarnings = FALSE)
files <- file.path(processed_dir, c("annual_unemployment.csv", "education_gaps.csv",
                                   "unemployment_by_age_2025.csv"))
if (!all(file.exists(files))) stop("Missing aggregate CSVs; see posts/week-03/README.md.")
annual <- read_csv(files[1], show_col_types = FALSE)
gaps <- read_csv(files[2], show_col_types = FALSE)
age_2025 <- read_csv(files[3], show_col_types = FALSE)

# Restore the original category order after reading CSVs, which store plain text.
education_levels <- c("Less than high school", "High school / GED",
                      "Some college / associate", "Bachelor's or higher")
annual$education <- factor(annual$education, levels = education_levels)
gaps$education <- factor(gaps$education, levels = education_levels[1:3])
age_2025$education <- factor(age_2025$education, levels = education_levels)
age_2025$age_group <- factor(age_2025$age_group,
                            levels = c("25-34", "35-44", "45-54", "55-64"))
# The article also uses this derived headline table.
headline <- annual |> filter(year %in% c(2000, 2010, 2020, 2025))
write_csv(headline, file.path(results_dir, "headline_rates.csv"))

palette <- c("Less than high school" = "#A63D40", "High school / GED" = "#D17C2F",
             "Some college / associate" = "#3C7A89", "Bachelor's or higher" = "#344E71")
theme_set(theme_minimal(base_size = 12) +
            theme(plot.title.position = "plot", legend.position = "bottom",
                  panel.grid.minor = element_blank()))

p1 <- ggplot(annual, aes(year, unemployment_rate, color = education)) +
  geom_line(linewidth = 1) + geom_point(size = 1.5) +
  scale_color_manual(values = palette) +
  scale_y_continuous(labels = percent_format(accuracy = 1)) +
  scale_x_continuous(breaks = seq(2000, 2025, 5)) +
  labs(title = "Unemployment is consistently lower for college graduates",
       subtitle = "April unemployment rate, civilian labor force ages 25-64",
       x = NULL, y = "Unemployment rate", color = NULL,
       caption = "Source: IPUMS CPS Basic Monthly samples. Estimates use WTFINL.")
ggsave(file.path(results_dir, "01_unemployment_trends.png"), p1,
       width = 9, height = 5.7, dpi = 180, bg = "white")

p2 <- ggplot(gaps, aes(year, gap, color = education)) +
  geom_hline(yintercept = 0, color = "grey70") +
  geom_line(linewidth = 1) +
  scale_color_manual(values = palette[names(palette) != "Bachelor's or higher"]) +
  scale_y_continuous(labels = percent_format(accuracy = 1)) +
  scale_x_continuous(breaks = seq(2000, 2025, 5)) +
  labs(title = "Education gaps widen when the labor market weakens",
       subtitle = "Unemployment-rate difference relative to bachelor's degree or higher",
       x = NULL, y = "Percentage-point gap", color = NULL,
       caption = "Source: IPUMS CPS Basic Monthly samples. Estimates use WTFINL.")
ggsave(file.path(results_dir, "02_education_gaps.png"), p2,
       width = 9, height = 5.7, dpi = 180, bg = "white")

p3 <- ggplot(age_2025, aes(age_group, education, fill = unemployment_rate)) +
  geom_tile(color = "white", linewidth = 1) +
  geom_text(aes(label = percent(unemployment_rate, accuracy = 0.1)), size = 3.8) +
  scale_fill_gradient(low = "#EAF2F4", high = "#A63D40",
                      labels = percent_format(accuracy = 1)) +
  labs(title = "The education gradient appears within age groups",
       subtitle = "April 2025 unemployment rate, civilian labor force ages 25-64",
       x = "Age group", y = NULL, fill = "Unemployment rate",
       caption = "Source: IPUMS CPS Basic Monthly sample. Estimates use WTFINL.") +
  theme(panel.grid = element_blank(), legend.position = "right")
ggsave(file.path(results_dir, "03_age_education_heatmap.png"), p3,
       width = 9, height = 5.4, dpi = 180, bg = "white")

