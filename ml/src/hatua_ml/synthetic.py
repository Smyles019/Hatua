"""A small model release built from synthetic children, for tests and demos only.

It has the same files, manifest and items as a real release, so the API can be tested
end to end without the survey data. Its numbers mean nothing about real children and it
must never be served to users: the manifest says "synthetic" in fitted_on and the API
refuses to serve it outside tests (see backend app.services.inference).
"""
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBClassifier

from hatua_ml.export import write_release
from hatua_ml.features.item_sets import SHORT_FORM_13
from hatua_ml.features.prepare import model_inputs, risk_target
from hatua_ml.models.anomaly import AnomalyFlagger
from hatua_ml.models.evaluation import choose_high_threshold, cv_probabilities
from hatua_ml.models.explain import Explainer

SYNTHETIC = "synthetic data (tests only)"


def synthetic_children(n: int = 1500, seed: int = 0) -> pd.DataFrame:
    """Children aged 24-59 months whose pass rates rise with age; about a quarter off track."""
    rng = np.random.default_rng(seed)
    age = rng.integers(24, 60, n).astype(float)
    ability = rng.normal(0, 1, n)
    df = pd.DataFrame({"age_months": age, "sex": rng.integers(1, 3, n)})
    for k, item in enumerate(SHORT_FORM_13):
        logit = (age - 30 - k) / 6 + 1.5 * ability
        df[item] = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(float)
    expected = 13 * (age - 18) / 45
    df["on_track"] = (df[SHORT_FORM_13].sum(axis=1) >= expected - 1).astype(int)
    return df


def build(out: Path, version: str = "0.0.0-synthetic") -> Path:
    df = synthetic_children()
    items = SHORT_FORM_13
    X, y = model_inputs(df, items), risk_target(df)
    model = XGBClassifier(n_estimators=60, max_depth=2, learning_rate=0.2,
                          eval_metric="logloss", random_state=0, n_jobs=1).fit(X, y)
    p = cv_probabilities(model, X, y)
    threshold = float(np.quantile(p[y == 1], 0.05))
    high = choose_high_threshold(p, y, threshold)
    flagger = AnomalyFlagger("iforest").fit(df, items)
    return write_release(
        Path(out) / version, version=version, item_set="short13", model=model, items=items,
        threshold=threshold, high_threshold=high, flagger=flagger,
        explainer=Explainer(model, items, X, threshold),
        test_metrics={"note": SYNTHETIC}, fitted_on=SYNTHETIC)


if __name__ == "__main__":
    import sys

    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("synthetic_release")
    print("synthetic release written to", build(target))
