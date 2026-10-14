"""Tests for external validation (#31)."""
import numpy as np
import pandas as pd
import pytest

from hatua_ml.config import ARTEFACTS
from hatua_ml.features.build_table import FEATURE_TABLE
from hatua_ml.models.evaluation import evaluate
from hatua_ml.models.external_validation import EXTERNAL, bootstrap_ci, cohorts


@pytest.fixture(scope="module")
def scores():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 400)
    p = np.clip(0.3 * y + rng.uniform(0, 0.7, 400), 0, 1)
    return y, p


def test_bootstrap_interval_contains_the_point_estimate(scores):
    y, p = scores
    point = evaluate(y, p, 0.5)
    ci = bootstrap_ci(y, p, 0.5, n_boot=200)
    for k in ("auc", "sensitivity", "specificity"):
        assert ci[f"{k}_lo"] <= point[k] <= ci[f"{k}_hi"]
        assert ci[f"{k}_hi"] - ci[f"{k}_lo"] < 0.2


def test_bootstrap_is_reproducible(scores):
    y, p = scores
    assert bootstrap_ci(y, p, 0.5, n_boot=100) == bootstrap_ci(y, p, 0.5, n_boot=100)


def test_cohorts_keep_countries_separate():
    table = pd.DataFrame({
        "source": ["kdhs_2022"] * 20 + ["mics_eswatini"] * 2 + ["mics_comoros"] * 3,
        "on_track": [1, 0] * 10 + [1, 0, 1, 1, 0],
        **{f"ecd{i}": 1.0 for i in range(21, 41)},
    })
    groups = cohorts(table)
    assert set(groups) == {"kenya_test", *EXTERNAL}
    assert (groups["kenya_test"]["source"] == "kdhs_2022").all()
    assert len(groups["kenya_test"]) == 4  # the fixed 20% Kenya test split
    assert len(groups["mics_eswatini"]) == 2 and len(groups["mics_comoros"]) == 3


@pytest.mark.skipif(not FEATURE_TABLE.is_file(), reason="feature table not built")
def test_report_covers_every_model_item_set_and_cohort(monkeypatch, tmp_path):
    if not (ARTEFACTS / "xgboost" / "short13" / "model.joblib").is_file():
        pytest.skip("models not trained")
    from hatua_ml.models import external_validation as ev

    # fast and side-effect free: fewer resamples, report written to a temp folder
    monkeypatch.setattr(ev, "REPORT", tmp_path / "external_validation.csv")
    monkeypatch.setattr(ev.bootstrap_ci, "__defaults__", (50, ev.SEED))
    t = ev.run()
    assert (tmp_path / "external_validation.csv").is_file()
    assert len(t) == len(ev.MODELS) * 3 * (1 + len(EXTERNAL))
    assert t[["auc", "sensitivity", "specificity"]].apply(lambda c: c.between(0, 1).all()).all()
    assert (t["sensitivity_lo"] <= t["sensitivity"]).all()
    assert (t["sensitivity"] <= t["sensitivity_hi"]).all()
