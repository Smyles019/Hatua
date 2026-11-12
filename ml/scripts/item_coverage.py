"""How many milestone items do the under-24 cohorts share? Read-only check."""
import pandas as pd

META = {"ctrycd", "cohort", "cohortn", "subjid", "agedays", "sex", "gagebrth",
        "n_items", "d", "daz", "n_items_gcdg", "d_gcdg", "daz_gcdg"}

df = pd.read_csv("ml/data/raw/childdevdata_under24.csv", low_memory=False)
df = df[df.cohort != "GCDG-ECU"]
items = [c for c in df.columns if c not in META]

# share of each cohort's rows that answered each item
answered = df[items].notna().groupby(df.cohort).mean()
covered = (answered > 0.05)  # item used by the cohort at all
n_cohorts = covered.sum()

print("cohorts:", answered.shape[0], "| total item columns:", len(items))
for k in range(1, answered.shape[0] + 1):
    print(f"items used by >= {k} cohorts: {(n_cohorts >= k).sum()}")

print("\nInstrument prefixes per cohort:")
pref = pd.Series({c: c[:3] for c in items})
for coh, row in covered.iterrows():
    used = pref[row[row].index].value_counts().to_dict()
    print(f"  {coh}: {used}")

top = n_cohorts.sort_values(ascending=False).head(15)
print("\nMost shared items:", top.to_dict())
