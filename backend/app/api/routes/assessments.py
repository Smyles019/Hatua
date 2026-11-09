"""Caregiver assessments: the questions for a child, and submitting answers (#13, #14, #15).

Only the child's own caregiver submits answers (CHWs review, they do not submit). The
same endpoints serve both age ranges: 24 to 59 months go through the trained model,
4 to 23 months through the WHO motor milestone check. The response says which.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_child, require
from app.db.models import CaregiverInput, MilestoneSummary, PredictionResult, User
from app.db.session import get_db
from app.schemas.assessment import AssessmentIn, AssessmentOut
from app.services import inference
from app.services.questions import code, questionnaire
from app.services.results import age_in_months, stored, to_out

router = APIRouter()
caregiver = require("caregiver")


def _items(age: int) -> list[str]:
    try:
        return inference.items_for_age(age)
    except inference.AgeNotSupported as e:
        raise HTTPException(422, str(e))
    except inference.ModelNotAvailable as e:
        raise HTTPException(503, f"model release not available: {e}")


@router.get("/questions")
def questions(child_id: uuid.UUID, user: User = Depends(caregiver), db: Session = Depends(get_db)):
    child = get_child(child_id, user, db)
    age = age_in_months(child.date_of_birth)
    items = _items(age)
    method = inference.method_for_age(age)
    qs = questionnaire(items)
    for q in qs:
        q["text"] = q["text"].replace("{name}", child.first_name)
    version = (inference.get_release()["manifest"]["version"] if method == "model"
               else "who-mgrs-2006")
    return {"child_id": child.child_id, "age_months": age, "age_band": inference.age_band(age),
            "method": method, "model_version": version, "questions": qs}


@router.post("", response_model=AssessmentOut, status_code=201)
def submit(body: AssessmentIn, user: User = Depends(caregiver), db: Session = Depends(get_db)):
    child = get_child(body.child_id, user, db)
    age = age_in_months(child.date_of_birth)
    items = _items(age)
    missing = [i for i in items if i not in body.responses]
    extra = [i for i in body.responses if i not in items]
    if missing or extra:
        raise HTTPException(422, {"missing": missing, "unexpected": extra})
    try:
        coded = {i: code(i, a) for i, a in body.responses.items()}
    except ValueError as e:
        raise HTTPException(422, str(e))

    try:
        result = inference.assess(age, child.sex, coded)
    except inference.AgeNotSupported as e:
        raise HTTPException(422, str(e))
    except inference.ModelNotAvailable as e:
        raise HTTPException(503, f"model release not available: {e}")

    inp = CaregiverInput(child_id=child.child_id, age_months=age, age_band=inference.age_band(age),
                         responses={"answers": body.responses, "coded": coded})
    db.add(inp)
    db.flush()
    pred = PredictionResult(input_id=inp.input_id, risk_level=result["risk_level"],
                            anomaly_flag=result["anomaly_flag"],
                            model_version=result["model_version"], shap_values=stored(result))
    db.add(pred)

    # Milestone summary: latest status per domain. A check that covers fewer domains
    # (under 24 months: movement only) updates those and leaves the others as they were.
    status = {d: v["status"] for d, v in result["explanation"]["domains"].items()}
    summary = db.scalar(select(MilestoneSummary).where(MilestoneSummary.child_id == child.child_id))
    if summary is None:
        db.add(MilestoneSummary(child_id=child.child_id, domain_status=status))
    else:
        summary.domain_status = {**summary.domain_status, **status}
    db.commit()
    db.refresh(inp)
    return to_out(pred, inp, child)
