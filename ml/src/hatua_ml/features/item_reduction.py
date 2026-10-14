"""Item reduction (#27): how few ECDI2030 questions keep the classification.

Everything here uses Kenya TRAINING children only (complete cases), with 5-fold
cross-validation. The held-out test children are touched only by the final models.

Run:  python -m hatua_ml.features.item_reduction             (order + curve + figure)
      python -m hatua_ml.features.item_reduction --stability (adds 50 resamples, ~11 min)
"""
import sys
from collections import Counter

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from hatua_ml.config import ROOT
from hatua_ml.features.ecdi2030 import ITEMS
from hatua_ml.models.split import SEED

SENSITIVITIES = (0.90, 0.95)
N_BOOT = 50
REPORTS = ROOT / "ml" / "reports"


def cv():
    return StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)


def selector():
    """Simple, fast model used only to rank questions."""
    return make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))


def training_data(train_df: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray]:
    """Complete-case items + age, and the risk target (1 = off track)."""
    complete = train_df.dropna(subset=ITEMS).reset_index(drop=True)
    X = complete[ITEMS + ["age_months"]].astype(float)
    y = (1 - complete["on_track"]).astype(int).to_numpy()
    return X, y


def forward_select(X: pd.DataFrame, y, k_max: int = len(ITEMS)) -> list[str]:
    """Add one question at a time, each time the one that most raises CV AUC.
    Age is always included."""
    selected, remaining = [], list(ITEMS)
    while remaining and len(selected) < k_max:
        scores = {item: cross_val_score(selector(), X[selected + [item, "age_months"]], y,
                                        cv=cv(), scoring="roc_auc").mean()
                  for item in remaining}
        best = max(scores, key=scores.get)
        selected.append(best)
        remaining.remove(best)
    return selected


def operating_curve(X: pd.DataFrame, y, order: list[str]) -> pd.DataFrame:
    """For each number of questions k: out-of-fold AUC, and specificity at each target
    sensitivity, plus missed and wrongly flagged children per 100 screened."""
    y = np.asarray(y)
    off = y.mean()
    rows = []
    for k in range(1, len(order) + 1):
        cols = order[:k] + ["age_months"]
        p = cross_val_predict(selector(), X[cols], y, cv=cv(), method="predict_proba")[:, 1]
        row = {"k": k, "added": order[k - 1], "auc": roc_auc_score(y, p)}
        for sens in SENSITIVITIES:
            t = np.quantile(p[y == 1], 1 - sens)
            caught, spec = (p[y == 1] >= t).mean(), (p[y == 0] < t).mean()
            tag = int(round(sens * 100))
            row[f"specificity_{tag}"] = spec
            row[f"missed_per_100_{tag}"] = 100 * off * (1 - caught)
            row[f"false_flags_per_100_{tag}"] = 100 * (1 - off) * (1 - spec)
        rows.append(row)
    return pd.DataFrame(rows)


def stability(X: pd.DataFrame, y, k: int, n_boot: int = N_BOOT) -> pd.Series:
    """Share of bootstrap resamples of the training children in which each question
    lands in the first k selected."""
    rng = np.random.default_rng(SEED)
    y = np.asarray(y)
    counts = Counter()
    for _ in range(n_boot):
        idx = rng.integers(0, len(X), len(X))
        counts.update(forward_select(X.iloc[idx].reset_index(drop=True), y[idx], k))
    return pd.Series({item: counts[item] / n_boot for item in ITEMS}).sort_values(ascending=False)


def plot_curve(curve: pd.DataFrame, path) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(curve.k, curve.auc, "k-o", label="AUC")
    ax.plot(curve.k, curve.specificity_95, "k--s", label="Specificity at 95% sensitivity")
    ax.plot(curve.k, curve.specificity_90, "k:^", label="Specificity at 90% sensitivity")
    ax.set_xlabel("Number of questions asked")
    ax.set_ylabel("Cross-validated score (training children)")
    ax.set_xticks(range(1, len(curve) + 1))
    ax.set_ylim(0.4, 1.0)
    ax.grid(alpha=0.3)
    ax.legend()
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def main(with_stability: bool = False) -> None:
    from hatua_ml.models.split import kenya_split, load_feature_table

    train_df, _ = kenya_split(load_feature_table())
    X, y = training_data(train_df)
    order = forward_select(X, y)
    curve = operating_curve(X, y, order)
    (REPORTS / "figures").mkdir(parents=True, exist_ok=True)
    curve.to_csv(REPORTS / "item_reduction_curve.csv", index=False)
    plot_curve(curve, REPORTS / "figures" / "item_reduction_curve.png")
    print("order:", order)
    print(curve.round(3).to_string(index=False))

    if with_stability:
        from hatua_ml.features.item_sets import SHORT_FORM_13

        freq = stability(X, y, k=len(SHORT_FORM_13))
        freq.rename("share_of_resamples").to_csv(REPORTS / "item_reduction_stability.csv")
        print(freq.round(2).to_string())


if __name__ == "__main__":
    main(with_stability="--stability" in sys.argv)
