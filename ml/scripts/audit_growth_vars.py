"""Audit coverage of growth and birth variables within the ECD module samples used for training."""
import pandas as pd
import pyreadstat

from hatua_ml.config import KDHS_FILE, MICS_FILES

# KDHS 2022: same filter as load_kdhs (ECD module only)
cols = ["ecd21", "b19", "hw70", "hw71", "hw72", "m19", "bord", "b0", "v025"]
k = pd.read_stata(KDHS_FILE, columns=cols, convert_categoricals=False)
k = k[k["ecd21"].notna()]
print(f"KDHS 2022 ECD sample: {len(k):,}")
for z, name in [("hw70", "height-for-age"), ("hw71", "weight-for-age"), ("hw72", "weight-for-height")]:
    print(f"  {name:18} {k[z].between(-600, 600).mean():.1%} valid")
print(f"  {'birth weight':18} {k['m19'].between(500, 6000).mean():.1%} valid")
for c in ["bord", "b0", "v025"]:
    print(f"  {c:18} {k[c].notna().mean():.1%} present")

# MICS6: same filter as load_mics (ECD module, 24+ months)
for country, path in MICS_FILES.items():
    m, _ = pyreadstat.read_sav(str(path), usecols=["EC21", "CAGE", "HAZ2", "WAZ2", "WHZ2", "HH6"])
    m = m[m["EC21"].notna() & (m["CAGE"] >= 24)]
    print(f"\nMICS {country} ECD sample: {len(m):,}")
    for z, name in [("HAZ2", "height-for-age"), ("WAZ2", "weight-for-age"), ("WHZ2", "weight-for-height")]:
        print(f"  {name:18} {m[z].between(-6, 6).mean():.1%} valid")
    print(f"  {'residence (HH6)':18} {m['HH6'].notna().mean():.1%} present")
