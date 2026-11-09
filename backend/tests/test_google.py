"""Google sign-in (/auth/google). Google itself is replaced by a stub: the real token
check (app/core/google.py) needs network access and a real token."""
import uuid

import pytest

from app.api.routes import auth as auth_routes
from app.core.google import GoogleIdentity, GoogleTokenError
from conftest import PASSWORD, auth, new_phone

TOKEN = "x" * 40


@pytest.fixture
def google(monkeypatch):
    """Makes the next sign-in come from a new Google account; returns it for the test."""
    who = GoogleIdentity(google_id=uuid.uuid4().hex, email=f"{uuid.uuid4().hex[:10]}@gmail.com",
                         name="Amina Wanjiku")
    monkeypatch.setattr(auth_routes, "verify_google_token", lambda token: who)
    return who


def test_new_google_account_asks_for_a_phone_number_first(client, google):
    r = client.post("/auth/google", json={"id_token": TOKEN})
    assert r.status_code == 428
    assert r.json()["detail"] == {"needs_phone": True, "full_name": "Amina Wanjiku",
                                  "email": google.email}


def test_new_google_account_with_phone_becomes_a_caregiver(client, google):
    phone = new_phone()
    r = client.post("/auth/google", json={"id_token": TOKEN, "phone_number": phone})
    assert r.status_code == 200
    user = r.json()["user"]
    assert user["role"] == "caregiver"
    assert user["email"] == google.email
    assert user["phone_number"] == "+254" + phone[1:]
    me = client.get("/auth/me", headers=auth(r.json()["access_token"]))
    assert me.status_code == 200


def test_returning_google_account_signs_straight_in(client, google):
    client.post("/auth/google", json={"id_token": TOKEN, "phone_number": new_phone()})
    r = client.post("/auth/google", json={"id_token": TOKEN})  # no phone needed now
    assert r.status_code == 200


def test_phone_that_already_has_an_account_is_not_taken_over(client, google):
    phone = new_phone()
    client.post("/auth/register", json={"full_name": "A", "phone_number": phone,
                                        "password": PASSWORD})
    r = client.post("/auth/google", json={"id_token": TOKEN, "phone_number": phone})
    assert r.status_code == 409


def test_google_only_account_cannot_sign_in_with_a_password(client, google):
    phone = new_phone()
    client.post("/auth/google", json={"id_token": TOKEN, "phone_number": phone})
    r = client.post("/auth/login", json={"phone_number": phone, "password": "anything"})
    assert r.status_code == 401


def test_bad_google_token_is_refused(client, monkeypatch):
    def reject(token):
        raise GoogleTokenError("invalid Google sign-in token")
    monkeypatch.setattr(auth_routes, "verify_google_token", reject)
    r = client.post("/auth/google", json={"id_token": TOKEN, "phone_number": new_phone()})
    assert r.status_code == 401


def test_google_sign_in_is_off_without_a_client_id(client, monkeypatch):
    from app.core import config
    monkeypatch.setattr(config.settings, "google_client_ids", "")
    r = client.post("/auth/google", json={"id_token": TOKEN})
    assert r.status_code == 401
