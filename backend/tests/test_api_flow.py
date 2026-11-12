"""Whole flow through the API (#12 to #16):
caregiver assessment -> CHW queue -> outcome -> caregiver sees the CHW's message.
"""
from conftest import (PASSWORD, add_child, answers, confirm_email, email_for, login,
                      make_user, months_ago,
                      new_phone,
                      register_caregiver, submit)


def model_questions(q: dict) -> list[dict]:
    """The questions that go to the model, without the hearing and vision red flags."""
    return [x for x in q["questions"] if not x.get("screening")]


def chw_with_caregiver(client, db_session):
    """A CHW who enrols a caregiver during a visit; returns (chw headers, caregiver headers)."""
    _, chw_phone = make_user(db_session, "chw", "Wanjiku")
    chw = login(client, chw_phone)
    phone = new_phone()
    r = client.post("/chw/caregivers", headers=chw,
                    json={"full_name": "Achieng", "email": email_for(phone),
                          "phone_number": phone, "password": PASSWORD})
    assert r.status_code == 201 and r.json()["linked_chw_id"]
    assert r.json()["email_verified"] is False
    # Cannot sign in until the emailed link is opened.
    r = client.post("/auth/login", json={"email": email_for(phone), "password": PASSWORD})
    assert r.status_code == 403
    confirm_email(client, email_for(phone))
    return chw, login(client, phone)


def test_whole_flow(client, db_session):
    chw, cg = chw_with_caregiver(client, db_session)
    child = add_child(client, cg, 48)["child_id"]

    q = client.get("/assessments/questions", params={"child_id": child}, headers=cg).json()
    assert q["method"] == "model" and len(model_questions(q)) == 13
    assert "Imani" in q["questions"][0]["text"]

    low = submit(client, cg, child, answers(client, cg, child, True))
    assert low["risk_level"] == "low" and low["top_reasons"] == [] and not low["sent_to_chw"]
    assert {d["domain"] for d in low["domains"]} == {"motor", "language", "cognitive",
                                                     "social_emotional"}

    high = submit(client, cg, child, answers(client, cg, child, False))
    assert high["risk_level"] in ("medium", "high") and high["sent_to_chw"]
    assert high["top_reasons"] and all(r["question"] for r in high["top_reasons"])
    assert high["model"]["high_threshold_source"] == "release"

    cases = client.get("/chw/cases", headers=chw).json()
    assert [c["prediction_id"] for c in cases] == [high["prediction_id"]]
    assert cases[0]["caregiver"]["full_name"] == "Achieng" and cases[0]["answers"]

    r = client.post(f"/chw/cases/{high['prediction_id']}/outcome", headers=chw,
                    json={"outcome": "refer_to_facility"})
    assert r.status_code == 200
    assert client.get("/chw/cases", headers=chw).json() == []
    assert len(client.get("/chw/cases", params={"include_reviewed": True}, headers=chw).json()) == 1

    latest = client.get(f"/children/{child}/assessments", headers=cg).json()[0]
    assert latest["chw_outcome"] == "refer_to_facility" and latest["caregiver_message"]

    m = client.get(f"/children/{child}/milestones", headers=cg).json()
    assert [h["risk_level"] for h in m["history"]] == ["low", high["risk_level"]]

    mine = client.get("/chw/caregivers", headers=chw).json()
    assert mine[0]["children"] == 1 and mine[0]["open_cases"] == 0


def test_unreachable_shows_the_caregiver_nothing(client, db_session):
    chw, cg = chw_with_caregiver(client, db_session)
    child = add_child(client, cg, 36)["child_id"]
    res = submit(client, cg, child, answers(client, cg, child, False))
    client.post(f"/chw/cases/{res['prediction_id']}/outcome", headers=chw,
                json={"outcome": "unreachable"})
    latest = client.get(f"/children/{child}/assessments", headers=cg).json()[0]
    assert latest["chw_outcome"] == "unreachable" and latest["caregiver_message"] is None


def test_under_24_months_uses_the_motor_milestone_check(client, db_session):
    chw, cg = chw_with_caregiver(client, db_session)
    child = add_child(client, cg, 20, name="Baby")["child_id"]
    q = client.get("/assessments/questions", params={"child_id": child}, headers=cg).json()
    assert q["method"] == "milestone_check" and q["model_version"] == "who-mgrs-2006"
    assert q["age_band"] == "18-23" and len(model_questions(q)) == 6

    ok = submit(client, cg, child, answers(client, cg, child, True))
    assert ok["method"] == "milestone_check" and ok["risk_level"] == "low"
    assert [d["domain"] for d in ok["domains"]] == ["motor"]

    late = dict(answers(client, cg, child, True), who_walk_alone="no", who_stand_alone="no")
    res = submit(client, cg, child, late)
    assert res["risk_level"] == "high" and res["sent_to_chw"]
    assert {r["item"] for r in res["top_reasons"]} == {"who_walk_alone", "who_stand_alone"}
    assert res["top_reasons"][0]["months_past_window"] > 0

    case = client.get("/chw/cases", headers=chw).json()[0]
    assert case["method"] == "milestone_check" and case["model"]["overdue"]


