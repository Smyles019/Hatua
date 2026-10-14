"""Compare anomaly detectors on real Kenya test children mixed with injected
inconsistent reports (#29). No real child is labelled anomalous; only the fakes are."""
import time

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from hatua_ml.config import ROOT
from hatua_ml.features.item_sets import ITEM_SETS
from hatua_ml.models.anomaly import AGE_MIN, AnomalyFlagger
from hatua_ml.models.split import SEED, kenya_split, load_feature_table

N_FAKE = 300  # per kind of fake report

# label: (detector kind, use the ahead-of-age feature)
CANDIDATES = {
    "dif": ("dif", False),
    "dif_small": ("dif_small", False),
    "iforest": ("iforest", False),
    "dif_age": ("dif", True),
    "iforest_age": ("iforest", True),
}

REPORT = ROOT / "ml" / "reports" / "anomaly_benchmark.csv"


def by_difficulty(train_df: pd.DataFrame, items: list[str]) -> list[str]:
    """Items from easiest to hardest, by pass rate among training children."""
    return list(train_df[items].fillna(0).mean().sort_values(ascending=False).index)


def reversed_reports(test_df, items, order, seed) -> pd.DataFrame:
    """Keep each child's number of achieved items, but put them on the hardest items."""
    achieved = test_df[items].fillna(0).sum(axis=1)
    pool = test_df[(achieved > 0) & (achieved < len(items))]  # all-or-nothing cannot be reversed
    rows = pool.sample(N_FAKE, replace=True, random_state=seed).reset_index(drop=True)
    k = rows[items].fillna(0).sum(axis=1).to_numpy()
    out = rows[["age_months", "sex"]].copy()
    for rank, item in enumerate(reversed(order)):  # hardest first
        out[item] = (rank < k).astype(float)
    return out


def random_reports(test_df, items, seed) -> pd.DataFrame:
    """Coin-flip answers with a real child's age and sex."""
    rng = np.random.default_rng(seed)
    rows = test_df.sample(N_FAKE, replace=True, random_state=seed).reset_index(drop=True)
    out = rows[["age_months", "sex"]].copy()
    for item in items:
        out[item] = rng.integers(0, 2, N_FAKE).astype(float)
    return out


def age_mismatch_reports(test_df, items, seed) -> pd.DataFrame:
    """Answers of a 54-59-month-old who achieved almost everything, relabelled as 24 months."""
    achieved = test_df[items].fillna(0).sum(axis=1)
    pool = test_df[(test_df["age_months"] >= 54) & (achieved >= len(items) - 1)]
    rows = pool.sample(N_FAKE, replace=True, random_state=seed).reset_index(drop=True)
    out = rows[["sex", *items]].copy()
    out["age_months"] = AGE_MIN
    return out


def run() -> pd.DataFrame:
    train_df, test_df = kenya_split(load_feature_table())
    rows = []
    for item_set, items in ITEM_SETS.items():
        fakes = {
            "reversed": reversed_reports(test_df, items, by_difficulty(train_df, items), SEED),
            "random": random_reports(test_df, items, SEED + 1),
            "age_mismatch": age_mismatch_reports(test_df, items, SEED + 2),
        }
        for label, (kind, age_norm) in CANDIDATES.items():
            start = time.perf_counter()
            flagger = AnomalyFlagger(kind, age_norm).fit(train_df, items)
            fit_seconds = time.perf_counter() - start

            s_real = flagger.score(test_df)
            row = {"item_set": item_set, "detector": label, "fit_seconds": round(fit_seconds, 1),
                   "false_flag_real": float((s_real >= flagger.threshold_).mean())}
            s_fakes = []
            for name, df in fakes.items():
                s = flagger.score(df)
                row[f"caught_{name}"] = float((s >= flagger.threshold_).mean())
                s_fakes.append(s)
            s_fake = np.concatenate(s_fakes)
            labels = np.r_[np.zeros(len(s_real)), np.ones(len(s_fake))]
            row["auc_real_vs_fake"] = float(roc_auc_score(labels, np.r_[s_real, s_fake]))
            rows.append(row)
            print(f"{item_set:7s} {label:12s} done in {fit_seconds:.1f}s", flush=True)

    table = pd.DataFrame(rows)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(REPORT, index=False)
    return table


if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore", message=".*pin_memory.*")
    print(run().round(3).to_string(index=False))
