"""Tests for the WHO motor check (#32), the high-risk cut-off and the synthetic release."""
import json

import numpy as np
import pytest

from hatua_ml.export import FILES, ReleaseError, load_release
from hatua_ml.features.item_sets import SHORT_FORM_13
from hatua_ml.models.evaluation import HIGH_RISK_SPECIFICITY, choose_high_threshold
from hatua_ml.norms import who_motor
from hatua_ml.synthetic import SYNTHETIC, build


# --- WHO motor windows ---

def answers(age, value=1, **override):
    return {i: override.get(i, value) for i in who_motor.items_for_age(age)}


def test_items_follow_the_window_starts():
    assert who_motor.items_for_age(4) == ["who_sit"]
    assert who_motor.items_for_age(23) == [m.item for m in who_motor.MILESTONES]


@pytest.mark.parametrize("age", [0, 3, 24, 40])
def test_ages_outside_the_check_are_refused(age):
    with pytest.raises(who_motor.AgeNotCovered):
        who_motor.items_for_age(age)


def test_all_achieved_is_low():
    r = who_motor.assess(20, answers(20))
    assert r["risk_level"] == "low" and r["overdue"] == [] and r["status"] == "on_track"


def test_not_yet_walking_inside_the_window_is_not_overdue():
    r = who_motor.assess(14, answers(14, who_walk_alone=0))
    assert r["risk_level"] == "low"


def test_one_overdue_is_medium_two_is_high():
    one = who_motor.assess(18, answers(18, who_walk_alone=0))
    assert one["risk_level"] == "medium"
    assert one["overdue"] == [{"item": "who_walk_alone", "domain": "motor",
                               "months_past_window": 0.4}]
    two = who_motor.assess(18, answers(18, who_walk_alone=0, who_stand_alone=0))
    assert two["risk_level"] == "high"
    assert [o["item"] for o in two["overdue"]] == ["who_stand_alone", "who_walk_alone"]


def test_crawling_and_dont_know_are_never_overdue():
    r = who_motor.assess(20, answers(20, who_crawl=0, who_walk_alone=None))
    assert r["risk_level"] == "low"


def test_walking_without_sitting_is_flagged_as_inconsistent():
    assert who_motor.assess(15, answers(15, who_sit=0))["consistency_flag"]
    assert not who_motor.assess(15, answers(15))["consistency_flag"]


def test_missing_answer_is_refused():
    with pytest.raises(ValueError, match="missing"):
        who_motor.assess(10, {"who_sit": 1})


# --- high-risk cut-off ---

def test_high_threshold_is_the_specificity_quantile_and_never_below_screening():
    rng = np.random.default_rng(1)
    y = np.r_[np.zeros(1000), np.ones(200)]
    p = np.r_[rng.uniform(0, 0.5, 1000), rng.uniform(0.3, 1, 200)]
    high = choose_high_threshold(p, y, threshold=0.3)
    assert high == pytest.approx(np.quantile(p[:1000], HIGH_RISK_SPECIFICITY))
    assert (p[:1000] >= high).mean() <= 1 - HIGH_RISK_SPECIFICITY + 0.002
    assert choose_high_threshold(p, y, threshold=0.9) == 0.9


# --- synthetic release ---

@pytest.fixture(scope="module")
def release(tmp_path_factory):
    return build(tmp_path_factory.mktemp("rel"))


def test_synthetic_release_loads_and_is_marked_synthetic(release):
    loaded = load_release(release)
    m = loaded["manifest"]
    assert sorted(p.name for p in release.iterdir()) == sorted([*FILES, "manifest.json"])
    assert loaded["items"] == SHORT_FORM_13 and m["anomaly"]["fitted_on"] == SYNTHETIC
    assert loaded["threshold"] <= loaded["high_threshold"] < 1


def test_release_without_high_threshold_still_loads(release, tmp_path):
    import shutil

    old = tmp_path / "old"
    shutil.copytree(release, old)
    m = json.loads((old / "manifest.json").read_text())
    del m["risk"]["high_threshold"]
    (old / "manifest.json").write_text(json.dumps(m))
    assert load_release(old)["high_threshold"] is None


def test_synthetic_release_is_never_overwritten(release):
    with pytest.raises(ReleaseError, match="already exists"):
        build(release.parent)
