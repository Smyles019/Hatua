"""Accounts, sign-in and the administrator's usage summary."""
import re
import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

Role = Literal["caregiver", "chw", "admin"]
Language = Literal["en", "sw"]


def kenyan_phone(value: str) -> str:
    """Accept 07.., 01.., 2547.., +2547.. (spaces and dashes ignored); store as +254XXXXXXXXX."""
    digits = re.sub(r"[\s-]", "", value)
    m = re.fullmatch(r"(?:\+?254|0)([17]\d{8})", digits)
    if not m:
        raise ValueError("enter a Kenyan mobile number, for example 0712 345 678")
    return "+254" + m.group(1)


def email_address(value: str) -> str:
    """One @, a dot in the domain, no spaces; stored in lower case."""
    v = value.strip().lower()
    if len(v) > 254 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s.]+", v):
        raise ValueError("enter an email address, for example amina@example.com")
    return v


Phone = Annotated[str, AfterValidator(kenyan_phone)]
Email = Annotated[str, AfterValidator(email_address)]
Password = Annotated[str, Field(min_length=6, max_length=128)]
Name = Annotated[str, Field(min_length=1, max_length=100)]


class Register(BaseModel):
    """Self-registration. Always creates a caregiver account. The email is how the
    person signs in; the phone number is how their CHW finds them."""
    full_name: Name
    email: Email
    phone_number: Phone
    password: Password


class Registered(BaseModel):
    """Answer to /auth/register: no session yet, the email has to be confirmed first."""
    email: str
    verification_sent: bool = True


class Login(BaseModel):
    email: Email
    password: str


class EmailOnly(BaseModel):
    email: Email


class GoogleSignIn(BaseModel):
    """id_token from Google Sign-In on the phone. phone_number is needed only the first
    time, to create the account: CHWs find and link caregivers by phone."""
    id_token: str = Field(min_length=20, max_length=4096)
    phone_number: Phone | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: uuid.UUID
    full_name: str
    phone_number: str | None  # empty only for a CHW invite still waiting (invite_pending)
    role: Role
    linked_chw_id: uuid.UUID | None
    is_active: bool
    email: str | None = None
    email_verified: bool = False
    language: Language = "en"
    invite_pending: bool = False


class PushToken(BaseModel):
    """A phone's Firebase Cloud Messaging registration token."""
    token: str = Field(min_length=20, max_length=4096)


class Preferences(BaseModel):
    """What a signed-in person may change about their own account."""
    language: Language


class Session(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserOut


class NewUser(BaseModel):
    """Account created by an administrator (any role) or a CHW (caregivers only)."""
    full_name: Name
    email: Email
    phone_number: Phone
    password: Password  # temporary password, handed to the person to change later
    role: Role = "caregiver"


class NewChw(BaseModel):
    """CHW added by an administrator: name and email only. The CHW gets an emailed link
    to choose a password and add their phone number, or signs in with Google using this
    email."""
    full_name: Name
    email: Email


class ChwOut(UserOut):
    """A CHW on the administrator's CHWs page."""
    invited_at: datetime | None = None
    created_at: datetime
    caregivers: int = 0  # active caregivers linked to this CHW


class EnrolCaregiver(BaseModel):
    full_name: Name
    email: Email
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
    red_flags: int = 0
    outcomes: dict[str, int]
    awaiting_review: int
    # Vaccine records of children under five (app.api.routes.admin._immunization).
    immunization: dict[str, int] = {}
    generated_at: datetime
