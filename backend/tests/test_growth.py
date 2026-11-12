"""The growth check: WHO z-scores, and underweight or stunted children routed to the CHW."""
from datetime import date, timedelta

from conftest import add_child, answers, register_caregiver, submit

from app.services.growth import growth_flags, latest_z_scores, z_score


def test_z_score_is_zero_at_the_who_median():
    assert abs(z_score("weight_for_age", "male", 12, 9.6479)) < 0.001
    assert abs(z_score("height_for_age", "female", 36, 95.0515)) < 0.001
    assert abs(z_score("height_for_age", "male", 6, 67.6236)) < 0.001  # length under 24 months


def test_z_score_matches_the_who_minus_two_line():
    # WHO weight-for-age, girls, 24 months: -2 SD is 9.0 kg (simplified table).
    assert abs(z_score("weight_for_age", "female", 24, 9.0) + 2) < 0.05


def test_old_and_implausible_measurements_are_ignored():
    dob, today = date(2023, 1, 1), date(2025, 1, 1)
    old = [{"measured_on": str(today - timedelta(days=120)), "weight_kg": 7.0}]
    assert latest_z_scores(dob, "female", old, today) == {}
    typo = [{"measured_on": str(today), "weight_kg": 1.5}]  # far below any child of 2
    assert latest_z_scores(dob, "female", typo, today) == {}


def test_flags_below_minus_two():
    dob, today = date(2023, 1, 1), date(2025, 1, 1)
    low = [{"measured_on": str(today), "weight_kg": 8.5, "height_cm": 79.0}]
    assert growth_flags(dob, "female", low, today) == ["growth_underweight", "growth_stunted"]
    fine = [{"measured_on": str(today), "weight_kg": 11.5, "height_cm": 86.0}]
    assert growth_flags(dob, "female", fine, today) == []


def test_low_weight_sends_an_on_track_check_to_the_chw(client):
    _, headers = register_caregiver(client)
    child = add_child(client, headers, 30)
    cid = child["child_id"]
    r = client.post(f"/children/{cid}/growth", headers=headers,
                    json={"measured_on": str(date.today()), "weight_kg": 9.0})
    assert r.status_code == 201, r.text
    result = submit(client, headers, cid, answers(client, headers, cid, True))
    assert result["risk_level"] == "low"
    assert result["sent_to_chw"] is True
    flags = {f["flag"]: f for f in result["red_flags"]}
    assert flags["growth_underweight"]["kind"] == "growth"
    assert "growth_stunted" not in flags  # no height entered


def test_no_measurement_no_growth_flag(client):
    _, headers = register_caregiver(client)
    child = add_child(client, headers, 30)
    cid = child["child_id"]
    result = submit(client, headers, cid, answers(client, headers, cid, True))
    assert not [f for f in result["red_flags"] if f["kind"] == "growth"]
