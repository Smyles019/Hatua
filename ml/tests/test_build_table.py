import pytest

from hatua_ml.config import KDHS_FILE, MICS_FILES
from hatua_ml.features.build_table import COLUMNS, FEATURES, build_feature_table
from hatua_ml.features.ecdi2030 import ITEMS


def test_features_are_only_app_inputs():
    assert FEATURES == ["age_months", "sex", *ITEMS]


@pytest.mark.parametrize("col", ["on_track", "weight", "source", "items_passed", "margin"])
def test_no_target_metadata_or_leaky_columns_in_features(col):
    assert col not in FEATURES


ALL_FILES = [KDHS_FILE, *MICS_FILES.values()]


@pytest.mark.skipif(not all(p.is_file() for p in ALL_FILES), reason="survey files not available")
def test_feature_table_has_expected_columns_and_rows():
    t = build_feature_table()
    assert list(t.columns) == COLUMNS
    assert t["source"].value_counts().to_dict() == {
        "kdhs_2022": 5478, "mics_comoros": 1846, "mics_eswatini": 1378,
    }
    