"""Under-24-month XGBoost model on the SMOCC table, with item reduction.

Differences from the KDHS model (train_xgboost.py):
- Blank items stay blank (NaN). Each visit only asks age-appropriate questions,
  so a blank means "not asked", not "not achieved". XGBoost handles NaN natively.
- Cross-validation groups by child, so no child sits in two folds.
- Items are ranked by XGBoost gain (forward selection with logistic regression
  cannot handle the blanks).

Cut-offs are chosen on out-of-fold training probabilities only:
- screening cut-off flags TARGET_SENSITIVITY (95%) of delayed training visits
- "high" cut-off as in evaluation.choose_high_threshold

Run:  python -m hatua_ml.models.train_under2
"""
import json

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold, cross_val_predict
from xgboost import XGBClassifier

from hatua_ml.config import ARTEFACTS, ROOT
from hatua_ml.data.files import require_file
from hatua_ml.features.build_under2_table import ITEM_PREFIX, UNDER2_TABLE
from hatua_ml.models.evaluation import (
    TARGET_SENSITIVITY, choose_high_threshold, evaluate, save_artefacts,
)
from hatua_ml.models.split import SEED

OUT = ARTEFACTS / "xgboost_under2"
REPORTS = ROOT / "ml" / "reports"
BASE = ["age_months", "female", "gest_weeks"]
AUC_TOLERANCE = 0.01  # shortest item list whose CV AUC is within this of the full list

PARAM_GRID = {
    "n_estimators": [300, 600],
    "max_depth": [2, 3, 4],
    "learning_rate": [0.05, 0.1],
}


def load_table() -> pd.DataFrame:
    return pd.read_csv(require_file(UNDER2_TABLE, "Under-2 table (run: python -m hatua_ml.features.build_under2_table)"))


def item_names(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c.startswith(ITEM_PREFIX)]


def inputs(df: pd.DataFrame, items: list[str]) -> pd.DataFrame:
    X = pd.DataFrame(index=df.index)
    X["age_months"] = df["age_months"].astype(float)
    X["female"] = (df["sex"] == 2).astype(float)
    X["gest_weeks"] = df["gest_weeks"].astype(float)
    X[items] = df[items].astype(float)  # NaN kept: not asked
    return X


def make_model(**params):
    return XGBClassifier(eval_metric="logloss", random_state=SEED, n_jobs=1, **params)


def group_cv():
    return StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)


def oof(model, X, y, groups) -> np.ndarray:
    return cross_val_predict(model, X, y, cv=group_cv(), groups=groups,
                             method="predict_proba")[:, 1]


def screening_threshold(p, y) -> float:
    return float(np.quantile(p[np.asarray(y) == 1], 1 - TARGET_SENSITIVITY))


def rank_items(model, items: list[str]) -> list[str]:
    gain = model.get_booster().get_score(importance_type="gain")
    return sorted(items, key=lambda i: gain.get(i, 0.0), reverse=True)


def reduction_curve(train, y, groups, order, params) -> pd.DataFrame:
    rows = []
    for k in range(1, len(order) + 1):
        X = inputs(train, order[:k])
        p = oof(make_model(**params), X, y, groups)
        t = screening_threshold(p, y)
        rows.append({"k": k, "added": order[k - 1], "auc": roc_auc_score(y, p),
                     "specificity_95": float((p[y == 0] < t).mean())})
        print(f"k={k:2d} auc={rows[-1]['auc']:.3f} spec95={rows[-1]['specificity_95']:.3f}", flush=True)
    return pd.DataFrame(rows)


def fit_final(name, train, test, items, params) -> dict:
    y_tr, y_te = train["delayed"].to_numpy(), test["delayed"].to_numpy()
    X_tr, X_te = inputs(train, items), inputs(test, items)
    p_oof = oof(make_model(**params), X_tr, y_tr, train["child_id"])
    t = screening_threshold(p_oof, y_tr)
    t_high = choose_high_threshold(p_oof, y_tr, t)
    model = make_model(**params).fit(X_tr, y_tr)
    p_te = model.predict_proba(X_te)[:, 1]

    strict = (test["daz"] < -2).to_numpy()  # sensitivity against the -2 line, reported too
    metrics = {
        "item_set": name, "n_items": len(items),
        **evaluate(y_te, p_te, t),
        "precision": float(y_te[p_te >= t].mean()),
        "sensitivity_daz_below_2": float((p_te[strict] >= t).mean()),
        "high_threshold": t_high,
        "cv_auc": float(roc_auc_score(y_tr, p_oof)),
        "n_test_children": int(test["child_id"].nunique()),
        "params": params,
    }
    save_artefacts(OUT / name, model, items, t, metrics)
    return metrics


def main() -> None:
    table = load_table()
    train = table[table["split"] == "train"].reset_index(drop=True)
    test = table[table["split"] == "test"].reset_index(drop=True)
    items = item_names(table)
    y, groups = train["delayed"].to_numpy(), train["child_id"]

    search = GridSearchCV(make_model(), PARAM_GRID, scoring="roc_auc", cv=group_cv(), n_jobs=-1)
    search.fit(inputs(train, items), y, groups=groups)
    params = search.best_params_
    print("best params:", params, "cv auc", round(search.best_score_, 3), flush=True)

    order = rank_items(search.best_estimator_, items)
    curve = reduction_curve(train, y, groups, order, params)
    REPORTS.mkdir(parents=True, exist_ok=True)
    curve.to_csv(REPORTS / "under2_item_reduction_curve.csv", index=False)

    full_auc = curve["auc"].iloc[-1]
    k = int(curve.loc[curve["auc"] >= full_auc - AUC_TOLERANCE, "k"].min())
    print(f"chosen k = {k} (full-list CV auc {full_auc:.3f})", flush=True)

    results = [fit_final("full", train, test, items, params),
               fit_final(f"short_{k}", train, test, order[:k], params)]
    (OUT / "summary.json").write_text(json.dumps(results, indent=2))
    for m in results:
        print(f"{m['item_set']:9s} items {m['n_items']:2d} auc {m['auc']:.3f} "
              f"sens {m['sensitivity']:.3f} spec {m['specificity']:.3f} "
              f"prec {m['precision']:.3f} sens(daz<-2) {m['sensitivity_daz_below_2']:.3f}")


if __name__ == "__main__":
    main()
