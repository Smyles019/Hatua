"""Password hashing (scrypt, standard library) and signed access tokens (JWT, HS256)."""
import hashlib
import hmac
import os
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    _, salt, digest = stored.split("$")
    check = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1)
    return hmac.compare_digest(check.hex(), digest)


def create_access_token(user_id: uuid.UUID, role: str) -> str:
    now = datetime.now(timezone.utc)
    claims = {"sub": str(user_id), "role": role, "iat": now,
              "exp": now + timedelta(hours=settings.access_token_hours)}
    return jwt.encode(claims, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> uuid.UUID:
    """Return the user id in a valid token. Raises jwt.InvalidTokenError otherwise."""
    claims = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM],
                        options={"require": ["sub", "exp"]})
    if "purpose" in claims:  # an emailed link token is not a session
        raise jwt.InvalidTokenError("not an access token")
    return uuid.UUID(claims["sub"])


# ---- Tokens inside emailed links (verify email, reset password) ----
#
# Signed like access tokens, with a "purpose" so one kind cannot be used as another.
# "fp" ties the link to the account as it was when the link was made: a reset link
# stops working once the password changes, so it can be used only once.

def _fingerprint(value: str | None) -> str:
    return hashlib.sha256((value or "").encode()).hexdigest()[:16]


def create_link_token(user_id: uuid.UUID, purpose: str, lifetime: timedelta,
                      bound_to: str | None = None) -> str:
    now = datetime.now(timezone.utc)
    claims = {"sub": str(user_id), "purpose": purpose, "iat": now, "exp": now + lifetime,
              "fp": _fingerprint(bound_to)}
    return jwt.encode(claims, settings.jwt_secret, algorithm=ALGORITHM)


def read_link_token(token: str, purpose: str) -> tuple[uuid.UUID, str]:
    """Return (user id, fingerprint). Raises jwt.InvalidTokenError if the token is not
    a valid, unexpired link token of this purpose."""
    claims = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM],
                        options={"require": ["sub", "exp", "purpose"]})
    if claims["purpose"] != purpose:
        raise jwt.InvalidTokenError("wrong kind of link")
    return uuid.UUID(claims["sub"]), claims.get("fp", "")


def link_still_matches(fingerprint: str, bound_to: str | None) -> bool:
    return hmac.compare_digest(fingerprint, _fingerprint(bound_to))
