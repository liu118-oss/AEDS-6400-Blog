# Run from the repository root after 01_get_data.R and 02_prepare_data.R.
# A fresh clone can also use the committed county inputs and PA GeoJSON offline.
library(sf)
library(ggplot2)
library(ggrepel)
library(scales)
root <- "posts/week-05"
processed <- file.path(root, "data/processed")
results <- file.path(root, "results")
dir.create(results, recursive = TRUE, showWarnings = FALSE)
x <- read.csv(file.path(processed, "pa_county_rental_inputs.csv"), colClasses = c(GEOID = "character"))
b <- read.csv(file.path(processed, "B25070_pa_counties.csv"))
b <- b[match(paste0("0500000US", x$GEOID), b$GEO_ID), ]
stopifnot(nrow(x) == 67, !anyDuplicated(x$GEOID), !anyNA(b$GEO_ID))
# Census approximation for sums and proportions, retaining 90% confidence level.
# Derive the denominator by summing computable categories (E002:E010).
# Replicate covariance information is not available in these summary files.
num_moe <- sqrt(rowSums(b[sprintf("B25070_M%03d", 7:10)]^2))
den_moe <- sqrt(rowSums(b[sprintf("B25070_M%03d", 2:10)]^2))
proportion_moe <- function(numerator_moe, denominator_moe, proportion, denominator) {
  v <- numerator_moe^2 - proportion^2 * denominator_moe^2
  # Census ratio approximation is the fallback when the subtraction is negative.
  v[v < 0] <- (numerator_moe^2 + proportion^2 * denominator_moe^2)[v < 0]
  sqrt(v) / denominator
}
x$burden_moe <- proportion_moe(num_moe, den_moe, x$burden_rate, x$eligible_households)
x$severe_burden_moe <- proportion_moe(b$B25070_M010, den_moe, x$severe_burden_rate, x$eligible_households)
x$burden_lower90 <- pmax(0, x$burden_rate - x$burden_moe)
x$burden_upper90 <- pmin(1, x$burden_rate + x$burden_moe)
x$imprecise <- x$burden_moe > 0.05
stopifnot(!anyNA(x$burden_moe), all(x$burden_moe >= 0))
geo_path <- file.path(processed, "pa_counties_2024.geojson")
zip_path <- file.path(root, "data/raw/cb_2024_us_county_500k.zip")
if (file.exists(zip_path)) {
  temp <- tempfile("county-boundaries-")
  dir.create(temp)
  unzip(zip_path, exdir = temp)
  shp <- list.files(temp, pattern = "\\.shp$", full.names = TRUE)
  stopifnot(length(shp) == 1)
  boundaries <- st_read(shp, quiet = TRUE)
  pa <- boundaries[boundaries$STATEFP == "42", c("GEOID", "NAME")]
  pa <- st_transform(pa, 4326)
  st_write(pa, geo_path, delete_dsn = TRUE, quiet = TRUE)
  unlink(temp, recursive = TRUE)
} else {
  if (!file.exists(geo_path)) stop("Run 01_get_data.R or restore the committed PA GeoJSON.")
  pa <- st_read(geo_path, quiet = TRUE)
}
stopifnot(nrow(pa) == 67, !anyDuplicated(pa$GEOID), setequal(pa$GEOID, x$GEOID),
          all(st_is_valid(pa)), !any(st_is_empty(pa)))
x$county <- pa$NAME[match(x$GEOID, pa$GEOID)]
x <- x[order(x$GEOID), ]
pa <- merge(pa, x, by = "GEOID", sort = TRUE)
pa <- st_transform(pa, 5070)
centers <- suppressWarnings(st_point_on_surface(pa))
xy <- st_coordinates(centers)
pa$label_x <- xy[,1]; pa$label_y <- xy[,2]
labels <- st_drop_geometry(pa[pa$NAME %in% c("Chester", "Philadelphia", "Bedford", "Centre", "Monroe", "Allegheny"), ])
write.csv(x, file.path(processed, "pa_county_rental_analysis.csv"), row.names = FALSE)
headline <- data.frame(
  income_ratio_r = cor(x$rent_to_income, x$burden_rate),
  counties = nrow(x), pearson_r = cor(x$median_gross_rent, x$burden_rate),
  eligible_households = sum(x$eligible_households),
  excluded_households = sum(x$not_computed_households),
  burden_rate_pooled = sum(x$burdened_households) / sum(x$eligible_households),
  severe_burden_rate_pooled = sum(x$severely_burdened_households) / sum(x$eligible_households),
  counties_imprecise = sum(x$imprecise))
write.csv(headline, file.path(results, "headline_results.csv"), row.names = FALSE)
write.csv(x[x$county %in% labels$NAME, ], file.path(results, "selected_counties.csv"), row.names = FALSE)
source_caption <- "Source: U.S. Census Bureau, 2020-2024 ACS; 2024 county boundaries."
theme_set(theme_minimal(base_size = 12) + theme(
  plot.title.position = "plot", plot.title = element_text(face = "bold", size = 18),
  plot.subtitle = element_text(size = 11, margin = margin(b = 12)),
  plot.caption = element_text(hjust = 0, size = 9, color = "#555555"),
  panel.grid.minor = element_blank(), legend.position = "bottom",
  plot.margin = margin(15, 22, 15, 15)))
map_base <- ggplot(pa) +
  coord_sf(crs = st_crs(pa), datum = NA, clip = "off") +
  theme(axis.text = element_blank(), axis.title = element_blank(),
        axis.ticks = element_blank(), panel.grid = element_blank())
