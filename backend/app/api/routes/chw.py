"""CHW dashboard (#16): enrolment, linked caregivers, routed cases and outcomes.

A result reaches the CHW when it is medium or high risk or carries an anomaly flag,
and the child's caregiver is linked to that CHW.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require
from app.api.routes.auth import add_user
from app.db.models import CaregiverInput, Child, PredictionResult, User
from app.db.session import get_db
from app.schemas.assessment import OutcomeIn
from app.schemas.users import EnrolCaregiver, LinkByPhone, UserOut
from app.services.results import to_out

router = APIRouter()
chw_only = require("chw")


def routed():
    """Results that go to a CHW: medium or high risk, or an anomaly flag."""
    return or_(PredictionResult.risk_level.in_(("medium", "high")),
               PredictionResult.anomaly_flag.is_(True))


@router.get("/caregivers")
def my_caregivers(user: User = Depends(chw_only), db: Session = Depends(get_db)):
    """Caregivers linked to this CHW, with how many children and open cases each has."""
    rows = db.execute(
        select(User, func.count(func.distinct(Child.child_id)))
        .outerjoin(Child, Child.caregiver_id == User.user_id)
        .where(User.linked_chw_id == user.user_id)
        .group_by(User.user_id).order_by(User.full_name)).all()
    open_cases = dict(db.execute(
        select(Child.caregiver_id, func.count())
        .join(CaregiverInput, CaregiverInput.child_id == Child.child_id)
        .join(PredictionResult, PredictionResult.input_id == CaregiverInput.input_id)
        .join(User, Child.caregiver_id == User.user_id)
        .where(User.linked_chw_id == user.user_id, routed(),
               PredictionResult.chw_outcome.is_(None))
        .group_by(Child.caregiver_id)).all())
    return [{**UserOut.model_validate(c).model_dump(), "children": n,
             "open_cases": open_cases.get(c.user_id, 0)} for c, n in rows]


@router.post("/caregivers", response_model=UserOut, status_code=201)
def enrol_caregiver(body: EnrolCaregiver, user: User = Depends(chw_only),
                    db: Session = Depends(get_db)):
    """Create a caregiver account during a household visit, already linked to this CHW."""
    return add_user(db, full_name=body.full_name, phone_number=body.phone_number,
                    password=body.password, role="caregiver", linked_chw_id=user.user_id)


@router.post("/caregivers/link", response_model=UserOut)
def link_existing(body: LinkByPhone, user: User = Depends(chw_only), db: Session = Depends(get_db)):
    """Link a caregiver who registered on their own. Refused if another CHW already has them;
    an administrator can move a caregiver between CHWs."""
    caregiver = db.scalar(select(User).where(User.phone_number == body.phone_number))
    if caregiver is None or caregiver.role != "caregiver" or not caregiver.is_active:
        raise HTTPException(404, "no caregiver account with this phone number")
    if caregiver.linked_chw_id not in (None, user.user_id):
        raise HTTPException(409, "this caregiver is linked to another CHW; ask an administrator")
    caregiver.linked_chw_id = user.user_id
    db.commit()
    return caregiver


@router.get("/cases")
def cases(include_reviewed: bool = False, user: User = Depends(chw_only),
          db: Session = Depends(get_db)):
    q = (select(PredictionResult, CaregiverInput, Child, User)
         .join(CaregiverInput, PredictionResult.input_id == CaregiverInput.input_id)
         .join(Child, CaregiverInput.child_id == Child.child_id)
         .join(User, Child.caregiver_id == User.user_id)
         .where(User.linked_chw_id == user.user_id, routed())
         .order_by(CaregiverInput.submitted_at.desc()))
    if not include_reviewed:
        q = q.where(PredictionResult.chw_outcome.is_(None))
    out = []
    for p, i, c, caregiver in db.execute(q):
        row = to_out(p, i, c)
        row["caregiver"] = {"user_id": caregiver.user_id, "full_name": caregiver.full_name,
                            "phone_number": caregiver.phone_number}
        row["location"] = c.location
        row["answers"] = i.responses["answers"]
        out.append(row)
    return out


@router.post("/cases/{prediction_id}/outcome")
def record_outcome(prediction_id: uuid.UUID, body: OutcomeIn, user: User = Depends(chw_only),
                   db: Session = Depends(get_db)):
    row = db.execute(select(PredictionResult, CaregiverInput, Child, User)
                     .join(CaregiverInput, PredictionResult.input_id == CaregiverInput.input_id)
                     .join(Child, CaregiverInput.child_id == Child.child_id)
                     .join(User, Child.caregiver_id == User.user_id)
                     .where(PredictionResult.prediction_id == prediction_id)).first()
    if row is None or row[3].linked_chw_id != user.user_id:
        raise HTTPException(404, "case not found")  # same answer for someone else's case
    pred, inp, child, _ = row
    if not (pred.risk_level in ("medium", "high") or pred.anomaly_flag):
        raise HTTPException(409, "low-risk results without a flag are not CHW cases")
    pred.chw_outcome = body.outcome
    pred.reviewed_by = user.user_id
    pred.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    return to_out(pred, inp, child)
