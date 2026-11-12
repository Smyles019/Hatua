"""SQLAlchemy models for the five tables in Figure 4.6.

Allowed values are enforced by CHECK constraints so bad data is refused by the
database itself, not only by the API. Timestamps are timezone-aware and set by
PostgreSQL.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import (Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer,
                        MetaData, String, false, func, text, true)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

ROLES = ("caregiver", "chw", "admin")
SEXES = ("male", "female")
RISK_LEVELS = ("low", "medium", "high")
CHW_OUTCOMES = ("refer_to_facility", "reviewed_not_concerning", "unreachable")
AVATARS = ("lion", "elephant", "giraffe", "zebra", "hippo", "monkey", "cheetah", "rhino")
LANGUAGES = ("en", "sw")
# "Reasons for special care" borrowed from the MOH Mother and Child Health Handbook.
# Only the ones a caregiver can tick without sharing sensitive family details.
CARE_FACTORS = ("low_birth_weight", "multiple_birth", "short_birth_spacing")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class Base(DeclarativeBase):
    # Predictable constraint and index names, so migrations can find them again.
    metadata = MetaData(naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    })


def _uuid():
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _now():
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(_in("role", ROLES), name="role_valid"),
        CheckConstraint(_in("language", LANGUAGES), name="language_valid"),
        # every account has a way to sign in: a Hatua password, a Google account, or both
        CheckConstraint("password_hash IS NOT NULL OR google_id IS NOT NULL",
                        name="has_sign_in"),
    )

    user_id: Mapped[uuid.UUID] = _uuid()
    full_name: Mapped[str] = mapped_column(String(100))
    phone_number: Mapped[str] = mapped_column(String(15), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    # People sign in with their email (and a password, or Google). The phone number is
    # a contact detail and how CHWs find a caregiver to link. Nullable only for accounts
    # made before email sign-in; every new account has one.
    email: Mapped[str | None] = mapped_column(String(254), unique=True)
    # True once the person opened the emailed link, signed in with Google (Google has
    # verified the address), or the account was created by an administrator or CHW.
    email_verified: Mapped[bool] = mapped_column(Boolean, server_default=false(),
                                                 default=False)
    # Google sign-in. google_id is Google's stable "sub" claim.
    google_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    role: Mapped[str] = mapped_column(String(20))
    linked_chw_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"), index=True)
    # Deactivated accounts cannot sign in. Used instead of deleting, so recorded CHW
    # outcomes keep their reviewer (see PredictionResult.reviewed_by).
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=true(), default=True)
    # App language: English or Swahili. Saved on the account so it follows the person
    # from the phone to the web.
    language: Mapped[str] = mapped_column(String(2), server_default="en", default="en")
    created_at: Mapped[datetime] = _now()


class Child(Base):
    __tablename__ = "children"
    __table_args__ = (
        CheckConstraint(_in("sex", SEXES), name="sex_valid"),
        CheckConstraint(f"avatar_id IS NULL OR {_in('avatar_id', AVATARS)}",
                        name="avatar_valid"),
    )

    child_id: Mapped[uuid.UUID] = _uuid()
    caregiver_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), index=True)
    first_name: Mapped[str] = mapped_column(String(50))
    date_of_birth: Mapped[date] = mapped_column(Date)
    sex: Mapped[str] = mapped_column(String(10))
    location: Mapped[str] = mapped_column(String(100))
    # Animal avatar shown instead of a photo; the app never stores pictures of children.
    avatar_id: Mapped[str | None] = mapped_column(String(20))
    # Weight and height entries, oldest first: [{"measured_on", "weight_kg", "height_cm"}].
    # JSONB on the child keeps the five-table design.
    growth: Mapped[list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"),
                                         default=list)
    # Ticked reasons for special care (see CARE_FACTORS). Shown to the CHW; not used by
    # the model.
    care_factors: Mapped[list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"),
                                               default=list)
    created_at: Mapped[datetime] = _now()


class CaregiverInput(Base):
    __tablename__ = "caregiver_inputs"
    __table_args__ = (CheckConstraint("age_months BETWEEN 0 AND 59", name="age_months_valid"),)

    input_id: Mapped[uuid.UUID] = _uuid()
    child_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("children.child_id", ondelete="CASCADE"), index=True)
    age_months: Mapped[int] = mapped_column(Integer)
    age_band: Mapped[str] = mapped_column(String(10))
    responses: Mapped[dict] = mapped_column(JSONB)
    submitted_at: Mapped[datetime] = _now()


class PredictionResult(Base):
    __tablename__ = "prediction_results"
    __table_args__ = (
        CheckConstraint(_in("risk_level", RISK_LEVELS), name="risk_level_valid"),
        CheckConstraint(f"chw_outcome IS NULL OR {_in('chw_outcome', CHW_OUTCOMES)}",
                        name="chw_outcome_valid"),
        # an outcome is always recorded together with who reviewed it and when
        CheckConstraint("(chw_outcome IS NULL) = (reviewed_by IS NULL) "
                        "AND (chw_outcome IS NULL) = (reviewed_at IS NULL)",
                        name="review_fields_together"),
    )

    prediction_id: Mapped[uuid.UUID] = _uuid()
    input_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("caregiver_inputs.input_id", ondelete="CASCADE"), unique=True)
    risk_level: Mapped[str] = mapped_column(String(10))
    anomaly_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    shap_values: Mapped[dict] = mapped_column(JSONB)
    # Hearing and vision screening answers that need a look (ids from
    # app.services.questions.RED_FLAGS). A rule, not a prediction: any entry sends the
    # result to the CHW whatever the model said.
    red_flags: Mapped[list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"),
                                            default=list)
    model_version: Mapped[str] = mapped_column(String(20))
    chw_outcome: Mapped[str | None] = mapped_column(String(30))
    # RESTRICT: a CHW with recorded outcomes cannot be deleted, so every outcome keeps
    # its reviewer (audit trail). Deactivate such accounts instead of deleting them.
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.user_id", ondelete="RESTRICT"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _now()


class Message(Base):
    """Ask a CHW. One thread per caregiver: their questions and the replies of whichever
    CHW is linked to them. A question asked before a CHW is linked waits in the thread."""
    __tablename__ = "messages"

    message_id: Mapped[uuid.UUID] = _uuid()
    caregiver_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), index=True)
    sender_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"))
    # Set when the question was asked from a result screen, so the CHW sees which check.
    prediction_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("prediction_results.prediction_id", ondelete="SET NULL"))
    body: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = _now()


class MilestoneSummary(Base):
    __tablename__ = "milestone_summaries"

    summary_id: Mapped[uuid.UUID] = _uuid()
    child_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("children.child_id", ondelete="CASCADE"), unique=True)
    domain_status: Mapped[dict] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
