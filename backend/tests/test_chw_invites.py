"""CHW invites: the administrator adds a CHW by name and email; the CHW sets up the
account from the emailed link (phone number and password) or with Google."""
import uuid

import pytest

from app.api.routes import auth as auth_routes
from app.core import mailer
from app.core.config import settings
from app.core.google import GoogleIdentity
from conftest import PASSWORD, make_user, new_phone, register_caregiver

TOKEN = "x" * 40


@pytest.fixture(scope="module")
def admin(client, db_session):
    from conftest import login
    _, phone = make_user(db_session, "admin")
    return login(client, phone)


def new_email() -> str:
    return f"chw{uuid.uuid4().hex[:10]}@example.com"


def invite(client, admin, email=None, name="Wanjiru") -> dict:
    r = client.post("/admin/chws", headers=admin, json={"full_name": name, "email": email or new_email()})
    assert r.status_code == 201, r.text
    return r.json()


def invite_link(email: str) -> str:
    """The path of the newest invite link 'sent' to this address (see app.core.mailer)."""
    sent = next(m for m in reversed(mailer.outbox) if m.to == email and "/auth/invite" in m.body)
    link = next(w for w in sent.body.split() if "/auth/invite?token=" in w)
    return link.removeprefix(settings.public_base_url)


def token_of(path: str) -> str:
    return path.split("token=", 1)[1]


def set_up(client, path, phone, password=PASSWORD, repeat=None):
    return client.post("/auth/invite", data={"token": token_of(path), "phone_number": phone,
                                             "new_password": password,
                                             "repeat_password": repeat or password})


def test_invited_chw_waits_and_cannot_sign_in_yet(client, admin):
    email = new_email()
    chw = invite(client, admin, email)
    assert chw["role"] == "chw" and chw["invite_pending"] is True
    assert chw["phone_number"] is None and chw["caregivers"] == 0
    assert client.post("/auth/login", json={"email": email, "password": PASSWORD}).status_code == 401
    listed = {c["user_id"]: c for c in client.get("/admin/chws", headers=admin).json()}
    assert listed[chw["user_id"]]["invite_pending"] is True
    # Not counted as a CHW people can use yet
    before = client.get("/admin/summary", headers=admin).json()["users"]["chw"]
    invite(client, admin)
    assert client.get("/admin/summary", headers=admin).json()["users"]["chw"] == before


def test_invite_link_sets_up_the_account(client, admin):
    email = new_email()
    chw = invite(client, admin, email)
    path = invite_link(email)
    page = client.get(path)
    assert page.status_code == 200 and "Set up your Hatua account" in page.text
    phone = new_phone()
    r = set_up(client, path, phone)
    assert r.status_code == 200 and "Your account is ready" in r.text
    r = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200
    user = r.json()["user"]
    assert user["role"] == "chw" and user["user_id"] == chw["user_id"]
    assert user["phone_number"] == "+254" + phone[1:] and user["invite_pending"] is False
    # The link works once
    assert client.get(path).status_code == 400
    assert set_up(client, path, new_phone()).status_code == 400


def test_invite_page_checks_what_is_typed(client, admin, db_session):
    email = new_email()
    invite(client, admin, email)
    path = invite_link(email)
    bad_phone = set_up(client, path, "12345")
    assert bad_phone.status_code == 400 and "Kenyan mobile number" in bad_phone.text
    assert set_up(client, path, new_phone(), "short").status_code == 400
    assert "do not match" in set_up(client, path, new_phone(), PASSWORD, "different1").text
    _, taken = make_user(db_session, "caregiver")
    assert "already has a Hatua account" in set_up(client, path, taken).text
    assert set_up(client, path, new_phone()).status_code == 200  # still usable after mistakes


def test_resending_replaces_the_old_link(client, admin):
    email = new_email()
    chw = invite(client, admin, email)
    first = invite_link(email)
    r = client.post(f"/admin/chws/{chw['user_id']}/invite", headers=admin)
    assert r.status_code == 200
    second = invite_link(email)
    assert first != second
    assert client.get(first).status_code == 400
    assert client.get(second).status_code == 200
    set_up(client, second, new_phone())
    r = client.post(f"/admin/chws/{chw['user_id']}/invite", headers=admin)
    assert r.status_code == 409


def test_forgot_password_sends_the_invite_to_a_waiting_chw(client, admin):
    email = new_email()
    invite(client, admin, email)
    count = sum(1 for m in mailer.outbox if m.to == email)
    assert client.post("/auth/password/forgot", json={"email": email}).status_code == 204
    newest = next(m for m in reversed(mailer.outbox) if m.to == email)
    assert sum(1 for m in mailer.outbox if m.to == email) == count + 1
    assert "/auth/invite?token=" in newest.body


def test_invited_chw_can_set_up_with_google(client, admin, monkeypatch):
    email = new_email()
    chw = invite(client, admin, email, name="Kamau")
    who = GoogleIdentity(google_id=uuid.uuid4().hex, email=email, name="Kamau G")
    monkeypatch.setattr(auth_routes, "verify_google_token", lambda token: who)
    r = client.post("/auth/google", json={"id_token": TOKEN})
    assert r.status_code == 428
    assert r.json()["detail"] == {"needs_phone": True, "full_name": "Kamau", "email": email,
                                  "role": "chw"}
    phone = new_phone()
    r = client.post("/auth/google", json={"id_token": TOKEN, "phone_number": phone})
    assert r.status_code == 200
    user = r.json()["user"]
    assert user["user_id"] == chw["user_id"] and user["role"] == "chw"
    assert user["phone_number"] == "+254" + phone[1:] and user["invite_pending"] is False
    # The emailed link no longer works once the account is set up
    assert client.get(invite_link(email)).status_code == 400
    assert client.post("/auth/google", json={"id_token": TOKEN}).status_code == 200


def test_invite_rules(client, admin):
    email = new_email()
    chw = invite(client, admin, email)
    r = client.post("/admin/chws", headers=admin, json={"full_name": "Again", "email": email})
    assert r.status_code == 409
    assert client.post("/admin/chws", headers=admin,
                       json={"full_name": "X", "email": "not-an-email"}).status_code == 422
    # A caregiver cannot be linked to a CHW who has not set up yet
    cg, _ = register_caregiver(client)
    r = client.put(f"/admin/users/{cg['user_id']}/chw", headers=admin,
                   json={"chw_id": chw["user_id"]})
    assert r.status_code == 409
    # Only administrators invite
    _, cg_headers = register_caregiver(client)
    assert client.post("/admin/chws", headers=cg_headers,
                       json={"full_name": "X", "email": new_email()}).status_code == 403
    # A deactivated invite gets no new link, and its old one stops working
    client.patch(f"/admin/users/{chw['user_id']}", headers=admin, json={"is_active": False})
    assert client.post(f"/admin/chws/{chw['user_id']}/invite", headers=admin).status_code == 409
    assert client.get(invite_link(email)).status_code == 400


def test_caregiver_count_on_the_chws_page(client, admin, db_session):
    chw, _ = make_user(db_session, "chw")
    cg, _ = register_caregiver(client)
    client.put(f"/admin/users/{cg['user_id']}/chw", headers=admin, json={"chw_id": str(chw.user_id)})
    listed = {c["user_id"]: c for c in client.get("/admin/chws", headers=admin).json()}
    assert listed[str(chw.user_id)]["caregivers"] == 1
    assert listed[str(chw.user_id)]["invite_pending"] is False
