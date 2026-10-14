"""Flag caregiver reports whose answer pattern looks inconsistent for the child's age.

Used at runtime only: a flagged report goes to the CHW for follow-up. Training
children are never removed on the basis of these scores.
"""
import numpy as np
import pandas as pd
from pyod.models.dif import DIF
from pyod.models.iforest import IForest

from hatua_ml.config import ARTEFACTS
from hatua_ml.features.item_sets import ITEM_SETS
from hatua_ml.features.prepare import model_inputs
from hatua_ml.models.evaluation import save_artefacts
from hatua_ml.models.split import SEED, kenya_split, load_feature_table

# ECDI2030 age window in KDHS 2022. Revisit when under-24-month norms land (#32).
AGE_MIN, AGE_MAX = 24.0, 59.0

# Share of real training children allowed above the flag line. A starting point.
FLAG_RATE = 0.05

DETECTORS = {
    "dif": lambda: DIF(random_state=SEED),          # Deep Isolation Forest (proposal)
    "iforest": lambda: IForest(random_state=SEED),  # plain Isolation Forest (comparison)
}


def anomaly_inputs(df: pd.DataFrame, items: list[str]) -> pd.DataFrame:
    """Age scaled to 0-1 plus the milestone answers. Sex is left out: it says
    nothing about whether a set of answers hangs together."""
    X = model_inputs(df, items).drop(columns="female")
    X["age_months"] = (X["age_months"] - AGE_MIN) / (AGE_MAX - AGE_MIN)
    return X


def fit_detector(kind: str, X: pd.DataFrame):
    """Fit one detector. PyOD scores: higher = more unusual."""
    detector = DETECTORS[kind]()
    detector.fit(X.to_numpy(dtype=float))
    return detector


def scores(detector, X: pd.DataFrame) -> np.ndarray:
    return detector.decision_function(X.to_numpy(dtype=float))


def flag_threshold(train_scores: np.ndarray) -> float:
    """Score above which a report is flagged: the top FLAG_RATE of training children."""
    return float(np.quantile(train_scores, 1 - FLAG_RATE))


def train(kind: str, item_set: str) -> dict:
    """Fit on Kenya training children only, set the flag line, save the artefacts."""
    items = ITEM_SETS[item_set]
    train_df, _ = kenya_split(load_feature_table())
    X = anomaly_inputs(train_df, items)

    detector = fit_detector(kind, X)
    threshold = flag_threshold(scores(detector, X))
    metrics = {"detector": kind, "item_set": item_set, "flag_rate": FLAG_RATE, "n_train": len(X)}
    save_artefacts(ARTEFACTS / "anomaly" / kind / item_set, detector, items, threshold, metrics)
    return {"threshold": threshold, **metrics}


if __name__ == "__main__":
    for kind in DETECTORS:
        for name in ITEM_SETS:
            m = train(kind, name)
            print(f"{kind:8s} {name:7s} threshold {m['threshold']:.3f}  (n_train={m['n_train']})")
