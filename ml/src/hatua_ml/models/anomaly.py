"""Flag caregiver reports whose answer pattern looks inconsistent for the child's age.

Used at runtime only: a flagged report goes to the CHW for follow-up. Training
children are never removed on the basis of these scores.
"""
import numpy as np
import pandas as pd
from pyod.models.dif import DIF
from pyod.models.iforest import IForest
from sklearn.linear_model import LogisticRegression

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
    "dif": lambda: DIF(random_state=SEED),  # Deep Isolation Forest (proposal)
    "dif_small": lambda: DIF(hidden_neurons=[32], representation_dim=8, random_state=SEED),
    "iforest": lambda: IForest(random_state=SEED),  # plain Isolation Forest
}


class AgeNorm:
    """Expected number of items achieved at a given age, learned from training children.

    One logistic curve per item (pass rate rising with age); the expected count at an
    age is the sum of the item pass probabilities at that age.
    """

    def fit(self, df: pd.DataFrame, items: list[str]) -> "AgeNorm":
        age = df[["age_months"]].astype(float)
        self.curves_ = [
            LogisticRegression(max_iter=1000).fit(age, df[item].fillna(0).astype(int))
            for item in items
        ]
        return self

    def expected(self, age_months) -> np.ndarray:
        age = pd.DataFrame({"age_months": np.asarray(age_months, dtype=float)})
        return np.sum([c.predict_proba(age)[:, 1] for c in self.curves_], axis=0)


def flag_threshold(train_scores: np.ndarray) -> float:
    """Score above which a report is flagged: the top FLAG_RATE of training children."""
    return float(np.quantile(train_scores, 1 - FLAG_RATE))


class AnomalyFlagger:
    """Detector plus everything it needs at runtime, saved and loaded as one object."""

    def __init__(self, kind: str = "iforest", age_norm: bool = False):
        # Shipped: plain Isolation Forest. DIF and the ahead-of-age feature were
        # benchmarked and not adopted (see anomaly_benchmark.py).
        self.kind, self.age_norm = kind, age_norm

    def inputs(self, df: pd.DataFrame) -> pd.DataFrame:
        """Age scaled to 0-1, the milestone answers and, optionally, how far the child is
        ahead of (+) or behind (-) the typical count for their age. Sex is left out: it
        says nothing about whether a set of answers hangs together."""
        X = model_inputs(df, self.items_).drop(columns="female")
        if self.age_norm:
            achieved = X[self.items_].sum(axis=1).to_numpy()
            X["ahead_of_age"] = (achieved - self.norm_.expected(X["age_months"])) / len(self.items_)
        X["age_months"] = (X["age_months"] - AGE_MIN) / (AGE_MAX - AGE_MIN)
        return X

    def fit(self, df: pd.DataFrame, items: list[str]) -> "AnomalyFlagger":
        self.items_ = list(items)
        self.norm_ = AgeNorm().fit(df, self.items_) if self.age_norm else None
        self.detector_ = DETECTORS[self.kind]()
        self.detector_.fit(self.inputs(df).to_numpy(dtype=float))
        self.threshold_ = flag_threshold(self.score(df))
        return self

    def score(self, df: pd.DataFrame) -> np.ndarray:
        """Higher = more unusual."""
        return self.detector_.decision_function(self.inputs(df).to_numpy(dtype=float))

    def flag(self, df: pd.DataFrame) -> np.ndarray:
        return self.score(df) >= self.threshold_


def train(kind: str, item_set: str, age_norm: bool = False) -> dict:
    """Fit on Kenya training children only and save the flagger."""
    items = ITEM_SETS[item_set]
    train_df, _ = kenya_split(load_feature_table())
    flagger = AnomalyFlagger(kind, age_norm).fit(train_df, items)
    metrics = {"detector": kind, "age_norm": age_norm, "item_set": item_set,
               "flag_rate": FLAG_RATE, "n_train": len(train_df)}
    save_artefacts(ARTEFACTS / "anomaly" / kind / item_set, flagger, items,
                   flagger.threshold_, metrics)
    return {"threshold": flagger.threshold_, **metrics}


if __name__ == "__main__":
    # Train through the package path so the saved flagger is recorded as
    # hatua_ml.models.anomaly.AnomalyFlagger, not __main__.AnomalyFlagger,
    # which nothing else (tests, the API) could load.
    from hatua_ml.models import anomaly

    for name in ITEM_SETS:
        m = anomaly.train("iforest", name)
        print(f"iforest {name:7s} threshold {m['threshold']:.3f}  (n_train={m['n_train']})")
