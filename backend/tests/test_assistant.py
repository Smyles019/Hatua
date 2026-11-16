"""The Hatua assistant. OpenAI is replaced by a stub that records what would have been
sent, so the tests also check what leaves the server."""
import pytest
import requests

from app.core.config import settings
from app.services import assistant
from conftest import add_child, login, make_user, register_caregiver


class FakeOpenAI:
    def __init__(self):
        self.sent = []
        self.fail = False

    def __call__(self, url, timeout, headers, json):
        self.sent.append(json)
        if self.fail:
            raise requests.ConnectionError("down")
        return self

    # the response
    status_code = 200

    def raise_for_status(self):
        pass

    def json(self):
        return {"choices": [{"message": {"content": " Try singing songs together. "}}]}


@pytest.fixture
def openai(monkeypatch):
    fake = FakeOpenAI()
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(assistant.requests, "post", fake)
    return fake


def test_answers_and_keeps_the_conversation(client, openai):
    _, cg = register_caregiver(client, "Wanjiru")
    child = add_child(client, cg, 14, name="Baraka")
    r = client.post("/assistant", headers=cg, json={"body": "How can I help him talk more?",
                                                   "child_id": child["child_id"]})
    assert r.status_code == 200, r.text
    s = r.json()
    assert s["available"] and s["used_today"] == 1
    assert [(m["role"], m["body"]) for m in s["messages"]] == [
        ("user", "How can I help him talk more?"), ("assistant", "Try singing songs together.")]
    [sent] = openai.sent
    system = sent["messages"][0]["content"]
    assert "14 months old" in system and "Answer in English" in system
    text = str(sent)
    assert "Baraka" not in text and "Wanjiru" not in text  # no names leave the server
    # A follow-up carries the earlier messages, and the saved conversation comes back
    client.post("/assistant", headers=cg, json={"body": "And for walking?"})
    assert [m["role"] for m in openai.sent[1]["messages"]] == ["system", "user", "assistant", "user"]
    assert len(client.get("/assistant", headers=cg).json()["messages"]) == 4


def test_danger_signs_get_the_fixed_reply_without_the_ai(client, openai):
    _, cg = register_caregiver(client)
    for text in ("She is having fits since morning", "my baby has fast breathing",
                 "Mtoto ana degedege", "there is blood in the stool", "he won't wake up"):
        s = client.post("/assistant", headers=cg, json={"body": text}).json()
        reply = s["messages"][-1]
        assert reply["flagged"] and "health facility now" in reply["body"], text
    assert openai.sent == []
    for fine in ("Do these shoes fit a 2 year old?", "What games help with walking?",
                 "my toddler is limping after a fall"):
        assert not assistant.mentions_danger_sign(fine), fine


def test_swahili_caregiver_gets_swahili(client, openai):
    _, cg = register_caregiver(client)
    client.patch("/auth/me", headers=cg, json={"language": "sw"})
    client.post("/assistant", headers=cg, json={"body": "Mtoto analala vibaya"})
    assert "Answer in Swahili" in openai.sent[0]["messages"][0]["content"]
    urgent = client.post("/assistant", headers=cg, json={"body": "ana degedege"}).json()
    assert urgent["messages"][-1]["body"] != assistant.URGENT  # translated


def test_limits_errors_and_ownership(client, openai, monkeypatch):
    _, cg = register_caregiver(client)
    _, other = register_caregiver(client)
    not_mine = add_child(client, other, 20)["child_id"]
    assert client.post("/assistant", headers=cg, json={"body": "hi", "child_id": not_mine}).status_code == 404
    assert client.post("/assistant", headers=cg, json={"body": "   "}).status_code == 422
    openai.fail = True
    assert client.post("/assistant", headers=cg, json={"body": "hello"}).status_code == 502
    assert client.get("/assistant", headers=cg).json()["messages"] == []  # nothing half-saved
    openai.fail = False
    monkeypatch.setattr(settings, "assistant_daily_limit", 2)
    client.post("/assistant", headers=cg, json={"body": "one"})
    client.post("/assistant", headers=cg, json={"body": "two"})
    r = client.post("/assistant", headers=cg, json={"body": "three"})
    assert r.status_code == 429 and "limit" in r.json()["detail"]


def test_switched_off_and_clearing(client, monkeypatch, db_session):
    monkeypatch.setattr(settings, "openai_api_key", "")
    _, cg = register_caregiver(client)
    assert client.get("/assistant", headers=cg).json()["available"] is False
    assert client.post("/assistant", headers=cg, json={"body": "hello"}).status_code == 503
    # The danger-sign reply still works with the assistant off
    s = client.post("/assistant", headers=cg, json={"body": "convulsions"}).json()
    assert s["messages"][-1]["flagged"]
    assert client.delete("/assistant", headers=cg).status_code == 204
    assert client.get("/assistant", headers=cg).json()["messages"] == []
    _, chw_phone = make_user(db_session, "chw")
    assert client.get("/assistant", headers=login(client, chw_phone)).status_code == 403


def test_an_openrouter_key_goes_to_openrouter(monkeypatch):
    monkeypatch.setattr(settings, "openai_model", "gpt-4o-mini")
    monkeypatch.setattr(settings, "openai_api_key", "sk-or-v1-abc")
    assert assistant.endpoint() == ("https://openrouter.ai/api/v1/chat/completions",
                                    "openai/gpt-4o-mini", True)
    monkeypatch.setattr(settings, "openai_api_key", "sk-proj-abc")
    assert assistant.endpoint() == ("https://api.openai.com/v1/chat/completions",
                                    "gpt-4o-mini", False)


def test_markdown_is_taken_out_of_answers():
    raw = "## Ideas\n1. **Push toys**: build strength.\n\n\n2. __Songs__ help."
    assert assistant.plain(raw) == "Ideas\n1. Push toys: build strength.\n\n2. Songs help."
