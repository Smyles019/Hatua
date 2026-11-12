"""Who is calling, and what they may see.

Every route except /health, /auth/register, /auth/login and /auth/token needs a bearer
token. Access rules (the role decides, the token proves the identity):

    caregiver  their own children, and assessments for them
    chw        children of caregivers linked to them, read only, plus outcomes
    admin      everything, read only for children and results
"""
import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.models import Child, User
from app.db.session import get_db

oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)

UNAUTHORISED = HTTPException(status.HTTP_401_UNAUTHORIZED, "not signed in or session expired",
                             headers={"WWW-Authenticate": "Bearer"})


def current_user(token: str | None = Depends(oauth2), db: Session = Depends(get_db)) -> User:
    if not token:
        raise UNAUTHORISED
    try:
        user_id = decode_access_token(token)
    except (jwt.InvalidTokenError, ValueError):
        raise UNAUTHORISED
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise UNAUTHORISED
    return user


def require(*roles: str):
    """Dependency that lets only the given roles through."""
    def check(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN,
                                f"this action is for {' or '.join(roles)} accounts")
        return user
    return check


def can_view_child(user: User, child: Child, db: Session) -> bool:
    if user.role == "admin":
        return True
    if user.role == "caregiver":
        return child.caregiver_id == user.user_id
    caregiver = db.get(User, child.caregiver_id)
    return caregiver is not None and caregiver.linked_chw_id == user.user_id


def get_child(child_id: uuid.UUID, user: User, db: Session) -> Child:
    """The child, if this user may see it. 404 either way, so ids cannot be probed."""
    child = db.get(Child, child_id)
    if child is None or not can_view_child(user, child, db):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "child not found")
    return child
