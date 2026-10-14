"""Item sets the models can be trained on."""
from hatua_ml.features.ecdi2030 import ITEMS

ALL_ITEMS = list(ITEMS)

# Forward-selection order on Kenya training children only (hatua_ml.features.item_reduction).
SELECTION_ORDER = ["ecd32", "ecd27", "ecd29", "ecd24", "ecd37", "ecd33", "ecd35", "ecd40",
                   "ecd36", "ecd21", "ecd25", "ecd39", "ecd28", "ecd30", "ecd23", "ecd34",
                   "ecd26", "ecd22", "ecd38", "ecd31"]

# Chosen form: 13 questions, fixed from the training cross-validation trade-off table
# (95% target sensitivity) before the held-out test children were used.
SHORT_FORM_13 = SELECTION_ORDER[:13]

# Earlier 9-question form, kept as a comparison point.
SHORT_FORM_9 = SELECTION_ORDER[:9]

ITEM_SETS = {"all20": ALL_ITEMS, "short13": SHORT_FORM_13, "short9": SHORT_FORM_9}
