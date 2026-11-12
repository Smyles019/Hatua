"""Registration, email confirmation, sign-in, password reset and tokens (#11)."""
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core import mailer
from app.core.config import settings
from app.core.security import ALGORITHM
from conftest import (PASSWORD, auth, confirm_email, email_for, make_user, new_phone,
                      register_caregiver)


def new_account() -> dict:
    phone = new_phone()
    return {"full_name": "Wambui", "email": email_for(phone), "phone_number": phone,
            "password": PASSWORD}


def link_to(email: str, path: str) -> str:
    """Path and query of the newest emailed link of this kind for this address."""
    sent = next(m for m in reversed(mailer.outbox) if m.to == email and path in m.body)
    word = next(w for w in sent.body.split() if path in w)
    return word.removeprefix(settings.public_base_url)


def sign_in(client, email: str, password: str = PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def test_register_makes_a_caregiver_but_gives_no_session(client):
    body = new_account()
    r = client.post("/auth/register", json={**body, "role": "admin"})
    assert r.status_code == 201
    assert r.json() == {"email": body["email"], "verification_sent": True}
    assert "access_token" not in r.json()


def test_sign_in_waits_for_the_email_to_be_confirmed(client):
    body = new_account()
    client.post("/auth/register", json=body)
    r = sign_in(client, body["email"])
    assert r.status_code == 403
    assert r.json()["detail"] == {"needs_verification": True, "email": body["email"]}

    confirm_email(client, body["email"])
    r = sign_in(client, body["email"])
    assert r.status_code == 200
    user = r.json()["user"]
    assert user["role"] == "caregiver"  # a role in the body is ignored
    assert user["email_verified"] is True
    assert user["phone_number"] == "+254" + body["phone_number"][1:]
    me = client.get("/auth/me", headers=auth(r.json()["access_token"])).json()
    assert me["user_id"] == user["user_id"]


def test_wrong_password_does_not_reveal_an_unconfirmed_account(client):
    body = new_account()
    client.post("/auth/register", json=body)
    assert sign_in(client, body["email"], "not-it").status_code == 401


def test_confirmation_email_can_be_sent_again(client):
    body = new_account()
    client.post("/auth/register", json=body)
    before = len(mailer.outbox)
    assert client.post("/auth/verify/resend", json={"email": body["email"]}).status_code == 204
    assert len(mailer.outbox) == before + 1
    # unknown or already confirmed addresses get the same answer and no email
    assert client.post("/auth/verify/resend",
                       json={"email": "nobody@example.com"}).status_code == 204
    confirm_email(client, body["email"])
    assert client.post("/auth/verify/resend", json={"email": body["email"]}).status_code == 204
    assert len(mailer.outbox) == before + 1


def test_a_broken_confirmation_link_is_refused(client):
    assert client.get("/auth/verify", params={"token": "nonsense"}).status_code == 400
    assert client.get("/auth/verify").status_code == 400


def test_an_emailed_link_is_not_a_session(client):
    body = new_account()
    client.post("/auth/register", json=body)
    token = link_to(body["email"], "/auth/verify?token=").split("token=")[1]
    assert client.get("/auth/me", headers=auth(token)).status_code == 401
    # and a confirmation link cannot be used to reset a password
    assert client.get("/auth/password/reset", params={"token": token}).status_code == 400


def test_email_is_stored_in_lower_case(client):
    body = new_account()
    client.post("/auth/register", json={**body, "email": "  " + body["email"].upper()})
    confirm_email(client, body["email"])
    assert sign_in(client, body["email"].title()).status_code == 200


@pytest.mark.parametrize("bad", ["not-an-email", "a@b", "two@@example.com", "a b@example.com", ""])
def test_malformed_emails_are_refused(client, bad):
    r = client.post("/auth/register", json={**new_account(), "email": bad})
    assert r.status_code == 422


@pytest.mark.parametrize("bad", ["12345", "0812345678", "07123456789", "+1 212 555 0100"])
def test_non_kenyan_or_malformed_numbers_are_refused(client, bad):
    r = client.post("/auth/register", json={**new_account(), "phone_number": bad})
    assert r.status_code == 422


def test_duplicate_email_or_phone_is_refused(client):
    body = new_account()
    assert client.post("/auth/register", json=body).status_code == 201
    same_email = client.post("/auth/register", json={**new_account(), "email": body["email"]})
    assert same_email.status_code == 409 and "email" in same_email.json()["detail"]
    # the same number in another spelling is still a duplicate
    spelled = "+254 " + body["phone_number"][1:]
    same_phone = client.post("/auth/register", json={**new_account(), "phone_number": spelled})
    assert same_phone.status_code == 409 and "phone" in same_phone.json()["detail"]


def test_the_phone_number_is_not_a_way_to_sign_in(client):
    user, _ = register_caregiver(client)
    r = client.post("/auth/login", json={"phone_number": user["phone_number"],
                                         "password": PASSWORD})
    assert r.status_code == 422


def test_wrong_password_and_unknown_email_get_the_same_answer(client):
    user, _ = register_caregiver(client)
    wrong = sign_in(client, user["email"], "not-it")
    unknown = sign_in(client, "nobody@example.com")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_short_password_is_refused(client):
    r = client.post("/auth/register", json={**new_account(), "password": "12345"})
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
    _, admin_phone = make_user(db_session, "admin")
    admin_h = sign_in(client, email_for(admin_phone)).json()["access_token"]
    user, headers = register_caregiver(client)
    r = client.patch(f"/admin/users/{user['user_id']}", headers=auth(admin_h),
                     json={"is_active": False})
    assert r.status_code == 200 and r.json()["is_active"] is False
    assert client.get("/auth/me", headers=headers).status_code == 401
    assert sign_in(client, user["email"]).status_code == 401


def test_password_change(client):
    user, headers = register_caregiver(client)
    bad = client.put("/auth/password", headers=headers,
                     json={"current_password": "wrong", "new_password": "newpass1"})
    assert bad.status_code == 400
    assert client.put("/auth/password", headers=headers,
                      json={"current_password": PASSWORD, "new_password": "newpass1"}
                      ).status_code == 204
    assert sign_in(client, user["email"], "newpass1").status_code == 200


def test_forgotten_password_is_reset_from_the_emailed_link(client):
    user, _ = register_caregiver(client)
    assert client.post("/auth/password/forgot", json={"email": user["email"]}).status_code == 204
    link = link_to(user["email"], "/auth/password/reset?token=")
    token = link.split("token=")[1]

    page = client.get(link)
    assert page.status_code == 200 and "New password" in page.text

    form = {"token": token, "new_password": "brand-new-1", "repeat_password": "different"}
    assert client.post("/auth/password/reset", data=form).status_code == 400
    assert client.post("/auth/password/reset",
                       data={**form, "new_password": "123", "repeat_password": "123"}
                       ).status_code == 400
    assert sign_in(client, user["email"]).status_code == 200  # nothing changed yet

    ok = client.post("/auth/password/reset", data={**form, "repeat_password": "brand-new-1"})
    assert ok.status_code == 200
    assert sign_in(client, user["email"], "brand-new-1").status_code == 200
    assert sign_in(client, user["email"]).status_code == 401

    # the link works only once
    again = client.post("/auth/password/reset",
                        data={"token": token, "new_password": "third-one-1",
                              "repeat_password": "third-one-1"})
    assert again.status_code == 400
    assert client.get(link).status_code == 400
    assert sign_in(client, user["email"], "brand-new-1").status_code == 200


def test_forgot_password_gives_the_same_answer_for_an_unknown_email(client):
    before = len(mailer.outbox)
    r = client.post("/auth/password/forgot", json={"email": "nobody@example.com"})
    assert r.status_code == 204
    assert len(mailer.outbox) == before


def test_resetting_the_password_also_confirms_the_email(client):
    body = new_account()
    client.post("/auth/register", json=body)  # never opens the confirmation link
    client.post("/auth/password/forgot", json={"email": body["email"]})
    token = link_to(body["email"], "/auth/password/reset?token=").split("token=")[1]
    client.post("/auth/password/reset", data={"token": token, "new_password": "brand-new-1",
                                              "repeat_password": "brand-new-1"})
    assert sign_in(client, body["email"], "brand-new-1").status_code == 200


def test_docs_form_login(client):
    user, _ = register_caregiver(client)
    r = client.post("/auth/token", data={"username": user["email"], "password": PASSWORD})
    assert r.status_code == 200 and r.json()["token_type"] == "bearer"
    r = client.post("/auth/token", data={"username": "nonsense", "password": PASSWORD})
    assert r.status_code == 401
