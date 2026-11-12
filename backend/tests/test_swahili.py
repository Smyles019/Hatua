"""Swahili: questions and results follow the language saved on the account."""
from conftest import add_child, answers, register_caregiver, submit

from app.services.growth import GROWTH_FLAGS
from app.services.i18n import _swahili
from app.services.questions import QUESTIONS, RED_FLAG_HINTS, RED_FLAG_KINDS, RED_FLAGS
from app.services.results import CAREGIVER_MESSAGES, DOMAIN_LABELS


def test_every_server_text_has_swahili():
    sw = _swahili()
    needed = set(DOMAIN_LABELS.values()) | set(CAREGIVER_MESSAGES.values())
    needed |= set(RED_FLAG_HINTS.values()) | set(RED_FLAG_KINDS.values())
    for q in QUESTIONS.values():
        needed |= {q["text"], q["short"], q["hint"]} | {label for _, label, _ in q["options"]}
    for text, _kind, _age, label in RED_FLAGS.values():
        needed |= {text, label}
    needed |= set(GROWTH_FLAGS.values())
    needed.discard(None)
    assert sorted(t for t in needed if t not in sw) == []


def test_swahili_keeps_the_name_placeholder():
    for en, sw in _swahili().items():
        assert ("{name}" in en) == ("{name}" in sw), en


def test_questions_and_results_in_swahili(client):
    _, headers = register_caregiver(client)
    child = add_child(client, headers, 30)
    assert client.patch("/auth/me", headers=headers, json={"language": "sw"}).status_code == 200
    q = client.get("/assessments/questions", params={"child_id": child["child_id"]},
                   headers=headers).json()["questions"]
    assert q[0]["options"][0]["label"] == "Ndiyo"
    assert all(child["first_name"] in x["text"] or "{name}" not in x["text"] for x in q)
    assert any(x["text"].startswith("Je,") for x in q)
    cid = child["child_id"]
    result = submit(client, headers, cid, answers(client, headers, cid, False))
    labels = {d["label"] for d in result["domains"]}
    assert labels <= {"Mwendo", "Lugha", "Kufikiri na kujifunza", "Kijamii na kihisia"}


def test_english_is_unchanged(client):
    _, headers = register_caregiver(client)
    child = add_child(client, headers, 30)
    q = client.get("/assessments/questions", params={"child_id": child["child_id"]},
                   headers=headers).json()["questions"]
    assert q[0]["options"][0]["label"] == "Yes"
