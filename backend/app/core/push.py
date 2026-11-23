"""Sends push notifications to people's phones through Firebase Cloud Messaging (FCM).

With FIREBASE_CREDENTIALS set (the path of a Firebase service account key), messages go
to FCM's HTTP v1 API. Without it nothing is sent: the notification is logged and kept in
`outbox`, so tests and development can read it, as with emails (app.core.mailer).

Notifications carry no health details: the lock screen of a shared phone shows them.
They say that something is waiting ("A check needs your review"), and the app shows the
details after sign-in.
"""
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache

from sqlalchemy import select

from app.core.config import settings

log = logging.getLogger("uvicorn.error")
SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
MAX_TOKENS = 5  # phones per person; the oldest token is dropped after that


@dataclass
class Pushed:
    user_id: uuid.UUID
    title: str
    body: str
    data: dict = field(default_factory=dict)


# Notifications not sent to FCM (development and tests). Newest last, capped.
outbox: list[Pushed] = []


def add_token(tokens: list, token: str) -> list:
    """The person's token list with this token added (or moved) to the end."""
    now = datetime.now(timezone.utc).isoformat()
    kept = [t for t in tokens if t.get("token") != token]
    return (kept + [{"token": token, "updated_at": now}])[-MAX_TOKENS:]


@lru_cache(maxsize=1)
def _session():
    from google.auth.transport.requests import AuthorizedSession
    from google.oauth2 import service_account

    creds = service_account.Credentials.from_service_account_file(
        settings.firebase_credentials, scopes=[SCOPE])
    with open(settings.firebase_credentials, encoding="utf-8") as f:
        project = json.load(f)["project_id"]
    return AuthorizedSession(creds), project


def _gone(response) -> bool:
    """FCM says this token no longer reaches a phone (app removed, token replaced)."""
    if response.status_code == 404:
        return True
    try:
        details = response.json()["error"].get("details", [])
    except (ValueError, KeyError, AttributeError):
        return False
    return any(d.get("errorCode") in ("UNREGISTERED", "INVALID_ARGUMENT") for d in details)


def send(user_id: uuid.UUID, tokens: list[str], title: str, body: str,
         data: dict | None = None) -> None:
    """Never raises: a notification problem must not break what the person was doing.
    Meant to run after the response (FastAPI BackgroundTasks)."""
    data = {k: str(v) for k, v in (data or {}).items()}
    if not settings.firebase_credentials:
        outbox.append(Pushed(user_id, title, body, data))
        del outbox[:-50]
        log.info("PUSH NOT SENT (FIREBASE_CREDENTIALS is empty). To %s (%d phone(s)): %s | %s",
                 user_id, len(tokens), title, body)
        return
    if not tokens:
        return
    try:
        session, project = _session()
    except Exception:  # bad or missing key file: log it, never break the request
        log.exception("push: could not load FIREBASE_CREDENTIALS")
        return
    url = f"https://fcm.googleapis.com/v1/projects/{project}/messages:send"
    gone = []
    for token in tokens:
        message = {"token": token, "notification": {"title": title, "body": body},
                   "data": data,
                   "android": {"priority": "high"}}
        try:
            r = session.post(url, json={"message": message}, timeout=10)
        except Exception:
            log.exception("push: could not reach FCM")
            continue
        if r.status_code == 200:
            continue
        if _gone(r):
            gone.append(token)
        else:
            log.warning("push: FCM answered %s: %s", r.status_code, r.text[:300])
    if gone:
        _forget(user_id, gone)


def _forget(user_id: uuid.UUID, gone: list[str]) -> None:
    from app.db.models import User
    from app.db.session import SessionLocal

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.user_id == user_id))
        if user is not None:
            user.push_tokens = [t for t in user.push_tokens if t.get("token") not in gone]
            db.commit()
