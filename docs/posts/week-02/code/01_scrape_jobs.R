# Run from the repository root: Rscript posts/week-02/code/01_scrape_jobs.R
# This script requests 100 public HTML listing pages with rvest, then uses
# Arbeitnow's published API for full descriptions. Raw pages are cached.
library(rvest)
library(dplyr)
library(readr)
library(jsonlite)
library(stringr)

root <- "posts/week-02"
html_dir <- file.path(root, "data/raw/html")
api_dir <- file.path(root, "data/raw/api")
processed_dir <- file.path(root, "data/processed")
for (path in c(html_dir, api_dir, processed_dir)) dir.create(path, recursive = TRUE, showWarnings = FALSE)

fetch_once <- function(url, path, pause_seconds = 1.25) {
  if (file.exists(path) && file.size(path) > 0) return(invisible(FALSE))
  temporary <- paste0(path, ".partial")
  if (file.exists(temporary)) file.remove(temporary)
  tryCatch(download.file(url, temporary, mode = "wb", quiet = TRUE),
           error = function(e) stop("Request failed for ", url, ": ", conditionMessage(e)))
  if (!file.exists(temporary) || file.size(temporary) == 0) stop("Empty response: ", url)
  file.rename(temporary, path)
  Sys.sleep(pause_seconds) # No parallel requests or access workarounds.
  invisible(TRUE)
}

message("Collecting 100 public HTML pages with rvest...")
for (page_number in 1:100) {
  url <- paste0("https://www.arbeitnow.com?page=", page_number)
  path <- file.path(html_dir, sprintf("page-%03d.html", page_number))
  fetch_once(url, path)
  if (page_number %% 10 == 0) message("HTML pages checked: ", page_number)
}

listing_rows <- lapply(1:100, function(page_number) {
  path <- file.path(html_dir, sprintf("page-%03d.html", page_number))
  document <- read_html(path)
  links <- html_elements(document, "a[data-job-item-link]")
  if (length(links) == 0) stop("No job links on HTML page ", page_number, "; inspect saved page")
  tibble(listing_page = page_number,
         url = html_attr(links, "href"),
         listing_title = str_squish(html_text2(links)))
})
listings <- bind_rows(listing_rows) |> filter(!is.na(url), nzchar(url)) |>
  distinct(url, .keep_all = TRUE)
write_csv(listings, file.path(processed_dir, "html_listings.csv"))
message("Unique HTML listings: ", nrow(listings))

# The site's documented public API provides descriptions without requesting
# thousands of individual job pages. The helper pauses eight seconds between
# new pages and stops on HTTP 429; saved pages are reused on later runs.
source(file.path(root, "code", "extend_api_cache.R"))
api_files <- sort(list.files(api_dir, pattern = "^page-[0-9]{3}\\.json$", full.names = TRUE))

api_rows <- lapply(api_files, function(path) {
  response <- jsonlite::fromJSON(path, simplifyVector = FALSE)
  if (is.null(response$data)) stop("Invalid API page: ", path)
  if (length(response$data) == 0) return(tibble())
  lapply(response$data, function(job) {
    tibble(url = job$url, title = job$title, company = job$company_name,
           location = job$location, remote = isTRUE(job$remote),
           posted_at = as.character(job$created_at),
           tags = paste(unlist(job$tags), collapse = "; "),
           job_types = paste(unlist(job$job_types), collapse = "; "),
           description_html = job$description)
  }) |> bind_rows()
}) |> bind_rows() |> distinct(url, .keep_all = TRUE)

# The API's descriptions are HTML-escaped HTML. Parse both layers with rvest.
plain_description <- function(value) {
  if (is.na(value) || !nzchar(value)) return(NA_character_)
  tryCatch({
    decoded <- html_text2(read_html(value))
    if (grepl("<[[:alpha:]][^>]*>", decoded)) decoded <- html_text2(read_html(decoded))
    str_squish(decoded)
  }, error = function(e) NA_character_)
}

jobs <- api_rows |>
  left_join(listings, by = "url") |>
  mutate(in_html_snapshot = !is.na(listing_page)) |>
  mutate(description = vapply(description_html, plain_description, character(1))) |>
  select(listing_page, in_html_snapshot, url, title, company, location, remote,
         posted_at, tags, job_types, description) |>
  filter(!is.na(description), nzchar(description))
write_csv(jobs, file.path(processed_dir, "jobs.csv"))

summary <- tibble(
  snapshot_date = as.character(Sys.Date()), html_pages = 100L, api_pages = length(api_files),
  unique_html_listings = nrow(listings), unique_api_records = nrow(api_rows),
  api_jobs_with_descriptions = nrow(jobs),
  matched_html_api_jobs = sum(jobs$in_html_snapshot)
)
write_csv(summary, file.path(processed_dir, "collection_summary.csv"))
print(summary)
if (nrow(jobs) < 1000) warning("Fewer than 1,000 API jobs with descriptions; see collection_summary.csv")
