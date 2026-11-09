"""Turns stored rows into what the caregiver and the CHW see."""
from datetime import date

from app.db.models import CaregiverInput, Child, PredictionResult

DOMAIN_LABELS = {"motor": "Movement", "language": "Language", "cognitive": "Thinking and learning",
                 "social_emotional": "Social and emotional"}

# Fixed messages shown to the caregiver once a CHW records an outcome. Nothing is
# shown for "unreachable".
CAREGIVER_MESSAGES = {
    "refer_to_facility": "Your community health worker recommends a visit to a health "
                         "facility for a developmental check.",
    "reviewed_not_concerning": "Your community health worker has reviewed this result "
                               "and is not concerned at this time.",
}


def age_in_months(dob: date, on: date | None = None) -> int:
    on = on or date.today()
    months = (on.year - dob.year) * 12 + on.month - dob.month
    return months - (on.day < dob.day)


def needs_chw(risk_level: str, anomaly_flag: bool) -> bool:
    return risk_level in ("medium", "high") or anomaly_flag


def stored(result: dict) -> dict:
    """What goes in prediction_results.shap_values (JSONB) for an inference result."""
    return {"method": result["method"], "explanation": result["explanation"],
            "details": result["details"]}


def _details(saved: dict) -> dict:
    # Rows saved before "details" existed kept the model numbers at the top level.
    if "details" in saved:
        return saved["details"]
    return {k: saved[k] for k in ("probability", "threshold", "anomaly_score") if k in saved}


def to_out(pred: PredictionResult, inp: CaregiverInput, child: Child) -> dict:
    saved = pred.shap_values
    expl = saved["explanation"]
    domains = [{"domain": d, "label": DOMAIN_LABELS[d], "status": v["status"],
                "contribution": v.get("contribution"), "n_items": v["n_items"]}
               for d, v in expl["domains"].items()]
    return {
        "prediction_id": pred.prediction_id, "child_id": child.child_id,
        "child_name": child.first_name, "child_avatar_id": child.avatar_id,
        "age_months": inp.age_months, "age_band": inp.age_band,
        "method": saved.get("method", "model"),
        "risk_level": pred.risk_level, "anomaly_flag": pred.anomaly_flag,
        "sent_to_chw": needs_chw(pred.risk_level, pred.anomaly_flag),
        "domains": domains,
        "top_reasons": [{**r, "domain_label": DOMAIN_LABELS[r["domain"]]}
                        for r in expl["top_reasons"]],
        "model": {"version": pred.model_version, **_details(saved)},
        "chw_outcome": pred.chw_outcome,
        "caregiver_message": CAREGIVER_MESSAGES.get(pred.chw_outcome),
        "reviewed_at": pred.reviewed_at,
        "submitted_at": inp.submitted_at,
    }
