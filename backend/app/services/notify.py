"""Who gets a push notification, and what it says (sent by app.core.push).

    CHW        a check from one of their families was sent to them for review
               a caregiver sent them a question
    caregiver  their CHW replied
               their CHW reviewed a check (refer or not concerning; nothing for
               "unreachable", as on the result screen)
               a child reached a new age band with no check yet (daily job:
               python -m app.cli send-reminders)

The text names no risk level and quotes no message, so a lock screen shows nothing
private. Each person gets it in their own language (users.language).
"""
from datetime import date

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import push
from app.db.models import CaregiverInput, Child, PredictionResult, User
from app.services import inference
from app.services.i18n import tr
from app.services.results import CAREGIVER_MESSAGES, age_in_months, needs_chw


def _t(text: str, lang: str, **params) -> str:
    out = tr(text, lang)
    for k, v in params.items():
        out = out.replace("{" + k + "}", str(v))
    return out


def _to(bg: BackgroundTasks | None, user: User | None, title: str, body: str,
        data: dict, **params) -> None:
    """Queue a notification for after the response (or send now without bg)."""
    if user is None or not user.is_active or not user.push_tokens:
        return
    tokens = [t["token"] for t in user.push_tokens if t.get("token")]
    args = (user.user_id, tokens, _t(title, user.language, **params),
            _t(body, user.language, **params), data)
    if bg is None:
        push.send(*args)
    else:
        bg.add_task(push.send, *args)


def _chw_of(db: Session, caregiver: User) -> User | None:
    if caregiver.linked_chw_id is None:
        return None
    chw = db.get(User, caregiver.linked_chw_id)
    return chw if chw is not None and not chw.invite_pending else None


def flagged_check(bg, db: Session, caregiver: User, child: Child, pred: PredictionResult) -> None:
    if needs_chw(pred.risk_level, pred.anomaly_flag, pred.red_flags):
        _to(bg, _chw_of(db, caregiver), "A check needs your review",
            "A check for {child} ({caregiver}) was sent to you.",
            {"type": "case", "id": pred.prediction_id},
            child=child.first_name, caregiver=caregiver.full_name)


def new_question(bg, db: Session, caregiver: User) -> None:
    _to(bg, _chw_of(db, caregiver), "New question", "{caregiver} sent you a question.",
        {"type": "thread", "id": caregiver.user_id}, caregiver=caregiver.full_name)


def chw_replied(bg, caregiver: User) -> None:
    _to(bg, caregiver, "New message", "Your health worker replied to your question.",
        {"type": "ask"})


def outcome_recorded(bg, caregiver: User, child: Child, pred: PredictionResult) -> None:
    if pred.chw_outcome in CAREGIVER_MESSAGES:
        _to(bg, caregiver, "{child}'s check was reviewed",
            "Your health worker has looked at {child}'s check. Open Hatua to see what they "
            "say.", {"type": "result", "id": pred.prediction_id, "child_id": child.child_id},
            child=child.first_name)


def send_check_reminders(session_factory, today: date | None = None) -> int:
    """One reminder per child per age band, when the band has no check yet. Run daily.
    Returns how many reminders were sent."""
    today = today or date.today()
    sent = 0
    with session_factory() as db:
        rows = db.execute(select(Child, User).join(User, Child.caregiver_id == User.user_id)
                          .where(User.is_active)).all()
        for child, caregiver in rows:
            age = age_in_months(child.date_of_birth, today)
            if not 0 <= age < 60:
                continue
            band = inference.age_band(age)
            if child.reminded_band == band:
                continue
            checked = db.scalar(select(CaregiverInput.input_id).where(
                CaregiverInput.child_id == child.child_id,
                CaregiverInput.age_band == band).limit(1))
            if checked is None and caregiver.push_tokens:
                _to(None, caregiver, "Time for {child}'s check",
                    "{child} has reached a new age stage. A short check shows how they are "
                    "doing.", {"type": "child", "id": child.child_id}, child=child.first_name)
                sent += 1
            # Either way this band is done: checked already, reminded now, or the caregiver
            # has no phone to remind (they will see the due check in the app).
            child.reminded_band = band
        db.commit()
    return sent
