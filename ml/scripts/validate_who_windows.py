"""Check the WHO motor windows used below 24 months against open cohort data.

The app's under-24 check (hatua_ml.norms.who_motor) flags a milestone as overdue when it
is not achieved after the end of its WHO window (the 99th percentile age). This script
asks, for children in three open cohorts (childdevdata, CC BY 4.0):

1. At what age do these children achieve each milestone (fitted median)?
2. How does the share achieved at each age compare with the WHO curve?
3. Of the children older than the end of the WHO window, how many have NOT achieved it,
   i.e. how many would the app flag as overdue?

Data: data/raw/childdevdata (see SOURCE.md). Override with CHILDDEV_DIR.
Outputs: ml/reports/who_windows_validation.csv and who_windows_validation.png

WHO reference: WHO Multicentre Growth Reference Study Group (2006). WHO Motor Development
Study: windows of achievement for six gross motor development milestones. Acta
Paediatrica Suppl 450: 86-95. Medians and 1st/99th percentiles below are from Table 2.
"""
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadr

HERE = Path(__file__).resolve()
ROOT = HERE.parents[2] if HERE.parent.name == "scripts" else HERE.parent
DATA = Path(os.environ.get("CHILDDEV_DIR", ROOT / "data" / "raw" / "childdevdata"))
OUT = Path(os.environ.get("REPORT_DIR", ROOT / "ml" / "reports"))
DAYS_PER_MONTH = 30.4375

# item: (label, 1st percentile, median, 99th percentile), months
WHO = {
    "who_sit": ("Sitting without support", 3.8, 5.9, 9.2),
    "who_stand_assist": ("Standing with assistance", 4.8, 7.4, 11.4),
    "who_crawl": ("Hands-and-knees crawling", 5.2, 8.3, 13.5),
    "who_walk_assist": ("Walking with assistance", 5.9, 9.0, 13.7),
    "who_stand_alone": ("Standing alone", 6.9, 10.8, 16.9),
    "who_walk_alone": ("Walking alone", 8.2, 12.0, 17.6),
}

# Closest item in each cohort (cohort, instrument, item). Labels from the dscore item table.
MAPPING = {
    "who_sit": [("zaf", "Griffiths", "grigmd017"),       # can be left sitting on the floor
                ("nld_smocc", "Van Wiechen", "ddigmd063"),  # sits stably without support
                ("col_lt42m", "WHO MGRS items", "mdsgmd001"),
                ("col_lt42m", "ASQ-3 (caregiver)", "aqigmc016")],
    # South Africa's Bayley "stands up by furniture" is left out: 77% pass it at 4 to 5
    # months, which is not the WHO milestone (likely a different item definition).
    "who_stand_assist": [("nld_smocc", "Van Wiechen", "ddigmm065"),  # pulls up to standing
                         ("col_lt42m", "WHO MGRS items", "mdsgmd003"),
                         ("col_lt42m", "ASQ-3 (caregiver)", "aqigmc018")],
    "who_crawl": [("zaf", "Griffiths", "grigmd022"),     # creeps on hands and knees
                  ("nld_smocc", "Van Wiechen", "ddigmm066"),  # crawls, abdomen off the floor
                  ("col_lt42m", "WHO MGRS items", "mdsgmd002")],
    "who_walk_assist": [("zaf", "Bayley I", "by1pdd042"),  # walks with help
                        ("nld_smocc", "Van Wiechen", "ddigmm067"),  # walks holding furniture
                        ("col_lt42m", "WHO MGRS items", "mdsgmd004"),
                        ("col_lt42m", "ASQ-3 (caregiver)", "aqigmc023")],
    "who_stand_alone": [("zaf", "Bayley I", "by1pdd045"),
                        ("col_lt42m", "WHO MGRS items", "mdsgmd005")],
    "who_walk_alone": [("zaf", "Bayley I", "by1pdd046"),
                       ("nld_smocc", "Van Wiechen", "ddigmd068"),
                       ("col_lt42m", "WHO MGRS items", "mdsgmd006"),
                       ("col_lt42m", "ASQ-3 (caregiver)", "aqigmc026")],
}
COHORTS = {"zaf": "South Africa", "nld_smocc": "Netherlands", "col_lt42m": "Colombia"}
Z99 = 2.3263


def phi(x):
    return 0.5 * (1 + np.vectorize(math.erf)(np.asarray(x) / math.sqrt(2)))


