# Run from the Git repository root. No API key is required.
options(timeout = max(300, getOption("timeout")))
root <- "posts/week-05"
raw_dir <- file.path(root, "data/raw")
dir.create(raw_dir, recursive = TRUE, showWarnings = FALSE)
base_url <- "https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/"
records <- list()
for (table in c("b25064", "b25070", "b25119")) {
  filename <- paste0("acsdt5y2024-", table, ".dat")
  destination <- file.path(raw_dir, filename)
  url <- paste0(base_url, filename)
  downloaded <- !file.exists(destination)
  if (downloaded) {
    temporary <- paste0(destination, ".part")
    download.file(url, temporary, mode = "wb", method = "libcurl")
    if (!file.rename(temporary, destination)) stop("Could not save ", destination)
  }
  header <- readLines(destination, n = 1, warn = FALSE)
  if (!startsWith(header, "GEO_ID|")) stop("Invalid Census table: ", destination)
  records[[table]] <- data.frame(table = toupper(table), file = filename,
    source_url = url, checked_date = as.character(Sys.Date()),
    action = if (downloaded) "downloaded" else "reused local file",
    md5 = unname(tools::md5sum(destination)))
}
write.csv(do.call(rbind, records), file.path(raw_dir, "download_log.csv"), row.names = FALSE)
message("Official source files ready. Next: Rscript posts/week-05/code/02_prepare_data.R")

# The boundary archive is public and does not require an API key.
boundary_file <- file.path(raw_dir, "cb_2024_us_county_500k.zip")
boundary_url <- "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_county_500k.zip"
if (!file.exists(boundary_file)) {
  download.file(boundary_url, paste0(boundary_file, ".part"), mode = "wb", method = "libcurl")
  if (!file.rename(paste0(boundary_file, ".part"), boundary_file)) stop("Cannot save boundaries")
}
write.csv(data.frame(file = basename(boundary_file), source_url = boundary_url,
  checked_date = as.character(Sys.Date()), md5 = unname(tools::md5sum(boundary_file))),
  file.path(raw_dir, "boundary_source.csv"), row.names = FALSE)
