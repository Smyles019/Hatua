"""CHW dashboard (#16): enrolment, linked caregivers, routed cases and outcomes.

A result reaches the CHW when it is medium or high risk or carries an anomaly flag,
and the child's caregiver is linked to that CHW.
"""
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import jwt
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import require
from app.api.routes.auth import add_user, send_verification
from app.core.config import settings
from app.core.security import create_link_token, link_still_matches, read_link_token
from app.db.models import CaregiverInput, Child, PredictionResult, User
from app.db.session import get_db
from app.schemas.assessment import OutcomeIn
from app.schemas.users import EnrolCaregiver, LinkByPhone, UserOut
from app.services import notify, report, report_pdf
from app.services.results import needs_chw, to_out

router = APIRouter()
chw_only = require("chw")


def routed():
    """Results that go to a CHW: medium or high risk, an anomaly flag, or a hearing or
    vision red flag."""
    return or_(PredictionResult.risk_level.in_(("medium", "high")),
               PredictionResult.anomaly_flag.is_(True),
               func.jsonb_array_length(PredictionResult.red_flags) > 0)


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
    """Create a caregiver account during a household visit, already linked to this CHW.
    The caregiver confirms their email from the link sent here before the first sign-in,
    the same as anyone who registers, so a mistyped address is caught at once."""
    new = add_user(db, full_name=body.full_name, email=body.email,
                   phone_number=body.phone_number, password=body.password, role="caregiver",
                   linked_chw_id=user.user_id)
    send_verification(new)
    return new


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
        row = to_out(p, i, c, user.language)
        row["caregiver"] = {"user_id": caregiver.user_id, "full_name": caregiver.full_name,
                            "phone_number": caregiver.phone_number}
        row["location"] = c.location
        row["answers"] = i.responses["answers"]
        # Context from the child's profile: reasons for special care and the latest
        # weight and height entry.
        row["care_factors"] = c.care_factors or []
        row["latest_growth"] = (c.growth or [None])[-1]
        out.append(row)
    return out


@router.post("/cases/{prediction_id}/outcome")
def record_outcome(prediction_id: uuid.UUID, body: OutcomeIn, bg: BackgroundTasks,
                   user: User = Depends(chw_only), db: Session = Depends(get_db)):
    row = db.execute(select(PredictionResult, CaregiverInput, Child, User)
                     .join(CaregiverInput, PredictionResult.input_id == CaregiverInput.input_id)
                     .join(Child, CaregiverInput.child_id == Child.child_id)
                     .join(User, Child.caregiver_id == User.user_id)
                     .where(PredictionResult.prediction_id == prediction_id)).first()
    if row is None or row[3].linked_chw_id != user.user_id:
        raise HTTPException(404, "case not found")  # same answer for someone else's case
    pred, inp, child, caregiver = row
    if not needs_chw(pred.risk_level, pred.anomaly_flag, pred.red_flags):
        raise HTTPException(409, "low-risk results without a flag are not CHW cases")
    changed = pred.chw_outcome != body.outcome
    pred.chw_outcome = body.outcome
    pred.reviewed_by = user.user_id
    pred.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    if changed:  # saving the same outcome again tells the caregiver nothing new
        notify.outcome_recorded(bg, caregiver, child, pred)
    return to_out(pred, inp, child, user.language)


# ---- Full check report (every question and answer), for the CHW only ----
#
# GET  /chw/cases/{id}/report        the report as data, for the app and website screens
# POST /chw/cases/{id}/report-link   a link to the PDF that works for REPORT_MINUTES,
#                                    so the phone's browser can open it without the
#                                    sign-in token (the link is tied to this CHW and check)
# GET  /chw/report.pdf?token=...     the PDF

REPORT = "check_report"
REPORT_MINUTES = 10


def _linked_check(db: Session, prediction_id: uuid.UUID, chw: User):
    """(pred, input, child, caregiver) for a check of a caregiver linked to this CHW."""
    row = db.execute(select(PredictionResult, CaregiverInput, Child, User)
                     .join(CaregiverInput, PredictionResult.input_id == CaregiverInput.input_id)
                     .join(Child, CaregiverInput.child_id == Child.child_id)
                     .join(User, Child.caregiver_id == User.user_id)
                     .where(PredictionResult.prediction_id == prediction_id)).first()
    if row is None or row[3].linked_chw_id != chw.user_id:
        raise HTTPException(404, "check not found")  # same answer for someone else's check
    return row


@router.get("/cases/{prediction_id}/report")
def check_report(prediction_id: uuid.UUID, user: User = Depends(chw_only),
                 db: Session = Depends(get_db)):
    pred, inp, child, caregiver = _linked_check(db, prediction_id, user)
    return report.build(pred, inp, child, caregiver, user.language)


@router.post("/cases/{prediction_id}/report-link")
def check_report_link(prediction_id: uuid.UUID, user: User = Depends(chw_only),
                      db: Session = Depends(get_db)):
    _linked_check(db, prediction_id, user)
    token = create_link_token(user.user_id, REPORT, timedelta(minutes=REPORT_MINUTES),
                              bound_to=str(prediction_id))
    base = settings.public_base_url.rstrip("/")
    return {"url": f"{base}/chw/report.pdf?{urlencode({'id': str(prediction_id), 'token': token})}",
            "expires_in_minutes": REPORT_MINUTES}


@router.get("/report.pdf", include_in_schema=False)
def check_report_pdf(id: uuid.UUID, token: str, db: Session = Depends(get_db)):
    try:
        chw_id, fingerprint = read_link_token(token, REPORT)
    except jwt.InvalidTokenError:
        raise HTTPException(403, "this report link has expired; open the report again in Hatua")
    chw = db.get(User, chw_id)
    if (chw is None or not chw.is_active or chw.role != "chw"
            or not link_still_matches(fingerprint, str(id))):
        raise HTTPException(403, "this report link does not work")
    pred, inp, child, caregiver = _linked_check(db, id, chw)
    data = report.build(pred, inp, child, caregiver, chw.language)
    pdf = report_pdf.render(data, chw.language)
    name = f"Hatua-check-{child.first_name}-{inp.submitted_at:%Y-%m-%d}.pdf"
    safe = "".join(ch if ch.isalnum() or ch in "-." else "-" for ch in name)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{safe}"',
                             "Cache-Control": "no-store"})
