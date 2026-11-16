"""The full check report (report.build) as a printable PDF, in black and white, for a CHW
to keep, print or take to a referral. Built with fpdf2 and its standard Helvetica font."""
from datetime import date, datetime

from fpdf import FPDF

from app.services.i18n import tr

STATUS = {"on_track": "On track", "needs_support": "Needs more practice",
          "not_assessed": "Not checked at this age"}
RESULT = {"done": "Achieved", "not_yet": "Not yet", "dont_know": "Not sure",
          "concern": "Needs a look", "ok": ""}
# Helvetica covers Latin-1 only; anything else (curly quotes, dashes) is written plainly.
PLAIN = {"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-",
         "—": "-", "…": "...", " ": " "}


def _t(s) -> str:
    s = "" if s is None else str(s)
    for a, b in PLAIN.items():
        s = s.replace(a, b)
    return s.encode("latin-1", "replace").decode("latin-1")


def _day(v) -> str:
    if isinstance(v, str):
        v = datetime.fromisoformat(v)
    return v.strftime("%d %b %Y") if isinstance(v, (date, datetime)) else ""


class _Doc(FPDF):
    footer_text = ""

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.cell(0, 5, _t(self.footer_text), align="L")
        self.cell(0, 5, f"{self.page_no()} / {{nb}}", align="R")


def render(r: dict, lang: str = "en") -> bytes:
    pdf = _Doc(format="A4")
    pdf.set_margins(18, 16, 18)
    pdf.set_auto_page_break(True, margin=18)
    pdf.footer_text = tr("Hatua check report, made {day}. Screening, not a diagnosis.", lang) \
        .replace("{day}", _day(date.today()))
    pdf.add_page()
    w = pdf.epw

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 9, _t(tr("Hatua check report", lang)), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5, _t(tr("For the community health worker. This is a screening result from "
                               "the caregiver's answers, not a diagnosis.", lang)),
                   new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    c, g = r["child"], r["caregiver"]
    growth = c.get("latest_growth") or {}
    measures = ", ".join(x for x in (
        f"{growth['weight_kg']} kg" if growth.get("weight_kg") else "",
        f"{growth['height_cm']} cm" if growth.get("height_cm") else "") if x)
    rows = [
        (tr("Child", lang), f"{c['first_name']}, {r['age_months']} {tr('months', lang)}"),
        (tr("Date of birth", lang), _day(c["date_of_birth"])),
        (tr("Location", lang), c.get("location") or ""),
        (tr("Caregiver", lang), f"{g['full_name']}, {g.get('phone_number') or ''}".strip(", ")),
        (tr("Check done", lang), _day(r["submitted_at"])),
        (tr("Result", lang), r["risk_label"]),
        (tr("Outcome", lang), r.get("outcome_label") or tr("Not recorded yet", lang)),
        (tr("Reasons for special care", lang), ", ".join(c["care_factors"]) or tr("None", lang)),
        (tr("Latest weight and height", lang),
         f"{measures} ({_day(growth['measured_on'])})" if measures else tr("None entered", lang)),
        (tr("Model", lang), r["model"]["version"]),
    ]
    pdf.set_font("Helvetica", "", 10)
    with pdf.table(col_widths=(0.32 * w, 0.68 * w), first_row_as_headings=False,
                   line_height=5.5) as table:
        for k, v in rows:
            row = table.row()
            row.cell(_t(k))
            row.cell(_t(v))
    pdf.ln(4)

    flags = [f"{f['kind_label']}: {f['label']}" for f in r["red_flags"]]
    if r["anomaly_flag"]:
        flags.append(tr("Unusual pattern of answers: check them with the caregiver.", lang))
    _heading(pdf, tr("Flags", lang))
    pdf.set_font("Helvetica", "", 10)
    for f in flags or [tr("No hearing, eye, growth or answer-pattern flags.", lang)]:
        pdf.multi_cell(0, 5.5, _t(("- " if flags else "") + f), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    n = r["counts"]
    pdf.multi_cell(0, 5.5, _t(tr("{done} achieved, {not_yet} not yet, {dont_know} not sure.", lang)
                              .replace("{done}", str(n["done"]))
                              .replace("{not_yet}", str(n["not_yet"]))
                              .replace("{dont_know}", str(n["dont_know"]))),
                   new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    for s in r["sections"]:
        _heading(pdf, f"{s['label']}: {tr(STATUS.get(s['status'], s['status']), lang)}")
        _answers(pdf, w, s["answers"], lang)
    if r["screening"]:
        _heading(pdf, tr("Hearing and eyes", lang))
        _answers(pdf, w, r["screening"], lang)
    return bytes(pdf.output())


def _heading(pdf: FPDF, text: str) -> None:
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 7, _t(text), new_x="LMARGIN", new_y="NEXT")


def _answers(pdf: FPDF, w: float, rows: list[dict], lang: str) -> None:
    pdf.set_font("Helvetica", "", 10)
    with pdf.table(col_widths=(0.08 * w, 0.56 * w, 0.18 * w, 0.18 * w), line_height=5.5) as table:
        head = table.row()
        for h in ("No.", tr("Question", lang), tr("Answer", lang), tr("Counts as", lang)):
            head.cell(_t(h))
        for i, a in enumerate(rows, 1):
            row = table.row()
            row.cell(str(i))
            row.cell(_t(a["question"]))
            row.cell(_t(a["answer_label"]))
            row.cell(_t(tr(RESULT[a["result"]], lang)) if RESULT[a["result"]] else "")
    pdf.ln(4)
