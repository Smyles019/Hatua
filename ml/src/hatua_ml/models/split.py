"""Fixed Kenya train/test split shared by every model."""
import pandas as pd
from sklearn.model_selection import train_test_split

from hatua_ml.data.files import require_file
from hatua_ml.features.build_table import FEATURE_TABLE
from hatua_ml.features.ecdi2030 import ITEMS

SEED = 42
TEST_SIZE = 0.2


def load_feature_table() -> pd.DataFrame:
    path = require_file(FEATURE_TABLE, "Feature table (run: python -m hatua_ml.features.build_table)")
    return pd.read_csv(path)


def kenya_split(table: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (train, test) for Kenya.

    The test set is the same held-out 20% used in notebook 01, so the short-form
    item selection never saw these children. Children with a don't-know answer
    were not in that split and always go to training.
    """
    kenya = table[table["source"] == "kdhs_2022"].reset_index(drop=True)
    complete = kenya.dropna(subset=ITEMS)
    risk = 1 - complete["on_track"]
    _, test_idx = train_test_split(
        complete.index, test_size=TEST_SIZE, stratify=risk, random_state=SEED
    )
    return kenya.drop(index=test_idx), kenya.loc[test_idx]