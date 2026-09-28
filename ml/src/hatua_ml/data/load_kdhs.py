"""Load the ECD sample (24 to 59 months) from the KDHS 2022 Children's Recode."""
import pandas as pd

from hatua_ml.config import KDHS_FILE
from hatua_ml.data.files import require_file
from hatua_ml.features.ecdi2030 import ITEMS, harmonise, on_track

CONTEXT = {
    "b19": "age_months",
    "b4": "sex",
    "v024": "county",
    "v025": "residence",
    "v106": "mother_education",
    "v190": "wealth_quintile",
    "hw70": "height_for_age_z",
    "v005": "weight_raw",
    "v021": "psu",
    "v022": "strata",
}


def load_kdhs(path=KDHS_FILE) -> pd.DataFrame:
    path = require_file(path, "KDHS 2022 Children's Recode (KEKR8CFL.DTA)")
    raw = pd.read_stata(path, convert_categoricals=False)
    raw = raw[raw["ecd21"].notna()].copy()          # children in the ECD module only
    df = raw[list(CONTEXT)].rename(columns=CONTEXT)
    df["weight"] = df.pop("weight_raw") / 1e6
    df["height_for_age_z"] = df["height_for_age_z"].where(df["height_for_age_z"] < 9990) / 100
    df = df.join(harmonise(raw, "dhs"))
    df["on_track"] = on_track(df[ITEMS], df["age_months"])
    df["source"] = "kdhs_2022"
    return df.reset_index(drop=True)


if __name__ == "__main__":
    d = load_kdhs()
    w = d["weight"]
    print(f"Children: {len(d)}  ages {d.age_months.min()}-{d.age_months.max()} months")
    print(f"On track (weighted): {(d.on_track * w).sum() / w.sum():.1%}  off track n = {(d.on_track == 0).sum()}")
