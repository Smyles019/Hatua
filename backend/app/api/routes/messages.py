"""Ask a CHW: a message thread between a caregiver and their community health worker.

Not live chat. The caregiver writes a question; the CHW linked to them replies when they
can; either side can follow up. There is one thread per caregiver. A question asked
before a CHW is linked waits in the thread and reaches the CHW once the link is made.
The app shows the danger signs before a question is sent: this is not for emergencies.

    caregiver  GET /messages, POST /messages
    chw        GET /messages/threads, GET and POST /messages/threads/{caregiver_id}
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require
from app.db.models import CaregiverInput, Child, Message, PredictionResult, User
from app.db.session import get_db
from app.schemas.assessment import MessageIn

router = APIRouter()
caregiver_only = require("caregiver")
chw_only = require("chw")


def _thread(db: Session, caregiver: User, viewer: User) -> dict:
    rows = db.execute(
        select(Message, User.role, User.full_name)
        .join(User, Message.sender_id == User.user_id)
        .where(Message.caregiver_id == caregiver.user_id)
        .order_by(Message.created_at, Message.message_id)).all()
    # Which child and check a question was asked about, for the messages that carry one.
    about = {}
    ids = [m.prediction_id for m, _r, _n in rows if m.prediction_id]
    if ids:
        for pid, name, risk in db.execute(
                select(PredictionResult.prediction_id, Child.first_name,
                       PredictionResult.risk_level)
                .join(CaregiverInput, PredictionResult.input_id == CaregiverInput.input_id)
                .join(Child, CaregiverInput.child_id == Child.child_id)
                .where(PredictionResult.prediction_id.in_(ids))):
            about[pid] = {"prediction_id": pid, "child_name": name, "risk_level": risk}
    messages = [{"message_id": m.message_id, "body": m.body, "created_at": m.created_at,
                 "from_me": m.sender_id == viewer.user_id, "sender_role": role,
                 "sender_name": name, "about": about.get(m.prediction_id)}
                for m, role, name in rows]
    chw = db.get(User, caregiver.linked_chw_id) if caregiver.linked_chw_id else None
    return {
        "caregiver": {"user_id": caregiver.user_id, "full_name": caregiver.full_name,
                      "phone_number": caregiver.phone_number},
        "chw": {"full_name": chw.full_name} if chw else None,
        # Waiting for the CHW when the newest message is the caregiver's.
        "waiting_for_chw": bool(messages) and messages[-1]["sender_role"] == "caregiver",
        "messages": messages,
    }


def _add(db: Session, caregiver: User, sender: User, body: str,
         prediction_id: uuid.UUID | None = None) -> None:
    db.add(Message(caregiver_id=caregiver.user_id, sender_id=sender.user_id,
                   prediction_id=prediction_id, body=body.strip()))
    db.commit()


# ---- caregiver ----

@router.get("")
def my_thread(user: User = Depends(caregiver_only), db: Session = Depends(get_db)):
    return _thread(db, user, user)


@router.post("", status_code=201)
def ask(body: MessageIn, user: User = Depends(caregiver_only), db: Session = Depends(get_db)):
    if not body.body.strip():
        raise HTTPException(422, "write your question first")
    if body.prediction_id is not None:
        owner = db.scalar(
            select(Child.caregiver_id)
            .join(CaregiverInput, CaregiverInput.child_id == Child.child_id)
            .join(PredictionResult, PredictionResult.input_id == CaregiverInput.input_id)
            .where(PredictionResult.prediction_id == body.prediction_id))
        if owner != user.user_id:
            raise HTTPException(404, "check not found")
    _add(db, user, user, body.body, body.prediction_id)
    return _thread(db, user, user)


# ---- CHW ----

def _linked(db: Session, caregiver_id: uuid.UUID, chw: User) -> User:
    caregiver = db.get(User, caregiver_id)
    if caregiver is None or caregiver.linked_chw_id != chw.user_id:
        raise HTTPException(404, "caregiver not found")  # same answer for someone else's
    return caregiver


@router.get("/threads")
def threads(user: User = Depends(chw_only), db: Session = Depends(get_db)):
    """One row per linked caregiver who has written, unanswered questions first."""
    newest = (select(Message.caregiver_id, func.max(Message.created_at).label("at"),
                     func.count().label("n"))
              .group_by(Message.caregiver_id).subquery())
    rows = db.execute(
        select(User, Message, newest.c.n)
        .join(newest, newest.c.caregiver_id == User.user_id)
        .join(Message, (Message.caregiver_id == User.user_id)
              & (Message.created_at == newest.c.at))
        .where(User.linked_chw_id == user.user_id)).all()
    out, seen = [], set()
    for caregiver, last, n in rows:
        if caregiver.user_id in seen:  # two messages in the same instant
            continue
        seen.add(caregiver.user_id)
        out.append({
            "caregiver": {"user_id": caregiver.user_id, "full_name": caregiver.full_name,
                          "phone_number": caregiver.phone_number},
            "messages": n,
            "waiting_for_chw": last.sender_id == caregiver.user_id,
            "last_message": {"body": last.body, "created_at": last.created_at,
                             "from_caregiver": last.sender_id == caregiver.user_id},
        })
    out.sort(key=lambda t: t["last_message"]["created_at"], reverse=True)
    out.sort(key=lambda t: not t["waiting_for_chw"])
    return out


@router.get("/threads/{caregiver_id}")
def thread(caregiver_id: uuid.UUID, user: User = Depends(chw_only),
           db: Session = Depends(get_db)):
    return _thread(db, _linked(db, caregiver_id, user), user)


@router.post("/threads/{caregiver_id}", status_code=201)
def reply(caregiver_id: uuid.UUID, body: MessageIn, user: User = Depends(chw_only),
          db: Session = Depends(get_db)):
    caregiver = _linked(db, caregiver_id, user)
    if not body.body.strip():
        raise HTTPException(422, "write your reply first")
    _add(db, caregiver, user, body.body)
    return _thread(db, caregiver, user)
