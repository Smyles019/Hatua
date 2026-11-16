"""The Hatua assistant for caregivers (app/services/assistant.py has the safety design).

    GET    /assistant   the caregiver's saved conversation, and whether the assistant is on
    POST   /assistant   ask; optional child_id (only that child's age goes to the AI)
    DELETE /assistant   clear the saved conversation
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_child, require
from app.core.config import settings
from app.db.models import AssistantMessage, User
from app.db.session import get_db
from app.services import assistant
from app.services.results import age_in_months

router = APIRouter()
caregiver_only = require("caregiver")


class AssistantIn(BaseModel):
    body: str = Field(min_length=1, max_length=1000)
    child_id: uuid.UUID | None = None


def _used_today(db: Session, user: User) -> int:
    return db.scalar(select(func.count()).select_from(AssistantMessage).where(
        AssistantMessage.caregiver_id == user.user_id, AssistantMessage.role == "user",
        AssistantMessage.created_at >= assistant.day_start())) or 0


def _state(db: Session, user: User) -> dict:
    rows = db.scalars(select(AssistantMessage)
                      .where(AssistantMessage.caregiver_id == user.user_id)
                      .order_by(AssistantMessage.created_at, AssistantMessage.role.desc())).all()
    return {
        "available": bool(settings.openai_api_key),
        "daily_limit": settings.assistant_daily_limit,
        "used_today": _used_today(db, user),
        "messages": [{"message_id": m.message_id, "role": m.role, "body": m.body,
                      "flagged": m.flagged, "child_id": m.child_id,
                      "created_at": m.created_at} for m in rows],
    }


@router.get("")
def conversation(user: User = Depends(caregiver_only), db: Session = Depends(get_db)):
    return _state(db, user)


@router.post("")
def ask(body: AssistantIn, user: User = Depends(caregiver_only), db: Session = Depends(get_db)):
    question = body.body.strip()
    if not question:
        raise HTTPException(422, "write a message first")
    child = get_child(body.child_id, user, db) if body.child_id else None
    if _used_today(db, user) >= settings.assistant_daily_limit:
        raise HTTPException(429, f"you have reached today's limit of "
                                 f"{settings.assistant_daily_limit} messages; try again "
                                 "tomorrow, or message your health worker")
    flagged = assistant.mentions_danger_sign(question)
    if flagged:
        # Fixed reply, no AI: works even when the assistant is switched off.
        reply = assistant.urgent_reply(user.language)
    else:
        history = [(m.role, m.body) for m in db.scalars(
            select(AssistantMessage).where(AssistantMessage.caregiver_id == user.user_id)
            .order_by(AssistantMessage.created_at.desc(), AssistantMessage.role)
            .limit(assistant.HISTORY)).all()][::-1]
        age = age_in_months(child.date_of_birth) if child else None
        try:
            reply = assistant.ask(history, question, user.language, age)
        except assistant.AssistantOff:
            raise HTTPException(503, "the assistant is not switched on yet")
        except assistant.AssistantFailed:
            raise HTTPException(502, "the assistant could not answer just now; please try again")
    child_id = child.child_id if child else None
    # Both rows get the same timestamp (one transaction); the queries above order a
    # question before its answer by role.
    db.add(AssistantMessage(caregiver_id=user.user_id, child_id=child_id, role="user",
                            body=question))
    db.add(AssistantMessage(caregiver_id=user.user_id, child_id=child_id, role="assistant",
                            body=reply, flagged=flagged))
    db.commit()
    return _state(db, user)


@router.delete("", status_code=204)
def clear(user: User = Depends(caregiver_only), db: Session = Depends(get_db)):
    db.execute(delete(AssistantMessage).where(AssistantMessage.caregiver_id == user.user_id))
    db.commit()
