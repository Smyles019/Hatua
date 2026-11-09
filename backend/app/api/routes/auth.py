"""Registration and sign-in (#11).

Anyone can register, and registering always makes a caregiver account. CHW and
administrator accounts are created by an administrator (/admin/users); the first
administrator is created from the command line (python -m app.cli create-admin).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.google import GoogleTokenError, verify_google_token
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import User
from app.db.session import get_db
from app.schemas.users import (GoogleSignIn, Login, PasswordChange, Register,
                               Session as SessionOut, UserOut, kenyan_phone)

router = APIRouter()

BAD_LOGIN = HTTPException(status.HTTP_401_UNAUTHORIZED, "wrong phone number or password")


def session_for(user: User) -> dict:
    return {"access_token": create_access_token(user.user_id, user.role),
            "token_type": "bearer", "user": UserOut.model_validate(user)}


def add_user(db: Session, *, full_name, phone_number, password, role, linked_chw_id=None) -> User:
    user = User(full_name=full_name, phone_number=phone_number,
                password_hash=hash_password(password), role=role, linked_chw_id=linked_chw_id)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "an account with this phone number already exists")
    return user


_DUMMY_HASH = hash_password("not a real password")


def authenticate(db: Session, phone_number: str, password: str) -> User:
    user = db.scalar(select(User).where(User.phone_number == phone_number))
    # Hash even for an unknown number (or a Google-only account with no password), so
    # response time does not reveal which numbers have accounts. Same message for unknown
    # number, wrong password and deactivated.
    stored = user.password_hash if user and user.password_hash else _DUMMY_HASH
    ok = verify_password(password, stored)
    if user is None or not user.password_hash or not ok or not user.is_active:
        raise BAD_LOGIN
    return user


@router.post("/register", response_model=SessionOut, status_code=201)
def register(body: Register, db: Session = Depends(get_db)):
    user = add_user(db, full_name=body.full_name, phone_number=body.phone_number,
                    password=body.password, role="caregiver")
    return session_for(user)


@router.post("/login", response_model=SessionOut)
def login(body: Login, db: Session = Depends(get_db)):
    return session_for(authenticate(db, body.phone_number, body.password))


@router.post("/google", response_model=SessionOut)
def google_sign_in(body: GoogleSignIn, db: Session = Depends(get_db)):
    """Sign in with a Google ID token.

    Known Google account: signs in. New Google account: needs phone_number, then creates
    a caregiver account. Without it the answer is 428 with the name and email from Google,
    so the app can show its "Add your phone number" step and call again.

    A phone number that already has a Hatua account is refused rather than taken over:
    nothing here proves the person owns that number. They sign in with their password.
    """
    try:
        who = verify_google_token(body.id_token)
    except GoogleTokenError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e))

    user = db.scalar(select(User).where(User.google_id == who.google_id))
    if user is not None:
        if not user.is_active:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "this account is deactivated")
        return session_for(user)

    if db.scalar(select(User).where(User.email == who.email)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "this email is already used by another account")
    if body.phone_number is None:
        raise HTTPException(status.HTTP_428_PRECONDITION_REQUIRED,
                            {"needs_phone": True, "full_name": who.name, "email": who.email})
    if db.scalar(select(User).where(User.phone_number == body.phone_number)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "this phone number already has an account; sign in with your "
                            "phone number and password")

    user = User(full_name=who.name[:100], phone_number=body.phone_number, password_hash=None,
                email=who.email, google_id=who.google_id, role="caregiver")
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "this account already exists")
    return session_for(user)


@router.post("/token", include_in_schema=False)
def token(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Form-based sign-in for the Authorize button in /docs (username = phone number)."""
    try:
        phone = kenyan_phone(form.username)
    except (ValueError, ValidationError):
        raise BAD_LOGIN
    user = authenticate(db, phone, form.password)
    return {"access_token": create_access_token(user.user_id, user.role), "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@router.put("/password", status_code=204)
def change_password(body: PasswordChange, user: User = Depends(current_user),
                    db: Session = Depends(get_db)):
    if not user.password_hash:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "this account signs in with Google and has no password")
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "current password is wrong")
    user.password_hash = hash_password(body.new_password)
    db.commit()
