"""The CHW's full check report: every question and answer, as data and as a PDF."""
from urllib.parse import urlsplit

from conftest import (PASSWORD, add_child, answers, confirm_email, email_for, login,
                      make_user, new_phone, submit)


def family(client, db_session):
    """A CHW and a linked caregiver who has done one check (all answers "not yet", so the
    hearing and eye questions are "No"). Returns chw headers, caregiver headers, check."""
    _, chw_phone = make_user(db_session, "chw", "Wanjiku")
    chw = login(client, chw_phone)
    phone = new_phone()
    r = client.post("/chw/caregivers", headers=chw,
                    json={"full_name": "Achieng Otieno", "email": email_for(phone),
                          "phone_number": phone, "password": PASSWORD})
    assert r.status_code == 201, r.text
    confirm_email(client, email_for(phone))
    cg = login(client, phone)
    child = add_child(client, cg, 30, name="Imani")
    check = submit(client, cg, child["child_id"], answers(client, cg, child["child_id"], False))
    return chw, cg, check


def test_the_chw_sees_every_question_and_answer(client, db_session):
    chw, _, check = family(client, db_session)
    r = client.get(f"/chw/cases/{check['prediction_id']}/report", headers=chw)
    assert r.status_code == 200, r.text
    rep = r.json()
    assert rep["child"]["first_name"] == "Imani"
    assert rep["caregiver"]["full_name"] == "Achieng Otieno"
    rows = [a for s in rep["sections"] for a in s["answers"]]
    assert rows and all("{name}" not in a["question"] and "Imani" in a["question"] for a in rows)
    assert {a["result"] for a in rows} == {"not_yet"}
    assert rep["counts"]["not_yet"] == len(rows)
    assert [s["domain"] for s in rep["sections"]] == [
        d for d in ("motor", "language", "cognitive", "social_emotional")
        if d in {s["domain"] for s in rep["sections"]}]
    assert rep["screening"] and all(s["result"] == "concern" for s in rep["screening"])


def test_only_the_linked_chw_gets_the_report(client, db_session):
    chw, cg, check = family(client, db_session)
    _, other_phone = make_user(db_session, "chw", "Otieno")
    other = login(client, other_phone)
    path = f"/chw/cases/{check['prediction_id']}"
    assert client.get(path + "/report", headers=other).status_code == 404
    assert client.post(path + "/report-link", headers=other).status_code == 404
    assert client.get(path + "/report", headers=cg).status_code == 403
    assert client.get(path + "/report").status_code == 401


def test_the_pdf_link(client, db_session):
    chw, _, check = family(client, db_session)
    r = client.post(f"/chw/cases/{check['prediction_id']}/report-link", headers=chw)
    assert r.status_code == 200, r.text
    url = urlsplit(r.json()["url"])
    pdf = client.get(f"{url.path}?{url.query}")
    assert pdf.status_code == 200, pdf.text
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF") and len(pdf.content) > 1500
    assert "Imani" in pdf.headers["content-disposition"]
    # The link is for this check only, and a sign-in token is not a report link
    _, _, another = family(client, db_session)
    swapped = url.query.replace(check["prediction_id"], another["prediction_id"])
    assert client.get(f"{url.path}?{swapped}").status_code == 403
    token = chw["Authorization"].split()[1]
    q = f"id={check['prediction_id']}&token={token}"
    assert client.get(f"{url.path}?{q}").status_code == 403
