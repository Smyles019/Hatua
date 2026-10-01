import numpy as np
import pandas as pd
import pytest

from hatua_ml.features.build_table import FEATURE_TABLE
from hatua_ml.features.ecdi2030 import ITEMS
from hatua_ml.features.item_sets import ITEM_SETS, SHORT_FORM_9
from hatua_ml.features.prepare import model_inputs, risk_target


# --- item sets ---

def test_short_form_is_nine_distinct_ecdi_items():
    assert len(set(SHORT_FORM_9)) == 9
    assert set(SHORT_FORM_9) <= set(ITEMS)


def test_item_sets_never_include_non_items():
    for items in ITEM_SETS.values():
        assert set(items) <= set(ITEMS)


# --- model inputs ---

def test_dont_know_becomes_not_achieved_and_sex_becomes_female_flag():
    df = pd.DataFrame({"age_months": [30, 50], "sex": [1, 2],
                       "ecd21": [1, np.nan], "on_track": [1, 0]})
    X = model_inputs(df, ["ecd21"])
    assert list(X.columns) == ["age_months", "female", "ecd21"]
    assert X["ecd21"].tolist() == [1.0, 0.0]
    assert X["female"].tolist() == [0.0, 1.0]
    assert not X.isna().any().any()


def test_risk_target_is_one_for_off_track():
    assert risk_target(pd.DataFrame({"on_track": [1, 0]})).tolist() == [0, 1]


# --- fixed split (needs the feature table) ---

@pytest.mark.skipif(not FEATURE_TABLE.is_file(), reason="feature table not built")
def test_kenya_split_is_fixed_and_clean():
    from hatua_ml.models.split import kenya_split, load_feature_table

    train, test = kenya_split(load_feature_table())
    assert (len(train), len(test)) == (4439, 1039)
    assert set(train.index).isdisjoint(test.index)
    assert (train["source"] == "kdhs_2022").all() and (test["source"] == "kdhs_2022").all()
    assert not test[ITEMS].isna().any().any()

    train2, test2 = kenya_split(load_feature_table())
    assert test.index.equals(test2.index)