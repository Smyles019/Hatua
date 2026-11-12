"""Registration and sign-in (#11).

People sign in with their email and a password, or with Google. Anyone can register,
and registering always makes a caregiver account, which has to confirm its email (a
link is sent) before the first sign-in. CHW and administrator accounts are created by
an administrator (/admin/users); the first administrator is created from the command
line (python -m app.cli create-admin).

The phone number is not a way to sign in. It is kept as a contact detail and is how a
CHW finds a caregiver to link.
"""
import html
from datetime import timedelta

import jwt
from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core import mailer
from app.core.config import settings
from app.core.google import GoogleTokenError, verify_google_token
from app.core.security import (create_access_token, create_link_token, hash_password,
                               link_still_matches, read_link_token, verify_password)
from app.db.models import User
from app.db.session import get_db
from app.schemas.users import (EmailOnly, GoogleSignIn, Login, PasswordChange, Preferences,
                               Register, Registered, Session as SessionOut, UserOut,
                               email_address)

router = APIRouter()

BAD_LOGIN = HTTPException(status.HTTP_401_UNAUTHORIZED, "wrong email or password")
VERIFY, RESET = "verify_email", "reset_password"


def session_for(user: User) -> dict:
    return {"access_token": create_access_token(user.user_id, user.role),
            "token_type": "bearer", "user": UserOut.model_validate(user)}


def add_user(db: Session, *, full_name, email, phone_number, password, role,
             linked_chw_id=None, email_verified=False) -> User:
    user = User(full_name=full_name, email=email, phone_number=phone_number,
                password_hash=hash_password(password), role=role,
                linked_chw_id=linked_chw_id, email_verified=email_verified)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        which = "email" if "uq_users_email" in str(e.orig) else "phone number"
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"an account with this {which} already exists")
    return user


_DUMMY_HASH = hash_password("not a real password")


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    # Hash even for an unknown email (or a Google-only account with no password), so
    # response time does not reveal which emails have accounts. Same message for unknown
    # email, wrong password and deactivated.
    stored = user.password_hash if user and user.password_hash else _DUMMY_HASH
    ok = verify_password(password, stored)
    if user is None or not user.password_hash or not ok or not user.is_active:
        raise BAD_LOGIN
    if not user.email_verified:
        # Only reached with the right password, so this tells nobody else anything.
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            {"needs_verification": True, "email": user.email})
    return user


def send_verification(user: User) -> None:
    token = create_link_token(user.user_id, VERIFY,
                              timedelta(hours=settings.verify_link_hours), user.email)
    mailer.send_verification(user.email, user.full_name,
                             f"{settings.public_base_url}/auth/verify?token={token}")


@router.post("/register", response_model=Registered, status_code=201)
def register(body: Register, db: Session = Depends(get_db)):
    """Creates the caregiver account and emails a confirmation link. There is no session
    until the link has been opened; then the person signs in."""
    user = add_user(db, full_name=body.full_name, email=body.email,
                    phone_number=body.phone_number, password=body.password, role="caregiver")
    send_verification(user)
    return {"email": user.email, "verification_sent": True}


@router.post("/verify/resend", status_code=204)
def resend_verification(body: EmailOnly, db: Session = Depends(get_db)):
    """Always 204, whether or not the email has an account waiting to be confirmed."""
    user = db.scalar(select(User).where(User.email == body.email))
    if user is not None and user.is_active and not user.email_verified:
        send_verification(user)


@router.post("/login", response_model=SessionOut)
def login(body: Login, db: Session = Depends(get_db)):
    return session_for(authenticate(db, body.email, body.password))


@router.post("/password/forgot", status_code=204)
def forgot_password(body: EmailOnly, db: Session = Depends(get_db)):
    """Emails a link to choose a new password. Always 204, so this cannot be used to
    find out which emails have accounts."""
    user = db.scalar(select(User).where(User.email == body.email))
    if user is not None and user.is_active:
        token = create_link_token(user.user_id, RESET,
                                  timedelta(minutes=settings.reset_link_minutes),
                                  user.password_hash)
        mailer.send_password_reset(
            user.email, user.full_name,
            f"{settings.public_base_url}/auth/password/reset?token={token}")


