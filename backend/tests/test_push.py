"""Push notifications: phone tokens, who is told what, and the daily check reminders.
Firebase is not called: without FIREBASE_CREDENTIALS notifications land in push.outbox."""
import uuid
from datetime import date

import pytest

from app.core import push
from app.services.notify import send_check_reminders
from conftest import (PASSWORD, add_child, answers, auth, confirm_email, email_for, login,
                      make_user, new_phone, register_caregiver, submit)


@pytest.fixture(autouse=True)
def empty_outbox():
    push.outbox.clear()
    yield


def token() -> str:
    return "fcm-" + uuid.uuid4().hex + uuid.uuid4().hex


def to(user_id) -> list[push.Pushed]:
    return [p for p in push.outbox if str(p.user_id) == str(user_id)]


def phone_of(client, headers, tok=None) -> str:
    tok = tok or token()
    assert client.put("/auth/me/push-token", headers=headers, json={"token": tok}).status_code == 204
    return tok


def family(client, db_session, chw_language="en"):
    """A CHW (with a phone) and a linked caregiver (with a phone).
    Returns chw user, chw headers, caregiver user, caregiver headers."""
    chw, chw_phone = make_user(db_session, "chw", "Wanjiku")
    chw_h = login(client, chw_phone)
    client.patch("/auth/me", headers=chw_h, json={"language": chw_language})
    phone = new_phone()
    r = client.post("/chw/caregivers", headers=chw_h,
                    json={"full_name": "Achieng", "email": email_for(phone),
                          "phone_number": phone, "password": PASSWORD})
    cg = r.json()
    confirm_email(client, email_for(phone))
    cg_h = login(client, phone)
    phone_of(client, chw_h)
    phone_of(client, cg_h)
    return chw, chw_h, cg, cg_h


def test_a_phone_belongs_to_whoever_signed_in_last(client, db_session):
    a, a_h = register_caregiver(client, "Amina")
    b, b_h = register_caregiver(client, "Baraka")
    shared = phone_of(client, a_h)
    phone_of(client, b_h, shared)  # Baraka signs in on Amina's phone
    with db_session() as db:
        from app.db.models import User
        tokens = {str(u.user_id): [t["token"] for t in u.push_tokens]
                  for u in db.query(User).filter(User.user_id.in_([a["user_id"], b["user_id"]]))}
    assert tokens[a["user_id"]] == [] and tokens[b["user_id"]] == [shared]
    # Signing out takes the phone off the account
    assert client.request("DELETE", "/auth/me/push-token", headers=b_h,
                          params={"token": shared}).status_code == 204
    assert client.get("/auth/me", headers=b_h).status_code == 200
    with db_session() as db:
        from app.db.models import User
        assert db.get(User, uuid.UUID(b["user_id"])).push_tokens == []
    assert client.put("/auth/me/push-token", headers=b_h, json={"token": "short"}).status_code == 422


def test_flagged_check_tells_the_chw_and_a_low_one_does_not(client, db_session):
    chw, _, cg, cg_h = family(client, db_session)
    child = add_child(client, cg_h, 48)["child_id"]
    submit(client, cg_h, child, answers(client, cg_h, child, True))
    assert to(chw.user_id) == []
    high = submit(client, cg_h, child, answers(client, cg_h, child, False))
    [p] = to(chw.user_id)
    assert p.title == "A check needs your review" and "Imani" in p.body and "Achieng" in p.body
    assert p.data == {"type": "case", "id": high["prediction_id"]}
    # No risk level on the lock screen
    assert high["risk_level"] not in (p.title + p.body).lower()


def test_messages_tell_the_other_side(client, db_session):
    chw, chw_h, cg, cg_h = family(client, db_session)
    client.post("/messages", headers=cg_h, json={"body": "My child has a fever, what do I do?"})
    [q] = to(chw.user_id)
    assert q.title == "New message" and "Achieng" in q.body and "fever" not in q.body
    assert q.data == {"type": "thread", "id": cg["user_id"], "name": "Achieng"}
    client.post(f"/messages/threads/{cg['user_id']}", headers=chw_h, json={"body": "Come to the clinic"})
    [r] = to(cg["user_id"])
    assert r.title == "New message" and "clinic" not in r.body and r.data == {"type": "ask"}