def who_curve(item, age):
    """Share expected to have achieved the milestone by `age`: log-normal through the
    WHO median and the 1st to 99th percentile window."""
    _, p1, med, p99 = WHO[item]
    sigma = (math.log(p99) - math.log(p1)) / (2 * Z99)
    return phi((np.log(age) - math.log(med)) / sigma)


def fit_probit(age, passed, iters=50):
    """P(pass) = Phi(a + b * log(age)), fitted by Newton-Raphson. Returns (a, b) or None."""
    x = np.column_stack([np.ones_like(age), np.log(age)])
    beta = np.zeros(2)
    for _ in range(iters):
        eta = x @ beta
        p = np.clip(phi(eta), 1e-9, 1 - 1e-9)
        dens = np.exp(-eta ** 2 / 2) / math.sqrt(2 * math.pi)
        w = dens ** 2 / (p * (1 - p))
        z = eta + (passed - p) / np.maximum(dens, 1e-12)
        xtw = x.T * w
        try:
            new = np.linalg.solve(xtw @ x, xtw @ z)
        except np.linalg.LinAlgError:
            return None
        if np.max(np.abs(new - beta)) < 1e-8:
            beta = new
            break
        beta = new
    return beta if beta[1] > 0 else None


def fitted_median(age, passed):
    beta = fit_probit(age, passed)
    return None if beta is None else math.exp(-beta[0] / beta[1])


def bootstrap_median(df, n=300, seed=0):
    """95% interval for the fitted median, resampling children (not visits)."""
    rng = np.random.default_rng(seed)
    kids = df["subjid"].unique()
    groups = {k: g for k, g in df.groupby("subjid")}
    meds = []
    for _ in range(n):
        s = pd.concat([groups[k] for k in rng.choice(kids, len(kids))])
        m = fitted_median(s["age"].to_numpy(), s["pass"].to_numpy())
        if m is not None and 0 < m < 60:
            meds.append(m)
    return (np.percentile(meds, 2.5), np.percentile(meds, 97.5)) if len(meds) > n / 2 else (None, None)


def load(cohort):
    name = f"gcdg_{cohort}"
    df = pyreadr.read_r(str(DATA / f"{name}.rda"))[name].copy()
    df["age"] = df["agedays"].astype(float) / DAYS_PER_MONTH
    return df


def main():
    data = {c: load(c) for c in COHORTS}
    rows, curves = [], []
    for item, sources in MAPPING.items():
        label, p1, med, p99 = WHO[item]
        for cohort, instrument, col in sources:
            d = data[cohort][["subjid", "age", col]].dropna().rename(columns={col: "pass"})
            d = d[d["age"] > 0].astype({"pass": float})
            age, passed = d["age"].to_numpy(), d["pass"].to_numpy().astype(float)
            m = fitted_median(age, passed)
            lo, hi = bootstrap_median(d) if m is not None else (None, None)
            # Only trust a median the observed ages bracket.
            in_range = m is not None and age.min() <= m <= age.max()
            past = d[d["age"] > p99]
            rows.append({
                "milestone": label, "who_item": item, "cohort": COHORTS[cohort],
                "instrument": instrument, "item": col,
                "visits": len(d), "children": d["subjid"].nunique(),
                "age_from": round(age.min(), 1), "age_to": round(age.max(), 1),
                "who_median": med, "cohort_median": round(m, 1) if in_range else None,
                "median_ci_low": round(lo, 1) if in_range and lo else None,
                "median_ci_high": round(hi, 1) if in_range and hi else None,
                "who_window_end": p99,
                "older_than_window": len(past),
                # The app would flag these children as overdue.
                "not_achieved_past_window_pct": round(100 * (1 - past["pass"].mean()), 1)
                if len(past) else None,
                # Observed minus WHO-expected share achieved, averaged over visits.
                "gap_vs_who_pct_points": round(100 * float(np.mean(passed - who_curve(item, age))), 1),
            })
            d = d.assign(bin=pd.cut(d["age"], np.arange(0, 25, 1.0)))
            for b, g in d.groupby("bin", observed=True):
                if len(g) >= 10:
                    curves.append({"who_item": item, "cohort": COHORTS[cohort],
                                   "instrument": instrument, "age": b.mid,
                                   "share": g["pass"].mean(), "n": len(g)})
    res = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    res.to_csv(OUT / "who_windows_validation.csv", index=False)
    plot(pd.DataFrame(curves), OUT / "who_windows_validation.png")
    rule = app_rule_on_colombia(data["col_lt42m"])
    rule.to_csv(OUT / "who_rule_flag_rate_colombia.csv", index=False)
    pd.set_option("display.width", 200)
    print("App rule applied to Colombian children (share flagged medium or high):")
    print(rule.to_string(index=False), "\n")
    print(res[["milestone", "cohort", "instrument", "children", "age_from", "age_to", "who_median",
               "cohort_median", "median_ci_low", "median_ci_high", "older_than_window",
               "not_achieved_past_window_pct", "gap_vs_who_pct_points"]].to_string(index=False))


