"""External validation (#31): saved Kenya models applied, unchanged, to other countries.

Nothing is refitted: same model, same items, same Kenya cut-off. The Kenya test
split is included as the reference row. Confidence intervals are 95% percentile
bootstrap intervals over children.

Run: python -m hatua_ml.models.external_validation
"""
import joblib
import numpy as np
import pandas as pd

from hatua_ml.config import ARTEFACTS, ROOT
from hatua_ml.features.item_sets import ITEM_SETS
from hatua_ml.features.prepare import model_inputs, risk_target
from hatua_ml.models.evaluation import evaluate
from hatua_ml.models.split import SEED, kenya_split, load_feature_table

EXTERNAL = ("mics_eswatini", "mics_comoros")
MODELS = ("xgboost", "logreg")
N_BOOT = 1000
REPORT = ROOT / "ml" / "reports" / "external_validation.csv"


def cohorts(table: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Kenya test split plus every external country, keyed by name."""
    _, kenya_test = kenya_split(table)
    out = {"kenya_test": kenya_test}
    for source in EXTERNAL:
        out[source] = table[table["source"] == source]
    return out


def bootstrap_ci(y, p, threshold, n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """95% percentile intervals for AUC, sensitivity and specificity."""
    y, p = np.asarray(y), np.asarray(p)
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(y), len(y))
        if y[idx].min() == y[idx].max():  # resample with one class only: skip
            continue
        draws.append(evaluate(y[idx], p[idx], threshold))
    d = pd.DataFrame(draws)
    return {f"{k}_{side}": float(d[k].quantile(q))
            for k in ("auc", "sensitivity", "specificity")
            for side, q in (("lo", 0.025), ("hi", 0.975))}


def score_cohort(bundle: dict, df: pd.DataFrame) -> dict:
    p = bundle["model"].predict_proba(model_inputs(df, bundle["items"]))[:, 1]
    y = risk_target(df)
    return {"n": len(df), "off_track_rate": float(y.mean()),
            "flagged_rate": float((p >= bundle["threshold"]).mean()),
            **evaluate(y, p, bundle["threshold"]), **bootstrap_ci(y, p, bundle["threshold"])}


def anomaly_rate(item_set: str, df: pd.DataFrame) -> float | None:
    """Share of real children the saved Kenya anomaly flagger marks as unusual."""
    path = ARTEFACTS / "anomaly" / "iforest" / item_set / "model.joblib"
    if not path.is_file():
        return None
    return float(joblib.load(path)["model"].flag(df).mean())


def run() -> pd.DataFrame:
    groups = cohorts(load_feature_table())
    rows = []
    for name in MODELS:
        for item_set in ITEM_SETS:
            bundle = joblib.load(ARTEFACTS / name / item_set / "model.joblib")
            for cohort, df in groups.items():
                rows.append({"model": name, "item_set": item_set, "cohort": cohort,
                             **score_cohort(bundle, df),
                             "anomaly_flag_rate": anomaly_rate(item_set, df)})
    table = pd.DataFrame(rows)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(REPORT, index=False)
    return table


if __name__ == "__main__":
    t = run()
    cols = ["model", "item_set", "cohort", "n", "off_track_rate", "auc", "sensitivity",
            "sensitivity_lo", "sensitivity_hi", "specificity", "specificity_lo",
            "specificity_hi", "anomaly_flag_rate"]
    print(t[cols].round(3).to_string(index=False))
