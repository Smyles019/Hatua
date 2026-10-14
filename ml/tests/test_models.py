"""Tests for the shared evaluation helpers and the saved model artefacts."""
import json

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.datasets import make_classification
from sklearn.exceptions import NotFittedError
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_predict
from sklearn.utils.validation import check_is_fitted

from hatua_ml.config import ARTEFACTS
from hatua_ml.features.build_table import FEATURE_TABLE
from hatua_ml.features.item_sets import ITEM_SETS
from hatua_ml.features.prepare import model_inputs, risk_target
from hatua_ml.models.evaluation import (
    TARGET_SENSITIVITY,
    choose_threshold,
    cv,
    evaluate,
    save_artefacts,
)


# --- evaluate ---

def test_evaluate_on_hand_worked_example():
    y = [0, 0, 1, 1]
    p = np.array([0.1, 0.6, 0.4, 0.9])
    m = evaluate(y, p, threshold=0.5)
    assert m["auc"] == pytest.approx(0.75)  # 3 of 4 off-track vs on-track pairs ranked right
    assert m["sensitivity"] == pytest.approx(0.5)
    assert m["specificity"] == pytest.approx(0.5)
    assert m["n_test"] == 4


def test_evaluate_flags_a_score_equal_to_the_threshold():
    m = evaluate([0, 1], np.array([0.2, 0.5]), threshold=0.5)
    assert m["sensitivity"] == 1.0
    assert m["specificity"] == 1.0


# --- choose_threshold ---

@pytest.fixture
def synthetic():
    X, y = make_classification(n_samples=600, n_features=5, weights=[0.7], random_state=0)
    return X, y


def test_threshold_hits_target_sensitivity_on_training_folds(synthetic):
    X, y = synthetic
    model = LogisticRegression(max_iter=1000)
    t = choose_threshold(model, X, y)
    p = cross_val_predict(model, X, y, cv=cv(), method="predict_proba")[:, 1]
    assert (p[y == 1] >= t).mean() == pytest.approx(TARGET_SENSITIVITY, abs=0.01)


def test_choose_threshold_uses_out_of_fold_scores_not_a_fitted_model(synthetic):
    X, y = synthetic
    model = LogisticRegression(max_iter=1000)
    choose_threshold(model, X, y)
    with pytest.raises(NotFittedError):
        check_is_fitted(model)


# --- save_artefacts ---

def test_save_artefacts_round_trip(tmp_path):
    out = tmp_path / "xgboost" / "short9"
    save_artefacts(out, LogisticRegression(), ["ecd32"], 0.4, {"auc": 0.9})
    bundle = joblib.load(out / "model.joblib")
    assert set(bundle) == {"model", "items", "threshold"}
    assert bundle["items"] == ["ecd32"]
    assert bundle["threshold"] == 0.4
    assert json.loads((out / "metrics.json").read_text()) == {"threshold": 0.4, "auc": 0.9}


# --- saved artefacts (skip until trained; ml/artefacts is git-ignored) ---

SAVED = [(name, item_set) for name in ("logreg", "xgboost") for item_set in ITEM_SETS]


def load_saved(name, item_set):
    path = ARTEFACTS / name / item_set / "model.joblib"
    if not path.is_file():
        pytest.skip(f"not trained: python -m hatua_ml.models.train_{name}")
    return joblib.load(path), json.loads((path.parent / "metrics.json").read_text())


def child(items, achieved):
    """One 48-month-old boy with every item achieved, or none."""
    df = pd.DataFrame({"age_months": [48.0], "sex": [1], **{i: [float(achieved)] for i in items}})
    return model_inputs(df, items)


@pytest.mark.parametrize("name,item_set", SAVED)
def test_saved_bundle_matches_its_item_set(name, item_set):
    bundle, metrics = load_saved(name, item_set)
    assert bundle["items"] == ITEM_SETS[item_set]
    assert 0 < bundle["threshold"] < 1
    assert metrics["threshold"] == pytest.approx(bundle["threshold"])
    assert metrics["item_set"] == item_set


@pytest.mark.parametrize("name,item_set", SAVED)
def test_saved_model_scores_new_input_and_ranks_sensibly(name, item_set):
    bundle, _ = load_saved(name, item_set)
    model, items = bundle["model"], bundle["items"]
    p_all = model.predict_proba(child(items, 1))[0, 1]
    p_none = model.predict_proba(child(items, 0))[0, 1]
    assert 0 <= p_all <= 1 and 0 <= p_none <= 1
    assert p_none > p_all  # achieving nothing must look riskier than achieving everything


@pytest.mark.skipif(not FEATURE_TABLE.is_file(), reason="feature table not built")
@pytest.mark.parametrize("name,item_set", SAVED)
def test_saved_metrics_reproduce_on_kenya_test_split(name, item_set):
    from hatua_ml.models.split import kenya_split, load_feature_table

    bundle, metrics = load_saved(name, item_set)
    _, test = kenya_split(load_feature_table())
    p = bundle["model"].predict_proba(model_inputs(test, bundle["items"]))[:, 1]
    again = evaluate(risk_target(test), p, bundle["threshold"])
    for key in ("auc", "sensitivity", "specificity", "n_test"):
        assert again[key] == pytest.approx(metrics[key])
