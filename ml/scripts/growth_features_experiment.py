"""Experiment: does adding height-for-age (HAZ) and weight-for-age (WAZ) z-scores to the
24-59 month short13 model help?

Same Kenya split, grid and 95%-sensitivity cut-off rule as hatua_ml.models.train_xgboost.
The z-scores are the KDHS 2022 ones (hw70, hw71: WHO 2006 standards, from measured
height and weight). Weight and height are optional in the app, so the growth model is
also scored with the measurements left out. Writes nothing; prints the comparison.

Run from ml/: python scripts/growth_features_experiment.py
"""
import json

import numpy as np
import pandas as pd
from sklearn.model_selection import GridSearchCV
from xgboost import XGBClassifier

from hatua_ml.config import KDHS_FILE
from hatua_ml.features.item_sets import SHORT_FORM_13
from hatua_ml.features.prepare import model_inputs, risk_target
from hatua_ml.models.evaluation import choose_threshold, cv, evaluate
from hatua_ml.models.split import SEED, kenya_split, load_feature_table
from hatua_ml.models.train_xgboost import PARAM_GRID


def kdhs_z_scores() -> pd.DataFrame:
    """HAZ and WAZ for the ECD-module children, in load_kdhs order. WHO flag limits:
    HAZ outside -6..6 and WAZ outside -6..5 are treated as missing."""
    raw = pd.read_stata(KDHS_FILE, convert_categoricals=False, columns=["ecd21", "hw70", "hw71"])
    raw = raw[raw["ecd21"].notna()].reset_index(drop=True)
    z = pd.DataFrame({"haz": raw["hw70"].where(raw["hw70"] < 9990) / 100,
                      "waz": raw["hw71"].where(raw["hw71"] < 9990) / 100})
    z.loc[(z["haz"] < -6) | (z["haz"] > 6), "haz"] = np.nan
    z.loc[(z["waz"] < -6) | (z["waz"] > 5), "waz"] = np.nan
    return z


def rounded(d: dict) -> dict:
    return {k: round(v, 4) if isinstance(v, float) else v for k, v in d.items()}


def main():
    z = kdhs_z_scores()
    table = load_feature_table()
    kenya = table["source"] == "kdhs_2022"
    assert kenya.sum() == len(z), "feature table and KDHS rows do not line up"
    table.loc[kenya, ["haz", "waz"]] = z[["haz", "waz"]].values
    train_df, test_df = kenya_split(table)

    k = table[kenya]
    print("measured share:", {c: round(float(k[c].notna().mean()), 3) for c in ["haz", "waz"]})
    for c in ["haz", "waz"]:
        print(f"mean {c}: on track {k.loc[k.on_track == 1, c].mean():.2f}, "
              f"off track {k.loc[k.on_track == 0, c].mean():.2f}")

    def inputs(df, growth):
        X = model_inputs(df, SHORT_FORM_13)
        if growth:
            X["haz"] = df["haz"].astype(float)
            X["waz"] = df["waz"].astype(float)
        return X

    y_tr, y_te = risk_target(train_df), risk_target(test_df)
    measured = (test_df["haz"].notna() | test_df["waz"].notna()).values
    results = {}
    for name, growth in [("short13 (now)", False), ("short13 + HAZ + WAZ", True)]:
        X_tr, X_te = inputs(train_df, growth), inputs(test_df, growth)
        search = GridSearchCV(XGBClassifier(eval_metric="logloss", random_state=SEED, n_jobs=1),
                              PARAM_GRID, scoring="roc_auc", cv=cv(), n_jobs=-1)
        search.fit(X_tr, y_tr)
        m = search.best_estimator_
        thr = choose_threshold(m, X_tr, y_tr)
        row = {"cv_auc": round(float(search.best_score_), 4), "params": search.best_params_,
               "threshold": round(thr, 4),
               "test": rounded(evaluate(y_te, m.predict_proba(X_te)[:, 1], thr)),
               "test_measured_children": rounded(
                   evaluate(y_te[measured], m.predict_proba(X_te[measured])[:, 1], thr))}
        if growth:
            blank = X_te.copy()
            blank[["haz", "waz"]] = np.nan
            row["test_measurements_left_out"] = rounded(evaluate(y_te, m.predict_proba(blank)[:, 1], thr))
            gain = m.get_booster().get_score(importance_type="total_gain")
            total = sum(gain.values())
            row["share_of_gain"] = {f: round(v / total, 3) for f, v in
                                    sorted(gain.items(), key=lambda kv: -kv[1])[:6]}
        results[name] = row
    print(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
