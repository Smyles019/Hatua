"""Tests for the under-24 explanation settings (domains, bands, not_assessed)."""
import numpy as np
import pandas as pd
import pytest

from hatua_ml.models.explain import UNDER2_BANDS, age_band, summarise, under2_domains

ITEMS = ["ddicmm030", "ddicmd141", "ddifmd007", "ddigmd068"]


def test_under2_domains_map_ddi_prefixes():
    d = under2_domains(ITEMS)
    assert d["language"] == ["ddicmm030", "ddicmd141"]
    assert d["motor"] == ["ddifmd007", "ddigmd068"]
    assert d["cognitive"] == [] and d["social_emotional"] == []


@pytest.mark.parametrize("age,band", [(0.5, (0, 5)), (5.9, (0, 5)), (11, (6, 11)),
                                      (12, (12, 17)), (23.9, (18, 23)), (30, (18, 23))])
def test_under2_bands(age, band):
    assert age_band(age, UNDER2_BANDS) == band


def test_unanswered_domain_is_not_assessed_and_reasons_skip_unasked_items():
    contrib = pd.Series({"age_months": 0.1, "female": 0.0, "gest_weeks": 0.0,
                         "ddicmm030": 0.9, "ddicmd141": 0.5, "ddifmd007": 0.0, "ddigmd068": 0.0})
    answers = pd.Series({"age_months": 3.0, "female": 1.0, "gest_weeks": 40.0,
                         "ddicmm030": 0.0, "ddicmd141": np.nan,
                         "ddifmd007": np.nan, "ddigmd068": np.nan})
    r = summarise(contrib, answers, ITEMS, flagged=True, domains=under2_domains(ITEMS))
    assert r["domains"]["motor"]["status"] == "not_assessed"
    assert r["domains"]["language"] == {"contribution": 0.9, "n_items": 1, "status": "needs_support"}
    assert r["domains"]["cognitive"]["status"] == "not_assessed"
    assert [x["item"] for x in r["top_reasons"]] == ["ddicmm030"]  # unasked ddicmd141 excluded
