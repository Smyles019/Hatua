"""Child profiles and a child's assessment history (#12).

caregiver  adds and sees their own children
chw        adds children for caregivers linked to them, sees those children
admin      sees all children, can add one for any caregiver
"""
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_child
from app.db.models import CaregiverInput, Child, MilestoneSummary, PredictionResult, User
from app.db.session import get_db
from app.schemas.assessment import (AssessmentOut, ChildCreate, ChildOut, ChildUpdate, GivenIn,
                                    GrowthEntry, SickVisitIn)
from app.services import immunization
from app.services.growth import reference_curves
from app.services.results import age_in_months, domain_label, to_out

router = APIRouter()


def child_out(c: Child) -> dict:
    return {**{k: getattr(c, k) for k in ("child_id", "caregiver_id", "first_name",
                                           "date_of_birth", "sex", "location", "avatar_id",
                                           "birth_certificate", "bed_net", "next_clinic_on")},
            "growth": c.growth or [], "care_factors": c.care_factors or [],
            "birth": c.birth or {}, "extra_vaccines": c.extra_vaccines or [],
            "sick_visits": c.sick_visits or [],
            "age_months": age_in_months(c.date_of_birth)}


def _caregiver_for(body: ChildCreate, user: User, db: Session) -> User:
    if user.role == "caregiver":
        return user
    if body.caregiver_id is None:
        raise HTTPException(422, "caregiver_id is required")
    caregiver = db.get(User, body.caregiver_id)
    if caregiver is None or caregiver.role != "caregiver" or not caregiver.is_active:
        raise HTTPException(404, "caregiver not found")
    if user.role == "chw" and caregiver.linked_chw_id != user.user_id:
        raise HTTPException(403, "this caregiver is not linked to you")
    return caregiver


@router.post("", response_model=ChildOut, status_code=201)
def create_child(body: ChildCreate, user: User = Depends(current_user),
                 db: Session = Depends(get_db)):
    caregiver = _caregiver_for(body, user, db)
    age = age_in_months(body.date_of_birth)
    if age < 0:
        raise HTTPException(422, "date of birth is in the future")
    if age > 59:
        raise HTTPException(422, "child must be under five (0 to 59 months)")
    child = Child(**body.model_dump(exclude={"caregiver_id", "care_factors"}),
                  care_factors=sorted(set(body.care_factors)), caregiver_id=caregiver.user_id)
    db.add(child)
    db.commit()
    return child_out(child)


@router.get("", response_model=list[ChildOut])
def list_children(caregiver_id: uuid.UUID | None = None, user: User = Depends(current_user),
                  db: Session = Depends(get_db)):
    q = select(Child).order_by(Child.created_at)
    if user.role == "caregiver":
        q = q.where(Child.caregiver_id == user.user_id)
    elif user.role == "chw":
        q = q.join(User, Child.caregiver_id == User.user_id).where(
            User.linked_chw_id == user.user_id)
    if caregiver_id:
        q = q.where(Child.caregiver_id == caregiver_id)
    return [child_out(c) for c in db.scalars(q)]


