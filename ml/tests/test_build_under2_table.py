import numpy as np
import pandas as pd
import pytest

from hatua_ml.features.build_under2_table import (
    BASE_FEATURES, COHORT, UNDER24_CSV, build_under2_table, risk_band,
)


def fake_raw(n_children=40, visits=4, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for c in range(n_children):
        for v in range(visits):
            rows.append({
                "cohort": COHORT, "subjid": c, "agedays": 60 * (v + 1),
                "sex": "female" if c % 2 else "male", "gagebrth": 280,
                "ddicmm029": float(rng.integers(0, 2)), "ddigmd055": np.nan,
                "daz": rng.normal(-0.5 if c % 4 else -2.5, 0.3),
            })
    rows.append({**rows[0], "cohort": "GCDG-ZAF", "subjid": 999})
    return pd.DataFrame(rows)


def test_risk_band_cutoffs():
    bands = risk_band(pd.Series([-2.5, -2.0, -1.6, -1.5, 0.0]))
    assert bands.tolist() == ["high", "medium", "medium", "low", "low"]


def test_only_smocc_and_answered_items():
    t = build_under2_table(fake_raw())
    assert t["child_id"].str.startswith(COHORT).all()
    assert "ddicmm029" in t.columns
    assert "ddigmd055" not in t.columns  # never answered, so dropped


def test_label_matches_daz():
    t = build_under2_table(fake_raw())
    assert (t["delayed"] == (t["daz"] < -1.5).astype(int)).all()


def test_no_child_in_both_splits():
    t = build_under2_table(fake_raw())
    per_child = t.groupby("child_id")["split"].nunique()
    assert (per_child == 1).all()
    assert set(t["split"]) == {"train", "test"}


def test_features_exclude_label_columns():
    for col in ["daz", "delayed", "risk_band", "child_id", "split"]:
        assert col not in BASE_FEATURES


@pytest.mark.skipif(not UNDER24_CSV.is_file(), reason="childdevdata export not available")
def test_real_smocc_table():
    t = build_under2_table()
    assert t["child_id"].nunique() == 2033  # 2034 in cohort; one child has no scoreable visit
    assert 0.03 < t["delayed"].mean() < 0.15
