"""Runs one assessment.

24 to 59 months: the trained release (XGBoost risk, Isolation Forest anomaly flag, SHAP
domain explanation), loaded once from MODEL_DIR/release/MODEL_RELEASE and checked
against its manifest checksums (hatua_ml.export.load_release).

0 to 23 months: the under-24 XGBoost short-form model (hatua_ml.models.train_under2),
loaded from UNDER2_MODEL_DIR, with SHAP explanations for motor and language. If that
model is not available, 4 to 23 months fall back to the WHO gross motor milestone check
(hatua_ml.norms.who_motor), a rule-based check that says so in its result.
"""
import json
import logging
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from app.core.config import settings
from app.services.questions import QUESTIONS

log = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parents[3]

# Used only with a release made before the second cut-off existed (1.0.0). Releases
# from hatua_ml.export 1.1.0 onwards carry their own high_threshold, chosen on training
# data at 99% specificity; re-export to replace this placeholder.
PROVISIONAL_HIGH_PROBABILITY = 0.70

# The app does not ask for gestational age yet. Assuming a full-term birth keeps the
# under-24 model's test sensitivity at 96.5% (93.2% if left unknown), and for a
# preterm child it errs towards flagging, the safer side for a screening tool.
DEFAULT_GEST_WEEKS = 40.0


class ModelNotAvailable(Exception):
    """The release folder is missing, does not pass its checksum check, or is synthetic."""


class AgeNotSupported(Exception):
    """The child's age is outside what the release or the milestone check covers."""


def _resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p


def release_path() -> Path:
    return _resolve(settings.model_dir) / "release" / settings.model_release


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


@lru_cache(maxsize=1)
def get_under2() -> dict:
    """Under-24 model, cut-offs, per-month questions and saved same-age SHAP averages."""
    import joblib

    from hatua_ml.models.explain import UNDER2_BANDS, Explainer, under2_domains

    path = _resolve(settings.under2_model_dir)
    try:
        art = joblib.load(path / "model.joblib")
        metrics = json.loads((path / "metrics.json").read_text())
        peers = json.loads((path / "peer_stats.json").read_text())
        by_month = json.loads((path / "items_by_month.json").read_text())
    except FileNotFoundError as e:
        raise ModelNotAvailable(f"under-24 model files missing: {e}") from e
    # Odd-answer check (hatua_ml.models.anomaly_under2). Optional: without it the
    # under-24 path never flags answers as unusual.
    flagger_path = path / "anomaly.joblib"
    flagger = joblib.load(flagger_path) if flagger_path.is_file() else None
    if flagger is None:
        log.warning("under-24 odd-answer check missing (%s); anomaly flag is off", flagger_path)
    explainer = Explainer(art["model"], art["items"], threshold=art["threshold"],
                          peer_stats=peers, domains=under2_domains(art["items"]),
                          bands=UNDER2_BANDS)
    return {"model": art["model"], "items": list(art["items"]), "threshold": art["threshold"],
            "high_threshold": max(float(metrics["high_threshold"]), art["threshold"]),
            "explainer": explainer, "items_by_month": by_month, "flagger": flagger,
            # prediction_results.model_version is VARCHAR(20)
            "version": f"u2-smocc-{len(art['items'])}-1.0"}


def under2_available() -> bool:
    try:
        get_under2()
        return True
    except ModelNotAvailable as e:
        log.warning("under-24 model not loaded, using the WHO motor check: %s", e)
        return False


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
    """'model' (0-23 with the under-24 model, and 24-59), 'milestone_check' (4-23 when the
    under-24 model is not available), or AgeNotSupported."""
    from hatua_ml.norms import who_motor

    if 0 <= age_months < 24:
        if under2_available():
            return "model"
        if age_months < who_motor.MIN_AGE:
            raise AgeNotSupported(f"the first milestone check is at {who_motor.MIN_AGE} "
                                  f"months; this child is {age_months} months")
        return "milestone_check"
    lo, hi = model_age_range()
    if lo <= age_months <= hi:
        return "model"
    raise AgeNotSupported(f"assessments cover 0 to {hi} months; this child is "
                          f"{age_months} months")


