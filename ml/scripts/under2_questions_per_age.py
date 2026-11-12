"""How many short-form questions does a caregiver actually see at each age?

Uses training visits only. A question "belongs" to a band if at least 10% of
visits in that band answered it.
Run from ml/:  python scripts/under2_questions_per_age.py
"""
import joblib
import pandas as pd

from hatua_ml.config import ARTEFACTS, ROOT
from hatua_ml.features.build_under2_table import UNDER2_TABLE

BANDS = [(0, 5), (6, 11), (12, 17), (18, 23)]
SHARE = 0.10

t = pd.read_csv(UNDER2_TABLE)
t = t[t["split"] == "train"]
items = joblib.load(ARTEFACTS / "xgboost_under2" / "short_30" / "model.joblib")["items"]
labels = pd.read_csv(ROOT / "ml" / "src" / "hatua_ml" / "features" / "ddi_items.csv").set_index("item")

rows, lists = [], []
for lo, hi in BANDS:
    band = t[(t["age_months"] >= lo) & (t["age_months"] < hi + 1)]
    answered = band[items].notna()
    share = answered.mean()
    in_band = share[share >= SHARE].index.tolist()
    rows.append({"band": f"{lo}-{hi}", "visits": len(band),
                 "per_visit_mean": round(answered.sum(axis=1).mean(), 1),
                 "per_visit_max": int(answered.sum(axis=1).max()),
                 "questions_in_band": len(in_band)})
    for i in in_band:
        lists.append({"band": f"{lo}-{hi}", "item": i, "share_asked": round(share[i], 2),
                      "domain": labels.loc[i, "domain"], "mode": labels.loc[i, "mode"],
                      "label": labels.loc[i, "label"]})

summary = pd.DataFrame(rows)
print(summary.to_string(index=False))
out = ROOT / "ml" / "reports" / "under2_questions_per_age.csv"
pd.DataFrame(lists).to_csv(out, index=False)
print("saved", out)
