"""SQLAlchemy models for the five tables in Figure 4.6."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _uuid():
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class User(Base):
    __tablename__ = "users"
    user_id: Mapped[uuid.UUID] = _uuid()
    full_name: Mapped[str] = mapped_column(String(100))
    phone_number: Mapped[str] = mapped_column(String(15), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))  # caregiver / chw / admin
    linked_chw_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.user_id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Child(Base):
    __tablename__ = "children"
    child_id: Mapped[uuid.UUID] = _uuid()
    caregiver_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id"))
    first_name: Mapped[str] = mapped_column(String(50))
    date_of_birth: Mapped[datetime] = mapped_column(Date)
    sex: Mapped[str] = mapped_column(String(10))
    location: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CaregiverInput(Base):
    __tablename__ = "caregiver_inputs"
    input_id: Mapped[uuid.UUID] = _uuid()
    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("children.child_id"))
    age_months: Mapped[int] = mapped_column(Integer)
    age_band: Mapped[str] = mapped_column(String(10))
    responses: Mapped[dict] = mapped_column(JSONB)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PredictionResult(Base):
    __tablename__ = "prediction_results"
    prediction_id: Mapped[uuid.UUID] = _uuid()
    input_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("caregiver_inputs.input_id"), unique=True)
    risk_level: Mapped[str] = mapped_column(String(10))  # low / medium / high
    anomaly_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    shap_values: Mapped[dict] = mapped_column(JSONB)
    model_version: Mapped[str] = mapped_column(String(20))
    chw_outcome: Mapped[str | None] = mapped_column(String(30))
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.user_id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MilestoneSummary(Base):
    __tablename__ = "milestone_summaries"
    summary_id: Mapped[uuid.UUID] = _uuid()
    child_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("children.child_id"), unique=True)
    domain_status: Mapped[dict] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