@router.post("/google", response_model=SessionOut)
def google_sign_in(body: GoogleSignIn, db: Session = Depends(get_db)):
    """Sign in with a Google ID token.

    Known Google account: signs in. Google email that already has a Hatua account: the
    two are joined and the person is signed in to that account (Google has verified the
    address, so they own it). New email: needs phone_number, then creates a caregiver
    account. Without it the answer is 428 with the name and email from Google, so the
    app can show its "Add your phone number" step and call again.

    A phone number that already has a Hatua account is refused rather than taken over:
    nothing here proves the person owns that number.
    """
    try:
        who = verify_google_token(body.id_token)
    except GoogleTokenError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e))
    deactivated = HTTPException(status.HTTP_401_UNAUTHORIZED, "this account is deactivated")

    user = db.scalar(select(User).where(User.google_id == who.google_id))
    if user is not None:
        if not user.is_active:
            raise deactivated
        return session_for(user)

    user = db.scalar(select(User).where(User.email == who.email))
    if user is not None:
        if not user.is_active:
            raise deactivated
        if user.google_id is not None:
            raise HTTPException(status.HTTP_409_CONFLICT,
                                "this email is already used by another Google account")
        if not user.email_verified:
            # Someone registered this address but never confirmed it, so the password
            # may not be the owner's. The owner (proved by Google) takes the account.
            user.password_hash = None
        user.google_id, user.email_verified = who.google_id, True
        db.commit()
        return session_for(user)

    if body.phone_number is None:
        raise HTTPException(status.HTTP_428_PRECONDITION_REQUIRED,
                            {"needs_phone": True, "full_name": who.name, "email": who.email})
    if db.scalar(select(User).where(User.phone_number == body.phone_number)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "this phone number already has an account; sign in with the "
                            "email and password of that account")

    user = User(full_name=who.name[:100], phone_number=body.phone_number, password_hash=None,
                email=who.email, email_verified=True, google_id=who.google_id,
                role="caregiver")
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "this account already exists")
    return session_for(user)


@router.get("/config")
def sign_in_config():
    """What a sign-in page needs to know: the Google client ID the website asks Google
    for tokens with (public, not a secret), or null when Google sign-in is off."""
    audiences = settings.google_audiences
    return {"google_client_id": audiences[0] if audiences else None}


