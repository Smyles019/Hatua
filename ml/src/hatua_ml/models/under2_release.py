"""Files the API needs for the under-24 model, written next to the model.

items_by_month.json: for each completed month 0-23, the short-form questions to ask,
    in the order the model ranks them. A question is asked at a month if at least
    MIN_SHARE of training visits at that month (plus or minus one month) answered it,
    matching what the Dutch clinics asked at that age.
Also prints how the model does on test children when gestational age is unknown,
since the app does not collect it yet.

Run:  python -m hatua_ml.models.under2_release
"""
import json

import joblib
import numpy as np

from hatua_ml.config import ARTEFACTS
from hatua_ml.models.evaluation import evaluate
from hatua_ml.models.train_under2 import inputs, load_table

MODEL_DIR = ARTEFACTS / "xgboost_under2" / "short_30"
MIN_SHARE = 0.20


def items_by_month(train, items: list[str]) -> dict[str, list[str]]:
    out = {}
    month = train["age_months"].astype(int)
    for m in range(24):
        near = train[(month >= m - 1) & (month <= m + 1)]
        share = near[items].notna().mean()
        out[str(m)] = [i for i in items if share[i] >= MIN_SHARE]
    return out


def main() -> None:
    art = joblib.load(MODEL_DIR / "model.joblib")
    items, model, t = art["items"], art["model"], art["threshold"]
    table = load_table()
    train = table[table["split"] == "train"]
    test = table[table["split"] == "test"]

    by_month = items_by_month(train, items)
    (MODEL_DIR / "items_by_month.json").write_text(json.dumps(by_month, indent=2))
    counts = {m: len(v) for m, v in by_month.items()}
    print("questions per month:", counts)

    y = test["delayed"].to_numpy()
    X = inputs(test, items)
    X_no_gest = X.assign(gest_weeks=np.nan)
    for name, data in [("with gestational age", X), ("gestational age unknown", X_no_gest)]:
        m = evaluate(y, model.predict_proba(data)[:, 1], t)
        print(f"{name:24s} auc {m['auc']:.3f} sens {m['sensitivity']:.3f} spec {m['specificity']:.3f}")


if __name__ == "__main__":
    main()
