# Data

Nothing in this folder is committed except this README and empty folders.
DHS and MICS terms of use forbid redistributing the data.

Place files as follows:

```
data/raw/kdhs_2022/KEKR8CFL.DTA          # from KEKR8CDT.zip
data/raw/mics/eswatini/ch.sav            # Eswatini MICS6 2021, children under five file
data/raw/mics/comoros/ch.sav             # Comoros MICS6 2022, children under five file
data/raw/childdevdata/gcdg_zaf.rda       # from childdevdata_1.1.0/data/
data/raw/childdevdata/gcdg_nld_smocc.rda # optional reference
```

`interim/` holds intermediate outputs. `processed/` holds model-ready tables.

## Sources and citation

- ICF. Kenya Demographic and Health Survey 2022. The DHS Program.
- UNICEF. Multiple Indicator Cluster Surveys (Eswatini 2021, Comoros 2022).
- van Buuren S, et al. childdevdata R package (CC BY 4.0).
  Birth to Twenty: Richter L, et al. Int J Epidemiol. 2007;36:504-511.
