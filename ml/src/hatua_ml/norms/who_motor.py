"""Under-24-month milestone check from the WHO gross motor windows (#32).

The ECDI2030 model only covers 24 to 59 months. Below 24 months there is no
caregiver-reported, East African, item-level training data, so this part is a
rule-based check against published norms, not a learned model and not a risk
prediction.

Source: WHO Multicentre Growth Reference Study Group (2006). WHO Motor Development
Study: windows of achievement for six gross motor development milestones.
Acta Paediatrica, Suppl 450, 86-95. The windows run from the 1st to the 99th
percentile of the age at first achievement in healthy children from Ghana, India,
Norway, Oman and the USA.

Rules
- A milestone is asked once the child has reached the start of its window.
- A milestone is overdue when it is not achieved and the child is past the end of its
  window (the 99th percentile). "Don't know" is never counted as overdue.
- Hands-and-knees crawling is asked but never counted as overdue: some healthy children
  skip it (a small share of children in the WHO study never crawled).
- Risk: no overdue milestone = low, one = medium, two or more = high.
- Consistency flag (the rule-based counterpart of the anomaly flag): standing or walking
  alone reported as achieved while sitting without support is reported as not achieved.
"""
from dataclasses import dataclass

VERSION = "who-mgrs-2006"
MIN_AGE, MAX_AGE = 4, 23  # first window starts at 3.8 months; the model takes over at 24

# Bands used for under-24 assessments (the CREDI bands in the proposal's design).
AGE_BANDS = [(0, 5), (6, 11), (12, 17), (18, 23)]


@dataclass(frozen=True)
class Milestone:
    item: str
    window: tuple[float, float]  # 1st and 99th percentile, months
    can_be_overdue: bool = True


MILESTONES = [
    Milestone("who_sit", (3.8, 9.2)),            # sitting without support
    Milestone("who_stand_assist", (4.8, 11.4)),  # standing with assistance
    Milestone("who_crawl", (5.2, 13.5), can_be_overdue=False),  # hands-and-knees crawling
    Milestone("who_walk_assist", (5.9, 13.7)),   # walking with assistance
    Milestone("who_stand_alone", (6.9, 16.9)),   # standing alone
    Milestone("who_walk_alone", (8.2, 17.6)),    # walking alone
]
BY_ITEM = {m.item: m for m in MILESTONES}


class AgeNotCovered(ValueError):
    """The child is outside the 4 to 23 month range this check covers."""


def age_band(age_months: int) -> tuple[int, int]:
    for lo, hi in AGE_BANDS:
        if age_months <= hi:
            return lo, hi
    return AGE_BANDS[-1]


def items_for_age(age_months: int) -> list[str]:
    """Milestones whose window has started by this age, in WHO order."""
    if not MIN_AGE <= age_months <= MAX_AGE:
        raise AgeNotCovered(f"the motor milestone check covers {MIN_AGE} to {MAX_AGE} "
                            f"months; this child is {age_months} months")
    return [m.item for m in MILESTONES if age_months >= m.window[0]]


def assess(age_months: int, coded: dict[str, float | None]) -> dict:
    """coded: item -> 1 achieved / 0 not achieved / None don't know, for items_for_age(age)."""
    asked = items_for_age(age_months)
    missing = [i for i in asked if i not in coded]
    if missing:
        raise ValueError(f"answers missing for {missing}")

    overdue = []
    for item in asked:
        m = BY_ITEM[item]
        if m.can_be_overdue and coded[item] == 0 and age_months > m.window[1]:
            overdue.append({"item": item, "domain": "motor",
                            "months_past_window": round(age_months - m.window[1], 1)})
    overdue.sort(key=lambda r: r["months_past_window"], reverse=True)

    risk = "low" if not overdue else "medium" if len(overdue) == 1 else "high"
    alone = [coded.get("who_stand_alone"), coded.get("who_walk_alone")]
    inconsistent = coded.get("who_sit") == 0 and 1 in alone
    return {
        "risk_level": risk,
        "consistency_flag": bool(inconsistent),
        "overdue": overdue,
        "n_items": len(asked),
        "status": "needs_support" if overdue else "on_track",
        "model_version": VERSION,
    }
