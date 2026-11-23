"""The child health record from the purple book: vaccines, vitamin A and deworming, birth
details, sick visits, the arm (MUAC) check, clinic reminders and the CHW's missed doses."""
import uuid
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

from app.core import push
from app.db.models import Child
from app.services import immunization
from app.services.growth import growth_flags
from app.services.notify import send_clinic_reminders
from conftest import (PASSWORD, add_child, confirm_email, email_for, login, make_user,
                      new_phone, register_caregiver)

TODAY = date.today()


def by_item(record: dict) -> dict:
    return {d["item"]: d for d in record["doses"]}


def test_the_schedule_and_ticking_a_dose(client):
    _, cg = register_caregiver(client)
    child = add_child(client, cg, 12)
    path = f"/children/{child['child_id']}/record"
    rec = client.get(path, headers=cg).json()
    doses = by_item(rec)
    for item in ("bcg", "opv0", "penta1", "pcv3", "rota3", "ipv1", "ipv2", "mr1", "mr2",
                 "vita_6", "deworm_12"):
        assert item in doses, item
    assert "malaria1" not in doses and "yf" not in doses  # county-only, off by default
    # Added today, so doses due before today are "not recorded", never "overdue"
    assert doses["bcg"]["status"] == "not_recorded"
    assert doses["mr2"]["status"] == "upcoming"
    assert rec["counts"]["vaccine"]["total"] == 18
    # Tick, untick, refuse a date in the future or an item not on the schedule
    given = (TODAY - timedelta(days=300)).isoformat()
    rec = client.put(path + "/bcg", headers=cg, json={"given_on": given}).json()
    assert by_item(rec)["bcg"]["status"] == "given" and by_item(rec)["bcg"]["given_on"] == given
    assert rec["counts"]["vaccine"]["given"] == 1
    future = (TODAY + timedelta(days=1)).isoformat()
    assert client.put(path + "/opv0", headers=cg, json={"given_on": future}).status_code == 422
    assert client.put(path + "/smallpox", headers=cg, json={"given_on": given}).status_code == 404
    rec = client.delete(path + "/bcg", headers=cg).json()
    assert by_item(rec)["bcg"]["given_on"] is None
    # County-only vaccines once switched on
    client.patch(f"/children/{child['child_id']}", headers=cg,
                 json={"extra_vaccines": ["malaria", "yellow_fever"]})
    doses = by_item(client.get(path, headers=cg).json())
    assert {"malaria1", "malaria4", "yf"} <= doses.keys()
    # Someone else's child
    _, other = register_caregiver(client)
    assert client.get(path, headers=other).status_code == 404


def test_status_rules():
    dob = date(2025, 1, 1)
    added = date(2025, 1, 1)
    due = immunization.add_months(dob, 9)
    assert immunization.status(due, None, due - timedelta(days=1), added) == "upcoming"
    assert immunization.status(due, None, due + timedelta(days=28), added) == "due"
    assert immunization.status(due, None, due + timedelta(days=29), added) == "overdue"
    assert immunization.status(due, "2025-10-02", due + timedelta(days=60), added) == "given"
    # Due before the child was added to Hatua: not called missed
    assert immunization.status(due, None, due + timedelta(days=60), due + timedelta(days=1)) \
        == "not_recorded"
    assert immunization.add_months(date(2025, 1, 31), 1) == date(2025, 2, 28)
    child = SimpleNamespace(date_of_birth=dob, extra_vaccines=[], care_given={"mr1": "2025-10-01"},
                            created_at=datetime(2025, 1, 2, tzinfo=timezone.utc))
    missed = {d["item"] for d in immunization.missed(child, today=date(2025, 12, 1))}
    assert "penta3" in missed and "mr1" not in missed and "mr2" not in missed


def test_birth_details_clinic_date_certificate_and_net(client):
    _, cg = register_caregiver(client)
    child = add_child(client, cg, 4)
    path = f"/children/{child['child_id']}"
    r = client.patch(path, headers=cg, json={
        "birth": {"weight_kg": 2.2, "gestation_weeks": 36, "place": "facility"},
        "birth_certificate": True, "bed_net": False,
        "next_clinic_on": (TODAY + timedelta(days=10)).isoformat()})
    assert r.status_code == 200, r.text
    c = r.json()
    assert c["birth"] == {"weight_kg": 2.2, "gestation_weeks": 36, "place": "facility"}
    assert "low_birth_weight" in c["care_factors"]  # under 2.5 kg
    assert c["birth_certificate"] is True and c["bed_net"] is False
    # Null clears; leaving a field out keeps it
    c = client.patch(path, headers=cg, json={"next_clinic_on": None, "bed_net": None}).json()
    assert c["next_clinic_on"] is None and c["bed_net"] is None and c["birth_certificate"] is True
    past = (TODAY - timedelta(days=1)).isoformat()
    assert client.patch(path, headers=cg, json={"next_clinic_on": past}).status_code == 422
    assert client.patch(path, headers=cg, json={"birth": {"weight_kg": 9}}).status_code == 422


