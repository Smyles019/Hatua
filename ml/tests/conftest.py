"""Shared fixtures for the hatua_ml test suite."""
import pandas as pd
import pytest

from hatua_ml.features.ecdi2030 import ITEMS


@pytest.fixture
def sample():
    """A small ECDI2030 sample that passes validation. Floats so tests can insert NaN."""
    df = pd.DataFrame({
        "age_months": [24.0, 36.0, 48.0, 59.0],
        "weight": [1.0, 1.0, 1.0, 1.0],
        "on_track": [1.0, 0.0, 1.0, 1.0],
        "source": ["test"] * 4,
    })
    for item in ITEMS:
        df[item] = [1.0, 0.0, 1.0, 1.0]
    return df