def test_milestone_summary_keeps_older_domains_when_a_check_covers_fewer(client, db_session):
    """A child checked at 20 months (movement only) keeps the other domains from before."""
    from app.db.models import MilestoneSummary
    from sqlalchemy import select

    _, cg = chw_with_caregiver(client, db_session)
    child = add_child(client, cg, 20, name="Neema")["child_id"]
    with db_session() as db:
        db.add(MilestoneSummary(child_id=child, domain_status={"language": "needs_support",
                                                               "motor": "needs_support"}))
        db.commit()
    submit(client, cg, child, answers(client, cg, child, True))
    with db_session() as db:
        s = db.scalar(select(MilestoneSummary).where(MilestoneSummary.child_id == child))
        assert s.domain_status == {"language": "needs_support", "motor": "on_track"}


def test_ages_outside_coverage_are_refused(client, db_session):
    _, cg = chw_with_caregiver(client, db_session)
    newborn = add_child(client, cg, 2, name="Tiny")["child_id"]
    r = client.get("/assessments/questions", params={"child_id": newborn}, headers=cg)
    assert r.status_code == 422 and "4 months" in r.json()["detail"]
    too_old = client.post("/children", headers=cg, json={
        "first_name": "Big", "date_of_birth": "2015-01-01", "sex": "male", "location": "Kibra"})
    assert too_old.status_code == 422


def test_bad_answers_are_refused(client, db_session):
    _, cg = chw_with_caregiver(client, db_session)
    child = add_child(client, cg, 30, name="Baraka")["child_id"]
    ans = answers(client, cg, child, False)
    bad = dict(ans, **{next(iter(ans)): "maybe"})
    assert client.post("/assessments", headers=cg,
                       json={"child_id": child, "responses": bad}).status_code == 422
    missing = dict(list(ans.items())[1:])
    r = client.post("/assessments", headers=cg, json={"child_id": child, "responses": missing})
    assert r.status_code == 422 and r.json()["detail"]["missing"]
    extra = dict(ans, ecd31="yes")  # asked in the full ECDI2030, not in the 13-question form
    r = client.post("/assessments", headers=cg, json={"child_id": child, "responses": extra})
    assert r.status_code == 422 and r.json()["detail"]["unexpected"] == ["ecd31"]


def test_self_registered_caregiver_linked_later_by_a_chw(client, db_session):
    user, cg = register_caregiver(client, "Faith")
    _, chw_phone = make_user(db_session, "chw")
    chw = login(client, chw_phone)
    r = client.post("/chw/caregivers/link", headers=chw,
                    json={"phone_number": user["phone_number"]})
    assert r.status_code == 200 and r.json()["linked_chw_id"]
    _, other_phone = make_user(db_session, "chw")
    r = client.post("/chw/caregivers/link", headers=login(client, other_phone),
                    json={"phone_number": user["phone_number"]})
    assert r.status_code == 409  # already someone else's; only an admin can move them
    # a CHW can add a child for a linked caregiver, not for others
    assert client.post("/children", headers=chw, json={
        "caregiver_id": user["user_id"], "first_name": "Zawadi", "date_of_birth": months_ago(43),
        "sex": "female", "location": "Kibra"}).status_code == 201
    assert [c["first_name"] for c in client.get("/children", headers=cg).json()] == ["Zawadi"]


def test_under_24_months_uses_the_under2_model(client, db_session, under2_model):
    """With the under-24 model loaded, a 9-month-old gets the model's questions and a
    motor and language explanation; cognitive and social-emotional are not assessed and
    never overwrite the milestone summary."""
    from app.db.models import MilestoneSummary
    from sqlalchemy import select

    chw, cg = chw_with_caregiver(client, db_session)
    child = add_child(client, cg, 9, name="Amani")["child_id"]
    q = client.get("/assessments/questions", params={"child_id": child}, headers=cg).json()
    assert q["method"] == "model" and q["model_version"] == under2_model["version"]
    assert q["age_band"] == "6-11" and 1 <= len(model_questions(q)) <= 15
    assert all(x["item"].startswith("ddi") for x in model_questions(q))

    ok = submit(client, cg, child, answers(client, cg, child, True))
    assert ok["method"] == "model" and ok["risk_level"] == "low" and not ok["sent_to_chw"]

    behind = submit(client, cg, child, answers(client, cg, child, False))
    assert behind["risk_level"] in ("medium", "high") and behind["sent_to_chw"]
    status = {d["domain"]: d["status"] for d in behind["domains"]}
    assert status["cognitive"] == status["social_emotional"] == "not_assessed"
    assert behind["top_reasons"] and all(r["question"] for r in behind["top_reasons"])

    with db_session() as db:
        s = db.scalar(select(MilestoneSummary).where(MilestoneSummary.child_id == child))
        assert "cognitive" not in s.domain_status and "social_emotional" not in s.domain_status

    case = client.get("/chw/cases", headers=chw).json()[0]
    assert case["model"]["gest_weeks_assumed"] == 40.0
