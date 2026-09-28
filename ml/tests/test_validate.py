import re

import numpy as np
import pytest

from hatua_ml.data.validate import SampleValidationError, validate_sample
from hatua_ml.features.ecdi2030 import ITEMS


def test_valid_sample_is_returned_unchanged(sample):
    assert validate_sample(sample, "test") is sample


def test_missing_column(sample):
    with pytest.raises(SampleValidationError, match="missing columns"):
        validate_sample(sample.drop(columns="weight"), "test")


def test_empty_sample(sample):
    with pytest.raises(SampleValidationError, match="empty"):
        validate_sample(sample.iloc[0:0], "test")


@pytest.mark.parametrize("age", [23.0, 60.0])
def test_age_outside_range(sample, age):
    sample.loc[0, "age_months"] = age
    with pytest.raises(SampleValidationError, match="outside 24-59"):
        validate_sample(sample, "test")


def test_missing_age(sample):
    sample.loc[0, "age_months"] = np.nan
    with pytest.raises(SampleValidationError, match="missing age"):
        validate_sample(sample, "test")


@pytest.mark.parametrize("weight", [np.nan, 0.0, -1.0])
def test_bad_weight(sample, weight):
    sample.loc[0, "weight"] = weight
    with pytest.raises(SampleValidationError, match="weight"):
        validate_sample(sample, "test")


def test_dont_know_code_is_rejected(sample):
    sample.loc[0, ITEMS[0]] = 8.0
    with pytest.raises(SampleValidationError, match=re.escape(ITEMS[0])):
        validate_sample(sample, "test")


def test_single_missing_item_is_allowed(sample):
    sample.loc[0, ITEMS[0]] = np.nan
    validate_sample(sample, "test")


def test_row_with_no_item_answers(sample):
    sample.loc[0, ITEMS] = np.nan
    with pytest.raises(SampleValidationError, match="no ECDI item answers"):
        validate_sample(sample, "test")


def test_on_track_not_binary(sample):
    sample.loc[0, "on_track"] = 2.0
    with pytest.raises(SampleValidationError, match="on_track has values"):
        validate_sample(sample, "test")


def test_on_track_all_missing(sample):
    sample["on_track"] = np.nan
    with pytest.raises(SampleValidationError, match="missing for every row"):
        validate_sample(sample, "test")


def test_all_problems_reported_together(sample):
    sample.loc[0, "age_months"] = 70.0
    sample.loc[1, "weight"] = 0.0
    with pytest.raises(SampleValidationError) as exc:
        validate_sample(sample, "test")
    msg = str(exc.value)
    assert "outside 24-59" in msg and "weight" in msg