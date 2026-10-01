"""Item sets the models can be trained on."""
from hatua_ml.features.ecdi2030 import ITEMS

ALL_ITEMS = list(ITEMS)

# Top 9 from forward selection in notebooks/01_leakage_item_reduction.ipynb,
# chosen on the KDHS training split only.
SHORT_FORM_9 = ["ecd32", "ecd27", "ecd29", "ecd24", "ecd37", "ecd33", "ecd35", "ecd40", "ecd36"]

ITEM_SETS = {"all20": ALL_ITEMS, "short9": SHORT_FORM_9}