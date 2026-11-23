"""The full check report for a CHW: every question the caregiver was asked and the answer
they gave, grouped by area, with the result, the hearing, eye and growth flags, and the
child's details. Shown on the CHW's screen and as a PDF (report_pdf.py).

Answers are shown as the caregiver chose them. "result" says how the answer counts:
  done       the child does this (counts as achieved)
  not_yet    the child does not do this yet (counts as not achieved)
  dont_know  the caregiver did not know (the model counts it as not achieved)
  concern    a hearing or eye question answered "No" (a red flag)
  ok         a hearing or eye question answered "Yes"
"""
from app.db.models import CaregiverInput, Child, PredictionResult, User
from app.services.i18n import tr
from app.services.questions import QUESTIONS, RED_FLAGS, YES_NO
from app.services.results import DOMAIN_LABELS, domain_label, to_out

DOMAIN_ORDER = list(DOMAIN_LABELS)
RISK_LABELS = {"low": "Low risk: on track", "medium": "Medium risk: keep an eye on the child",
               "high": "High risk: needs a check by a health worker"}
OUTCOME_LABELS = {"refer_to_facility": "Refer to facility",
                  "reviewed_not_concerning": "Reviewed, not concerning",
                  "unreachable": "Could not reach caregiver"}
CARE_FACTOR_LABELS = {"low_birth_weight": "Low birth weight",
                      "multiple_birth": "Twin or multiple birth",
                      "short_birth_spacing": "Born less than 2 years after a sibling"}


def domain_of(item: str) -> str:
    """The area a question belongs to (the same rule as the app's DomainStyle.domainOfItem)."""
    if item.startswith("who_"):
        return "motor"
    if item.startswith("ddi") and len(item) >= 5:
        return "language" if item[3:5] == "cm" else "motor"
    digits = "".join(ch for ch in item if ch.isdigit())
    n = int(digits) if digits else 0
    if 21 <= n <= 24:
        return "motor"
    if 25 <= n <= 29:
        return "language"
    if 30 <= n <= 35:
        return "cognitive"
    return "social_emotional"


def _option(options, answer: str):
    return next(((label, value) for key, label, value in options if key == answer),
                (answer, None))


def _model_answer(item: str, answer: str, coded, name: str, lang: str) -> dict:
    q = QUESTIONS.get(item)
    if q is None:  # a question no longer asked: keep the raw answer
        return {"item": item, "question": item, "answer": answer, "answer_label": answer,
                "result": "dont_know"}
    label, value = _option(q["options"], answer)
    value = coded if coded is not None or answer == "dont_know" else value
    result = "dont_know" if value is None else ("done" if value == 1 else "not_yet")
    return {"item": item, "question": tr(q["text"], lang).replace("{name}", name),
            "answer": answer, "answer_label": tr(label, lang), "result": result}


def build(pred: PredictionResult, inp: CaregiverInput, child: Child, caregiver: User,
          lang: str = "en") -> dict:
    out = to_out(pred, inp, child, lang)
    name = child.first_name
    answers = inp.responses.get("answers", {})
    coded = inp.responses.get("coded", {})
    status = {d["domain"]: d for d in out["domains"]}

    sections = []
    for domain in DOMAIN_ORDER:
        rows = [_model_answer(i, a, coded.get(i), name, lang)
                for i, a in answers.items() if domain_of(i) == domain]
        if rows:
            d = status.get(domain)
            sections.append({"domain": domain, "label": domain_label(domain, lang),
                             "status": d["status"] if d else "not_assessed", "answers": rows})

    screening = []
    for item, answer in inp.responses.get("screening", {}).items():
        if item not in RED_FLAGS:
            continue
        label, _ = _option(YES_NO, answer)
        screening.append({
            "item": item, "kind": RED_FLAGS[item][1],
            "question": tr(RED_FLAGS[item][0], lang).replace("{name}", name),
            "answer": answer, "answer_label": tr(label, lang),
            "result": {"no": "concern", "yes": "ok"}.get(answer, "dont_know")})

    counts = {k: sum(r["result"] == k for s in sections for r in s["answers"])
              for k in ("done", "not_yet", "dont_know")}
    return {
        **out,
        "risk_label": tr(RISK_LABELS[pred.risk_level], lang),
        "outcome_label": tr(OUTCOME_LABELS[pred.chw_outcome], lang) if pred.chw_outcome else None,
        "child": {"first_name": name, "sex": child.sex, "date_of_birth": child.date_of_birth,
                  "location": child.location,
                  "care_factors": [tr(CARE_FACTOR_LABELS.get(f, f), lang)
                                   for f in child.care_factors or []],
                  "latest_growth": (child.growth or [None])[-1]},
        "caregiver": {"full_name": caregiver.full_name, "phone_number": caregiver.phone_number},
        "counts": counts,
        "sections": sections,
        "screening": screening,
    }
