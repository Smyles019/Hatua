"""Runs one assessment.

24 to 59 months: the trained release (XGBoost risk, Isolation Forest anomaly flag, SHAP
domain explanation), loaded once from MODEL_DIR/release/MODEL_RELEASE and checked
against its manifest checksums (hatua_ml.export.load_release).

4 to 23 months: the WHO gross motor milestone check (hatua_ml.norms.who_motor). This is
a rule-based check against published windows, not a model, and the result says so.
"""
import logging
from functools import lru_cache
from pathlib import Path

import pandas as pd

from app.core.config import settings
from app.services.questions import QUESTIONS

log = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parents[3]

# Used only with a release made before the second cut-off existed (1.0.0). Releases
# from hatua_ml.export 1.1.0 onwards carry their own high_threshold, chosen on training
# data at 99% specificity; re-export to replace this placeholder.
PROVISIONAL_HIGH_PROBABILITY = 0.70


class ModelNotAvailable(Exception):
    """The release folder is missing, does not pass its checksum check, or is synthetic."""


class AgeNotSupported(Exception):
    """The child's age is outside what the release or the milestone check covers."""


def release_path() -> Path:
    base = Path(settings.model_dir)
    if not base.is_absolute():
        base = REPO_ROOT / base
    return base / "release" / settings.model_release


@lru_cache(maxsize=1)
def get_release() -> dict:
    from hatua_ml.export import ReleaseError, load_release
    from hatua_ml.synthetic import SYNTHETIC

    path = release_path()
    try:
        release = load_release(path)
    except (ReleaseError, FileNotFoundError) as e:
        raise ModelNotAvailable(f"{e} (looked in {path})") from e
    if release["manifest"]["anomaly"].get("fitted_on") == SYNTHETIC and not settings.dev_mode:
        raise ModelNotAvailable(f"{path} is a synthetic test release; it is only served "
                                "with DEV_MODE=true")
    if release["high_threshold"] is None:
        log.warning("release %s has no high-risk cut-off; using the provisional %.2f",
                    release["manifest"]["version"], PROVISIONAL_HIGH_PROBABILITY)
    return release


def high_threshold(release: dict) -> tuple[float, str]:
    if release["high_threshold"] is not None:
        return float(release["high_threshold"]), "release"
    return max(PROVISIONAL_HIGH_PROBABILITY, release["threshold"]), "provisional"


def risk_level(probability: float, threshold: float, high: float) -> str:
    if probability < threshold:
        return "low"
    return "high" if probability >= high else "medium"


def model_age_range() -> tuple[int, int]:
    lo, hi = get_release()["manifest"]["age_range_months"]
    return int(lo), int(hi)


def method_for_age(age_months: int) -> str:
    """'model' (24-59 months), 'milestone_check' (4-23), or AgeNotSupported."""
    from hatua_ml.norms import who_motor

    if age_months < who_motor.MIN_AGE:
        raise AgeNotSupported(f"the first milestone check is at {who_motor.MIN_AGE} months; "
                              f"this child is {age_months} months")
    if age_months <= who_motor.MAX_AGE:
        return "milestone_check"
    lo, hi = model_age_range()
    if lo <= age_months <= hi:
        return "model"
    raise AgeNotSupported(f"assessments cover {who_motor.MIN_AGE} to {hi} months; "
                          f"this child is {age_months} months")


def items_for_age(age_months: int) -> list[str]:
    from hatua_ml.norms import who_motor

    if method_for_age(age_months) == "milestone_check":
        return who_motor.items_for_age(age_months)
    return list(get_release()["items"])


def age_band(age_months: int) -> str:
    from hatua_ml.models.explain import age_band as ecdi_band
    from hatua_ml.norms import who_motor

    band = who_motor.age_band if age_months < 24 else ecdi_band
    lo, hi = band(age_months)
    return f"{lo}-{hi}"


def assess(age_months: int, sex: str, coded: dict[str, float | None]) -> dict:
    """coded: item -> 1 achieved / 0 not achieved / None don't know, for items_for_age(age).

    Returns a common shape for both methods: risk_level, anomaly_flag, explanation
    (domains + top_reasons), model details and model_version."""
    if method_for_age(age_months) == "milestone_check":
        return _milestone_check(age_months, coded)
    return _model(age_months, sex, coded)


def _model(age_months: int, sex: str, coded: dict) -> dict:
    from hatua_ml.features.prepare import model_inputs

    release = get_release()
    row = {"age_months": age_months, "sex": 2 if sex == "female" else 1,
           **{i: coded.get(i) for i in release["items"]}}
    df = pd.DataFrame([row])
    X = model_inputs(df, release["items"])
    probability = float(release["model"].predict_proba(X)[:, 1][0])
    flagger = release["flagger"]
    anomaly_score = float(flagger.score(df)[0])
    explanation = release["explainer"].explain(X)[0]
    for reason in explanation["top_reasons"]:
        reason["question"] = QUESTIONS[reason["item"]]["short"]
    high, high_source = high_threshold(release)

    return {
        "method": "model",
        "risk_level": risk_level(probability, release["threshold"], high),
        "anomaly_flag": anomaly_score >= flagger.threshold_,
        "explanation": explanation,
        "details": {"probability": probability, "threshold": release["threshold"],
                    "high_threshold": high, "high_threshold_source": high_source,
                    "anomaly_score": anomaly_score},
        "model_version": release["manifest"]["version"],
    }


def _milestone_check(age_months: int, coded: dict) -> dict:
    from hatua_ml.norms import who_motor

    r = who_motor.assess(age_months, coded)
    reasons = [{"item": o["item"], "domain": "motor", "months_past_window": o["months_past_window"],
                "question": QUESTIONS[o["item"]]["short"]} for o in r["overdue"]]
    explanation = {
        "flagged": r["risk_level"] != "low",
        # Only movement is checked below 24 months; other domains are not reported.
        "domains": {"motor": {"status": r["status"], "n_items": r["n_items"],
                              "contribution": None}},
        "top_reasons": reasons[:3],
    }
    return {
        "method": "milestone_check",
        "risk_level": r["risk_level"],
        "anomaly_flag": r["consistency_flag"],
        "explanation": explanation,
        "details": {"rule": "WHO motor windows: overdue = not achieved after the 99th "
                            "percentile age; 1 overdue = medium, 2 or more = high",
                    "overdue": r["overdue"]},
        "model_version": r["model_version"],
    }
