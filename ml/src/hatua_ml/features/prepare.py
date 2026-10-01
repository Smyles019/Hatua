"""Turn feature-table rows into model inputs. Used in training and, later, by the API."""
import pandas as pd


def model_inputs(df: pd.DataFrame, items: list[str]) -> pd.DataFrame:
    X = pd.DataFrame(index=df.index)
    X["age_months"] = df["age_months"].astype(float)
    X["female"] = (df["sex"] == 2).astype(float)
    X[items] = df[items].astype(float).fillna(0)  # don't-know = not achieved, as in ECDI2030 scoring
    return X


def risk_target(df: pd.DataFrame) -> pd.Series:
    return (1 - df["on_track"]).astype(int)  # 1 = off track