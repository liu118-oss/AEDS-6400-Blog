# AEDS 6400 Blog — Jin Liu

This is the single active Quarto website repository connected to GitHub:
https://github.com/liu118-oss/AEDS-6400-Blog

## Articles

- Week 1: eigenvalues and eigenvectors — `posts/week-01/index.qmd`
- Week 2: skills in job postings — [replication instructions](posts/week-02/README.md)
- Week 3: education and unemployment — [replication instructions](posts/week-03/README.md)
- Week 4: housing affordability — [replication instructions](posts/week-04/README.md)
- Week 5: Pennsylvania rent burden — [article source](posts/week-05/index.qmd) and [replication instructions](posts/week-05/README.md).

Source articles live in `posts/`; rendered website files live in `docs/`. Follow each post's README for analysis dependencies and data access. With Quarto and the required R/Python dependencies installed, `quarto render` builds the website. Review the generated pages and links before committing or publishing.

Week 2 raw collection caches and Week 3 restricted microdata are local resources excluded from Git. Their README files explain replication and data access. Week 5 uses public file downloads without an API key.
