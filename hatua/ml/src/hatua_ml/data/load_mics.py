"""Load ECDI2030 samples from MICS6 child files (Eswatini 2021, Comoros 2022)."""
import pandas as pd
import pyreadstat

from hatua_ml.config import MICS_FILES
from hatua_ml.features.ecdi2030 import ITEMS, harmonise, on_track


def load_mics(country: str) -> pd.DataFrame:
    raw, _ = pyreadstat.read_sav(str(MICS_FILES[country]))
    raw = raw[raw["EC21"].notna()].copy()
    df = pd.DataFrame({
        "age_months": raw["CAGE"],
        "sex": raw["HL4"] if "HL4" in raw else pd.NA,
        "weight": raw["chweight"],
    })
    df = df.join(harmonise(raw, "mics"))
    df = df[df["age_months"] >= 24]                  # ECDI2030 range
    df["on_track"] = on_track(df[ITEMS], df["age_months"])
    df["source"] = f"mics_{country}"
    return df.reset_index(drop=True)


if __name__ == "__main__":
    for c in MICS_FILES:
        d = load_mics(c)
        w = d["weight"]
        print(f"{c}: n={len(d)} ages {d.age_months.min()}-{d.age_months.max()}  "
              f"on track (weighted) {(d.on_track * w).sum() / w.sum():.1%}")