@router.post("/token", include_in_schema=False)
def token(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Form-based sign-in for the Authorize button in /docs (username = email)."""
    try:
        email = email_address(form.username)
    except ValueError:
        raise BAD_LOGIN
    user = authenticate(db, email, form.password)
    return {"access_token": create_access_token(user.user_id, user.role), "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@router.patch("/me", response_model=UserOut)
def update_me(body: Preferences, user: User = Depends(current_user),
              db: Session = Depends(get_db)):
    """Save the person's app language, so it follows them to another device."""
    user.language = body.language
    db.commit()
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


# ---- Pages opened from the emailed links ----
#
# Plain HTML served by the API, so the links work in any browser on any phone without
# the app being installed. After either page the person goes back to the app.

def _page(title: str, body_html: str, status_code: int = 200) -> HTMLResponse:
    return HTMLResponse(status_code=status_code, content=f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} | Hatua</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&family=Nunito:wght@800&display=swap">
<style>
body{{margin:0;font-family:"Atkinson Hyperlegible",system-ui,sans-serif;background:#FBF7FA;color:#3A1F36}}
main{{max-width:26rem;margin:2.5rem auto;padding:2rem 1.5rem;background:#fff;border-radius:1.25rem;
box-shadow:0 2px 10px rgba(58,31,54,.08)}}
h1{{font-family:Nunito,system-ui,sans-serif;font-weight:800;font-size:1.7rem;color:#3A1F36;margin:0 0 .75rem}}
p{{font-size:1rem;line-height:1.5}}
label{{display:block;font-weight:700;margin:1rem 0 .3rem}}
input{{width:100%;box-sizing:border-box;padding:.8rem 1rem;font:inherit;color:#3A1F36;
border:2px solid #F1E6EF;border-radius:999px;background:#F1E6EF}}
input:focus{{background:#fff;border-color:#7B3F70;outline:none}}
button{{margin-top:1.25rem;width:100%;padding:.9rem;font:inherit;font-weight:700;
color:#fff;background:#3A1F36;border:0;border-radius:999px;cursor:pointer}}
button:hover{{background:#7B3F70}}
.err{{color:#A32020;font-weight:600}}
label.show{{display:flex;align-items:center;gap:.5rem;font-weight:400}}
label.show input{{width:auto}}
</style></head><body><main><h1>{html.escape(title)}</h1>{body_html}</main></body></html>""")


def _user_from_link(db: Session, token: str, purpose: str) -> tuple[User | None, str]:
    try:
        user_id, fingerprint = read_link_token(token, purpose)
    except jwt.InvalidTokenError:
        return None, ""
    user = db.get(User, user_id)
    return (user if user is not None and user.is_active else None), fingerprint


@router.get("/verify", response_class=HTMLResponse, include_in_schema=False)
def verify_email(token: str = "", db: Session = Depends(get_db)):
    user, fingerprint = _user_from_link(db, token, VERIFY)
    if user is None or not link_still_matches(fingerprint, user.email):
        return _page("This link does not work",
                     "<p>The link is old or incomplete. Open the Hatua app, sign in, and "
                     "ask for a new confirmation email.</p>", 400)
    if not user.email_verified:
        user.email_verified = True
        db.commit()
    return _page("Your email is confirmed",
                 "<p>Thank you. Go back to the Hatua app and sign in with your email and "
                 "password.</p>")


def _reset_form(token: str, error: str = "") -> str:
    err = f'<p class="err">{html.escape(error)}</p>' if error else ""
    return (f'{err}<form method="post" action="/auth/password/reset">'
            f'<input type="hidden" name="token" value="{html.escape(token)}">'
            '<label for="p1">New password</label>'
            '<input id="p1" name="new_password" type="password" minlength="6" '
            'maxlength="128" required autocomplete="new-password">'
            '<label for="p2">Repeat the new password</label>'
            '<input id="p2" name="repeat_password" type="password" minlength="6" '
            'maxlength="128" required autocomplete="new-password">'
            # Show password, as on every other password field in Hatua.
            '<label class="show"><input type="checkbox" onchange="for (const i of '
            'document.querySelectorAll(\'#p1,#p2\')) i.type = this.checked ? \'text\' : '
            '\'password\'"> Show the passwords</label>'
            '<button type="submit">Save new password</button></form>')


_BAD_RESET = ("This link does not work",
              "<p>The link is old or was already used. Open the Hatua app and choose "
              "\"Forgot password?\" to get a new one.</p>")


@router.get("/password/reset", response_class=HTMLResponse, include_in_schema=False)
def reset_password_page(token: str = "", db: Session = Depends(get_db)):
    user, fingerprint = _user_from_link(db, token, RESET)
    if user is None or not link_still_matches(fingerprint, user.password_hash):
        return _page(*_BAD_RESET, 400)
    return _page("Choose a new password", _reset_form(token))


@router.post("/password/reset", response_class=HTMLResponse, include_in_schema=False)
def reset_password(token: str = Form(""), new_password: str = Form(""),
                   repeat_password: str = Form(""), db: Session = Depends(get_db)):
    user, fingerprint = _user_from_link(db, token, RESET)
    if user is None or not link_still_matches(fingerprint, user.password_hash):
        return _page(*_BAD_RESET, 400)
    if not 6 <= len(new_password) <= 128:
        return _page("Choose a new password",
                     _reset_form(token, "Use at least 6 characters."), 400)
    if new_password != repeat_password:
        return _page("Choose a new password",
                     _reset_form(token, "The two passwords do not match."), 400)
    user.password_hash = hash_password(new_password)
    user.email_verified = True  # opening the emailed link proves they own the address
    db.commit()
    return _page("Your password is changed",
                 "<p>Go back to the Hatua app and sign in with your email and your new "
                 "password.</p>")
