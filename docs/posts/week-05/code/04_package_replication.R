# Run from the repository root after generating the analysis.
root <- "posts/week-05"
files <- c(file.path(root, c("README.md", "index.qmd", ".gitignore")),
  list.files(file.path(root, "code"), pattern = "\\.R$", full.names = TRUE),
  list.files(file.path(root, "data/processed"), full.names = TRUE),
  list.files(file.path(root, "data/raw"), pattern = "\\.(json|csv)$", full.names = TRUE),
  list.files(file.path(root, "results"), pattern = "\\.(png|csv|txt)$", full.names = TRUE))
stopifnot(all(file.exists(files)))
zipfile <- file.path(root, "results/replication.zip")
if (file.exists(zipfile)) unlink(zipfile)
utils::zip(zipfile, files = files, flags = "-q")
stopifnot(file.exists(zipfile), file.info(zipfile)$size > 0)
