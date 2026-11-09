"""Check which ECDI2030 items form ladders (passing a harder item implies passing an easier one).

For every pair within a domain, harder = lower pass rate. Violation rate =
share of children who pass the harder item but fail the easier one.
Under 5% in every source = safe to imply the easier item from the harder one.
"""
import itertools
import pandas as pd

from hatua_ml.config import ROOT
from hatua_ml.data.load_kdhs import load_kdhs
from hatua_ml.data.load_mics import load_mics

DOMAINS = {
    "motor": ["ecd21", "ecd22", "ecd23", "ecd24"],
    "language": ["ecd25", "ecd26", "ecd27", "ecd28", "ecd29"],
    "cognitive": ["ecd30", "ecd31", "ecd32", "ecd33", "ecd34", "ecd35"],
    "social_emotional": ["ecd36", "ecd37", "ecd38", "ecd39", "ecd40"],
}
FORCED = {("ecd26", "ecd27"), ("ecd33", "ecd34")}  # skip patterns make these 0 by construction
BANDS = [(24, 29), (30, 35), (36, 41), (42, 47), (48, 59)]

df = pd.concat([load_kdhs(), load_mics("eswatini"), load_mics("comoros")], ignore_index=True)
print(f"Children: {len(df):,}  ({df.source.value_counts().to_dict()})\n")

# 1. Pass rate by age band
rows = []
for dom, items in DOMAINS.items():
    for it in items:
        r = {"domain": dom, "item": it, "all": df[it].mean()}
        for lo, hi in BANDS:
            r[f"{lo}-{hi}"] = df.loc[df.age_months.between(lo, hi), it].mean()
        rows.append(r)
rates = pd.DataFrame(rows)
print("PASS RATE BY AGE BAND")
print(rates.round(2).to_string(index=False), "\n")

# 2. Pairwise violation rates within each domain
pairs = []
for dom, items in DOMAINS.items():
    for a, b in itertools.combinations(items, 2):
        easy, hard = (a, b) if df[a].mean() >= df[b].mean() else (b, a)
        r = {"domain": dom, "easier": easy, "harder": hard, "forced": (a, b) in FORCED}
        for src, g in [("all", df), *df.groupby("source")]:
            passed_hard = g[(g[hard] == 1) & g[easy].notna()]
            r[f"viol_{src}"] = (passed_hard[easy] == 0).mean()
            if src == "all":
                r["n"] = len(passed_hard)
        pairs.append(r)
pairs = pd.DataFrame(pairs)
viol_cols = [c for c in pairs if c.startswith("viol_") and c != "viol_all"]
pairs["viol_max"] = pairs[viol_cols].max(axis=1)
pairs["safe"] = pairs["viol_max"] < 0.05
print("PAIRWISE VIOLATIONS (harder passed, easier failed)")
print(pairs.sort_values(["domain", "viol_max"]).round(3).to_string(index=False))

out = ROOT / "ml" / "reports"
out.mkdir(parents=True, exist_ok=True)
rates.to_csv(out / "item_pass_rates.csv", index=False)
pairs.to_csv(out / "item_ladder_violations.csv", index=False)
print(f"\nSaved to {out}")
