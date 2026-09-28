"""Sanity checks on a loaded ECDI2030 sample."""
import pandas as pd

from hatua_ml.features.ecdi2030 import ITEMS

AGE_MIN, AGE_MAX = 24, 59
REQUIRED = ["age_months", "weight", "on_track", "source", *ITEMS]
BINARY = [0, 1, True, False]


class SampleValidationError(ValueError):
    """A loaded sample breaks an assumption the rest of the pipeline relies on."""


def validate_sample(df: pd.DataFrame, name: str) -> pd.DataFrame:
    """Return df unchanged if it passes all checks, else raise with every problem found."""
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise SampleValidationError(f"{name}: missing columns {missing}")
    if df.empty:
        raise SampleValidationError(f"{name}: sample is empty")

    problems = []

    age = df["age_months"]
    if age.isna().any():
        problems.append(f"{age.isna().sum()} rows with missing age")
    outside = ~age.dropna().between(AGE_MIN, AGE_MAX)
    if outside.any():
        problems.append(f"{outside.sum()} rows with age outside {AGE_MIN}-{AGE_MAX} months")

    w = df["weight"]
    bad_w = w.isna() | (w <= 0)
    if bad_w.any():
        problems.append(f"{bad_w.sum()} rows with missing or non-positive weight")

    bad_items = [c for c in ITEMS if not df[c].dropna().isin(BINARY).all()]
    if bad_items:
        problems.append(f"items with values other than 0/1: {bad_items}")

    no_answers = df[ITEMS].isna().all(axis=1)
    if no_answers.any():
        problems.append(f"{no_answers.sum()} rows with no ECDI item answers (not in the ECD module?)")
        
    ot = df["on_track"]
    if ot.isna().all():
        problems.append("on_track is missing for every row")
    elif not ot.dropna().isin(BINARY).all():
        problems.append("on_track has values other than 0/1")

    if problems:
        raise SampleValidationError(f"{name} failed validation:\n  - " + "\n  - ".join(problems))
    return df