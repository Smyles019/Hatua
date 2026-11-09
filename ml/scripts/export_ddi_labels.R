# Write labels and domains for the Dutch DDI items used by the under-24 model.
# Run from the repo root:  Rscript ml/scripts/export_ddi_labels.R
suppressMessages(library(dscore))
ib <- dscore::builtin_itembank
ddi <- unique(ib[substr(ib$item, 1, 3) == "ddi", c("item", "label", "domain", "mode")])
ddi <- ddi[!duplicated(ddi$item), ]
out <- file.path("ml", "src", "hatua_ml", "features", "ddi_items.csv")
write.csv(ddi[order(ddi$item), ], out, row.names = FALSE)
cat("items:", nrow(ddi), "\n")
print(table(ddi$domain, useNA = "ifany"))
print(table(ddi$mode, useNA = "ifany"))
