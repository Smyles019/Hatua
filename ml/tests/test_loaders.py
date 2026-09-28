import pytest

from hatua_ml.config import KDHS_FILE, MICS_FILES
from hatua_ml.data.files import DataFileNotFoundError
from hatua_ml.data.load_kdhs import load_kdhs
from hatua_ml.data.load_mics import load_mics


def weighted_on_track(d):
    return (d.on_track * d.weight).sum() / d.weight.sum()


# --- Error handling (no data needed) ---

def test_unknown_mics_country():
    with pytest.raises(ValueError, match="Unknown MICS country"):
        load_mics("atlantis")


def test_kdhs_missing_file(tmp_path):
    with pytest.raises(DataFileNotFoundError):
        load_kdhs(tmp_path / "KEKR8CFL.DTA")


def test_mics_missing_file(tmp_path):
    with pytest.raises(DataFileNotFoundError):
        load_mics("comoros", tmp_path / "ch.sav")


# --- Regression on real data (skipped if files are absent) ---

@pytest.mark.skipif(not KDHS_FILE.is_file(), reason="KDHS 2022 file not available")
def test_kdhs_known_sample():
    d = load_kdhs()
    assert len(d) == 5478
    assert d.age_months.between(24, 59).all()
    assert weighted_on_track(d) == pytest.approx(0.771, abs=0.0005)


@pytest.mark.parametrize("country, n, rate", [
    ("eswatini", 1378, 0.466),
    ("comoros", 1846, 0.324),
])
def test_mics_known_sample(country, n, rate):
    if not MICS_FILES[country].is_file():
        pytest.skip(f"MICS {country} file not available")
    d = load_mics(country)
    assert len(d) == n
    assert weighted_on_track(d) == pytest.approx(rate, abs=0.0005)