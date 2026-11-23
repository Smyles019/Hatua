"""The child health record from the MOH Mother and Child Health Handbook (the purple
book): vaccines, vitamin A and deworming, with the date each was given.

The schedule is the routine KEPI one printed in the handbook. It lives only here (the app
and website show what GET /children/{id}/record returns), so a schedule change is one
edit. Check it against the current MOH chart before release: Kenya adds vaccines (the
typhoid vaccine from 2025) and some are given only in some counties (malaria, yellow
fever), which a caregiver switches on for their child (Child.extra_vaccines).

Status of each dose on a day:
  given         a date is recorded
  upcoming      not due yet
  due           due, within the 4 weeks a clinic usually allows
  overdue       due more than 4 weeks ago, after the child was added to Hatua
  not_recorded  fell due before the child was added to Hatua and was never ticked: the
                caregiver may simply not have copied it from the booklet, so it is not
                called missed and does not reach the CHW
"""
from datetime import date, datetime, timedelta

from app.services.i18n import tr

GRACE_DAYS = 28

# (id, name, visit) by age in days for the weeks schedule, months for the rest.
_WEEKS = [
    (0, [("bcg", "BCG (tuberculosis)"), ("opv0", "Polio drops (OPV 0)")]),
    (42, [("opv1", "Polio drops (OPV 1)"), ("penta1", "Pentavalent 1"), ("pcv1", "Pneumococcal (PCV) 1"),
          ("rota1", "Rotavirus 1")]),
    (70, [("opv2", "Polio drops (OPV 2)"), ("penta2", "Pentavalent 2"), ("pcv2", "Pneumococcal (PCV) 2"),
          ("rota2", "Rotavirus 2")]),
    (98, [("opv3", "Polio drops (OPV 3)"), ("penta3", "Pentavalent 3"), ("pcv3", "Pneumococcal (PCV) 3"),
          ("rota3", "Rotavirus 3"), ("ipv1", "Polio injection (IPV 1)")]),
]
_MONTHS = [
    (9, [("mr1", "Measles-rubella 1"), ("ipv2", "Polio injection (IPV 2)")]),
    (18, [("mr2", "Measles-rubella 2")]),
]
# Only in some counties: shown when the caregiver switches them on.
EXTRA = {
    "malaria": [(6, "malaria1", "Malaria vaccine 1"), (7, "malaria2", "Malaria vaccine 2"),
                (9, "malaria3", "Malaria vaccine 3"), (24, "malaria4", "Malaria vaccine 4")],
    "yellow_fever": [(9, "yf", "Yellow fever")],
}
VITAMIN_A = [6, 12, 18, 24, 30, 36, 42, 48, 54, 59]
DEWORMING = [12, 18, 24, 30, 36, 42, 48, 54, 59]


def add_months(d: date, months: int) -> date:
    total = d.year * 12 + d.month - 1 + months
    y, m = divmod(total, 12)
    m += 1
    last = (date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)).day
    return date(y, m, min(d.day, last))


def _visit(days: int | None = None, months: int | None = None) -> str:
    if days is not None:
        return "At birth" if days == 0 else f"At {days // 7} weeks"
    return f"At {months} months"


def schedule(dob: date, extra: list[str] | None = None) -> list[dict]:
    """Every dose for a child, in due order: item, kind, name, visit, due_on."""
    out = []
    for days, doses in _WEEKS:
        for item, name in doses:
            out.append({"item": item, "kind": "vaccine", "name": name,
                        "visit": _visit(days=days), "due_on": dob + timedelta(days=days)})
    for months, doses in _MONTHS:
        for item, name in doses:
            out.append({"item": item, "kind": "vaccine", "name": name,
                        "visit": _visit(months=months), "due_on": add_months(dob, months)})
    for key in extra or []:
        for months, item, name in EXTRA.get(key, []):
            out.append({"item": item, "kind": "vaccine", "name": name, "optional": key,
                        "visit": _visit(months=months), "due_on": add_months(dob, months)})
    for m in VITAMIN_A:
        out.append({"item": f"vita_{m}", "kind": "vitamin_a", "name": "Vitamin A",
                    "visit": _visit(months=m), "due_on": add_months(dob, m)})
    for m in DEWORMING:
        out.append({"item": f"deworm_{m}", "kind": "deworming", "name": "Deworming",
                    "visit": _visit(months=m), "due_on": add_months(dob, m)})
    return sorted(out, key=lambda d: (d["due_on"], d["kind"] != "vaccine"))


def items(dob: date, extra: list[str] | None = None) -> set[str]:
    return {d["item"] for d in schedule(dob, extra)}


def status(due_on: date, given_on: str | None, today: date, added_on: date) -> str:
    if given_on:
        return "given"
    if due_on > today:
        return "upcoming"
    if today - due_on <= timedelta(days=GRACE_DAYS):
        return "due"
    return "overdue" if due_on >= added_on else "not_recorded"


def record(child, lang: str = "en", today: date | None = None) -> dict:
    """The child's whole record, each dose with its status, and counts for the graphs."""
    today = today or date.today()
    added = child.created_at.date() if isinstance(child.created_at, datetime) else today
    given = child.care_given or {}
    rows = []
    for d in schedule(child.date_of_birth, child.extra_vaccines):
        if d["due_on"] > add_months(child.date_of_birth, 60):
            continue
        st = status(d["due_on"], given.get(d["item"]), today, added)
        rows.append({**d, "name": tr(d["name"], lang), "visit": _visit_tr(d["visit"], lang),
                     "given_on": given.get(d["item"]), "status": st})
    counts = {}
    for kind in ("vaccine", "vitamin_a", "deworming"):
        mine = [r for r in rows if r["kind"] == kind]
        counts[kind] = {s: sum(r["status"] == s for r in mine)
                        for s in ("given", "due", "overdue", "upcoming", "not_recorded")}
        counts[kind]["total"] = len(mine)
    return {"child_id": child.child_id, "doses": rows, "counts": counts,
            "extra_vaccines": child.extra_vaccines or []}


def _visit_tr(visit: str, lang: str) -> str:
    """'At 6 weeks' -> the person's language, keeping the number."""
    if visit == "At birth":
        return tr("At birth", lang)
    n, unit = visit.split()[1:]
    return tr("At {n} " + unit, lang).replace("{n}", n)


def missed(child, today: date | None = None) -> list[dict]:
    """Vaccines overdue (see the module notes), for the CHW's missed-dose list."""
    today = today or date.today()
    added = child.created_at.date() if isinstance(child.created_at, datetime) else today
    given = child.care_given or {}
    return [{"item": d["item"], "name": d["name"], "due_on": d["due_on"],
             "days_overdue": (today - d["due_on"]).days}
            for d in schedule(child.date_of_birth, child.extra_vaccines)
            if d["kind"] == "vaccine"
            and status(d["due_on"], given.get(d["item"]), today, added) == "overdue"]
