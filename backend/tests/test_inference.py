"""Inference service rules (#14): risk bands, release checks, age routing. No database."""
import pytest

from app.core.config import settings
from app.services import inference


@pytest.mark.parametrize("p, expected", [(0.10, "low"), (0.34, "low"), (0.35, "medium"),
                                         (0.79, "medium"), (0.80, "high"), (0.99, "high")])
def test_risk_bands(p, expected):
    assert inference.risk_level(p, threshold=0.35, high=0.80) == expected


def test_release_high_threshold_is_used(synthetic_release):
    release = inference.get_release()
    high, source = inference.high_threshold(release)
    assert source == "release" and high == release["high_threshold"] >= release["threshold"]


def test_old_release_falls_back_to_the_provisional_value():
    release = {"high_threshold": None, "threshold": 0.35}
    assert inference.high_threshold(release) == (inference.PROVISIONAL_HIGH_PROBABILITY,
                                                 "provisional")
    # never below the screening cut-off
    assert inference.high_threshold({"high_threshold": None, "threshold": 0.9})[0] == 0.9


def test_synthetic_release_is_refused_outside_development(synthetic_release):
    inference.get_release.cache_clear()
    settings.dev_mode = False
    try:
        with pytest.raises(inference.ModelNotAvailable, match="synthetic"):
            inference.get_release()
    finally:
        settings.dev_mode = True
        inference.get_release.cache_clear()


def test_missing_release_is_reported(synthetic_release):
    saved = settings.model_release
    settings.model_release = "9.9.9"
    inference.get_release.cache_clear()
    try:
        with pytest.raises(inference.ModelNotAvailable, match="9.9.9"):
            inference.get_release()
    finally:
        settings.model_release = saved
        inference.get_release.cache_clear()


@pytest.mark.parametrize("age, method", [(4, "milestone_check"), (23, "milestone_check"),
                                         (24, "model"), (59, "model")])
def test_age_routing(synthetic_release, age, method):
    assert inference.method_for_age(age) == method


@pytest.mark.parametrize("age", [0, 3, 60])
def test_ages_outside_coverage(synthetic_release, age):
    with pytest.raises(inference.AgeNotSupported):
        inference.method_for_age(age)


@pytest.mark.parametrize("age, band", [(5, "0-5"), (12, "12-17"), (23, "18-23"),
                                       (24, "24-29"), (47, "42-47"), (59, "48-59")])
def test_age_bands(age, band):
    assert inference.age_band(age) == band
