"""Registration, sign-in and tokens (#11)."""
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.config import settings
from app.core.security import ALGORITHM
from conftest import PASSWORD, auth, make_user, new_phone, register_caregiver


def test_register_makes_a_caregiver_and_signs_in(client):
    phone = new_phone()
    r = client.post("/auth/register", json={"full_name": "Wambui", "phone_number": phone,
                                            "password": PASSWORD, "role": "admin"})
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["role"] == "caregiver"  # a role in the body is ignored
    assert body["user"]["phone_number"] == "+254" + phone[1:]
    me = client.get("/auth/me", headers=auth(body["access_token"])).json()
    assert me["user_id"] == body["user"]["user_id"]


@pytest.mark.parametrize("written", ["0712 345 678", "254712345678", "+254-712-345-678"])
def test_phone_numbers_are_stored_in_one_form(client, written):
    r = client.post("/auth/register", json={"full_name": "A", "phone_number": written,
                                            "password": PASSWORD})
    assert r.status_code in (201, 409)  # the same number in another spelling is a duplicate
    login = client.post("/auth/login", json={"phone_number": "0712345678", "password": PASSWORD})
    assert login.status_code == 200


@pytest.mark.parametrize("bad", ["12345", "0812345678", "07123456789", "+1 212 555 0100"])
def test_non_kenyan_or_malformed_numbers_are_refused(client, bad):
    r = client.post("/auth/register", json={"full_name": "A", "phone_number": bad,
                                            "password": PASSWORD})
    assert r.status_code == 422


def test_duplicate_phone_is_refused(client):
    phone = new_phone()
    body = {"full_name": "A", "phone_number": phone, "password": PASSWORD}
    assert client.post("/auth/register", json=body).status_code == 201
    assert client.post("/auth/register", json=body).status_code == 409


def test_wrong_password_and_unknown_number_get_the_same_answer(client):
    user, _ = register_caregiver(client)
    wrong = client.post("/auth/login", json={"phone_number": user["phone_number"],
                                             "password": "not-it"})
    unknown = client.post("/auth/login", json={"phone_number": new_phone(),
                                               "password": PASSWORD})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_short_password_is_refused(client):
    r = client.post("/auth/register", json={"full_name": "A", "phone_number": new_phone(),
                                            "password": "12345"})
    assert r.status_code == 422


def test_routes_need_a_valid_token(client):
    assert client.get("/children").status_code == 401
    assert client.get("/children", headers=auth("not-a-token")).status_code == 401
    expired = jwt.encode({"sub": "00000000-0000-0000-0000-000000000000",
                          "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
                         settings.jwt_secret, algorithm=ALGORITHM)
    assert client.get("/children", headers=auth(expired)).status_code == 401
    forged = jwt.encode({"sub": "00000000-0000-0000-0000-000000000000",
                         "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
                        "some-other-secret", algorithm=ALGORITHM)
    assert client.get("/children", headers=auth(forged)).status_code == 401


def test_deactivated_account_cannot_sign_in_or_use_a_token(client, db_session):
    admin, admin_phone = make_user(db_session, "admin")
    admin_h = client.post("/auth/login", json={"phone_number": admin_phone,
                                               "password": PASSWORD}).json()["access_token"]
    user, headers = register_caregiver(client)
    r = client.patch(f"/admin/users/{user['user_id']}", headers=auth(admin_h),
                     json={"is_active": False})
    assert r.status_code == 200 and r.json()["is_active"] is False
    assert client.get("/auth/me", headers=headers).status_code == 401
    assert client.post("/auth/login", json={"phone_number": user["phone_number"],
                                            "password": PASSWORD}).status_code == 401


def test_password_change(client):
    user, headers = register_caregiver(client)
    bad = client.put("/auth/password", headers=headers,
                     json={"current_password": "wrong", "new_password": "newpass1"})
    assert bad.status_code == 400
    assert client.put("/auth/password", headers=headers,
                      json={"current_password": PASSWORD, "new_password": "newpass1"}
                      ).status_code == 204
    assert client.post("/auth/login", json={"phone_number": user["phone_number"],
                                            "password": "newpass1"}).status_code == 200


def test_docs_form_login(client):
    user, _ = register_caregiver(client)
    r = client.post("/auth/token", data={"username": user["phone_number"], "password": PASSWORD})
    assert r.status_code == 200 and r.json()["token_type"] == "bearer"
    r = client.post("/auth/token", data={"username": "nonsense", "password": PASSWORD})
    assert r.status_code == 401
