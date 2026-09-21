# Optional continuation of the public API cache toward 1,000 technology roles.
# Run from the repository root. Stops immediately on HTTP 429 or other errors.
library(jsonlite)
library(stringr)

cache <- "posts/week-02/data/raw/api"
dir.create(cache, recursive = TRUE, showWarnings = FALSE)
tech_title <- paste0(
  "software|entwickl|developer|development engineer|programmer|programmier|",
  "data scientist|data engineer|data analyst|datenanal|datenbank|",
  "devops|backend|front.?end|full.?stack|cloud engineer|platform engineer|",
  "site reliability|cyber|security engineer|\\bit\\b|systemadmin|",
  "informatik|web.?entwickl|machine learning|ml engineer|app developer|",
  "mobile developer|qa engineer|test automation|solutions architect|",
  "software architect|sap consultant"
)
seen <- new.env(parent = emptyenv(), hash = TRUE)
tech_count <- 0L
add_page <- function(path) {
  response <- fromJSON(path, simplifyVector = FALSE)
  if (is.null(response$data)) stop("Invalid API page: ", path)
  if (length(response$data) == 0) return(0L)
  for (job in response$data) {
    if (is.null(job$url) || exists(job$url, envir = seen, inherits = FALSE)) next
    assign(job$url, TRUE, envir = seen)
    if (str_detect(job$title, regex(tech_title, ignore_case = TRUE)))
      tech_count <<- tech_count + 1L
  }
  invisible(length(response$data))
}

for (page in 1:120) {
  path <- file.path(cache, sprintf("page-%03d.json", page))
  if (file.exists(path) && file.size(path) > 0) {
    n_records <- add_page(path)
  } else {
    if (tech_count >= 1000) break
    url <- paste0("https://www.arbeitnow.com/api/job-board-api?page=", page)
    temporary <- paste0(path, ".partial")
    if (file.exists(temporary)) file.remove(temporary)
    ok <- tryCatch({
      download.file(url, temporary, mode = "wb", quiet = TRUE)
      n_records <- add_page(temporary)
      file.rename(temporary, path)
    }, error = function(e) {
      message("Stopped at page ", page, ": ", conditionMessage(e))
      FALSE
    })
    if (!ok) break
    Sys.sleep(8)
  }
  if (n_records == 0) {
    message("Reached the end of the public API at page ", page)
    break
  }
  if (page %% 5 == 0 || tech_count >= 1000)
    message("Through API page ", page, ": ", tech_count, " unique technology roles")
  if (tech_count >= 1000) break
}
message("Cached technology roles: ", tech_count)
