"""Tests for SHAP domain explanations (#30)."""
import joblib
import numpy as np
import pandas as pd
import pytest
from xgboost import XGBClassifier

from hatua_ml.config import ARTEFACTS
from hatua_ml.features.build_table import FEATURE_TABLE
from hatua_ml.features.ecdi2030 import ITEMS
from hatua_ml.features.item_sets import ITEM_SETS
from hatua_ml.features.prepare import model_inputs
from hatua_ml.models.explain import DOMAINS, TOP_N, Explainer, age_band, summarise


# --- domain map and age bands ---

def test_domains_cover_every_ecdi_item_exactly_once():
    mapped = [item for items in DOMAINS.values() for item in items]
    assert sorted(mapped) == sorted(ITEMS)
    assert len(mapped) == len(set(mapped))


@pytest.mark.parametrize("age,band", [(24, (24, 29)), (29, (24, 29)), (30, (30, 35)),
                                      (47, (42, 47)), (59, (48, 59)),
                                      (20, (24, 29)), (70, (48, 59))])
def test_age_band_uses_ecdi_bands_and_clamps_outside_ages(age, band):
    assert age_band(age) == band


# --- summarise (hand-built contributions) ---

ONE_PER_DOMAIN = ["ecd24", "ecd27", "ecd32", "ecd36"]  # motor, language, cognitive, social
CONTRIB = pd.Series({"age_months": 0.5, "female": 0.3,
                     "ecd24": -0.2, "ecd27": 1.0, "ecd32": 2.0, "ecd36": 0.4})
ANSWERS = pd.Series({"age_months": 40.0, "female": 1.0,
                     "ecd24": 1.0, "ecd27": 0.0, "ecd32": 0.0, "ecd36": 1.0})


def test_unflagged_child_is_on_track_everywhere_with_no_reasons():
    e = summarise(CONTRIB, ANSWERS, ONE_PER_DOMAIN, flagged=False)
    assert {d["status"] for d in e["domains"].values()} == {"on_track"}
    assert e["top_reasons"] == []


def test_flagged_child_needs_support_only_where_risk_is_pushed_up():
    e = summarise(CONTRIB, ANSWERS, ONE_PER_DOMAIN, flagged=True)
    status = {name: d["status"] for name, d in e["domains"].items()}
    assert status == {"motor": "on_track", "language": "needs_support",
                      "cognitive": "needs_support", "social_emotional": "needs_support"}
    assert all(d["n_items"] == 1 for d in e["domains"].values())


def test_top_reasons_are_missed_items_only_largest_first_and_never_sex():
    e = summarise(CONTRIB, ANSWERS, ONE_PER_DOMAIN, flagged=True)
    # ecd36 pushed risk up but was achieved, so it is not a reason
    assert [r["item"] for r in e["top_reasons"]] == ["ecd32", "ecd27"]
    assert len(e["top_reasons"]) <= TOP_N
    assert "female" not in str(e)


# --- Explainer on a small synthetic model with deeper trees ---

@pytest.fixture(scope="module")
def synthetic():
    rng = np.random.default_rng(0)
    n = 800
    df = pd.DataFrame({"age_months": rng.uniform(24, 59, n), "sex": rng.integers(1, 3, n)})
    for k, item in enumerate(ONE_PER_DOMAIN):
        p_pass = np.clip((df["age_months"] - 20) / 40 - 0.1 * k, 0.05, 0.95)
        df[item] = (rng.random(n) < p_pass).astype(float)
    X = model_inputs(df, ONE_PER_DOMAIN)
    y = (X[ONE_PER_DOMAIN].sum(axis=1) < (X["age_months"] - 20) / 12).astype(int)
    model = XGBClassifier(n_estimators=50, max_depth=3, random_state=0).fit(X, y)
    return model, X


def test_contributions_add_up_to_model_output(synthetic):
    model, X = synthetic
    ex = Explainer(model, ONE_PER_DOMAIN, X, threshold=0.5)
    base = np.array([ex.base(a) for a in X["age_months"]])
    margin = model.predict(X, output_margin=True)
    assert np.allclose(base + ex.contributions(X).sum(axis=1), margin, atol=1e-4)


def test_typical_same_age_child_has_zero_contribution_on_average(synthetic):
    model, X = synthetic
    c = Explainer(model, ONE_PER_DOMAIN, X, threshold=0.5).contributions(X)
    by_band = c.groupby(X["age_months"].map(age_band)).mean()
    assert np.allclose(by_band.to_numpy(), 0, atol=1e-6)


# --- the saved XGBoost risk models (skip until trained and the table is built) ---

@pytest.mark.skipif(not FEATURE_TABLE.is_file(), reason="feature table not built")
@pytest.mark.parametrize("item_set", ITEM_SETS)
def test_saved_model_explanations_are_consistent(item_set):
    path = ARTEFACTS / "xgboost" / item_set / "model.joblib"
    if not path.is_file():
        pytest.skip("not trained: python -m hatua_ml.models.train_xgboost")
    from hatua_ml.models.split import kenya_split, load_feature_table

    bundle = joblib.load(path)
    model, items = bundle["model"], bundle["items"]
    train, test = kenya_split(load_feature_table())
    ex = Explainer(model, items, model_inputs(train, items), bundle["threshold"])
    X = model_inputs(test, items)

    base = np.array([ex.base(a) for a in X["age_months"]])
    assert np.allclose(base + ex.contributions(X).sum(axis=1),
                       model.predict(X, output_margin=True), atol=1e-3)

    for e, (_, answers) in zip(ex.explain(X), X.iterrows()):
        assert set(e["domains"]) == set(DOMAINS)
        assert sum(d["n_items"] for d in e["domains"].values()) == len(items)
        if not e["flagged"]:
            assert e["top_reasons"] == []
            assert all(d["status"] == "on_track" for d in e["domains"].values())
        for r in e["top_reasons"]:
            assert answers[r["item"]] == 0 and r["contribution"] > 0
