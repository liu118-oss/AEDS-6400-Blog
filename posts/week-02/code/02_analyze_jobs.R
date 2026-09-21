# Run from the repository root after 01_scrape_jobs.R.
library(dplyr)
library(tidyr)
library(stringr)
library(readr)
library(ggplot2)

root <- "posts/week-02"
listings <- read_csv(file.path(root, "data/processed/html_listings.csv"), show_col_types = FALSE)
jobs <- read_csv(file.path(root, "data/processed/jobs.csv"), show_col_types = FALSE)
dir.create(file.path(root, "results"), recursive = TRUE, showWarnings = FALSE)

# Select software, data, and IT roles using titles. This is a deliberately
# auditable definition; it avoids treating every nontechnical job as evidence
# about demand for programming skills.
tech_title <- paste0(
  "software|entwickl|developer|development engineer|programmer|programmier|",
  "data scientist|data engineer|data analyst|datenanal|datenbank|",
  "devops|backend|front.?end|full.?stack|cloud engineer|platform engineer|",
  "site reliability|cyber|security engineer|\\bit\\b|",
  "systemadmin|informatik|web.?entwickl|machine learning|ml engineer|",
  "app developer|mobile developer|qa engineer|test automation|",
  "solutions architect|software architect|sap consultant"
)
tech_listings <- listings |>
  filter(str_detect(listing_title, regex(tech_title, ignore_case = TRUE)))
tech <- jobs |>
  filter(str_detect(title, regex(tech_title, ignore_case = TRUE))) |>
  mutate(role_group = case_when(
    str_detect(title, regex("data scientist|data engineer|data analyst|datenanal|machine learning|ml engineer", TRUE)) ~ "Data / ML",
    str_detect(title, regex("devops|cloud|platform|site reliability|systemadmin|cyber|security|\\bit\\b", TRUE)) ~ "Infrastructure / security",
    TRUE ~ "Software development"
  ),
  seniority = case_when(
    str_detect(title, regex("intern|praktik|werkstudent|junior|trainee|graduate", TRUE)) ~ "Early career",
    str_detect(title, regex("senior|staff|principal|lead|leiter|head of|director", TRUE)) ~ "Senior / lead",
    TRUE ~ "No level stated"
  ))

skills <- tibble(
  skill = c("Python", "JavaScript", "TypeScript", "React", "Node.js", "Java",
            "C#", "SQL", "PostgreSQL", "AWS", "Azure", "Google Cloud",
            "Docker", "Kubernetes", "Git", "Go", "PHP", "Ruby", "SAP", "Power BI"),
  pattern = c("\\bpython\\b", "\\bjavascript\\b", "\\btypescript\\b",
              "\\breact(?:\\.js)?\\b", "\\bnode(?:\\.js)?\\b", "\\bjava\\b",
              "(?<![[:alnum:]])c#(?![[:alnum:]])", "\\bsql\\b",
              "\\bpostgres(?:ql)?\\b", "\\baws\\b|amazon web services",
              "\\bazure\\b", "google cloud|\\bgcp\\b", "\\bdocker\\b",
              "\\bkubernetes\\b|\\bk8s\\b", "\\bgit\\b|\\bgithub\\b",
              "\\bgolang\\b|\\bgo language\\b", "\\bphp\\b", "\\bruby\\b",
              "\\bsap\\b", "\\bpower\\s*bi\\b")
)

long <- crossing(job_id = seq_len(nrow(tech)), skills) |>
  mutate(mentioned = mapply(function(i, p) {
    str_detect(paste(tech$title[i], tech$description[i]), regex(p, ignore_case = TRUE))
  }, job_id, pattern)) |>
  filter(mentioned) |>
  select(job_id, skill) |>
  left_join(tech |> mutate(job_id = row_number()) |>
              select(job_id, remote, role_group, seniority), by = "job_id")

skill_counts <- long |>
  count(skill, name = "postings") |>
  right_join(skills |> select(skill), by = "skill") |>
  mutate(postings = replace_na(postings, 0L),
         share_pct = round(100 * postings / nrow(tech), 1)) |>
  arrange(desc(postings), skill)

# Title mentions cover the entire 100-page listing sample. They are a separate,
# narrower measure: a skill may be required even if absent from the title.
title_mentions <- crossing(listing_id = seq_len(nrow(tech_listings)), skills) |>
  mutate(mentioned = mapply(function(i, p) {
    str_detect(tech_listings$listing_title[i], regex(p, ignore_case = TRUE))
  }, listing_id, pattern)) |>
  filter(mentioned) |>
  select(listing_id, skill)
title_skill_counts <- title_mentions |>
  count(skill, name = "titles") |>
  right_join(skills |> select(skill), by = "skill") |>
  mutate(titles = replace_na(titles, 0L),
         share_pct = round(100 * titles / nrow(tech_listings), 1)) |>
  arrange(desc(titles), skill)

remote_skill <- long |>
  count(remote, skill, name = "postings") |>
  complete(remote = c(FALSE, TRUE), skill = skills$skill,
           fill = list(postings = 0L)) |>
  mutate(total_jobs = if_else(remote, sum(tech$remote), sum(!tech$remote)),
         share_pct = round(100 * postings / total_jobs, 1))

