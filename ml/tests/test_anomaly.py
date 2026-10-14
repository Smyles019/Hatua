"""Tests for the runtime anomaly flagger (#29)."""
import json

import joblib
import numpy as np
import pandas as pd
import pytest

from hatua_ml.config import ARTEFACTS
from hatua_ml.features.build_table import FEATURE_TABLE
from hatua_ml.features.item_sets import ITEM_SETS
from hatua_ml.models.anomaly import FLAG_RATE, AgeNorm, AnomalyFlagger, flag_threshold

ITEMS = [f"i{n}" for n in range(6)]  # synthetic items, easiest first


def reports(ages, achieved, hardest_first=False):
    """Children who pass `achieved` items, starting from the easiest (or the hardest)."""
    order = ITEMS[::-1] if hardest_first else ITEMS
    df = pd.DataFrame({"age_months": np.asarray(ages, dtype=float), "sex": 1})
    for rank, item in enumerate(order):
        df[item] = (rank < np.asarray(achieved)).astype(float)
    return df


@pytest.fixture(scope="module")
def consistent():
    """600 children whose achievements rise with age and always fill the easiest items first."""
    rng = np.random.default_rng(0)
    age = rng.uniform(24, 59, 600)
    k = np.clip(np.round((age - 24) / 35 * 6 + rng.normal(0, 1, 600)), 0, 6)
    return reports(age, k)


# --- building blocks ---

def test_flag_threshold_leaves_flag_rate_above_the_line():
    s = np.arange(1000, dtype=float)
    assert (s >= flag_threshold(s)).mean() == pytest.approx(FLAG_RATE, abs=0.002)


def test_default_inputs_are_scaled_age_and_answers_only(consistent):
    f = AnomalyFlagger().fit(consistent, ITEMS)
    X = f.inputs(reports([24, 59], [0, 6]))
    assert list(X.columns) == ["age_months", *ITEMS]  # no sex, no ahead_of_age
    assert X["age_months"].tolist() == [0.0, 1.0]


def test_age_norm_expects_more_items_at_older_ages(consistent):
    expected = AgeNorm().fit(consistent, ITEMS).expected([24, 36, 48, 59])
    assert np.all(np.diff(expected) > 0)
    assert "ahead_of_age" in AnomalyFlagger(age_norm=True).fit(consistent, ITEMS).inputs(consistent)


# --- behaviour ---

def test_flags_about_flag_rate_of_training_children(consistent):
    f = AnomalyFlagger().fit(consistent, ITEMS)
    assert f.flag(consistent).mean() == pytest.approx(FLAG_RATE, abs=0.02)


def test_reversed_report_is_flagged_and_consistent_one_is_not(consistent):
    f = AnomalyFlagger().fit(consistent, ITEMS)
    normal = reports([42], [3])                     # easiest three passed
    odd = reports([42], [3], hardest_first=True)    # hardest three passed, easiest failed
    assert f.score(odd)[0] > f.score(normal)[0]
    assert f.flag(odd)[0] and not f.flag(normal)[0]


# --- saved flaggers (skip until trained; ml/artefacts is git-ignored) ---

def load_saved(item_set):
    path = ARTEFACTS / "anomaly" / "iforest" / item_set / "model.joblib"
    if not path.is_file():
        pytest.skip("not trained: python -m hatua_ml.models.anomaly")
    return joblib.load(path), json.loads((path.parent / "metrics.json").read_text())


@pytest.mark.parametrize("item_set", ITEM_SETS)
def test_saved_flagger_matches_its_item_set(item_set):
    bundle, metrics = load_saved(item_set)
    flagger = bundle["model"]
    assert isinstance(flagger, AnomalyFlagger)
    assert flagger.kind == "iforest" and not flagger.age_norm
    assert bundle["items"] == flagger.items_ == ITEM_SETS[item_set]
    assert metrics["threshold"] == pytest.approx(flagger.threshold_)


@pytest.mark.skipif(not FEATURE_TABLE.is_file(), reason="feature table not built")
@pytest.mark.parametrize("item_set", ITEM_SETS)
def test_saved_flagger_rarely_flags_real_test_children(item_set):
    from hatua_ml.models.split import kenya_split, load_feature_table

    flagger = load_saved(item_set)[0]["model"]
    _, test = kenya_split(load_feature_table())
    assert flagger.flag(test).mean() <= 2 * FLAG_RATE
