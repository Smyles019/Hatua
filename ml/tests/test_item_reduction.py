"""Tests for item reduction (#27)."""
import numpy as np
import pandas as pd
import pytest

from hatua_ml.features.build_table import FEATURE_TABLE
from hatua_ml.features.ecdi2030 import ITEMS
from hatua_ml.features.item_reduction import (
    SENSITIVITIES, forward_select, operating_curve, training_data)
from hatua_ml.features.item_sets import (
    ITEM_SETS, SELECTION_ORDER, SHORT_FORM_9, SHORT_FORM_13)

INFORMATIVE = ["ecd30", "ecd25", "ecd38"]  # synthetic: only these drive the target


@pytest.fixture(scope="module")
def synthetic():
    rng = np.random.default_rng(0)
    n = 500
    X = pd.DataFrame(rng.integers(0, 2, (n, len(ITEMS))).astype(float), columns=ITEMS)
    X["age_months"] = rng.uniform(24, 59, n)
    score = 3 * X["ecd30"] + 2 * X["ecd25"] + 1 * X["ecd38"] + rng.normal(0, 0.5, n)
    y = (score < 2.5).astype(int).to_numpy()
    return X, y


# --- item sets ---

def test_selection_order_is_a_ranking_of_all_twenty_items():
    assert sorted(SELECTION_ORDER) == sorted(ITEMS)


def test_short_forms_are_prefixes_of_the_selection_order():
    assert SHORT_FORM_13 == SELECTION_ORDER[:13] and SHORT_FORM_9 == SELECTION_ORDER[:9]
    assert set(ITEM_SETS) == {"all20", "short13", "short9"}


# --- selection and curve on synthetic data ---

def test_forward_select_finds_the_informative_items_in_order(synthetic):
    X, y = synthetic
    assert forward_select(X, y, k_max=3) == INFORMATIVE


def test_operating_curve_shape_and_bookkeeping(synthetic):
    X, y = synthetic
    order = forward_select(X, y, k_max=3)
    curve = operating_curve(X, y, order)
    assert curve["k"].tolist() == [1, 2, 3]
    assert curve["added"].tolist() == order
    off = y.mean()
    for sens in SENSITIVITIES:
        tag = int(round(sens * 100))
        # missed per 100 matches the target sensitivity (quantile rounding allowed)
        assert np.allclose(curve[f"missed_per_100_{tag}"], 100 * off * (1 - sens), atol=1.0)
        # false flags per 100 are consistent with specificity
        assert np.allclose(curve[f"false_flags_per_100_{tag}"],
                           100 * (1 - off) * (1 - curve[f"specificity_{tag}"]))
    # more informative questions never make the 95% specificity worse here
    assert curve["specificity_95"].is_monotonic_increasing


def test_training_data_drops_incomplete_children_and_codes_risk():
    df = pd.DataFrame({**{i: [1.0, 1.0] for i in ITEMS}, "age_months": [30, 40],
                       "on_track": [1, 0]})
    df.loc[0, "ecd21"] = np.nan
    X, y = training_data(df)
    assert len(X) == 1 and y.tolist() == [1]
    assert list(X.columns) == ITEMS + ["age_months"]


# --- real Kenya training children (slow, ~30 s) ---

@pytest.mark.skipif(not FEATURE_TABLE.is_file(), reason="feature table not built")
def test_selection_on_kenya_training_reproduces_saved_order():
    from hatua_ml.models.split import kenya_split, load_feature_table

    train, _ = kenya_split(load_feature_table())
    X, y = training_data(train)
    assert forward_select(X, y) == SELECTION_ORDER
