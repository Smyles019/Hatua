"""Logistic regression baseline on Kenya, for each item set."""
import json

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from hatua_ml.config import ARTEFACTS
from hatua_ml.features.item_sets import ITEM_SETS
from hatua_ml.features.prepare import model_inputs, risk_target
from hatua_ml.models.split import SEED, kenya_split, load_feature_table

TARGET_SENSITIVITY = 0.90


def make_model():
    return make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))


def choose_threshold(model, X, y) -> float:
    """Cut-off that flags 90% of off-track children, chosen on training data only."""
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    p = cross_val_predict(model, X, y, cv=cv, method="predict_proba")[:, 1]
    return float(np.quantile(p[np.asarray(y) == 1], 1 - TARGET_SENSITIVITY))


def evaluate(y, p, threshold) -> dict:
    y = np.asarray(y)
    flagged = p >= threshold
    return {
        "auc": float(roc_auc_score(y, p)),
        "sensitivity": float(flagged[y == 1].mean()),
        "specificity": float((~flagged[y == 0]).mean()),
        "n_test": int(len(y)),
    }


def train(item_set: str) -> dict:
    items = ITEM_SETS[item_set]
    train_df, test_df = kenya_split(load_feature_table())
    X_tr, y_tr = model_inputs(train_df, items), risk_target(train_df)
    X_te, y_te = model_inputs(test_df, items), risk_target(test_df)

    model = make_model()
    threshold = choose_threshold(model, X_tr, y_tr)
    model.fit(X_tr, y_tr)
    metrics = evaluate(y_te, model.predict_proba(X_te)[:, 1], threshold)

    out = ARTEFACTS / "logreg" / item_set
    out.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "items": items, "threshold": threshold}, out / "model.joblib")
    (out / "metrics.json").write_text(
        json.dumps({"item_set": item_set, "threshold": threshold, **metrics}, indent=2)
    )
    return metrics


if __name__ == "__main__":
    for name in ITEM_SETS:
        m = train(name)
        print(f"{name:7s} auc {m['auc']:.3f}  sensitivity {m['sensitivity']:.3f}  "
              f"specificity {m['specificity']:.3f}  (n={m['n_test']})")