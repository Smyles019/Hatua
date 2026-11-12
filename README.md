# Hatua

Developmental risk prediction and milestone monitoring for children under five, built for
caregivers and community health workers in Kenya.
Final-year ICS capstone, Strathmore University.

## Repository layout

| Folder | Contents |
|---|---|
| `data/` | Raw and processed datasets. **Not committed.** See `data/README.md`. |
| `ml/` | Data loading, ECDI2030 scoring, the 24 to 59 month model (XGBoost risk, Isolation Forest odd-answer check, SHAP domain explanations, versioned releases), the under-24 model (XGBoost on milestone items, odd-answer check, SHAP for movement and language), and the WHO motor milestone fallback. |
| `backend/` | FastAPI service: sign-in and roles, child profiles, assessments routed by age, CHW cases and outcomes, administrator endpoints, PostgreSQL access. Includes a throwaway test UI. See `backend/README.md`. |
| `app/` | Flutter application (Android and web) for caregivers, CHWs and administrators, including offline save and retry of checks. |
| `docs/` | Chapter drafts, diagram sources (PlantUML, Mermaid, draw.io), wireframes and test records (`docs/testing/`). |

## Data sources

| Dataset | Use |
|---|---|
| Kenya DHS 2022 Children's Recode (KEKR8C) | Training data for the 24 to 59 month model, ECDI2030 |
| MICS6 Eswatini 2021 and Comoros 2022 | External validation, ECDI2030 |
| childdevdata (R package, CC BY 4.0): Dutch SMOCC cohort | Training data for the under-24 model, 0 to 23 months |
| WHO Motor Development Study (2006), published windows | Rule-based gross motor check, 4 to 23 months, used only when the under-24 model is not available (no dataset needed) |

The under-24 model learns from Dutch children whose milestones were mostly observed by
clinic staff, while the app asks caregivers. This mismatch, and the lack of Kenyan
under-24 milestone data, are stated limitations. The other childdevdata cohorts used
different instruments and share no questions with SMOCC; adding them needs a manual
milestone crosswalk (future work). Under 24 months, thinking and learning and social and
emotional areas are not assessed.

## From data to a running system

1. **24 to 59 month model** (from `ml/`): set up the environment and data (below), then

   ```bash
   python -m hatua_ml.features.build_table          # feature table
   python -m hatua_ml.models.train_xgboost          # risk models
   python -m hatua_ml.models.anomaly                # odd-answer checks
   python -m hatua_ml.export 1.1.0                  # versioned release for the API
   ```

2. **Under-24 model.** Needs R (4.x) for the export step; the packages install on first run.
   From the repository root:

   ```bash
   Rscript ml/scripts/export_childdevdata.R          # childdevdata cohorts with D-scores
   ```

   Then from `ml/`:

   ```bash
   python -m hatua_ml.features.build_under2_table   # SMOCC table, delay label, split by child
   python -m hatua_ml.models.train_under2           # XGBoost, item reduction (about 10 min)
   python -m hatua_ml.models.explain_under2         # SHAP same-age averages
   python -m hatua_ml.models.under2_release         # questions for each month
   python -m hatua_ml.models.anomaly_under2         # odd-answer check
   ```

   Everything the API needs ends up in `ml/artefacts/xgboost_under2/short_30/`.
   A child is "delayed" when D-score-for-age (daz) is below -1.5; "high" risk lines up
   with daz below -2.

3. **Backend**: follow `backend/README.md` (database, migrations, first administrator,
   `uvicorn`). In `backend/.env`, `MODEL_RELEASE` names the release from step 1 and
   `UNDER2_MODEL_DIR` the folder from step 2. If the under-24 folder is missing, 4 to 23
   months fall back to the WHO motor check and under 4 months are refused.

4. **Try it**: open http://127.0.0.1:8000/ for the test UI (development mode), or
   http://127.0.0.1:8000/docs for the API. For the app, see `app/README.md` or run
   `flutter run` from `app/`.

## ML setup

```bash
cd ml
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

## Data

Place the raw data files as described in `data/README.md`. The under-24 export writes
`data/raw/childdevdata/childdevdata_under24.csv` itself.

To keep the data outside the repository (for example on Google Drive when training on Colab), set `HATUA_DATA_DIR` to the folder that contains `raw/`:

```bash
export HATUA_DATA_DIR=/content/drive/MyDrive/hatua-data     # PowerShell: $env:HATUA_DATA_DIR = "D:\hatua-data"
```

If a file is missing, the loaders raise `DataFileNotFoundError` with the dataset name and the exact path they looked for. File names are case-sensitive on Linux and Colab.

## Loading and tests

From `ml/`:

```bash
python -m hatua_ml.data.load_kdhs     # KDHS 2022 ECD sample summary
python -m hatua_ml.data.load_mics     # MICS6 Eswatini and Comoros summaries
pytest
```

Every loaded sample is validated (age range, weights, item coding, target). Tests that need the real survey files or trained artefacts are skipped when they are not present.

Backend tests: `python -m pytest -q` from `backend/` (needs the Docker database only; the
under-24 tests run when the under-24 artefacts exist).

App tests: `flutter test` from `app/`.

Chapter 5 test cases and the latest results are in `docs/testing/chapter5_test_cases.md`;
API response times are measured with `backend/scripts/measure_latency.py` (results in
`docs/testing/`).
