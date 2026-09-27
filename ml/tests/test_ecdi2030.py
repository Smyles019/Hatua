import pandas as pd

from hatua_ml.features.ecdi2030 import ITEMS, harmonise, on_track


def _dhs_row(yes: int, age: int) -> pd.DataFrame:
    row = {f"ecd{i}": (1 if i - 21 < yes else 0) for i in range(21, 39)}
    row.update({"ecd39": 5, "ecd40": 1})
    return pd.DataFrame([row]), pd.Series([age])


def test_on_track_at_cutoff():
    raw, age = _dhs_row(yes=13, age=45)          # 13 yes items + 2 behaviour items = 15 >= 13
    items = harmonise(raw, "dhs")
    assert on_track(items[ITEMS], age).iloc[0] == 1


def test_off_track_below_cutoff():
    raw, age = _dhs_row(yes=5, age=50)           # 5 + 2 = 7 < 15
    items = harmonise(raw, "dhs")
    assert on_track(items[ITEMS], age).iloc[0] == 0


def test_mics_no_coded_as_zero():
    raw = pd.DataFrame([{f"EC{i}": 2 for i in range(21, 41)}])
    items = harmonise(raw, "mics")
    assert items[ITEMS[:18]].eq(0).all(axis=1).iloc[0]