# Colombia recorded the six WHO MGRS milestones themselves, so the app's exact rule can be
# applied to each child: overdue = not achieved after the 99th percentile age (crawling never
# counts); 0 overdue = low, 1 = medium, 2 or more = high.
COLOMBIA_WHO_ITEMS = {"who_sit": "mdsgmd001", "who_crawl": "mdsgmd002",
                      "who_stand_assist": "mdsgmd003", "who_walk_assist": "mdsgmd004",
                      "who_stand_alone": "mdsgmd005", "who_walk_alone": "mdsgmd006"}


def app_rule_on_colombia(df):
    cols = list(COLOMBIA_WHO_ITEMS.values())
    d = df[df[cols].notna().any(axis=1) & df["age"].between(4, 24, inclusive="left")]
    out = []
    for _, r in d.iterrows():
        overdue = sum(1 for item, col in COLOMBIA_WHO_ITEMS.items()
                      if item != "who_crawl" and r["age"] > WHO[item][3] and r[col] == 0)
        out.append({"age": r["age"], "risk": "low" if overdue == 0 else
                    "medium" if overdue == 1 else "high"})
    res = pd.DataFrame(out)
    res["band"] = pd.cut(res["age"], [4, 6, 12, 18, 24], right=False,
                         labels=["4-5", "6-11", "12-17", "18-23"])
    table = (res.groupby("band", observed=True)["risk"]
             .agg(children="size", flagged_pct=lambda s: round(100 * (s != "low").mean(), 1))
             .reset_index())
    total = {"band": "all", "children": len(res),
             "flagged_pct": round(100 * (res["risk"] != "low").mean(), 1)}
    return pd.concat([table, pd.DataFrame([total])], ignore_index=True)


def plot(curves, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Black and white for the report: one marker per cohort, WHO curve as a line.
    marks = {"South Africa": {"Griffiths": "o", "Bayley I": "D"},
             "Netherlands": {"Van Wiechen": "s"},
             "Colombia": {"WHO MGRS items": "^", "ASQ-3 (caregiver)": "^"}}
    fig, axes = plt.subplots(2, 3, figsize=(11, 6.5), sharey=True)
    for ax, (item, (label, p1, med, p99)) in zip(axes.flat, WHO.items()):
        ages = np.linspace(2, 24, 200)
        ax.plot(ages, who_curve(item, ages), color="black", lw=1.5, label="WHO")
        ax.axvline(p99, color="black", ls=":", lw=1)
        c = curves[curves["who_item"] == item]
        for (cohort, instrument), g in c.groupby(["cohort", "instrument"]):
            filled = "caregiver" not in instrument
            ax.plot(g["age"], g["share"], marks[cohort][instrument], ms=5, color="black",
                    mfc="black" if filled else "white",
                    label=f"{cohort}, {instrument}")
        ax.set_title(label, fontsize=10)
        ax.set_xlim(2, 24)
        ax.set_ylim(-0.02, 1.02)
        ax.set_xlabel("Age (months)")
    for ax in axes[:, 0]:
        ax.set_ylabel("Share achieved")
    handles, labels = {}, {}
    for ax in axes.flat:
        for h, l in zip(*ax.get_legend_handles_labels()):
            handles.setdefault(l, h)
    fig.legend(handles.values(), handles.keys(), loc="lower center", ncol=4, fontsize=8,
               frameon=False)
    fig.suptitle("WHO motor windows vs open cohort data (dotted line: end of WHO window)",
                 fontsize=11)
    fig.tight_layout(rect=(0, 0.08, 1, 0.96))
    fig.savefig(path, dpi=200)


if __name__ == "__main__":
    main()
