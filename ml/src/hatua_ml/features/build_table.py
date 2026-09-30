"""Model-ready feature table: one row per child, only inputs the app can collect."""
import pandas as pd

from hatua_ml.config import PROCESSED
from hatua_ml.data.load_kdhs import load_kdhs
from hatua_ml.data.load_mics import load_mics
from hatua_ml.features.ecdi2030 import ITEMS

FEATURES = ["age_months", "sex", *ITEMS]
COLUMNS = ["source", *FEATURES, "on_track", "weight"]
FEATURE_TABLE = PROCESSED / "feature_table.csv"


def build_feature_table() -> pd.DataFrame:
    frames = [load_kdhs(), load_mics("eswatini"), load_mics("comoros")]
    return pd.concat([f[COLUMNS] for f in frames], ignore_index=True)


if __name__ == "__main__":
    table = build_feature_table()
    FEATURE_TABLE.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(FEATURE_TABLE, index=False)
    print(table.groupby("source")["on_track"].agg(n="size", on_track_rate="mean").round(3))
    print(f"saved {len(table)} rows to {FEATURE_TABLE}")