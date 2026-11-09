"""Accounts, sign-in and the administrator's usage summary."""
import re
import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

Role = Literal["caregiver", "chw", "admin"]


def kenyan_phone(value: str) -> str:
    """Accept 07.., 01.., 2547.., +2547.. (spaces and dashes ignored); store as +254XXXXXXXXX."""
    digits = re.sub(r"[\s-]", "", value)
    m = re.fullmatch(r"(?:\+?254|0)([17]\d{8})", digits)
    if not m:
        raise ValueError("enter a Kenyan mobile number, for example 0712 345 678")
    return "+254" + m.group(1)


Phone = Annotated[str, AfterValidator(kenyan_phone)]
Password = Annotated[str, Field(min_length=6, max_length=128)]
Name = Annotated[str, Field(min_length=1, max_length=100)]


class Register(BaseModel):
    """Self-registration. Always creates a caregiver account."""
    full_name: Name
    phone_number: Phone
    password: Password


class Login(BaseModel):
    phone_number: Phone
    password: str


class GoogleSignIn(BaseModel):
    """id_token from Google Sign-In on the phone. phone_number is needed only the first
    time, to create the account: CHWs find and link caregivers by phone."""
    id_token: str = Field(min_length=20, max_length=4096)
    phone_number: Phone | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: uuid.UUID
    full_name: str
    phone_number: str
    role: Role
    linked_chw_id: uuid.UUID | None
    is_active: bool
    email: str | None = None


class Session(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserOut


class NewUser(BaseModel):
    """Account created by an administrator (any role) or a CHW (caregivers only)."""
    full_name: Name
    phone_number: Phone
    password: Password  # temporary password, handed to the person to change later
    role: Role = "caregiver"


class EnrolCaregiver(BaseModel):
    full_name: Name
    phone_number: Phone
    password: Password


class LinkByPhone(BaseModel):
    phone_number: Phone


class LinkChw(BaseModel):
    chw_id: uuid.UUID | None  # None removes the link


class UserUpdate(BaseModel):
    is_active: bool | None = None
    full_name: Name | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: Password


class UsageSummary(BaseModel):
    period: dict[str, date | None]
    users: dict[str, int]
    children: int
    assessments: int
    by_risk_level: dict[str, int]
    flagged_for_chw: int
    anomaly_flags: int
    outcomes: dict[str, int]
    awaiting_review: int
    generated_at: datetime