@router.get("/{child_id}", response_model=ChildOut)
def get_one(child_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return child_out(get_child(child_id, user, db))


@router.patch("/{child_id}", response_model=ChildOut)
def update_child(child_id: uuid.UUID, body: ChildUpdate, user: User = Depends(current_user),
                 db: Session = Depends(get_db)):
    """Change the avatar, the reasons for special care, or the purple-book details: birth,
    birth certificate, bed net, next clinic date, county-only vaccines."""
    # Anyone who may view the child may edit these: caregiver, linked CHW, admin.
    child = get_child(child_id, user, db)
    sent = body.model_fields_set
    if body.avatar_id is not None:
        child.avatar_id = body.avatar_id
    if body.care_factors is not None:
        child.care_factors = sorted(set(body.care_factors))
    if body.birth is not None:
        child.birth = body.birth.model_dump(exclude_none=True)
        # The booklet's birth weight answers the "low birth weight" reason for special
        # care (under 2.5 kg, the WHO definition).
        w = body.birth.weight_kg
        if w is not None and w < 2.5 and "low_birth_weight" not in (child.care_factors or []):
            child.care_factors = sorted({*(child.care_factors or []), "low_birth_weight"})
    # Sent as null: cleared (back to "not answered").
    for field in ("birth_certificate", "bed_net"):
        if field in sent:
            setattr(child, field, getattr(body, field))
    if "next_clinic_on" in sent:
        if body.next_clinic_on and body.next_clinic_on < date.today():
            raise HTTPException(422, "the next clinic date is in the past")
        child.next_clinic_on = body.next_clinic_on
    if body.extra_vaccines is not None:
        child.extra_vaccines = sorted(set(body.extra_vaccines))
    db.commit()
    return child_out(child)


# ---- The child health record from the purple book ----

@router.get("/{child_id}/growth-reference")
def growth_reference(child_id: uuid.UUID, user: User = Depends(current_user),
                     db: Session = Depends(get_db)):
    """The WHO zones for this child's growth charts (app.services.growth.reference_curves)."""
    return reference_curves(get_child(child_id, user, db).sex)


@router.get("/{child_id}/record")
def health_record(child_id: uuid.UUID, user: User = Depends(current_user),
                  db: Session = Depends(get_db)):
    """Vaccines, vitamin A and deworming, each with its due date, the date given and a
    status, plus counts for the graphs (app.services.immunization)."""
    return immunization.record(get_child(child_id, user, db), user.language)


@router.put("/{child_id}/record/{item}")
def mark_given(child_id: uuid.UUID, item: str, body: GivenIn,
               user: User = Depends(current_user), db: Session = Depends(get_db)):
    child = get_child(child_id, user, db)
    if item not in immunization.items(child.date_of_birth, child.extra_vaccines):
        raise HTTPException(404, "not on this child's schedule")
    if body.given_on > date.today():
        raise HTTPException(422, "the date given is in the future")
    if body.given_on < child.date_of_birth:
        raise HTTPException(422, "the date given is before the date of birth")
    child.care_given = {**(child.care_given or {}), item: body.given_on.isoformat()}
    db.commit()
    return immunization.record(child, user.language)


@router.delete("/{child_id}/record/{item}")
def unmark_given(child_id: uuid.UUID, item: str, user: User = Depends(current_user),
                 db: Session = Depends(get_db)):
    """Untick a dose ticked by mistake."""
    child = get_child(child_id, user, db)
    child.care_given = {k: v for k, v in (child.care_given or {}).items() if k != item}
    db.commit()
    return immunization.record(child, user.language)


@router.post("/{child_id}/sick-visits", response_model=ChildOut, status_code=201)
def add_sick_visit(child_id: uuid.UUID, body: SickVisitIn, user: User = Depends(current_user),
                   db: Session = Depends(get_db)):
    """The caregiver's note of a sick visit: when, what the illness was, what was given.
    Newest first."""
    child = get_child(child_id, user, db)
    if body.visit_on > date.today() or body.visit_on < child.date_of_birth:
        raise HTTPException(422, "the visit date must be between the birth and today")
    visit = {"visit_id": uuid.uuid4().hex, "visit_on": body.visit_on.isoformat(),
             "illness": body.illness.strip(), "treatment": (body.treatment or "").strip() or None}
    child.sick_visits = sorted([*(child.sick_visits or []), visit],
                               key=lambda v: v["visit_on"], reverse=True)
    db.commit()
    return child_out(child)


@router.delete("/{child_id}/sick-visits/{visit_id}", response_model=ChildOut)
def delete_sick_visit(child_id: uuid.UUID, visit_id: str, user: User = Depends(current_user),
                      db: Session = Depends(get_db)):
    child = get_child(child_id, user, db)
    kept = [v for v in child.sick_visits or [] if v.get("visit_id") != visit_id]
    if len(kept) == len(child.sick_visits or []):
        raise HTTPException(404, "visit not found")
    child.sick_visits = kept
    db.commit()
    return child_out(child)


@router.post("/{child_id}/growth", response_model=ChildOut, status_code=201)
def add_growth(child_id: uuid.UUID, body: GrowthEntry, user: User = Depends(current_user),
               db: Session = Depends(get_db)):
    """Add a weight and height entry. Entries stay sorted by date, oldest first."""
    # Anyone who may view the child may edit these: caregiver, linked CHW, admin.
    child = get_child(child_id, user, db)
    if body.measured_on > date.today():
        raise HTTPException(422, "measurement date is in the future")
    if body.measured_on < child.date_of_birth:
        raise HTTPException(422, "measurement date is before the date of birth")
    entries = [*(child.growth or []), body.model_dump(mode="json")]
    # A new list, so SQLAlchemy sees the JSONB change.
    child.growth = sorted(entries, key=lambda e: e["measured_on"])
    db.commit()
    return child_out(child)


@router.get("/{child_id}/assessments", response_model=list[AssessmentOut])
def child_history(child_id: uuid.UUID, user: User = Depends(current_user),
                  db: Session = Depends(get_db)):
    child = get_child(child_id, user, db)
    rows = db.execute(select(PredictionResult, CaregiverInput)
                      .join(CaregiverInput, PredictionResult.input_id == CaregiverInput.input_id)
                      .where(CaregiverInput.child_id == child.child_id)
                      .order_by(CaregiverInput.submitted_at.desc())).all()
    return [to_out(p, i, child, user.language) for p, i in rows]


@router.get("/{child_id}/milestones")
def milestones(child_id: uuid.UUID, user: User = Depends(current_user),
               db: Session = Depends(get_db)):
    """Latest status per domain, and the trajectory of risk levels over past assessments."""
    child = get_child(child_id, user, db)
    s = db.scalar(select(MilestoneSummary).where(MilestoneSummary.child_id == child.child_id))
    if s is None:
        raise HTTPException(404, "no assessments yet")
    history = db.execute(select(CaregiverInput.submitted_at, CaregiverInput.age_months,
                                PredictionResult.risk_level)
                         .join(PredictionResult, PredictionResult.input_id == CaregiverInput.input_id)
                         .where(CaregiverInput.child_id == child.child_id)
                         .order_by(CaregiverInput.submitted_at)).all()
    return {"child_id": child.child_id,
            "domains": [{"domain": d, "label": domain_label(d, user.language), "status": st}
                        for d, st in s.domain_status.items()],
            "domain_status": s.domain_status, "updated_at": s.updated_at,
            "history": [{"submitted_at": t, "age_months": a, "risk_level": r}
                        for t, a, r in history]}
