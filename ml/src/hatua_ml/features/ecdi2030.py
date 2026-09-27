"""ECDI2030 item harmonisation and on-track scoring.

Items are stored as ecd21..ecd40 (KDHS) or EC21..EC40 (MICS). After
harmonisation every item is 1 = achieved, 0 = not achieved, NaN = don't know.
"""
import numpy as np
import pandas as pd

ITEMS = [f"ecd{i}" for i in range(21, 41)]
YES_NO_ITEMS = ITEMS[:18]  # ecd21..ecd38

# Age-specific cut-offs: minimum milestones achieved to be "on track".
AGE_BANDS = [(24, 29, 7), (30, 35, 9), (36, 41, 11), (42, 47, 13), (48, 59, 15)]


def harmonise(raw: pd.DataFrame, source: str) -> pd.DataFrame:
    """Return a frame of the 20 items coded 1/0/NaN.

    source: "dhs" (1 = yes, 0 = no, 8 = don't know)
            "mics" (1 = yes, 2 = no, 8 = don't know)
    """
    out = pd.DataFrame(index=raw.index)
    prefix = "ecd" if source == "dhs" else "EC"
    no_code = 0 if source == "dhs" else 2

    for i, item in enumerate(YES_NO_ITEMS, start=21):
        s = raw[f"{prefix}{i}"]
        out[item] = np.select([s == 1, s == no_code], [1, 0], default=np.nan)

    # Skip patterns: a follow-up item is not asked when the easier item is "no".
    # ecd27 (5+ word sentences) follows ecd26 (3+ words); ecd34 (count 10) follows ecd33 (give 3).
    out.loc[out["ecd26"] == 0, "ecd27"] = 0
    out.loc[(out["ecd33"] == 0) & out["ecd34"].isna(), "ecd34"] = 0

    # ecd39: how often very sad or depressed. Achieved if "a few times a year" or "never".
    s39 = raw[f"{prefix}39"]
    out["ecd39"] = np.select([s39.isin([4, 5]), s39.isin([1, 2, 3])], [1, 0], default=np.nan)

    # ecd40: kicks, bites or hits compared with other children.
    s40 = raw[f"{prefix}40"]
    if source == "dhs":   # 1 not at all, 2 same or less, 3 more, 4 a lot more
        achieved, not_achieved = [1, 2], [3, 4]
    else:                 # 1 not at all, 2 less, 3 same, 4 more, 5 a lot more
        achieved, not_achieved = [1, 2, 3], [4, 5]
    out["ecd40"] = np.select([s40.isin(achieved), s40.isin(not_achieved)], [1, 0], default=np.nan)
    return out


def cutoff_for_age(age_months: pd.Series) -> pd.Series:
    cut = pd.Series(np.nan, index=age_months.index)
    for lo, hi, c in AGE_BANDS:
        cut[(age_months >= lo) & (age_months <= hi)] = c
    return cut


def on_track(items: pd.DataFrame, age_months: pd.Series) -> pd.Series:
    """1 if developmentally on track, 0 if not. Don't-know counts as not achieved."""
    score = items[ITEMS].fillna(0).sum(axis=1)
    return (score >= cutoff_for_age(age_months)).astype("Int64")
