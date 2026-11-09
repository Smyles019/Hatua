"""SQLAlchemy models for the five tables in Figure 4.6.

Allowed values are enforced by CHECK constraints so bad data is refused by the
database itself, not only by the API. Timestamps are timezone-aware and set by
PostgreSQL.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import (Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer,
                        MetaData, String, func, text, true)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

ROLES = ("caregiver", "chw", "admin")
SEXES = ("male", "female")
RISK_LEVELS = ("low", "medium", "high")
CHW_OUTCOMES = ("refer_to_facility", "reviewed_not_concerning", "unreachable")
AVATARS = ("lion", "elephant", "giraffe", "zebra", "hippo", "monkey", "cheetah", "rhino")


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
        # every account has a way to sign in: a Hatua password, a Google account, or both
        CheckConstraint("password_hash IS NOT NULL OR google_id IS NOT NULL",
                        name="has_sign_in"),
    )

    user_id: Mapped[uuid.UUID] = _uuid()
    full_name: Mapped[str] = mapped_column(String(100))
    phone_number: Mapped[str] = mapped_column(String(15), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    # Google sign-in (caregivers only). google_id is Google's stable "sub" claim.
    email: Mapped[str | None] = mapped_column(String(254), unique=True)
    google_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    role: Mapped[str] = mapped_column(String(20))
    linked_chw_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"), index=True)
    # Deactivated accounts cannot sign in. Used instead of deleting, so recorded CHW
    # outcomes keep their reviewer (see PredictionResult.reviewed_by).
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=true(), default=True)
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
    model_version: Mapped[str] = mapped_column(String(20))
    chw_outcome: Mapped[str | None] = mapped_column(String(30))
    # RESTRICT: a CHW with recorded outcomes cannot be deleted, so every outcome keeps
    # its reviewer (audit trail). Deactivate such accounts instead of deleting them.
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.user_id", ondelete="RESTRICT"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _now()


class MilestoneSummary(Base):
    __tablename__ = "milestone_summaries"

    summary_id: Mapped[uuid.UUID] = _uuid()
    child_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("children.child_id", ondelete="CASCADE"), unique=True)
    domain_status: Mapped[dict] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
