"""Development-only helpers for the test UI and scripts. Mounted only when DEV_MODE=true.

POST /dev/admin-session signs the test UI in as a fixed development administrator,
creating that account on first use. It exists so the throwaway test UI can set up
users and links without a manual admin login.

POST /dev/verify-email confirms an email without opening the emailed link, so scripts
(scripts/measure_latency.py) can register and sign in unattended.

Never enable DEV_MODE on a server that holds real data: these endpoints hand out an
administrator session and skip email confirmation for anyone.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.auth import session_for
from app.core.security import hash_password
from app.db.models import User
from app.db.session import get_db
from app.schemas.users import EmailOnly, Session as SessionOut

router = APIRouter()

DEV_ADMIN_PHONE = "+254700000000"
DEV_ADMIN_EMAIL = "dev-admin@hatua.test"
DEV_PASSWORD = "test123"  # the test UI gives every account it creates this password


@router.post("/admin-session", response_model=SessionOut)
def admin_session(db: Session = Depends(get_db)):
    admin = db.scalar(select(User).where(User.phone_number == DEV_ADMIN_PHONE))
    if admin is None:
        admin = User(full_name="Dev administrator", phone_number=DEV_ADMIN_PHONE,
                     email=DEV_ADMIN_EMAIL, email_verified=True,
                     password_hash=hash_password(DEV_PASSWORD), role="admin")
        db.add(admin)
        db.commit()
    return session_for(admin)


@router.post("/verify-email", status_code=204)
def verify_email(body: EmailOnly, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email))
    if user is None:
        raise HTTPException(404, "no account with this email")
    user.email_verified = True
    db.commit()
