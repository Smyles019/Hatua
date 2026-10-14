"""SHAP explanations of a child's risk, grouped into four developmental domains.

Each child is compared with training children in the same ECDI2030 age band, so a
domain only reads as "behind" when the child is behind same-age peers. SHAP values
are in log-odds of being off track: positive pushes risk up, negative pushes it
down. Sex is a model input but is never reported; age is reported on its own.
"""
import numpy as np
import pandas as pd
import shap

from hatua_ml.features.ecdi2030 import AGE_BANDS

# ECDI2030 items grouped into the proposal's four domains. ECDI2030's own three
# areas are kept intact; "learning" is split into language and cognitive.
DOMAINS = {
    "motor": ["ecd21", "ecd22", "ecd23", "ecd24"],
    "language": ["ecd25", "ecd26", "ecd27", "ecd28", "ecd29"],
    "cognitive": ["ecd30", "ecd31", "ecd32", "ecd33", "ecd34", "ecd35"],
    "social_emotional": ["ecd36", "ecd37", "ecd38", "ecd39", "ecd40"],
}
DOMAIN_OF = {item: domain for domain, items in DOMAINS.items() for item in items}

TOP_N = 3  # questions reported as the main reasons


def age_band(age_months: float) -> tuple[int, int]:
    """ECDI2030 band for an age; ages outside 24-59 use the nearest band."""
    for lo, hi, _ in AGE_BANDS:
        if age_months <= hi:
            return lo, hi
    return AGE_BANDS[-1][0], AGE_BANDS[-1][1]


def summarise(contrib: pd.Series, answers: pd.Series, items: list[str], flagged: bool) -> dict:
    """One child's explanation.

    domains:     per domain, summed contribution, how many asked items it rests on, and
                 a status: "needs_support" only if the child is flagged AND the domain
                 pushes risk up; otherwise "on_track"
    top_reasons: up to TOP_N questions not achieved that pushed risk up most (empty if
                 the child is not flagged)
    age:         contribution of age within the band
    """
    domains = {}
    for domain, members in DOMAINS.items():
        asked = [i for i in members if i in items]
        c = float(contrib[asked].sum())
        domains[domain] = {"contribution": c, "n_items": len(asked),
                           "status": "needs_support" if flagged and c > 0 else "on_track"}

    top_reasons = []
    if flagged:
        item_contrib = contrib[items]
        missed = item_contrib[(item_contrib > 0) & (answers[items] == 0)]
        top_reasons = [{"item": i, "domain": DOMAIN_OF[i], "contribution": float(v)}
                       for i, v in missed.sort_values(ascending=False).head(TOP_N).items()]

    return {"flagged": flagged, "domains": domains, "top_reasons": top_reasons,
            "age": float(contrib["age_months"])}


class Explainer:
    """Explains the XGBoost risk model for one or more children, against same-age peers.

    Standard (tree path-dependent) SHAP values are computed, then the mean SHAP values
    of training children in the same age band are subtracted. Each number then reads
    as "how much this input pushes risk up compared with a typical same-age child", and
    the numbers still add up exactly: band base + contributions = model output. For
    depth-1 trees this equals interventional SHAP against the band; for deeper trees it
    is a close approximation. (SHAP's interventional mode does not support XGBoost 3.)

    background: model_inputs(...) of the TRAINING children, same items as the model.
    threshold:  the model's saved risk cut-off, used for the flagged rule.
    """

    def __init__(self, model, items: list[str], background: pd.DataFrame, threshold: float):
        self.model, self.items, self.threshold = model, list(items), float(threshold)
        self._tree = shap.TreeExplainer(model)
        self._peer_mean, self._base = {}, {}
        # Group peers with the same rule used to place a child in a band.
        for band, peers in background.groupby(background["age_months"].map(age_band)):
            self._peer_mean[band] = self._raw(peers).mean()
            self._base[band] = float(model.predict(peers, output_margin=True).mean())

    def _raw(self, X: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame(self._tree.shap_values(X), index=X.index, columns=X.columns)

    def base(self, age_months: float) -> float:
        """Average model output (log-odds) for training children in this age band."""
        return self._base[age_band(age_months)]

    def contributions(self, X: pd.DataFrame) -> pd.DataFrame:
        """SHAP values relative to same-age peers, one column per model input."""
        raw = self._raw(X)
        peer = pd.DataFrame([self._peer_mean[age_band(a)] for a in X["age_months"]],
                            index=X.index)
        return raw - peer[raw.columns]

    def explain(self, X: pd.DataFrame) -> list[dict]:
        """X is model_inputs(...) for the same items the model was trained on."""
        flagged = self.model.predict_proba(X)[:, 1] >= self.threshold
        c = self.contributions(X)
        return [summarise(c.loc[i], X.loc[i], self.items, bool(f))
                for i, f in zip(X.index, flagged)]
