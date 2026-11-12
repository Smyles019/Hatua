"""The growth check: weight-for-age and height-for-age against the WHO Child Growth
Standards (2006), from the weight and height a caregiver copies from the clinic booklet.

It is a rule, like the hearing and vision red flags, and not a model input: the
experiment in ml/scripts/growth_features_experiment.py found that adding the z-scores to
the risk model changed nothing. A z-score below -2 is the WHO cut-off for underweight
(weight-for-age) or stunted (height-for-age); it sends the result to the CHW whatever the
model said.

z-scores use the LMS method, z = ((x/M)**L - 1) / (L*S), with L, M and S interpolated
between the monthly WHO tables (app/data/who_growth.json). Weight-for-age beyond +-3 uses
WHO's restricted adjustment. Length-for-age is used under 24 months, height-for-age from
24 months. Values outside the WHO plausibility limits are taken as entry mistakes and
ignored.
"""
import json
import math
from datetime import date
from functools import lru_cache
from pathlib import Path

TABLES = Path(__file__).resolve().parents[1] / "data" / "who_growth.json"
DAYS_PER_MONTH = 30.4375
RECENT_DAYS = 90        # a measurement counts for a check if taken within this many days
CUTOFF = -2.0           # WHO: below -2 SD is underweight / stunted
PLAUSIBLE = {"weight_for_age": (-6.0, 5.0), "height_for_age": (-6.0, 6.0)}

# Flag ids stored in prediction_results.red_flags, with what the CHW reads.
GROWTH_FLAGS = {
    "growth_underweight": "Weight is low for age (below -2 SD, WHO standard)",
    "growth_stunted": "Height is low for age (below -2 SD, WHO standard)",
}


@lru_cache(maxsize=1)
def _tables() -> dict:
    return json.loads(TABLES.read_text(encoding="utf-8"))


def _lms(table: str, sex: str, months: float) -> tuple[float, float, float]:
    rows = _tables()[table][sex]
    m = min(max(months, rows[0][0]), rows[-1][0])
    for a, b in zip(rows, rows[1:]):
        if m <= b[0]:
            f = (m - a[0]) / (b[0] - a[0])
            return tuple(a[i] + (b[i] - a[i]) * f for i in (1, 2, 3))
    return tuple(rows[-1][1:])


def _value_at(L: float, M: float, S: float, z: float) -> float:
    return M * (1 + L * S * z) ** (1 / L)


def z_score(indicator: str, sex: str, age_months: float, value: float) -> float:
    """indicator: "weight_for_age" (kg) or "height_for_age" (cm; length under 24 months)."""
    table = indicator
    if indicator == "height_for_age" and age_months < 24:
        table = "length_for_age"
    L, M, S = _lms(table, sex, age_months)
    z = math.log(value / M) / S if abs(L) < 1e-9 else ((value / M) ** L - 1) / (L * S)
    if indicator == "weight_for_age" and abs(z) > 3:
        # WHO restricted adjustment: past +-3, distance in units of the 2-to-3 SD gap.
        sd3, sd2 = _value_at(L, M, S, 3 if z > 0 else -3), _value_at(L, M, S, 2 if z > 0 else -2)
        z = (3 + (value - sd3) / (sd3 - sd2)) if z > 0 else (-3 + (value - sd3) / (sd2 - sd3))
    return z


def age_in_months_on(dob: date, day: date) -> float:
    return (day - dob).days / DAYS_PER_MONTH


def latest_z_scores(dob: date, sex: str, growth: list[dict], on: date) -> dict:
    """z-scores from the most recent weight and height measured within RECENT_DAYS before
    `on` (each taken separately). Missing, too old or implausible values are left out."""
    out = {}
    for indicator, field in (("weight_for_age", "weight_kg"), ("height_for_age", "height_cm")):
        entries = [g for g in growth or [] if g.get(field)
                   and 0 <= (on - date.fromisoformat(str(g["measured_on"]))).days <= RECENT_DAYS]
        if not entries:
            continue
        g = max(entries, key=lambda e: str(e["measured_on"]))
        measured = date.fromisoformat(str(g["measured_on"]))
        months = age_in_months_on(dob, measured)
        if not 0 <= months <= 60:
            continue
        z = z_score(indicator, sex, months, float(g[field]))
        lo, hi = PLAUSIBLE[indicator]
        if lo <= z <= hi:
            out[indicator] = {"z": round(z, 2), "measured_on": str(measured), "value": g[field]}
    return out


def growth_flags(dob: date, sex: str, growth: list[dict], on: date) -> list[str]:
    """Flag ids for a check on `on`: underweight and/or stunted by the WHO cut-off."""
    z = latest_z_scores(dob, sex, growth, on)
    flags = []
    if "weight_for_age" in z and z["weight_for_age"]["z"] < CUTOFF:
        flags.append("growth_underweight")
    if "height_for_age" in z and z["height_for_age"]["z"] < CUTOFF:
        flags.append("growth_stunted")
    return flags
