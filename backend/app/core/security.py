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
    return uuid.UUID(claims["sub"])
