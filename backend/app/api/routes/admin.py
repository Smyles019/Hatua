"""Administrator endpoints (#17): accounts, caregiver-to-CHW links, usage summary.

Accounts are deactivated, never deleted: a CHW's recorded outcomes must keep their
reviewer, and a deactivated account simply cannot sign in.
"""
import uuid
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require
from app.api.routes.auth import add_user
from app.db.models import CHW_OUTCOMES, RISK_LEVELS, ROLES, CaregiverInput, Child, PredictionResult, User
from app.db.session import get_db
from app.schemas.users import LinkChw, NewUser, UsageSummary, UserOut, UserUpdate

router = APIRouter()
admin_only = require("admin")


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(body: NewUser, _: User = Depends(admin_only), db: Session = Depends(get_db)):
    # The administrator vouches for the address, so no confirmation email is needed.
    return add_user(db, full_name=body.full_name, email=body.email,
                    phone_number=body.phone_number, password=body.password, role=body.role,
                    email_verified=True)


@router.get("/users", response_model=list[UserOut])
def list_users(role: str | None = None, active: bool | None = None,
               _: User = Depends(admin_only), db: Session = Depends(get_db)):
    q = select(User).order_by(User.created_at)
    if role:
        if role not in ROLES:
            raise HTTPException(422, f"role must be one of {', '.join(ROLES)}")
        q = q.where(User.role == role)
    if active is not None:
        q = q.where(User.is_active.is_(active))
    return db.scalars(q).all()


def _user(user_id: uuid.UUID, db: Session) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "user not found")
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: uuid.UUID, body: UserUpdate, admin: User = Depends(admin_only),
                db: Session = Depends(get_db)):
    user = _user(user_id, db)
    if body.is_active is False and user.user_id == admin.user_id:
        raise HTTPException(409, "you cannot deactivate your own account")
    if body.is_active is False and user.role == "chw":
        # Their caregivers would otherwise be routed to nobody without anyone noticing.
        linked = db.scalar(select(func.count()).where(User.linked_chw_id == user.user_id))
        if linked:
            raise HTTPException(409, f"move this CHW's {linked} caregiver(s) to another CHW first")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    db.commit()
    return user


@router.put("/users/{caregiver_id}/chw", response_model=UserOut)
def link_chw(caregiver_id: uuid.UUID, body: LinkChw, _: User = Depends(admin_only),
             db: Session = Depends(get_db)):
    caregiver = _user(caregiver_id, db)
    if caregiver.role != "caregiver":
        raise HTTPException(404, "caregiver not found")
    if body.chw_id is not None:
        chw = db.get(User, body.chw_id)
        if chw is None or chw.role != "chw" or not chw.is_active:
            raise HTTPException(404, "CHW not found")
    caregiver.linked_chw_id = body.chw_id
    db.commit()
    return caregiver


@router.get("/summary", response_model=UsageSummary)
def summary(start: date | None = None, end: date | None = None,
            _: User = Depends(admin_only), db: Session = Depends(get_db)):
    """Usage over a period (inclusive dates, East Africa Time). Without dates: all time.

    assessments    submitted in the period
    by_risk_level  of those assessments
    outcomes       CHW outcomes recorded in the period
    awaiting_review  routed cases with no outcome yet, at the time of the request
    """
    if start and end and start > end:
        raise HTTPException(422, "start is after end")
    eat = timezone(timedelta(hours=3))
    lo = datetime.combine(start, time.min, eat) if start else None
    hi = datetime.combine(end + timedelta(days=1), time.min, eat) if end else None

    def within(col):
        conds = []
        if lo:
            conds.append(col >= lo)
        if hi:
            conds.append(col < hi)
        return conds

    results = (select(PredictionResult)
               .join(CaregiverInput, PredictionResult.input_id == CaregiverInput.input_id)
               .where(*within(CaregiverInput.submitted_at)).subquery())
    by_risk = dict(db.execute(select(results.c.risk_level, func.count())
                              .group_by(results.c.risk_level)).all())
    routed = ((results.c.risk_level.in_(("medium", "high"))) | results.c.anomaly_flag
              | (func.jsonb_array_length(results.c.red_flags) > 0))
    outcomes = dict(db.execute(select(PredictionResult.chw_outcome, func.count())
                               .where(PredictionResult.chw_outcome.is_not(None),
                                      *within(PredictionResult.reviewed_at))
                               .group_by(PredictionResult.chw_outcome)).all())
    awaiting = db.scalar(select(func.count()).select_from(PredictionResult).where(
        (PredictionResult.risk_level.in_(("medium", "high")) | PredictionResult.anomaly_flag
         | (func.jsonb_array_length(PredictionResult.red_flags) > 0)),
        PredictionResult.chw_outcome.is_(None)))
    users = dict(db.execute(select(User.role, func.count()).where(User.is_active)
                            .group_by(User.role)).all())
    return {
        "period": {"start": start, "end": end},
        "users": {r: users.get(r, 0) for r in ROLES},
        "children": db.scalar(select(func.count()).select_from(Child)),
        "assessments": sum(by_risk.values()),
        "by_risk_level": {r: by_risk.get(r, 0) for r in RISK_LEVELS},
        "flagged_for_chw": db.scalar(select(func.count()).select_from(results).where(routed)),
        "anomaly_flags": db.scalar(select(func.count()).select_from(results)
                                   .where(results.c.anomaly_flag)),
        "red_flags": db.scalar(select(func.count()).select_from(results)
                               .where(func.jsonb_array_length(results.c.red_flags) > 0)),
        "outcomes": {o: outcomes.get(o, 0) for o in CHW_OUTCOMES},
        "awaiting_review": awaiting,
        "generated_at": datetime.now(timezone.utc),
    }
