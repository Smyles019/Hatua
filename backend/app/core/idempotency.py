"""Safe resending for the phone's offline queue.

The phone keeps changes made without signal (a check, a message, a growth entry, a CHW
outcome) and sends them when it is back online, each with an Idempotency-Key header: a
random key made on the phone. On a bad connection the change can reach the server while
the answer is lost, so the phone sends it again. The first successful answer is saved
under the key, and a repeat gets that saved answer back without running the change again.

Only POST, PUT and PATCH with the header are handled; everything else passes straight
through. Keys are kept for KEEP_DAYS (prune, run by the daily task).
"""
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.db.models import IdempotentRequest
from app.db.session import get_db

HEADER = "Idempotency-Key"
VALID = re.compile(r"^[A-Za-z0-9-]{16,64}$")
KEEP_DAYS = 30


def _with_db(app, work):
    """Runs work(db) with the app's database session (the tests' one under test)."""
    gen = app.dependency_overrides.get(get_db, get_db)()
    db = next(gen)
    try:
        return work(db)
    finally:
        gen.close()


def _find(db, key: str):
    row = db.get(IdempotentRequest, key)
    return None if row is None else (row.path, row.status_code, row.body)


def _save(db, key: str, path: str, status: int, body: str) -> None:
    db.add(IdempotentRequest(key=key, path=path, status_code=status, body=body))
    try:
        db.commit()
    except IntegrityError:  # the same key finished twice at once: the first one stands
        db.rollback()


def prune(session_factory, now: datetime | None = None) -> int:
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=KEEP_DAYS)
    with session_factory() as db:
        n = db.execute(delete(IdempotentRequest)
                       .where(IdempotentRequest.created_at < cutoff)).rowcount
        db.commit()
    return n


class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        key = request.headers.get(HEADER)
        if key is None or request.method not in ("POST", "PUT", "PATCH"):
            return await call_next(request)
        if not VALID.match(key):
            return Response('{"detail":"Idempotency-Key must be 16 to 64 letters, digits '
                            'or dashes"}', status_code=422, media_type="application/json")
        path = request.url.path
        saved = await run_in_threadpool(_with_db, request.app, lambda db: _find(db, key))
        if saved is not None:
            saved_path, status, body = saved
            if saved_path != path:
                return Response('{"detail":"this Idempotency-Key was used for another '
                                'request"}', status_code=422, media_type="application/json")
            return Response(body, status_code=status, media_type="application/json",
                            headers={"Idempotent-Replay": "true"})

        response = await call_next(request)
        if not 200 <= response.status_code < 300:
            return response  # failures are not saved: the phone may try again
        body = b"".join([chunk async for chunk in response.body_iterator])
        await run_in_threadpool(
            _with_db, request.app,
            lambda db: _save(db, key, path, response.status_code, body.decode("utf-8")))
        return Response(body, status_code=response.status_code,
                        headers={k: v for k, v in response.headers.items()
                                 if k.lower() != "content-length"},
                        media_type=response.media_type)