def test_sick_visits(client):
    _, cg = register_caregiver(client)
    child = add_child(client, cg, 20)
    path = f"/children/{child['child_id']}/sick-visits"
    older = client.post(path, headers=cg, json={"visit_on": (TODAY - timedelta(days=40)).isoformat(),
                                                "illness": "Diarrhoea", "treatment": "ORS and zinc"})
    assert older.status_code == 201, older.text
    newer = client.post(path, headers=cg, json={"visit_on": TODAY.isoformat(), "illness": "Cough"})
    visits = newer.json()["sick_visits"]
    assert [v["illness"] for v in visits] == ["Cough", "Diarrhoea"]  # newest first
    assert visits[0]["treatment"] is None
    assert client.post(path, headers=cg, json={"visit_on": TODAY.isoformat(),
                                               "illness": ""}).status_code == 422
    gone = client.delete(f"{path}/{visits[0]['visit_id']}", headers=cg).json()["sick_visits"]
    assert [v["illness"] for v in gone] == ["Diarrhoea"]
    assert client.delete(f"{path}/nope", headers=cg).status_code == 404


def test_the_arm_measurement(client):
    dob = TODAY - timedelta(days=400)
    entry = lambda muac, days_ago=5: {"measured_on": (TODAY - timedelta(days=days_ago)).isoformat(),
                                      "muac_cm": muac}
    assert growth_flags(dob, "female", [entry(11.0)], TODAY) == ["growth_muac_severe"]
    assert growth_flags(dob, "female", [entry(12.0)], TODAY) == ["growth_muac_moderate"]
    assert growth_flags(dob, "female", [entry(13.0)], TODAY) == []
    assert growth_flags(dob, "female", [entry(11.0, days_ago=120)], TODAY) == []  # too old
    young = TODAY - timedelta(days=100)  # under 6 months: MUAC not used
    assert growth_flags(young, "female", [entry(11.0)], TODAY) == []
    _, cg = register_caregiver(client)
    child = add_child(client, cg, 13)
    r = client.post(f"/children/{child['child_id']}/growth", headers=cg, json=entry(12.8))
    assert r.status_code == 201 and r.json()["growth"][-1]["muac_cm"] == 12.8
    ref = client.get(f"/children/{child['child_id']}/growth-reference", headers=cg).json()
    weights = ref["weight_for_age"]
    assert len(weights) == 61 and weights[0]["month"] == 0 and weights[-1]["month"] == 60
    assert all(w["sd_m3"] < w["sd_m2"] < w["median"] < w["sd_p2"] for w in weights)
    assert ref["height_for_age"][60]["median"] > ref["height_for_age"][0]["median"]


def test_clinic_reminder_goes_once(client, db_session):
    push.outbox.clear()
    user, cg = register_caregiver(client)
    client.put("/auth/me/push-token", headers=cg, json={"token": "fcm-" + uuid.uuid4().hex * 2})
    child = add_child(client, cg, 8, name="Zawadi")
    tomorrow = TODAY + timedelta(days=1)
    client.patch(f"/children/{child['child_id']}", headers=cg,
                 json={"next_clinic_on": tomorrow.isoformat()})
    send_clinic_reminders(db_session, TODAY)
    mine = [p for p in push.outbox if str(p.user_id) == str(user["user_id"])]
    assert len(mine) == 1 and "Zawadi" in mine[0].body
    send_clinic_reminders(db_session, TODAY)
    assert len([p for p in push.outbox if str(p.user_id) == str(user["user_id"])]) == 1


def test_the_chw_sees_missed_doses(client, db_session):
    _, chw_phone = make_user(db_session, "chw", "Wanjiku")
    chw = login(client, chw_phone)
    phone = new_phone()
    client.post("/chw/caregivers", headers=chw,
                json={"full_name": "Achieng", "email": email_for(phone), "phone_number": phone,
                      "password": PASSWORD})
    confirm_email(client, email_for(phone))
    cg = login(client, phone)
    child = add_child(client, cg, 6, name="Baraka")
    assert client.get("/chw/missed-doses", headers=chw).json() == []  # added today
    # As if the child had been in Hatua since birth: the 6, 10 and 14 week doses are missed
    with db_session() as db:
        c = db.get(Child, uuid.UUID(child["child_id"]))
        c.created_at = datetime.combine(date.fromisoformat(child["date_of_birth"]),
                                        datetime.min.time(), timezone.utc)
        db.commit()
    rows = client.get("/chw/missed-doses", headers=chw).json()
    assert [r["child_name"] for r in rows] == ["Baraka"]
    missed = {d["item"] for d in rows[0]["doses"]}
    assert {"bcg", "penta1", "penta3"} <= missed
    # Ticked from the booklet: no longer missed
    record = f"/children/{child['child_id']}/record"
    for item in missed:
        client.put(f"{record}/{item}", headers=cg, json={"given_on": TODAY.isoformat()})
    assert client.get("/chw/missed-doses", headers=chw).json() == []
    assert client.get("/chw/missed-doses", headers=cg).status_code == 403
    # The administrator sees counts only
    _, admin_phone = make_user(db_session, "admin")
    s = client.get("/admin/summary", headers=login(client, admin_phone)).json()
    assert s["immunization"]["children"] >= 1
    assert set(s["immunization"]) == {"children", "up_to_date", "overdue", "not_started",
                                      "partly_recorded"}
