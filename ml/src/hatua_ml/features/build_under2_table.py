"""Labelled under-24-month table from the Dutch SMOCC cohort (childdevdata).

One row per clinic visit. Label: delayed = D-score-for-age (daz) below -1.5.
risk_band: "high" below -2, "medium" from -2 to -1.5, "low" otherwise.
Train/test split is by child, so no child appears in both sets.

Input: data/raw/childdevdata/childdevdata_under24.csv
       (made by ml/scripts/export_childdevdata.R)
"""
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from hatua_ml.config import PROCESSED, RAW
from hatua_ml.data.files import require_file

UNDER24_CSV = RAW / "childdevdata" / "childdevdata_under24.csv"
UNDER2_TABLE = PROCESSED / "under2_table.csv"

COHORT = "GCDG-NLD-SMOCC"
DELAY_CUTOFF = -1.5
HIGH_CUTOFF = -2.0
SEED = 42
TEST_FOLDS = 5  # one fold of five, about 20% of children, is the test set

ITEM_PREFIX = "ddi"
BASE_FEATURES = ["age_months", "sex", "gest_weeks"]


def load_under24() -> pd.DataFrame:
    path = require_file(UNDER24_CSV, "childdevdata export (run: Rscript ml/scripts/export_childdevdata.R)")
    return pd.read_csv(path, low_memory=False)


def item_columns(df: pd.DataFrame) -> list[str]:
    """DDI items the cohort actually answered."""
    cols = [c for c in df.columns if c.startswith(ITEM_PREFIX)]
    return [c for c in cols if df[c].notna().any()]


def risk_band(daz: pd.Series) -> pd.Series:
    band = pd.Series("low", index=daz.index)
    band[daz < DELAY_CUTOFF] = "medium"
    band[daz < HIGH_CUTOFF] = "high"
    return band


def child_split(df: pd.DataFrame) -> pd.Series:
    """Return 'train' or 'test' per row, grouped by child and stratified by label."""
    cv = StratifiedGroupKFold(n_splits=TEST_FOLDS, shuffle=True, random_state=SEED)
    _, test_idx = next(cv.split(df, df["delayed"], groups=df["child_id"]))
    split = pd.Series("train", index=df.index)
    split.iloc[test_idx] = "test"
    return split


def build_under2_table(raw: pd.DataFrame | None = None) -> pd.DataFrame:
    raw = load_under24() if raw is None else raw
    df = raw[(raw["cohort"] == COHORT) & raw["daz"].notna()].copy()
    items = item_columns(df)

    out = pd.DataFrame({
        "child_id": df["cohort"] + "_" + df["subjid"].astype(str),
        "age_months": df["agedays"] / 30.4375,
        "sex": df["sex"].map({"male": 1, "female": 2}),  # same coding as KDHS
        "gest_weeks": df["gagebrth"] / 7,
    })
    out = pd.concat([out, df[items]], axis=1)
    out["daz"] = df["daz"]
    out["delayed"] = (df["daz"] < DELAY_CUTOFF).astype(int)
    out["risk_band"] = risk_band(df["daz"])
    out = out.reset_index(drop=True)
    out["split"] = child_split(out)
    return out


if __name__ == "__main__":
    table = build_under2_table()
    UNDER2_TABLE.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(UNDER2_TABLE, index=False)
    items = [c for c in table.columns if c.startswith(ITEM_PREFIX)]
    print(f"rows {len(table)} | children {table['child_id'].nunique()} | items {len(items)}")
    print(table.groupby("split").agg(rows=("delayed", "size"),
                                     children=("child_id", "nunique"),
                                     delayed_rate=("delayed", "mean")).round(3))
    print(table["risk_band"].value_counts().to_dict())
    print(f"saved to {UNDER2_TABLE}")