def model_version(age_months: int) -> str:
    method = method_for_age(age_months)
    if method == "milestone_check":
        return "who-mgrs-2006"
    if age_months < 24:
        return get_under2()["version"]
    return get_release()["manifest"]["version"]


def items_for_age(age_months: int) -> list[str]:
    from hatua_ml.norms import who_motor

    method = method_for_age(age_months)
    if method == "milestone_check":
        return who_motor.items_for_age(age_months)
    if age_months < 24:
        return list(get_under2()["items_by_month"][str(age_months)])
    return list(get_release()["items"])


def age_band(age_months: int) -> str:
    from hatua_ml.models.explain import UNDER2_BANDS
    from hatua_ml.models.explain import age_band as band

    lo, hi = band(age_months, UNDER2_BANDS) if age_months < 24 else band(age_months)
    return f"{lo}-{hi}"


def assess(age_months: int, sex: str, coded: dict[str, float | None]) -> dict:
    """coded: item -> 1 achieved / 0 not achieved / None don't know, for items_for_age(age).

    Returns a common shape for every method: risk_level, anomaly_flag, explanation
    (domains + top_reasons), model details and model_version."""
    method = method_for_age(age_months)
    if method == "milestone_check":
        return _milestone_check(age_months, coded)
    if age_months < 24:
        return _under2_model(age_months, sex, coded)
    return _model(age_months, sex, coded)


def _with_questions(explanation: dict) -> dict:
    for reason in explanation["top_reasons"]:
        reason["question"] = QUESTIONS[reason["item"]]["short"]
    return explanation


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
    explanation = _with_questions(release["explainer"].explain(X)[0])
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


def under2_inputs(age_months: int, sex: str, coded: dict, items: list[str]) -> pd.DataFrame:
    """Same columns as hatua_ml.models.train_under2.inputs. Age is the middle of the
    completed month (training ages are exact days). Questions not asked, and "don't
    know", stay blank: the model was trained with blanks meaning "not asked"."""
    row = {"age_months": age_months + 0.5, "female": 1.0 if sex == "female" else 0.0,
           "gest_weeks": DEFAULT_GEST_WEEKS}
    for i in items:
        v = coded.get(i)
        row[i] = np.nan if v is None else float(v)
    return pd.DataFrame([row])


def _under2_model(age_months: int, sex: str, coded: dict) -> dict:
    m = get_under2()
    X = under2_inputs(age_months, sex, coded, m["items"])
    probability = float(m["model"].predict_proba(X)[:, 1][0])
    explanation = _with_questions(m["explainer"].explain(X)[0])
    flagger = m["flagger"]
    anomaly_score, anomaly_flag = None, False
    if flagger is not None:
        raw = float(flagger.score(X)[0])  # -inf when too few answers to judge
        anomaly_flag = raw >= flagger.threshold_
        anomaly_score = raw if np.isfinite(raw) else None
    return {
        "method": "model",
        "risk_level": risk_level(probability, m["threshold"], m["high_threshold"]),
        "anomaly_flag": bool(anomaly_flag),
        "explanation": explanation,
        "details": {"probability": probability, "threshold": m["threshold"],
                    "high_threshold": m["high_threshold"], "high_threshold_source": "release",
                    "anomaly_score": anomaly_score, "gest_weeks_assumed": DEFAULT_GEST_WEEKS},
        "model_version": m["version"],
    }


def _milestone_check(age_months: int, coded: dict) -> dict:
    from hatua_ml.norms import who_motor

    r = who_motor.assess(age_months, coded)
    reasons = [{"item": o["item"], "domain": "motor", "months_past_window": o["months_past_window"],
                "question": QUESTIONS[o["item"]]["short"]} for o in r["overdue"]]
    explanation = {
        "flagged": r["risk_level"] != "low",
        # Only movement is checked by this rule; other domains are not reported.
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
