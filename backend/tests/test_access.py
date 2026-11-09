"""Who may see and do what (#11, #12, #16). Other people's records answer 404, not 403,
so ids cannot be used to probe for children or cases that exist."""
import pytest

from conftest import (PASSWORD, add_child, answers, login, make_user, months_ago, new_phone,
                      register_caregiver, submit)


@pytest.fixture(scope="module")
def world(client, db_session):
    """Two CHWs; caregiver A linked to CHW 1 with a flagged case; caregiver B unlinked."""
    _, p1 = make_user(db_session, "chw")
    _, p2 = make_user(db_session, "chw")
    chw1, chw2 = login(client, p1), login(client, p2)
    phone_a = new_phone()
    client.post("/chw/caregivers", headers=chw1,
                json={"full_name": "A", "phone_number": phone_a, "password": PASSWORD})
    cg_a = login(client, phone_a)
    _, cg_b = register_caregiver(client, "B")
    child_a = add_child(client, cg_a, 40, name="ChildA")["child_id"]
    child_b = add_child(client, cg_b, 40, name="ChildB")["child_id"]
    case = submit(client, cg_a, child_a, answers(client, cg_a, child_a, False))
    _, admin_phone = make_user(db_session, "admin")
    return {"chw1": chw1, "chw2": chw2, "cg_a": cg_a, "cg_b": cg_b, "child_a": child_a,
            "child_b": child_b, "case": case["prediction_id"], "admin": login(client, admin_phone)}


def test_caregiver_sees_only_their_own_children(client, world):
    names = [c["first_name"] for c in client.get("/children", headers=world["cg_b"]).json()]
    assert names == ["ChildB"]
    for path in (f"/children/{world['child_a']}", f"/children/{world['child_a']}/assessments",
                 f"/children/{world['child_a']}/milestones"):
        assert client.get(path, headers=world["cg_b"]).status_code == 404


def test_caregiver_cannot_assess_or_add_a_child_for_someone_else(client, world):
    r = client.get("/assessments/questions", params={"child_id": world["child_a"]},
                   headers=world["cg_b"])
    assert r.status_code == 404
    # caregiver_id in the body is ignored for caregivers: the child is always their own
    other = client.get("/auth/me", headers=world["cg_a"]).json()["user_id"]
    r = client.post("/children", headers=world["cg_b"], json={
        "caregiver_id": other, "first_name": "Sneaky", "date_of_birth": months_ago(30),
        "sex": "male", "location": "X"})
    assert r.status_code == 201
    assert r.json()["caregiver_id"] == client.get("/auth/me", headers=world["cg_b"]).json()["user_id"]


def test_chw_sees_children_of_linked_caregivers_only(client, world):
    names = {c["first_name"] for c in client.get("/children", headers=world["chw1"]).json()}
    assert names == {"ChildA"}
    assert client.get(f"/children/{world['child_b']}", headers=world["chw1"]).status_code == 404
    assert client.get("/children", headers=world["chw2"]).json() == []


def test_chw_does_not_submit_assessments(client, world):
    r = client.get("/assessments/questions", params={"child_id": world["child_a"]},
                   headers=world["chw1"])
    assert r.status_code == 403


def test_cases_and_outcomes_belong_to_the_linked_chw(client, world):
    assert len(client.get("/chw/cases", headers=world["chw1"]).json()) == 1
    assert client.get("/chw/cases", headers=world["chw2"]).json() == []
    r = client.post(f"/chw/cases/{world['case']}/outcome", headers=world["chw2"],
                    json={"outcome": "unreachable"})
    assert r.status_code == 404


def test_role_gates(client, world):
    assert client.get("/chw/cases", headers=world["cg_a"]).status_code == 403
    assert client.get("/admin/users", headers=world["chw1"]).status_code == 403
    assert client.get("/admin/summary", headers=world["cg_a"]).status_code == 403
    assert client.get("/admin/users", headers=world["admin"]).status_code == 200


def test_admin_reads_everything_but_does_not_submit(client, world):
    assert len(client.get("/children", headers=world["admin"]).json()) >= 2
    assert client.get(f"/children/{world['child_a']}/assessments",
                      headers=world["admin"]).status_code == 200
    r = client.get("/assessments/questions", params={"child_id": world["child_a"]},
                   headers=world["admin"])
    assert r.status_code == 403
