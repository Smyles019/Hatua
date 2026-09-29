"""Our weighted on-track rates must stay close to the published KDHS 2022 figures."""
import pandas as pd
import pytest

from hatua_ml.config import KDHS_FILE
from hatua_ml.data.load_kdhs import load_kdhs

# KDHS 2022 Key Indicators Report, Table 13 (percentage developmentally on track)
PUBLISHED = {
    "Total": 77.9, "24-35": 82.8, "36-47": 77.4, "48-59": 73.8,
    "Male": 76.3, "Female": 79.7, "Urban": 87.4, "Rural": 72.7,
}
TOLERANCE = 1.5  # percentage points; observed max difference is 1.1

pytestmark = pytest.mark.skipif(not KDHS_FILE.is_file(), reason="KDHS 2022 file not available")


@pytest.fixture(scope="module")
def rates():
    d = load_kdhs()

    def pct(g):
        return (g["on_track"] * g["weight"]).sum() / g["weight"].sum() * 100

    out = {"Total": pct(d)}
    bands = pd.cut(d["age_months"], [23, 35, 47, 59], labels=["24-35", "36-47", "48-59"])
    for k, g in d.groupby(bands, observed=True):
        out[str(k)] = pct(g)
    for k, g in d.groupby(d["sex"].map({1: "Male", 2: "Female"})):
        out[k] = pct(g)
    for k, g in d.groupby(d["residence"].map({1: "Urban", 2: "Rural"})):
        out[k] = pct(g)
    return out


@pytest.mark.parametrize("group, published", PUBLISHED.items())
def test_matches_published_rate(rates, group, published):
    assert rates[group] == pytest.approx(published, abs=TOLERANCE)
    