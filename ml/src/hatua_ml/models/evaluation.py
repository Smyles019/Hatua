"""Cut-off choice, test metrics and saving, shared by every model."""
import json

import joblib
import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict

from hatua_ml.models.split import SEED

TARGET_SENSITIVITY = 0.95  # missing an off-track child is the costlier error (#27)

# Second cut-off, splitting flagged children into medium and high risk. "High" means
# at most 1 in 100 on-track training children score this high, so a high result
# rarely comes from a child who is in fact on track.
HIGH_RISK_SPECIFICITY = 0.99


def cv():
    return StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)


def cv_probabilities(model, X, y) -> np.ndarray:
    """Out-of-fold risk probabilities for the training children (model is refitted per fold)."""
    return cross_val_predict(model, X, y, cv=cv(), method="predict_proba")[:, 1]


def choose_threshold(model, X, y) -> float:
    """Cut-off that flags TARGET_SENSITIVITY of off-track children, chosen on training data only."""
    p = cv_probabilities(model, X, y)
    return float(np.quantile(p[np.asarray(y) == 1], 1 - TARGET_SENSITIVITY))


def choose_high_threshold(p: np.ndarray, y, threshold: float) -> float:
    """Cut-off for "high" risk: the HIGH_RISK_SPECIFICITY quantile of on-track children's
    out-of-fold probabilities. Never below the screening cut-off, so every high result
    is also a flagged result."""
    on_track = p[np.asarray(y) == 0]
    return float(max(np.quantile(on_track, HIGH_RISK_SPECIFICITY), threshold))


def evaluate(y, p, threshold) -> dict:
    y = np.asarray(y)
    flagged = p >= threshold
    return {
        "auc": float(roc_auc_score(y, p)),
        "sensitivity": float(flagged[y == 1].mean()),
        "specificity": float((~flagged[y == 0]).mean()),
        "n_test": int(len(y)),
    }


def save_artefacts(out, model, items, threshold, metrics: dict) -> None:
    out.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "items": items, "threshold": threshold}, out / "model.joblib")
    (out / "metrics.json").write_text(json.dumps({"threshold": threshold, **metrics}, indent=2))