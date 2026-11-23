"""Children, assessments and CHW outcomes: request and response models."""
import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Sex = Literal["male", "female"]
# Same list as app.db.models.AVATARS and the app's assets/avatars.
Avatar = Literal["lion", "elephant", "giraffe", "zebra", "hippo", "monkey", "cheetah", "rhino"]
Outcome = Literal["refer_to_facility", "reviewed_not_concerning", "unreachable"]
# Same list as app.db.models.CARE_FACTORS.
CareFactor = Literal["low_birth_weight", "multiple_birth", "short_birth_spacing"]


class MessageIn(BaseModel):
    """A caregiver's question, or a CHW's reply. prediction_id is only used on a
    caregiver's question asked from a result screen."""
    body: str = Field(min_length=1, max_length=1000)
    prediction_id: uuid.UUID | None = None


class ChildCreate(BaseModel):
    # Required when a CHW or admin adds the child; ignored for a caregiver (always themselves).
    caregiver_id: uuid.UUID | None = None
    first_name: str = Field(min_length=1, max_length=50)
    date_of_birth: date
    sex: Sex
    location: str = Field(min_length=1, max_length=100)
    avatar_id: Avatar | None = None
    care_factors: list[CareFactor] = []


class GrowthEntry(BaseModel):
    """One weight, height and arm (MUAC) entry, usually copied from the clinic booklet."""
    measured_on: date
    weight_kg: float | None = Field(default=None, ge=1, le=35)
    height_cm: float | None = Field(default=None, ge=40, le=130)
    # Mid-upper arm circumference, from the coloured tape; used from 6 months.
    muac_cm: float | None = Field(default=None, ge=8, le=25)

    @model_validator(mode="after")
    def _one_measure(self):
        if self.weight_kg is None and self.height_cm is None and self.muac_cm is None:
            raise ValueError("give a weight, a height or an arm measurement")
        return self


BirthPlace = Literal["facility", "home", "on_the_way"]
ExtraVaccine = Literal["malaria", "yellow_fever"]


class BirthDetails(BaseModel):
    """From the birth page of the booklet. Any field may be left out."""
    weight_kg: float | None = Field(default=None, ge=0.4, le=6.5)
    gestation_weeks: int | None = Field(default=None, ge=22, le=44)
    place: BirthPlace | None = None


class ChildUpdate(BaseModel):
    """Only the fields that are sent are changed. For the yes/no fields and the clinic
    date, sending null clears them (see update_child)."""
    avatar_id: Avatar | None = None
    care_factors: list[CareFactor] | None = None
    birth: BirthDetails | None = None
    birth_certificate: bool | None = None
    bed_net: bool | None = None
    next_clinic_on: date | None = None
    extra_vaccines: list[ExtraVaccine] | None = None


class GivenIn(BaseModel):
    """A vaccine, vitamin A or deworming dose ticked as given."""
    given_on: date


class SickVisitIn(BaseModel):
    visit_on: date
    illness: str = Field(min_length=1, max_length=200)
    treatment: str | None = Field(default=None, max_length=300)


class ChildOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    child_id: uuid.UUID
    caregiver_id: uuid.UUID
    first_name: str
    date_of_birth: date
    sex: Sex
    location: str
    age_months: int
    avatar_id: Avatar | None = None
    growth: list[GrowthEntry] = []
    care_factors: list[CareFactor] = []
    birth: BirthDetails = BirthDetails()
    birth_certificate: bool | None = None
    bed_net: bool | None = None
    next_clinic_on: date | None = None
    extra_vaccines: list[ExtraVaccine] = []
    sick_visits: list[dict] = []


class AssessmentIn(BaseModel):
    child_id: uuid.UUID
    responses: dict[str, str]  # item -> answer value from GET /assessments/questions


class OutcomeIn(BaseModel):
    outcome: Outcome


class AssessmentOut(BaseModel):
    prediction_id: uuid.UUID
    child_id: uuid.UUID
    child_name: str
    child_avatar_id: Avatar | None = None
    age_months: int
    age_band: str
    method: Literal["model", "milestone_check"]
    risk_level: Literal["low", "medium", "high"]
    anomaly_flag: bool
    sent_to_chw: bool
    # Hearing and vision screening answers that need a look: [{flag, kind, kind_label, label}]
    red_flags: list[dict] = []
    domains: list[dict]
    top_reasons: list[dict]
    model: dict
    chw_outcome: Outcome | None
    caregiver_message: str | None
    reviewed_at: datetime | None
    submitted_at: datetime
