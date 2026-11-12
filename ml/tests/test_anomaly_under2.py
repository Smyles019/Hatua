"""Under-24 odd-answer check: age curves, surprise features, flag rule."""
import numpy as np
import pandas as pd

from hatua_ml.models.anomaly import FLAG_RATE
from hatua_ml.models.anomaly_under2 import (
    MIN_ANSWERED, ItemCurve, Under2Flagger, inject_contradictory,
)

ITEMS = ["ddigmd063", "ddigmd068"]  # sits alone (earlier), walks alone (later)


def visits(n=600, seed=0) -> pd.DataFrame:
    """Typical children: sitting from about 7 months, walking from about 13."""
    rng = np.random.default_rng(seed)
    age = rng.uniform(4, 20, n)
    sit = (age + rng.normal(0, 1, n) > 7).astype(float)
    walk = (age + rng.normal(0, 1.5, n) > 13).astype(float)
    return pd.DataFrame({"age_months": age, ITEMS[0]: sit, ITEMS[1]: walk})


def test_item_curve_rises_with_age_and_handles_one_answer():
    c = ItemCurve().fit(np.array([5., 6., 9., 10.]), np.array([0, 0, 1, 1]))
    assert c.p(np.array([5.]))[0] < c.p(np.array([10.]))[0]
    const = ItemCurve().fit(np.array([5., 6.]), np.array([1, 1]))
    assert 0 < const.p(np.array([3.]))[0] <= 0.99


def test_flags_about_flag_rate_of_training_visits():
    df = visits()
    f = Under2Flagger().fit(df, ITEMS)
    assert abs(f.flag(df).mean() - FLAG_RATE) < 0.03


def test_walking_without_sitting_is_flagged():
    f = Under2Flagger().fit(visits(), ITEMS)
    odd = pd.DataFrame({"age_months": [16.0], ITEMS[0]: [0.0], ITEMS[1]: [1.0]})
    usual = pd.DataFrame({"age_months": [16.0], ITEMS[0]: [1.0], ITEMS[1]: [1.0]})
    assert f.flag(odd)[0]
    assert not f.flag(usual)[0]


def test_too_few_answers_are_never_flagged():
    f = Under2Flagger().fit(visits(), ITEMS)
    one = pd.DataFrame({"age_months": [16.0], ITEMS[0]: [0.0], ITEMS[1]: [np.nan]})
    assert MIN_ANSWERED == 2
    assert np.isneginf(f.score(one)[0]) and not f.flag(one)[0]


def test_contradictory_injection_raises_flag_rate():
    df = visits()
    f = Under2Flagger().fit(df, ITEMS)
    assert f.flag(inject_contradictory(df, f)).mean() > 3 * f.flag(df).mean()
