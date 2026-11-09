# Export childdevdata cohorts that cover 0-23 months, with D-scores, to one CSV.
# Run from the repo root:  Rscript ml/scripts/export_childdevdata.R
#
# dscore 2.x has a default key that does not cover these older instruments,
# so the key is set explicitly. Primary score: gsed2406 (current WHO GSED key).
# The original gcdg key is kept alongside for comparison.

options(repos = c(CRAN = "https://cloud.r-project.org"))
for (p in c("childdevdata", "dscore", "dplyr")) {
  if (!requireNamespace(p, quietly = TRUE)) install.packages(p)
}
suppressMessages({
  library(childdevdata)
  library(dscore)
  library(dplyr)
})

# Cohorts with children under 24 months (Madagascar starts at 2.8 years, so it is left out)
cohorts <- c(
  "gcdg_chl_1", "gcdg_chn", "gcdg_col_lt42m", "gcdg_col_lt45m",
  "gcdg_ecu", "gcdg_jam_lbw", "gcdg_jam_stunted", "gcdg_nld_smocc", "gcdg_zaf"
)

score <- function(df, items, key) {
  dscore(items = items, data = df, xname = "agedays", xunit = "days", key = key)
}

frames <- lapply(cohorts, function(name) {
  df <- get(name, envir = asNamespace("childdevdata"))
  items <- get_itemnames(df)
  g <- score(df, items, "gsed2406")
  o <- score(df, items, "gcdg")
  bind_cols(
    df,
    tibble(n_items = g$n, d = g$d, daz = g$daz,
           n_items_gcdg = o$n, d_gcdg = o$d, daz_gcdg = o$daz)
  )
})

all_rows <- bind_rows(frames) %>%
  filter(agedays < 731)  # keep 0-23 months only

out_dir <- file.path("data", "raw", "childdevdata")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
out_file <- file.path(out_dir, "childdevdata_under24.csv")
write.csv(all_rows, out_file, row.names = FALSE)

cat("Rows:", nrow(all_rows), "\n")
cat("Children:", n_distinct(paste(all_rows$cohort, all_rows$subjid)), "\n")
print(all_rows %>%
  group_by(cohort) %>%
  summarise(rows = n(),
            items_used = round(mean(n_items), 1),
            daz_ok_pct = round(100 * mean(!is.na(daz))),
            daz_gcdg_ok_pct = round(100 * mean(!is.na(daz_gcdg))),
            .groups = "drop"),
  n = Inf)