map_labels <- function() geom_label_repel(data = labels,
  aes(x = label_x, y = label_y, label = NAME), inherit.aes = FALSE,
  size = 3.1, seed = 42, box.padding = 0.35, min.segment.length = 0,
  fill = "white", color = "#333333", segment.color = "#666666", max.overlaps = Inf)
p1 <- map_base + geom_sf(aes(fill = median_gross_rent), color = "white", linewidth = 0.25) +
  scale_fill_gradient(low = "#EAF2F4", high = "#245A81", labels = label_dollar(),
                      name = "Monthly median gross rent", breaks = c(800,1000,1200,1400,1600)) +
  guides(fill = guide_colorbar(title.position = "top", barwidth = grid::unit(12, "cm"), barheight = grid::unit(0.45, "cm"))) +
  map_labels() + labs(title = "Rents are highest in Pennsylvania's southeast",
  subtitle = "Median gross rent includes contract rent and tenant-paid utilities. Values in 2024 dollars.",
  caption = source_caption)
ggsave(file.path(results, "01_median_rent_map.png"), p1, width = 10, height = 6.5, dpi = 180, bg = "white")
p2 <- map_base + geom_sf(aes(fill = burden_rate), color = "white", linewidth = 0.25) +
  scale_fill_gradient(low = "#FFF2DF", high = "#A63D40", labels = label_percent(accuracy = 1),
                      name = "Households spending 30% or more on rent", breaks = seq(.3,.55,.05)) +
  geom_sf(data = centers[centers$imprecise, ], shape = 1, size = 2, color = "#222222", inherit.aes = FALSE) +
  guides(fill = guide_colorbar(title.position = "top", barwidth = grid::unit(12, "cm"), barheight = grid::unit(0.45, "cm"))) +
  map_labels() + labs(title = "Rent burden does not follow the same map",
  subtitle = "Share of cash-rent households with a computable rent-to-income ratio, 2020-2024.",
  caption = paste0(source_caption, "\nOpen circles: approximate 90% margin of error exceeds 5 percentage points."))
ggsave(file.path(results, "02_rent_burden_map.png"), p2, width = 10, height = 6.5, dpi = 180, bg = "white")
highlight <- x$county %in% labels$NAME
p3 <- ggplot(x, aes(median_gross_rent, burden_rate)) +
  geom_errorbar(aes(ymin = burden_lower90, ymax = burden_upper90), width = 0,
                color = "#C5CFD5", linewidth = 0.45) +
  geom_point(color = "#245A81", alpha = 0.8, size = 2.3) +
  geom_point(data = x[highlight, ], color = "#A63D40", size = 2.7) +
  geom_text_repel(data = transform(x, plot_label = ifelse(highlight, county, "")), aes(label = plot_label), seed = 42,
                 size = 3.4, box.padding = .65, point.padding = .6, min.segment.length = 0, max.overlaps = Inf) +
  scale_x_continuous(labels = label_dollar()) +
  scale_y_continuous(labels = label_percent(accuracy = 1)) +
  labs(title = "Lower rents do not guarantee a lower burden",
       subtitle = "Each point is one county; vertical bars show approximate 90% margins of error.",
       x = "Median monthly gross rent", y = "Households spending at least 30% of income on rent",
       caption = "Source: U.S. Census Bureau, 2020-2024 ACS, B25064 and B25070.\nCounty comparisons are descriptive; each point receives equal weight.")
ggsave(file.path(results, "03_rent_vs_burden.png"), p3, width = 9, height = 6, dpi = 180, bg = "white")
p4 <- ggplot(x, aes(rent_to_income, burden_rate)) +
  geom_errorbar(aes(ymin = burden_lower90, ymax = burden_upper90), width = 0, color = "#C5CFD5") +
  geom_point(color = "#245A81", size = 2.3, alpha = .8) +
  geom_point(data = x[highlight, ], color = "#A63D40", size = 2.7) +
  geom_text_repel(data = transform(x, plot_label = ifelse(highlight, county, "")),
    aes(label = plot_label), seed = 42, size = 3.4, box.padding = .65,
    point.padding = .6, min.segment.length = 0, max.overlaps = Inf) +
  scale_x_continuous(labels = label_percent(accuracy = 1)) +
  scale_y_continuous(labels = label_percent(accuracy = 1)) +
  labs(title = "Income helps explain the gap between the maps",
    subtitle = "Each point is one county; vertical bars show approximate 90% margins of error for burden.",
    x = "Annual median rent / median renter household income",
    y = "Households spending at least 30% of income on rent",
    caption = "Source: 2020-2024 ACS, B25064, B25070 and B25119.\nThe horizontal measure divides two county medians; it is not a household burden rate.")
ggsave(file.path(results, "04_income_vs_burden.png"), p4, width = 9, height = 6, dpi = 180, bg = "white")
writeLines(c("PASS: all 67 unique Pennsylvania county GEOIDs matched the boundary file.",
  "PASS: geometries valid and nonempty; maps use EPSG:5070.",
  "PASS: source estimates, component totals and denominators checked by 02_prepare_data.R.",
  "PASS: approximate derived MOEs finite and nonnegative; intervals bounded to [0,1].",
  paste("CHECK: counties with burden MOE above 5 percentage points:", sum(x$imprecise)),
  "PASS: two maps, two scatterplots and analysis CSV generated programmatically."),
  file.path(results, "analysis_checks.txt"))
writeLines(capture.output(sessionInfo()), file.path(results, "sessionInfo.txt"))
print(headline)
print(x[x$county %in% labels$NAME, c("county","median_gross_rent","burden_rate","burden_moe","severe_burden_rate")])
