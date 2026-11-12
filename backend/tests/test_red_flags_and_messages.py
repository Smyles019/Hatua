"""Hearing and vision red flags, reasons for special care, Ask a CHW and language."""
from conftest import (add_child, answers, auth, login, make_user, register_caregiver,
                      submit)


def linked_pair(client, db_session):
    """A caregiver linked to a CHW. Returns (caregiver, caregiver headers, chw headers)."""
    _, chw_phone = make_user(db_session, "chw")
    chw_h = login(client, chw_phone)
    user, headers = register_caregiver(client)
    r = client.post("/chw/caregivers/link", headers=chw_h,
                    json={"phone_number": user["phone_number"]})
    assert r.status_code == 200, r.text
    return user, headers, chw_h


# ---------- red flags ----------

def test_red_flag_questions_come_after_the_model_questions(client):
    _, headers = register_caregiver(client)
    child = add_child(client, headers, 30)
    qs = client.get("/assessments/questions", params={"child_id": child["child_id"]},
                    headers=headers).json()["questions"]
    kinds = [q.get("screening") for q in qs]
    first = next(i for i, k in enumerate(kinds) if k)
    assert all(k is None for k in kinds[:first]) and all(kinds[first:])
    assert {q["item"] for q in qs if q.get("screening")} == {
        "rf_hearing", "rf_pupil", "rf_sight", "rf_eyes_straight"}
    assert child["first_name"] in qs[-1]["text"]


def test_young_babies_get_fewer_red_flag_questions(client):
    _, headers = register_caregiver(client)
    child = add_child(client, headers, 5)  # the squint question starts at 6 months
    qs = client.get("/assessments/questions", params={"child_id": child["child_id"]},
                    headers=headers).json()["questions"]
    assert {q["item"] for q in qs if q.get("screening")} == {
        "rf_hearing", "rf_pupil", "rf_sight"}


def test_a_red_flag_sends_a_low_risk_result_to_the_chw(client, db_session):
    _, headers, chw_h = linked_pair(client, db_session)
    child = add_child(client, headers, 30)
    good = answers(client, headers, child["child_id"], achieved=True)
    quiet = submit(client, headers, child["child_id"], good)
    assert quiet["risk_level"] == "low" and quiet["red_flags"] == []
    assert quiet["sent_to_chw"] is False

    flagged = submit(client, headers, child["child_id"], {**good, "rf_hearing": "no"})
    assert flagged["risk_level"] == "low"  # the model's answer is unchanged
    assert flagged["sent_to_chw"] is True
    assert [f["flag"] for f in flagged["red_flags"]] == ["rf_hearing"]
    assert flagged["red_flags"][0]["kind"] == "hearing"

    cases = client.get("/chw/cases", headers=chw_h).json()
    assert [c["prediction_id"] for c in cases] == [flagged["prediction_id"]]
    # and the CHW can record an outcome for it
    r = client.post(f"/chw/cases/{flagged['prediction_id']}/outcome", headers=chw_h,
                    json={"outcome": "refer_to_facility"})
    assert r.status_code == 200


def test_dont_know_raises_no_flag_and_red_flag_answers_may_be_left_out(client):
    _, headers = register_caregiver(client)
    child = add_child(client, headers, 30)
    good = answers(client, headers, child["child_id"], achieved=True)
    out = submit(client, headers, child["child_id"], {**good, "rf_sight": "dont_know"})
    assert out["red_flags"] == []
    only_model = {k: v for k, v in good.items() if not k.startswith("rf_")}
    assert submit(client, headers, child["child_id"], only_model)["red_flags"] == []


def test_a_bad_red_flag_answer_is_refused(client):
    _, headers = register_caregiver(client)
    child = add_child(client, headers, 30)
    good = answers(client, headers, child["child_id"], achieved=True)
    r = client.post("/assessments", headers=headers,
                    json={"child_id": child["child_id"],
                          "responses": {**good, "rf_hearing": "maybe"}})
    assert r.status_code == 422


# ---------- reasons for special care ----------

def test_care_factors_are_saved_and_shown_to_the_chw(client, db_session):
    _, headers, chw_h = linked_pair(client, db_session)
    child = add_child(client, headers, 30,
                      care_factors=["multiple_birth", "low_birth_weight", "multiple_birth"])
    assert child["care_factors"] == ["low_birth_weight", "multiple_birth"]

    r = client.patch(f"/children/{child['child_id']}", headers=headers,
                     json={"care_factors": ["short_birth_spacing"]})
    assert r.status_code == 200 and r.json()["care_factors"] == ["short_birth_spacing"]
    # changing the avatar leaves them alone
    r = client.patch(f"/children/{child['child_id']}", headers=headers,
                     json={"avatar_id": "lion"})
    assert r.json()["care_factors"] == ["short_birth_spacing"]
    assert r.json()["avatar_id"] == "lion"

    bad = answers(client, headers, child["child_id"], achieved=False)
    submit(client, headers, child["child_id"], bad)
    case = client.get("/chw/cases", headers=chw_h).json()[0]
    assert case["care_factors"] == ["short_birth_spacing"]
    assert case["latest_growth"] is None


