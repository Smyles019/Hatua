"""SHAP explanations of a child's risk, grouped into four developmental domains.

Each child is compared with training children in the same age band, so a
domain only reads as "behind" when the child is behind same-age peers. SHAP values
are in log-odds of being off track: positive pushes risk up, negative pushes it
down. Sex is a model input but is never reported; age is reported on its own.

Defaults are the ECDI2030 (24-59 month) model. The under-24 model passes its own
domain map and age bands (UNDER2_DOMAINS, UNDER2_BANDS). A domain with no answered
question for a child is reported as "not_assessed".
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

# Under-24 bands, same (lo, hi, label) shape as AGE_BANDS.
UNDER2_BANDS = [(0, 5, "0-5"), (6, 11, "6-11"), (12, 17, "12-17"), (18, 23, "18-23")]


def under2_domains(items: list[str]) -> dict[str, list[str]]:
    """Dutch DDI items into the four app domains. The DDI has communication (cm),
    fine motor (fm) and gross motor (gm) only, so cognitive and social-emotional are
    empty and always come out "not_assessed"."""
    return {
        "motor": [i for i in items if i[3:5] in ("fm", "gm")],
        "language": [i for i in items if i[3:5] == "cm"],
        "cognitive": [],
        "social_emotional": [],
    }


def age_band(age_months: float, bands=AGE_BANDS) -> tuple[int, int]:
    """Band for an age in completed months; ages outside the bands use the nearest band."""
    for lo, hi, _ in bands:
        if int(age_months) <= hi:
            return lo, hi
    return bands[-1][0], bands[-1][1]


def summarise(contrib: pd.Series, answers: pd.Series, items: list[str], flagged: bool,
              domains: dict[str, list[str]] | None = None) -> dict:
    """One child's explanation.

    domains:     per domain, summed contribution, how many answered items it rests on,
                 and a status: "not_assessed" if no item in it was answered;
                 "needs_support" only if the child is flagged AND the domain pushes
                 risk up; otherwise "on_track"
    top_reasons: up to TOP_N questions not achieved that pushed risk up most (empty if
                 the child is not flagged)
    age:         contribution of age within the band
    """
    domains = DOMAINS if domains is None else domains
    domain_of = {item: d for d, members in domains.items() for item in members}

    out = {}
    for domain, members in domains.items():
        asked = [i for i in members if i in items and pd.notna(answers.get(i))]
        c = float(contrib[asked].sum()) if asked else 0.0
        if not asked:
            status = "not_assessed"
        elif flagged and c > 0:
            status = "needs_support"
        else:
            status = "on_track"
        out[domain] = {"contribution": c, "n_items": len(asked), "status": status}

    top_reasons = []
    if flagged:
        item_contrib = contrib[items]
        missed = item_contrib[(item_contrib > 0) & (answers[items] == 0)]
        top_reasons = [{"item": i, "domain": domain_of[i], "contribution": float(v)}
                       for i, v in missed.sort_values(ascending=False).head(TOP_N).items()]

    return {"flagged": flagged, "domains": out, "top_reasons": top_reasons,
            "age": float(contrib["age_months"])}


class Explainer:
    """Explains an XGBoost risk model for one or more children, against same-age peers.

    Standard (tree path-dependent) SHAP values are computed, then the mean SHAP values
    of training children in the same age band are subtracted. Each number then reads
    as "how much this input pushes risk up compared with a typical same-age child", and
    the numbers still add up exactly: band base + contributions = model output. For
    depth-1 trees this equals interventional SHAP against the band; for deeper trees it
    is a close approximation. (SHAP's interventional mode does not support XGBoost 3.)

    background: model inputs of the TRAINING children, same items as the model.
    threshold:  the model's saved risk cut-off, used for the flagged rule.
    peer_stats: alternative to background, as returned by peer_stats(); lets the API
                rebuild the explainer without loading any training data.
    domains:    item-to-domain map (default: ECDI2030 DOMAINS).
    bands:      age bands as (lo, hi, label) (default: ECDI2030 AGE_BANDS).
    """

    def __init__(self, model, items: list[str], background: pd.DataFrame | None = None,
                 threshold: float = 0.5, peer_stats: dict | None = None,
                 domains: dict[str, list[str]] | None = None, bands=None):
        self.model, self.items, self.threshold = model, list(items), float(threshold)
        self.domains = DOMAINS if domains is None else domains
        self.bands = AGE_BANDS if bands is None else bands
        self._tree = shap.TreeExplainer(model)
        self._peer_mean, self._base = {}, {}
        if peer_stats is not None:
            for key, s in peer_stats.items():
                band = tuple(int(x) for x in key.split("-"))
                self._peer_mean[band] = pd.Series(s["mean"], dtype=float)
                self._base[band] = float(s["base"])
            return
        # Group peers with the same rule used to place a child in a band.
        for band, peers in background.groupby(background["age_months"].map(self._band)):
            self._peer_mean[band] = self._raw(peers).mean()
            self._base[band] = float(model.predict(peers, output_margin=True).mean())

    def _band(self, age_months: float) -> tuple[int, int]:
        return age_band(age_months, self.bands)

    def peer_stats(self) -> dict:
        """Same-age averages as plain JSON-ready numbers, keyed "lo-hi"."""
        return {f"{lo}-{hi}": {"mean": {k: float(v) for k, v in self._peer_mean[(lo, hi)].items()},
                               "base": self._base[(lo, hi)]}
                for lo, hi in sorted(self._peer_mean)}

    def _raw(self, X: pd.DataFrame) -> pd.DataFrame:
        # float64 throughout, so an explainer rebuilt from saved peer_stats (JSON, float64)
        # gives bit-identical results to one built from training data.
        values = np.asarray(self._tree.shap_values(X), dtype=np.float64)
        return pd.DataFrame(values, index=X.index, columns=X.columns)

    def base(self, age_months: float) -> float:
        """Average model output (log-odds) for training children in this age band."""
        return self._base[self._band(age_months)]

    def contributions(self, X: pd.DataFrame) -> pd.DataFrame:
        """SHAP values relative to same-age peers, one column per model input."""
        raw = self._raw(X)
        peer = pd.DataFrame([self._peer_mean[self._band(a)] for a in X["age_months"]],
                            index=X.index)
        return raw - peer[raw.columns]

    def explain(self, X: pd.DataFrame) -> list[dict]:
        """X is the model inputs for the same items the model was trained on."""
        flagged = self.model.predict_proba(X)[:, 1] >= self.threshold
        c = self.contributions(X)
        return [summarise(c.loc[i], X.loc[i], self.items, bool(f), self.domains)
                for i, f in zip(X.index, flagged)]
