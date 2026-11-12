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


# --- under-24 model (issue 5: age routing) ---

@pytest.mark.parametrize("age", [0, 3, 12, 23])
def test_under2_model_covers_0_to_23(synthetic_release, under2_model, age):
    assert inference.method_for_age(age) == "model"
    assert inference.model_version(age) == under2_model["version"]
    assert inference.model_version(24) != under2_model["version"]


def test_without_under2_model_falls_back_to_who_check(synthetic_release):
    assert inference.method_for_age(10) == "milestone_check"
    assert inference.model_version(10) == "who-mgrs-2006"


def test_under2_questions_follow_the_child_month(under2_model):
    for age in range(24):
        items = inference.items_for_age(age)
        assert 1 <= len(items) <= 15
        assert set(items) <= set(under2_model["items"])


def test_under2_inputs_keep_unasked_and_dont_know_blank(under2_model):
    items = under2_model["items"]
    X = inference.under2_inputs(7, "female", {items[0]: 1.0, items[1]: None}, items)
    assert list(X.columns) == ["age_months", "female", "gest_weeks", *items]
    assert X.loc[0, "age_months"] == 7.5 and X.loc[0, "female"] == 1.0
    assert X.loc[0, "gest_weeks"] == inference.DEFAULT_GEST_WEEKS
    assert X.loc[0, items[0]] == 1.0 and X[items[1:]].isna().all(axis=None)


def test_under2_assessment_shape_and_risk(synthetic_release, under2_model):
    age = 9
    items = inference.items_for_age(age)
    all_yes = inference.assess(age, "male", {i: 1.0 for i in items})
    all_no = inference.assess(age, "male", {i: 0.0 for i in items})
    assert all_yes["method"] == all_no["method"] == "model"
    assert all_yes["risk_level"] == "low"
    assert all_no["risk_level"] in ("medium", "high")
    domains = all_no["explanation"]["domains"]
    assert domains["cognitive"]["status"] == domains["social_emotional"]["status"] == "not_assessed"
    assert all_no["explanation"]["top_reasons"]
    assert all("question" in r for r in all_no["explanation"]["top_reasons"])
    # odd-answer check is loaded and scores reports with enough answers
    assert under2_model["flagger"] is not None
    assert isinstance(all_yes["anomaly_flag"], bool)
    if len(items) >= 2:
        assert isinstance(all_yes["details"]["anomaly_score"], float)


def test_under2_contradictory_report_is_flagged(synthetic_release, under2_model):
    """"No" to the easiest questions for the age and "yes" to the hardest."""
    import numpy as np

    flagger = under2_model["flagger"]
    age = 10
    items = inference.items_for_age(age)
    p = {i: float(flagger.curves_[i].p(np.array([age + 0.5]))[0]) for i in items}
    ranked = sorted(items, key=p.get)  # hardest first
    half = len(ranked) // 2
    coded = {i: (1.0 if k < half else 0.0) for k, i in enumerate(ranked)}
    assert inference.assess(age, "female", coded)["anomaly_flag"] is True