def test_an_unknown_care_factor_is_refused(client):
    _, headers = register_caregiver(client)
    r = client.post("/children", headers=headers,
                    json={"first_name": "Imani", "date_of_birth": "2026-01-01",
                          "sex": "female", "location": "Kibra",
                          "care_factors": ["hiv_exposed"]})
    assert r.status_code == 422


# ---------- Ask a CHW ----------

def test_a_question_and_its_reply(client, db_session):
    user, headers, chw_h = linked_pair(client, db_session)
    empty = client.get("/messages", headers=headers).json()
    assert empty["messages"] == [] and empty["waiting_for_chw"] is False
    assert empty["chw"] is not None

    r = client.post("/messages", headers=headers, json={"body": "  Is it normal?  "})
    assert r.status_code == 201
    assert r.json()["waiting_for_chw"] is True
    assert r.json()["messages"][0]["body"] == "Is it normal?"
    assert r.json()["messages"][0]["from_me"] is True

    inbox = client.get("/messages/threads", headers=chw_h).json()
    assert len(inbox) == 1 and inbox[0]["waiting_for_chw"] is True
    assert inbox[0]["caregiver"]["user_id"] == user["user_id"]

    r = client.post(f"/messages/threads/{user['user_id']}", headers=chw_h,
                    json={"body": "Yes, at this age it is."})
    assert r.status_code == 201 and r.json()["waiting_for_chw"] is False
    assert [m["from_me"] for m in r.json()["messages"]] == [False, True]

    mine = client.get("/messages", headers=headers).json()
    assert mine["waiting_for_chw"] is False
    assert [m["sender_role"] for m in mine["messages"]] == ["caregiver", "chw"]
    assert client.get("/messages/threads", headers=chw_h).json()[0]["waiting_for_chw"] is False


def test_a_question_can_be_about_a_check(client, db_session):
    user, headers, chw_h = linked_pair(client, db_session)
    child = add_child(client, headers, 30, name="Baraka")
    out = submit(client, headers, child["child_id"],
                 answers(client, headers, child["child_id"], achieved=False))
    r = client.post("/messages", headers=headers,
                    json={"body": "What does this mean?", "prediction_id": out["prediction_id"]})
    assert r.status_code == 201
    seen = client.get(f"/messages/threads/{user['user_id']}", headers=chw_h).json()
    assert seen["messages"][0]["about"]["child_name"] == "Baraka"
    assert seen["messages"][0]["about"]["prediction_id"] == out["prediction_id"]

    # someone else's check cannot be attached
    _, other_h = register_caregiver(client)
    r = client.post("/messages", headers=other_h,
                    json={"body": "Hello", "prediction_id": out["prediction_id"]})
    assert r.status_code == 404


def test_a_question_waits_until_a_chw_is_linked(client, db_session):
    user, headers = register_caregiver(client)
    r = client.post("/messages", headers=headers, json={"body": "Anyone there?"})
    assert r.status_code == 201 and r.json()["chw"] is None

    _, chw_phone = make_user(db_session, "chw")
    chw_h = login(client, chw_phone)
    assert client.get("/messages/threads", headers=chw_h).json() == []
    assert client.get(f"/messages/threads/{user['user_id']}", headers=chw_h).status_code == 404
    client.post("/chw/caregivers/link", headers=chw_h,
                json={"phone_number": user["phone_number"]})
    inbox = client.get("/messages/threads", headers=chw_h).json()
    assert len(inbox) == 1 and inbox[0]["last_message"]["body"] == "Anyone there?"


def test_only_the_linked_chw_and_the_caregiver_see_a_thread(client, db_session):
    user, headers, _ = linked_pair(client, db_session)
    client.post("/messages", headers=headers, json={"body": "Private question"})
    _, other_phone = make_user(db_session, "chw")
    other_h = login(client, other_phone)
    assert client.get(f"/messages/threads/{user['user_id']}", headers=other_h).status_code == 404
    assert client.post(f"/messages/threads/{user['user_id']}", headers=other_h,
                       json={"body": "hi"}).status_code == 404
    # roles are kept apart
    assert client.get("/messages/threads", headers=headers).status_code == 403
    assert client.get("/messages", headers=other_h).status_code == 403
    assert client.get("/messages").status_code == 401


def test_empty_and_overlong_messages_are_refused(client):
    _, headers = register_caregiver(client)
    assert client.post("/messages", headers=headers, json={"body": "   "}).status_code == 422
    assert client.post("/messages", headers=headers, json={"body": ""}).status_code == 422
    assert client.post("/messages", headers=headers,
                       json={"body": "x" * 1001}).status_code == 422


# ---------- language ----------

def test_language_is_saved_on_the_account(client):
    _, headers = register_caregiver(client)
    assert client.get("/auth/me", headers=headers).json()["language"] == "en"
    r = client.patch("/auth/me", headers=headers, json={"language": "sw"})
    assert r.status_code == 200 and r.json()["language"] == "sw"
    assert client.get("/auth/me", headers=headers).json()["language"] == "sw"
    assert client.patch("/auth/me", headers=headers, json={"language": "fr"}).status_code == 422
