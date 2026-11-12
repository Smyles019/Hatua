"""Odd-answer check for the under-24 model: flags caregiver reports whose answers do
not hang together for the child's age.

The KDHS flagger (anomaly.py) fills unanswered items with 0. That does not work here:
under 24 months each check asks only a few age-appropriate questions, so most items are
"not asked". Instead each answer is scored against what is typical at the child's age:

- one logistic curve per question: chance a child of this age has achieved it
  (fitted on the training visits that were asked it)
- surprise_yes: mean over answered questions of -log(chance) for "yes" answers, so
  "yes" to something few same-age children do scores high
- surprise_no: the same for "no" answers, with -log(1 - chance)

A plain Isolation Forest (the detector adopted in #29) learns which combinations of
age, surprise_yes and surprise_no are normal. The flag line is the top FLAG_RATE of
training visits, as for KDHS. Runtime only: training visits are never removed.

Run:  python -m hatua_ml.models.anomaly_under2
"""
import json

import joblib
import numpy as np
import pandas as pd
from pyod.models.iforest import IForest
from sklearn.linear_model import LogisticRegression

from hatua_ml.models.anomaly import FLAG_RATE, flag_threshold
from hatua_ml.models.split import SEED

AGE_MAX = 24.0
P_CLIP = (0.01, 0.99)
MIN_ANSWERED = 2  # fewer answers than this: never flagged (too little to judge)


class ItemCurve:
    """Chance a child of a given age has achieved one question."""

    def fit(self, age: np.ndarray, achieved: np.ndarray) -> "ItemCurve":
        if len(np.unique(achieved)) < 2:  # everyone asked gave the same answer
            self.const_ = float(np.clip(achieved.mean(), *P_CLIP))
            self.model_ = None
        else:
            self.const_ = None
            self.model_ = LogisticRegression(max_iter=1000).fit(age.reshape(-1, 1), achieved)
        return self

    def p(self, age: np.ndarray) -> np.ndarray:
        if self.model_ is None:
            return np.full(len(age), self.const_)
        return np.clip(self.model_.predict_proba(age.reshape(-1, 1))[:, 1], *P_CLIP)


class Under2Flagger:
    """Curves plus detector, saved and loaded as one object."""

    def fit(self, df: pd.DataFrame, items: list[str]) -> "Under2Flagger":
        self.items_ = list(items)
        self.curves_ = {}
        for i in self.items_:
            asked = df[df[i].notna()]
            self.curves_[i] = ItemCurve().fit(asked["age_months"].to_numpy(float),
                                              asked[i].to_numpy(int))
        X = self.features(df).drop(columns="n_answered")
        self.detector_ = IForest(random_state=SEED).fit(X.to_numpy())
        self.threshold_ = flag_threshold(self.score(df))
        return self

    def features(self, df: pd.DataFrame) -> pd.DataFrame:
        age = df["age_months"].to_numpy(float)
        yes_sum = np.zeros(len(df))
        no_sum = np.zeros(len(df))
        n = np.zeros(len(df))
        for i in self.items_:
            v = df[i].to_numpy(float)
            asked = ~np.isnan(v)
            if not asked.any():
                continue
            p = self.curves_[i].p(age)
            yes_sum += np.where(asked & (v == 1), -np.log(p), 0.0)
            no_sum += np.where(asked & (v == 0), -np.log(1 - p), 0.0)
            n += asked
        safe_n = np.maximum(n, 1)
        return pd.DataFrame({"age": age / AGE_MAX, "surprise_yes": yes_sum / safe_n,
                             "surprise_no": no_sum / safe_n, "n_answered": n},
                            index=df.index)

    def score(self, df: pd.DataFrame) -> np.ndarray:
        """Higher = more unusual. Reports with fewer than MIN_ANSWERED answers score -inf."""
        X = self.features(df)
        s = self.detector_.decision_function(X.drop(columns="n_answered").to_numpy())
        return np.where(X["n_answered"].to_numpy() >= MIN_ANSWERED, s, -np.inf)

    def flag(self, df: pd.DataFrame) -> np.ndarray:
        return self.score(df) >= self.threshold_


def inject_random(df: pd.DataFrame, items: list[str], rng) -> pd.DataFrame:
    """Each answered question gets a random yes or no: a careless or confused report."""
    out = df.copy()
    for i in items:
        asked = out[i].notna()
        out.loc[asked, i] = rng.integers(0, 2, asked.sum()).astype(float)
    return out


def inject_contradictory(df: pd.DataFrame, flagger: Under2Flagger) -> pd.DataFrame:
    """For each report: "no" to its easiest answered question and "yes" to its hardest,
    for the child's age. Hard skills present while easy ones are missing."""
    out = df.copy()
    for idx, row in out.iterrows():
        asked = [i for i in flagger.items_ if pd.notna(row[i])]
        if len(asked) < 2:
            continue
        p = {i: float(flagger.curves_[i].p(np.array([row["age_months"]]))[0]) for i in asked}
        easiest, hardest = max(p, key=p.get), min(p, key=p.get)
        out.at[idx, easiest], out.at[idx, hardest] = 0.0, 1.0
    return out


def main() -> None:
    from hatua_ml.config import ARTEFACTS
    from hatua_ml.models import anomaly_under2  # pickle under the package path
    from hatua_ml.models.train_under2 import load_table

    model_dir = ARTEFACTS / "xgboost_under2" / "short_30"
    items = joblib.load(model_dir / "model.joblib")["items"]
    table = load_table()
    train = table[table["split"] == "train"].reset_index(drop=True)
    test = table[table["split"] == "test"].reset_index(drop=True)

    flagger = anomaly_under2.Under2Flagger().fit(train, items)
    rng = np.random.default_rng(SEED)
    judged = test[items].notna().sum(axis=1) >= MIN_ANSWERED
    t = test[judged].reset_index(drop=True)
    rates = {
        "flag_rate_train": float(flagger.flag(train).mean()),
        "flag_rate_test_real": float(flagger.flag(t).mean()),
        "flag_rate_test_random": float(flagger.flag(inject_random(t, items, rng)).mean()),
        "flag_rate_test_contradictory":
            float(flagger.flag(inject_contradictory(t, flagger)).mean()),
        "flag_rate_test_real_delayed": float(flagger.flag(t[t["delayed"] == 1]).mean()),
    }
    metrics = {"detector": "iforest", "features": ["age", "surprise_yes", "surprise_no"],
               "flag_rate_target": FLAG_RATE, "threshold": flagger.threshold_,
               "n_train": len(train), "n_test_judged": len(t), **rates}
    joblib.dump(flagger, model_dir / "anomaly.joblib")
    (model_dir / "anomaly_metrics.json").write_text(json.dumps(metrics, indent=2))
    for k, v in rates.items():
        print(f"{k:32s} {v:.3f}")


if __name__ == "__main__":
    main()
