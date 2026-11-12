"""Caregiver assessments: the questions for a child, and submitting answers (#13, #14, #15).

Only the child's own caregiver submits answers (CHWs review, they do not submit). The
same endpoints serve both age ranges: 24 to 59 months go through the trained model,
0 to 23 months through the under-24 model (or the WHO motor milestone check if that model is not available). The response says which.
"""
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_child, require
from app.db.models import CaregiverInput, MilestoneSummary, PredictionResult, User
from app.db.session import get_db
from app.schemas.assessment import AssessmentIn, AssessmentOut
from app.services import inference
from app.services.growth import growth_flags, latest_z_scores
from app.services.questions import (code, questionnaire, raised_red_flags, red_flag_items,
                                    red_flag_questions)
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
    # The model's questions first, then the hearing and vision red-flag questions.
    qs = questionnaire(items, user.language) + red_flag_questions(age, user.language)
    for q in qs:
        q["text"] = q["text"].replace("{name}", child.first_name)
        if q["hint"]:
            q["hint"] = q["hint"].replace("{name}", child.first_name)
    version = inference.model_version(age)
    return {"child_id": child.child_id, "age_months": age, "age_band": inference.age_band(age),
            "method": method, "model_version": version, "questions": qs}


@router.post("", response_model=AssessmentOut, status_code=201)
def submit(body: AssessmentIn, user: User = Depends(caregiver), db: Session = Depends(get_db)):
    child = get_child(body.child_id, user, db)
    age = age_in_months(child.date_of_birth)
    items = _items(age)
    # Red-flag answers are kept apart from the model's. They may be left out (a check
    # saved on the phone before these questions existed still goes through).
    screening = {i: a for i, a in body.responses.items() if i in red_flag_items(age)}
    answers = {i: a for i, a in body.responses.items() if i not in screening}
    missing = [i for i in items if i not in answers]
    extra = [i for i in answers if i not in items]
    if missing or extra:
        raise HTTPException(422, {"missing": missing, "unexpected": extra})
    try:
        coded = {i: code(i, a) for i, a in answers.items()}
        red_flags = raised_red_flags(screening)
    except ValueError as e:
        raise HTTPException(422, str(e))
    # The growth check: the latest weight and height from the last 90 days, against the
    # WHO standard. Like the red flags, a rule that routes to the CHW, not a model input.
    today = date.today()
    growth_z = latest_z_scores(child.date_of_birth, child.sex, child.growth or [], today)
    red_flags += growth_flags(child.date_of_birth, child.sex, child.growth or [], today)

    try:
        result = inference.assess(age, child.sex, coded)
    except inference.AgeNotSupported as e:
        raise HTTPException(422, str(e))
    except inference.ModelNotAvailable as e:
        raise HTTPException(503, f"model release not available: {e}")

    inp = CaregiverInput(child_id=child.child_id, age_months=age, age_band=inference.age_band(age),
                         responses={"answers": answers, "coded": coded,
                                    "screening": screening, "growth": growth_z})
    db.add(inp)
    db.flush()
    pred = PredictionResult(input_id=inp.input_id, risk_level=result["risk_level"],
                            anomaly_flag=result["anomaly_flag"], red_flags=red_flags,
                            model_version=result["model_version"], shap_values=stored(result))
    db.add(pred)

    # Milestone summary: latest status per domain. A check that covers fewer domains
    # (under 24 months: movement and language only) updates those and leaves the others
    # as they were; a "not_assessed" domain never overwrites an earlier result.
    status = {d: v["status"] for d, v in result["explanation"]["domains"].items()
              if v["status"] != "not_assessed"}
    summary = db.scalar(select(MilestoneSummary).where(MilestoneSummary.child_id == child.child_id))
    if summary is None:
        db.add(MilestoneSummary(child_id=child.child_id, domain_status=status))
    else:
        summary.domain_status = {**summary.domain_status, **status}
    db.commit()
    db.refresh(inp)
    return to_out(pred, inp, child, user.language)
