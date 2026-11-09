"""Development-only helpers for the test UI. Mounted only when DEV_MODE=true.

POST /dev/admin-session signs the test UI in as a fixed development administrator,
creating that account on first use. It exists so the throwaway test UI can set up
users and links without a manual admin login. Never enable DEV_MODE on a server that
holds real data: this endpoint hands out an administrator session to anyone.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.auth import session_for
from app.core.security import hash_password
from app.db.models import User
from app.db.session import get_db
from app.schemas.users import Session as SessionOut

router = APIRouter()

DEV_ADMIN_PHONE = "+254700000000"
DEV_PASSWORD = "test123"  # the test UI gives every account it creates this password


@router.post("/admin-session", response_model=SessionOut)
def admin_session(db: Session = Depends(get_db)):
    admin = db.scalar(select(User).where(User.phone_number == DEV_ADMIN_PHONE))
    if admin is None:
        admin = User(full_name="Dev administrator", phone_number=DEV_ADMIN_PHONE,
                     password_hash=hash_password(DEV_PASSWORD), role="admin")
        db.add(admin)
        db.commit()
    return session_for(admin)