def test_outcome_tells_the_caregiver_except_unreachable(client, db_session):
    _, chw_h, cg, cg_h = family(client, db_session)
    child = add_child(client, cg_h, 36)["child_id"]
    res = submit(client, cg_h, child, answers(client, cg_h, child, False))
    url = f"/chw/cases/{res['prediction_id']}/outcome"
    client.post(url, headers=chw_h, json={"outcome": "unreachable"})
    assert to(cg["user_id"]) == []
    client.post(url, headers=chw_h, json={"outcome": "refer_to_facility"})
    [p] = to(cg["user_id"])
    assert p.title == "Imani's check was reviewed" and "facility" not in p.body
    assert p.data == {"type": "result", "id": res["prediction_id"], "child_id": child}
    client.post(url, headers=chw_h, json={"outcome": "refer_to_facility"})  # saved again
    assert len(to(cg["user_id"])) == 1


def test_notifications_come_in_the_persons_language(client, db_session):
    chw, _, _, cg_h = family(client, db_session, chw_language="sw")
    client.post("/messages", headers=cg_h, json={"body": "Habari"})
    [q] = to(chw.user_id)
    assert q.title != "New message" and "Achieng" in q.body


def test_nothing_is_sent_without_a_phone(client, db_session):
    chw, chw_phone = make_user(db_session, "chw")
    chw_h = login(client, chw_phone)
    cg, cg_h = register_caregiver(client)
    client.post("/chw/caregivers/link", headers=chw_h, json={"phone_number": cg["phone_number"]})
    client.post("/messages", headers=cg_h, json={"body": "Hello"})
    assert push.outbox == []


def months_later(d: date, n: int) -> date:
    y, m = divmod(d.year * 12 + d.month - 1 + n, 12)
    return date(y, m + 1, min(d.day, 28))


def test_check_reminders_once_per_age_band(client, db_session):
    cg, cg_h = register_caregiver(client, "Neema")
    phone_of(client, cg_h)
    due = add_child(client, cg_h, 30, name="Zawadi")["child_id"]      # 24-35, no check
    done = add_child(client, cg_h, 48, name="Juma")["child_id"]       # 48-59, checked
    submit(client, cg_h, done, answers(client, cg_h, done, True))
    _, quiet_h = register_caregiver(client, "Without a phone")
    quiet = add_child(client, quiet_h, 30, name="Tumaini")["child_id"]

    today = date.today()
    send_check_reminders(db_session, today)
    mine = to(cg["user_id"])
    assert [p.data for p in mine] == [{"type": "child", "id": due}]
    assert mine[0].title == "Time for Zawadi's check"
    assert all("Tumaini" not in p.title for p in push.outbox)

    push.outbox.clear()
    send_check_reminders(db_session, today)  # the next day: already reminded
    assert to(cg["user_id"]) == []

    # Zawadi turns 36 months: a new band, so one new reminder
    send_check_reminders(db_session, months_later(today, 7))
    assert {p.data["id"] for p in to(cg["user_id"])} >= {due}
    with db_session() as db:
        from app.db.models import Child
        assert db.get(Child, uuid.UUID(quiet)).reminded_band is not None


def test_a_chw_can_start_the_chat(client, db_session):
    _, chw_h, cg, cg_h = family(client, db_session)
    r = client.post(f"/messages/threads/{cg['user_id']}", headers=chw_h,
                    json={"body": "Hello, I am your health worker"})
    assert r.status_code == 201
    [p] = to(cg["user_id"])
    assert p.title == "New message" and p.data == {"type": "ask"}
    thread = client.get("/messages", headers=cg_h).json()
    assert [m["sender_role"] for m in thread["messages"]] == ["chw"]
    assert client.post("/messages", headers=cg_h, json={"body": "  "}).status_code == 422
