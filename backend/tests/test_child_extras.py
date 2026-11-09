"""Child avatar and growth entries (stored on the children table)."""
from datetime import date, timedelta

from conftest import add_child, register_caregiver


def test_new_child_has_no_avatar_and_no_growth(client):
    _, cg = register_caregiver(client)
    child = add_child(client, cg, 30)
    assert child["avatar_id"] is None and child["growth"] == []


def test_avatar_can_be_set_at_creation_and_changed(client):
    _, cg = register_caregiver(client)
    child = add_child(client, cg, 30, avatar_id="giraffe")
    assert child["avatar_id"] == "giraffe"
    r = client.patch(f"/children/{child['child_id']}", headers=cg, json={"avatar_id": "zebra"})
    assert r.status_code == 200 and r.json()["avatar_id"] == "zebra"
    assert client.get(f"/children/{child['child_id']}", headers=cg).json()["avatar_id"] == "zebra"


def test_unknown_avatar_is_refused(client):
    _, cg = register_caregiver(client)
    child = add_child(client, cg, 30)
    r = client.patch(f"/children/{child['child_id']}", headers=cg, json={"avatar_id": "dragon"})
    assert r.status_code == 422


def test_growth_entries_are_kept_in_date_order(client):
    _, cg = register_caregiver(client)
    child = add_child(client, cg, 30)
    url = f"/children/{child['child_id']}/growth"
    today = date.today()
    later = {"measured_on": today.isoformat(), "weight_kg": 12.1, "height_cm": 88}
    earlier = {"measured_on": (today - timedelta(days=60)).isoformat(), "weight_kg": 11.5}
    assert client.post(url, headers=cg, json=later).status_code == 201
    r = client.post(url, headers=cg, json=earlier)
    assert r.status_code == 201
    growth = r.json()["growth"]
    assert [g["measured_on"] for g in growth] == [earlier["measured_on"], later["measured_on"]]
    assert growth[0]["height_cm"] is None


def test_bad_growth_entries_are_refused(client):
    _, cg = register_caregiver(client)
    child = add_child(client, cg, 30)
    url = f"/children/{child['child_id']}/growth"
    today = date.today().isoformat()
    assert client.post(url, headers=cg, json={"measured_on": today}).status_code == 422
    assert client.post(url, headers=cg,
                       json={"measured_on": today, "weight_kg": 80}).status_code == 422
    future = (date.today() + timedelta(days=3)).isoformat()
    assert client.post(url, headers=cg,
                       json={"measured_on": future, "weight_kg": 10}).status_code == 422
    before_birth = "2015-01-01"
    assert client.post(url, headers=cg,
                       json={"measured_on": before_birth, "weight_kg": 10}).status_code == 422


def test_another_caregiver_cannot_edit_the_child(client):
    _, cg = register_caregiver(client)
    _, other = register_caregiver(client, "Otieno")
    child = add_child(client, cg, 30)
    r = client.patch(f"/children/{child['child_id']}", headers=other, json={"avatar_id": "lion"})
    assert r.status_code == 404
    r = client.post(f"/children/{child['child_id']}/growth", headers=other,
                    json={"measured_on": date.today().isoformat(), "weight_kg": 10})
    assert r.status_code == 404
