"""Offline mode: a change the phone queued and sends twice is only saved once."""
import uuid
from datetime import datetime, timedelta, timezone

from app.core import idempotency
from app.db.models import IdempotentRequest
from conftest import add_child, answers, months_ago, register_caregiver


def key() -> str:
    return uuid.uuid4().hex


def test_a_check_sent_twice_is_saved_once(client):
    _, cg = register_caregiver(client)
    child = add_child(client, cg, 30)
    body = {"child_id": child["child_id"], "responses": answers(client, cg, child["child_id"], True)}
    k = {**cg, "Idempotency-Key": key()}
    first = client.post("/assessments", headers=k, json=body)
    again = client.post("/assessments", headers=k, json=body)
    assert first.status_code == again.status_code == 201, first.text
    assert again.headers.get("Idempotent-Replay") == "true"
    assert again.json()["prediction_id"] == first.json()["prediction_id"]
    checks = client.get(f"/children/{child['child_id']}/assessments", headers=cg).json()
    assert len(checks) == 1
    # A new key is a new check
    client.post("/assessments", headers={**cg, "Idempotency-Key": key()}, json=body)
    assert len(client.get(f"/children/{child['child_id']}/assessments", headers=cg).json()) == 2


def test_without_a_key_nothing_changes(client):
    _, cg = register_caregiver(client)
    body = {"first_name": "Zawadi", "date_of_birth": months_ago(20), "sex": "female", "location": "Kibra"}
    a = client.post("/children", headers=cg, json=body)
    b = client.post("/children", headers=cg, json=body)
    assert a.status_code == b.status_code == 201
    assert a.json()["child_id"] != b.json()["child_id"]
    assert "Idempotent-Replay" not in b.headers


def test_failures_are_not_saved_and_bad_keys_are_refused(client):
    _, cg = register_caregiver(client)
    k = key()
    bad = {"first_name": "", "date_of_birth": months_ago(20), "sex": "female", "location": "Kibra"}
    assert client.post("/children", headers={**cg, "Idempotency-Key": k}, json=bad).status_code == 422
    good = {"first_name": "Zawadi", "date_of_birth": months_ago(20), "sex": "female", "location": "Kibra"}
    assert client.post("/children", headers={**cg, "Idempotency-Key": k}, json=good).status_code == 201
    # The same key on a different request, and keys that are too short or odd
    r = client.patch("/auth/me", headers={**cg, "Idempotency-Key": k}, json={"language": "sw"})
    assert r.status_code == 422 and "another request" in r.json()["detail"]
    for odd in ("short", "x" * 65, "has spaces in it ok"):
        r = client.post("/children", headers={**cg, "Idempotency-Key": odd}, json=good)
        assert r.status_code == 422, odd


def test_old_keys_are_pruned(db_session):
    old, new = key(), key()
    with db_session() as db:
        db.add_all([IdempotentRequest(key=old, path="/x", status_code=201, body="{}",
                                      created_at=datetime.now(timezone.utc) - timedelta(days=31)),
                    IdempotentRequest(key=new, path="/x", status_code=201, body="{}")])
        db.commit()
    assert idempotency.prune(db_session) >= 1
    with db_session() as db:
        assert db.get(IdempotentRequest, old) is None
        assert db.get(IdempotentRequest, new) is not None
