"""Administrator endpoints (#17): accounts, CHW invites, caregiver-to-CHW links, usage
summary.

Accounts are deactivated, never deleted: a CHW's recorded outcomes must keep their
reviewer, and a deactivated account simply cannot sign in.
"""
import uuid
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require
from app.api.routes.auth import add_user, send_invite
from app.db.models import CHW_OUTCOMES, RISK_LEVELS, ROLES, CaregiverInput, Child, PredictionResult, User
from app.db.session import get_db
from app.services import immunization
from app.schemas.users import (ChwOut, LinkChw, NewChw, NewUser, UsageSummary, UserOut,
                               UserUpdate)

router = APIRouter()
admin_only = require("admin")


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(body: NewUser, _: User = Depends(admin_only), db: Session = Depends(get_db)):
    # The administrator vouches for the address, so no confirmation email is needed.
    return add_user(db, full_name=body.full_name, email=body.email,
                    phone_number=body.phone_number, password=body.password, role=body.role,
                    email_verified=True)


# ---- CHWs: invite by name and email ----

@router.get("/chws", response_model=list[ChwOut])
def list_chws(_: User = Depends(admin_only), db: Session = Depends(get_db)):
    """Every CHW, newest first, with how many active caregivers each has. A CHW whose
    invite_pending is true has not set up their account yet."""
    linked = dict(db.execute(select(User.linked_chw_id, func.count())
                             .where(User.role == "caregiver", User.is_active,
                                    User.linked_chw_id.is_not(None))
                             .group_by(User.linked_chw_id)).all())
    chws = db.scalars(select(User).where(User.role == "chw")
                      .order_by(User.created_at.desc())).all()
    return [ChwOut.model_validate(c).model_copy(update={"caregivers": linked.get(c.user_id, 0)})
            for c in chws]


@router.post("/chws", response_model=ChwOut, status_code=201)
def invite_chw(body: NewChw, _: User = Depends(admin_only), db: Session = Depends(get_db)):
    """Adds a CHW by name and email and emails them the link to set up their account."""
    if db.scalar(select(User).where(User.email == body.email)) is not None:
        raise HTTPException(409, "an account with this email already exists")
    user = User(full_name=body.full_name, email=body.email, role="chw",
                invited_at=datetime.now(timezone.utc))
    db.add(user)
    db.commit()
    send_invite(db, user)
    return user


@router.post("/chws/{user_id}/invite", response_model=ChwOut)
def resend_invite(user_id: uuid.UUID, _: User = Depends(admin_only),
                  db: Session = Depends(get_db)):
    """Sends a new invite; the earlier link stops working."""
    user = _user(user_id, db)
    if user.role != "chw":
        raise HTTPException(404, "CHW not found")
    if not user.invite_pending:
        raise HTTPException(409, "this CHW has already set up their account")
    if not user.is_active:
        raise HTTPException(409, "reactivate this CHW before sending an invite")
    send_invite(db, user)
    return user


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
        if chw.invite_pending:
            raise HTTPException(409, "this CHW has not set up their account yet")
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
    # Accounts people can use: active, and not an invite still waiting to be set up.
    users = dict(db.execute(select(User.role, func.count())
                            .where(User.is_active, (User.password_hash.is_not(None)
                                                    | User.google_id.is_not(None)))
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
        "immunization": _immunization(db),
        "generated_at": datetime.now(timezone.utc),
    }


def _immunization(db: Session) -> dict:
    """Children under five today, by the state of their vaccine record: every dose due so
    far ticked; some dose overdue (app.services.immunization); not started (nothing
    ticked); the rest are partly copied from the booklet. Counts only, no children."""
    out = {"children": 0, "up_to_date": 0, "overdue": 0, "not_started": 0, "partly_recorded": 0}
    for child in db.scalars(select(Child)):
        r = immunization.record(child)
        v = r["counts"]["vaccine"]
        if not r["doses"] or v["total"] == v["upcoming"] and not v["given"]:
            continue  # too young for any dose, or five already
        out["children"] += 1
        if v["overdue"]:
            out["overdue"] += 1
        elif not v["given"]:
            out["not_started"] += 1
        elif v["not_recorded"] or v["due"]:
            out["partly_recorded"] += 1
        else:
            out["up_to_date"] += 1
    return out
