"""Check the backend's WHO z-scores (backend/app/services/growth.py) against the KDHS 2022
ones (hw70 height-for-age, hw71 weight-for-age), computed by DHS from the same WHO 2006
standard. Uses measured weight (hw2, kg x10), height (hw3, cm x10) and age in days from
the interview and birth dates. Writes nothing; prints how closely they agree.

Run from ml/: python scripts/check_growth_zscores.py
"""
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app.services.growth import DAYS_PER_MONTH, z_score  # noqa: E402

from hatua_ml.config import KDHS_FILE  # noqa: E402

COLS = ["b4", "b1", "b2", "hw16", "v006", "v007", "v016", "hw2", "hw3", "hw70", "hw71"]
raw = pd.read_stata(KDHS_FILE, convert_categoricals=False, columns=COLS)
d = raw[(raw.hw2 < 9990) & (raw.hw3 < 9990) & (raw.hw70 < 9990) & (raw.hw71 < 9990)
        & raw.hw16.between(1, 31)].copy()


def days(r):
    try:
        return (date(int(r.v007), int(r.v006), int(r.v016)) - date(int(r.b2), int(r.b1), int(r.hw16))).days
    except ValueError:
        return np.nan


d["days"] = d.apply(days, axis=1)
d = d[d.days.between(0, 1856)]
d["months"] = d.days / DAYS_PER_MONTH
d["sex"] = np.where(d.b4 == 2, "female", "male")
d["waz"] = [z_score("weight_for_age", s, m, w / 10) for s, m, w in zip(d.sex, d.months, d.hw2)]
d["haz"] = [z_score("height_for_age", s, m, h / 10) for s, m, h in zip(d.sex, d.months, d.hw3)]

for ours, theirs, name in [("waz", "hw71", "weight-for-age"), ("haz", "hw70", "height-for-age")]:
    diff = (d[ours] - d[theirs] / 100).abs()
    agree = ((d[ours] < -2) == (d[theirs] / 100 < -2)).mean()
    print(f"{name}: n={len(d)}  median |diff| {diff.median():.3f}  95th pct {diff.quantile(.95):.3f}  "
          f"same side of -2: {agree:.2%}")