role_skill <- long |>
  count(role_group, skill, name = "postings") |>
  left_join(tech |> count(role_group, name = "role_jobs"), by = "role_group") |>
  mutate(share_pct = round(100 * postings / role_jobs, 1)) |>
  arrange(role_group, desc(postings), skill)

role_counts <- tech |> count(role_group, name = "postings") |>
  mutate(share_pct = round(100 * postings / nrow(tech), 1)) |>
  arrange(desc(postings))
seniority_counts <- tech |> count(seniority, name = "postings") |>
  mutate(share_pct = round(100 * postings / nrow(tech), 1)) |>
  arrange(desc(postings))
work_mode_counts <- tech |>
  mutate(work_mode = if_else(remote, "Marked remote", "Not marked remote")) |>
  count(work_mode, name = "postings") |>
  mutate(share_pct = round(100 * postings / nrow(tech), 1))
remote_by_role <- tech |>
  group_by(role_group) |>
  summarise(total_jobs = n(), remote_jobs = sum(remote),
            remote_share_pct = round(100 * remote_jobs / total_jobs, 1),
            .groups = "drop") |>
  arrange(desc(remote_share_pct))
company_counts <- tech |> count(company, sort = TRUE, name = "postings") |>
  slice_head(n = 15)
location_counts <- tech |>
  mutate(location = if_else(is.na(location) | location == "", "Unspecified", location)) |>
  count(location, sort = TRUE, name = "postings") |>
  slice_head(n = 15)
skill_pairs <- long |> select(job_id, skill) |>
  inner_join(long |> select(job_id, skill), by = "job_id", suffix = c("_1", "_2"),
             relationship = "many-to-many") |>
  filter(skill_1 < skill_2) |>
  count(skill_1, skill_2, sort = TRUE, name = "postings") |>
  slice_head(n = 15)

summary <- tibble(all_html_listings = nrow(listings),
                  tech_titles_in_100_pages = nrow(tech_listings),
                  api_jobs_with_descriptions = nrow(jobs),
                  html_api_overlap = sum(jobs$in_html_snapshot),
                  tech_jobs_with_descriptions = nrow(tech),
                  tech_jobs_also_in_html = sum(tech$in_html_snapshot),
                  tech_share_pct = round(100 * nrow(tech) / nrow(jobs), 1),
                  remote_tech_jobs = sum(tech$remote),
                  remote_share_pct = round(100 * mean(tech$remote), 1),
                  jobs_with_named_skill = n_distinct(long$job_id),
                  skill_coverage_pct = round(100 * n_distinct(long$job_id) / nrow(tech), 1))

write_csv(tech, file.path(root, "data/processed/tech_jobs.csv"))
write_csv(tech_listings, file.path(root, "data/processed/tech_listings.csv"))
write_csv(long, file.path(root, "data/processed/skill_mentions.csv"))
for (name in c("summary", "skill_counts", "title_skill_counts", "remote_skill", "role_skill", "role_counts",
               "seniority_counts", "work_mode_counts", "remote_by_role", "company_counts", "location_counts", "skill_pairs")) {
  write_csv(get(name), file.path(root, "results", paste0(name, ".csv")))
}

p <- skill_counts |>
  slice_head(n = 12) |>
  mutate(skill = reorder(skill, share_pct)) |>
  ggplot(aes(skill, share_pct)) +
  geom_col(fill = "#236d83") +
  coord_flip() +
  scale_y_continuous(limits = c(0, max(skill_counts$share_pct) * 1.05)) +
  labs(title = "Named skills in technology job postings",
       subtitle = paste(nrow(tech), "software, data, and IT roles from 100 listing pages"),
       x = NULL, y = "Share of technology postings mentioning skill") +
  theme_minimal(base_size = 11) +
  theme(plot.background = element_rect(fill = "white", colour = NA))
ggsave(file.path(root, "results/skill_frequencies.png"), p, width = 8, height = 6, dpi = 160)

p_title <- title_skill_counts |>
  slice_head(n = 10) |>
  mutate(skill = reorder(skill, titles)) |>
  ggplot(aes(skill, titles)) +
  geom_col(fill = "#926c33") +
  coord_flip() +
  labs(title = "Named technologies in technology job titles",
       subtitle = paste(nrow(tech_listings), "technology-related titles across 100 pages"),
       x = NULL, y = "Number of job titles naming skill") +
  theme_minimal(base_size = 11) +
  theme(plot.background = element_rect(fill = "white", colour = NA))
ggsave(file.path(root, "results/title_skill_frequencies.png"), p_title,
       width = 8, height = 5, dpi = 160)

p_remote <- remote_by_role |>
  mutate(role_group = reorder(role_group, remote_share_pct)) |>
  ggplot(aes(role_group, remote_share_pct)) +
  geom_col(fill = "#72649A") +
  coord_flip() +
  scale_y_continuous(limits = c(0, max(remote_by_role$remote_share_pct) * 1.08)) +
  labs(title = "Share of technology postings marked remote, by role",
       subtitle = paste(nrow(tech), "technology postings in the API snapshot"),
       x = NULL, y = "Marked remote (%)") +
  theme_minimal(base_size = 11) +
  theme(plot.background = element_rect(fill = "white", colour = NA))
ggsave(file.path(root, "results/remote_by_role.png"), p_remote,
       width = 8, height = 4, dpi = 160)

print(summary)
print(head(skill_counts, 12))
print(head(skill_pairs, 5))
