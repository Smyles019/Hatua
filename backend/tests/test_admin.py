"""Administrator endpoints and the usage summary (#17)."""
from datetime import date, timedelta

import pytest

from conftest import (PASSWORD, add_child, answers, confirm_email, email_for, login, make_user, new_phone,
                      register_caregiver, submit)


@pytest.fixture(scope="module")
def admin(client, db_session):
    _, phone = make_user(db_session, "admin")
    return login(client, phone)


def test_admin_creates_a_chw_who_can_sign_in(client, admin):
    phone = new_phone()
    r = client.post("/admin/users", headers=admin,
                    json={"full_name": "Otieno", "email": email_for(phone),
                          "phone_number": phone, "password": PASSWORD,
                          "role": "chw"})
    assert r.status_code == 201 and r.json()["role"] == "chw"
    assert client.get("/auth/me", headers=login(client, phone)).json()["role"] == "chw"
    roles = {u["role"] for u in client.get("/admin/users", params={"role": "chw"},
                                           headers=admin).json()}
    assert roles == {"chw"}
    assert client.get("/admin/users", params={"role": "boss"}, headers=admin).status_code == 422


def test_admin_links_and_moves_a_caregiver(client, admin, db_session):
    cg, _ = register_caregiver(client)
    chw1, _ = make_user(db_session, "chw")
    chw2, _ = make_user(db_session, "chw")
    url = f"/admin/users/{cg['user_id']}/chw"
    assert client.put(url, headers=admin, json={"chw_id": str(chw1.user_id)}).json()[
        "linked_chw_id"] == str(chw1.user_id)
    assert client.put(url, headers=admin, json={"chw_id": str(chw2.user_id)}).json()[
        "linked_chw_id"] == str(chw2.user_id)
    assert client.put(url, headers=admin, json={"chw_id": None}).json()["linked_chw_id"] is None
    assert client.put(url, headers=admin, json={"chw_id": cg["user_id"]}).status_code == 404


def test_deactivation_rules(client, admin, db_session):
    me = client.get("/auth/me", headers=admin).json()
    r = client.patch(f"/admin/users/{me['user_id']}", headers=admin, json={"is_active": False})
    assert r.status_code == 409

    chw, chw_phone = make_user(db_session, "chw")
    cg, _ = register_caregiver(client)
    client.put(f"/admin/users/{cg['user_id']}/chw", headers=admin, json={"chw_id": str(chw.user_id)})
    r = client.patch(f"/admin/users/{chw.user_id}", headers=admin, json={"is_active": False})
    assert r.status_code == 409 and "caregiver" in r.json()["detail"]

    client.put(f"/admin/users/{cg['user_id']}/chw", headers=admin, json={"chw_id": None})
    r = client.patch(f"/admin/users/{chw.user_id}", headers=admin, json={"is_active": False})
    assert r.status_code == 200
    assert client.post("/auth/login", json={"email": email_for(chw_phone),
                                            "password": PASSWORD}).status_code == 401
    inactive = client.get("/admin/users", params={"active": False}, headers=admin).json()
    assert str(chw.user_id) in {u["user_id"] for u in inactive}


def test_usage_summary_counts(client, admin, db_session):
    before = client.get("/admin/summary", headers=admin).json()

    _, chw_phone = make_user(db_session, "chw")
    chw = login(client, chw_phone)
    phone = new_phone()
    client.post("/chw/caregivers", headers=chw,
                json={"full_name": "C", "email": email_for(phone),
                      "phone_number": phone, "password": PASSWORD})
    confirm_email(client, email_for(phone))
    cg = login(client, phone)
    child = add_child(client, cg, 45)["child_id"]
    submit(client, cg, child, answers(client, cg, child, True))
    flagged = submit(client, cg, child, answers(client, cg, child, False))
    client.post(f"/chw/cases/{flagged['prediction_id']}/outcome", headers=chw,
                json={"outcome": "reviewed_not_concerning"})

    after = client.get("/admin/summary", headers=admin).json()
    assert after["assessments"] - before["assessments"] == 2
    assert after["by_risk_level"]["low"] - before["by_risk_level"]["low"] == 1
    assert after["flagged_for_chw"] - before["flagged_for_chw"] == 1
    assert (after["outcomes"]["reviewed_not_concerning"]
            - before["outcomes"]["reviewed_not_concerning"]) == 1
    assert after["users"]["chw"] - before["users"]["chw"] == 1
    assert after["children"] - before["children"] == 1

    today = date.today()
    future = client.get("/admin/summary", headers=admin,
                        params={"start": (today + timedelta(days=5)).isoformat()}).json()
    assert future["assessments"] == 0 and future["period"]["start"]
    bad = client.get("/admin/summary", headers=admin,
                     params={"start": today.isoformat(),
                             "end": (today - timedelta(days=1)).isoformat()})
    assert bad.status_code == 422
