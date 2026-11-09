"""Measure API response time (#20).

Run against a running server (uvicorn app.main:app, from backend/):

    python scripts/measure_latency.py                      # 50 rounds, http://127.0.0.1:8000
    python scripts/measure_latency.py --runs 200 --base http://127.0.0.1:8000

It registers a throwaway caregiver, adds a 40-month-old (model path) and an
18-month-old (milestone check), then times, for each round: fetching the questions
and submitting the answers. Results go to docs/testing/latency_<date>.csv and a
summary is printed and written to docs/testing/latency_<date>.md.

What it measures: the full round trip on this machine, so server work (validation,
database, model, SHAP) plus local HTTP. It does not include mobile network time. For
that, the report gives each response's size and the transfer time it adds on slow
links, using the bandwidth and round-trip figures in NETWORKS (planning estimates, not
measurements). Measuring on a real phone network is listed as a limitation.
"""
import argparse
import csv
import json
import random
import statistics
import time
from datetime import date
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "testing"
TARGET_SECONDS = 3.0  # proposal target, end to end

# name: (downlink kbit/s, uplink kbit/s, round trip ms). Chrome DevTools presets.
NETWORKS = {"Slow 3G": (400, 400, 2000), "Fast 3G": (1600, 750, 562)}

GOOD = {"yes", "few_times_year", "never", "not_at_all", "same_or_less"}


def months_ago(n: int) -> str:
    t = date.today()
    y, m = divmod(t.year * 12 + t.month - 1 - n, 12)
    return date(y, m + 1, 1).isoformat()


def setup(c: httpx.Client) -> tuple[dict, list[str]]:
    phone = "07" + "".join(random.choices("0123456789", k=8))
    r = c.post("/auth/register", json={"full_name": "Latency test", "phone_number": phone,
                                       "password": "latency-test"})
    r.raise_for_status()
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    kids = []
    for name, months in (("Model", 40), ("Motor", 18)):
        r = c.post("/children", headers=headers, json={
            "first_name": name, "date_of_birth": months_ago(months), "sex": "female",
            "location": "Latency test"})
        r.raise_for_status()
        kids.append(r.json()["child_id"])
    return headers, kids


def one_round(c: httpx.Client, headers: dict, child: str) -> dict:
    t0 = time.perf_counter()
    q = c.get("/assessments/questions", params={"child_id": child}, headers=headers)
    t1 = time.perf_counter()
    q.raise_for_status()
    body = q.json()
    achieved = random.random() < 0.5
    responses = {x["item"]: next(o["value"] for o in x["options"]
                                 if (o["value"] in GOOD) == achieved and o["value"] != "dont_know")
                 for x in body["questions"]}
    payload = json.dumps({"child_id": child, "responses": responses})
    t2 = time.perf_counter()
    s = c.post("/assessments", headers={**headers, "Content-Type": "application/json"},
               content=payload)
    t3 = time.perf_counter()
    s.raise_for_status()
    return {"method": body["method"], "questions_s": t1 - t0, "submit_s": t3 - t2,
            "questions_bytes": len(q.content), "request_bytes": len(payload),
            "result_bytes": len(s.content), "risk_level": s.json()["risk_level"]}


def transfer_seconds(nbytes: int, kbps: float) -> float:
    return nbytes * 8 / (kbps * 1000)


def summarise(rows: list[dict]) -> str:
    lines = [f"# API response time ({date.today().isoformat()})", "",
             f"{len(rows)} assessments against a local server. Times are full round trips on "
             "the test machine (server work plus local HTTP), in seconds.", "",
             "| Path | Step | Median | 95th percentile | Max |", "|---|---|---|---|---|"]
    for method in sorted({r["method"] for r in rows}):
        sub = [r for r in rows if r["method"] == method]
        for step in ("questions_s", "submit_s"):
            v = sorted(r[step] for r in sub)
            p95 = v[min(len(v) - 1, int(round(0.95 * (len(v) - 1))))]
            lines.append(f"| {method} | {step[:-2]} | {statistics.median(v):.3f} | {p95:.3f} | "
                         f"{max(v):.3f} |")
    size = {k: statistics.median(r[k] for r in rows)
            for k in ("questions_bytes", "request_bytes", "result_bytes")}
    lines += ["", "Median sizes: questions response {questions_bytes:.0f} B, answers sent "
              "{request_bytes:.0f} B, result {result_bytes:.0f} B.".format(**size), "",
              "Estimated time added by a slow mobile link for one assessment (fetch questions, "
              "then submit), from the sizes above. Estimates from bandwidth and round-trip "
              "figures, not measured:", "", "| Network | Added seconds | Total with median server "
              f"time | Within {TARGET_SECONDS:.0f} s target |", "|---|---|---|---|"]
    server = statistics.median(r["questions_s"] + r["submit_s"] for r in rows)
    for name, (down, up, rtt) in NETWORKS.items():
        added = ((2 + 2) * rtt / 1000  # new connection (TCP + TLS) then one per request
                 + transfer_seconds(size["questions_bytes"] + size["result_bytes"], down)
                 + transfer_seconds(size["request_bytes"], up))
        total = server + added
        lines.append(f"| {name} | {added:.2f} | {total:.2f} | "
                     f"{'yes' if total <= TARGET_SECONDS else 'no'} |")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--runs", type=int, default=50)
    args = ap.parse_args()

    with httpx.Client(base_url=args.base, timeout=30) as c:
        c.get("/health").raise_for_status()
        headers, kids = setup(c)
        for child in kids:  # warm up: first call loads the model release
            one_round(c, headers, child)
        rows = [one_round(c, headers, kids[i % 2]) for i in range(args.runs)]

    OUT.mkdir(parents=True, exist_ok=True)
    stem = OUT / f"latency_{date.today().isoformat()}"
    with open(stem.with_suffix(".csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    report = summarise(rows)
    stem.with_suffix(".md").write_text(report)
    print(report)
    print(f"written: {stem}.csv and .md")


if __name__ == "__main__":
    main()
