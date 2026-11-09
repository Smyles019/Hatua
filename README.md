# Hatua

Developmental risk prediction and milestone monitoring for children under five in Kenya.
Final-year ICS capstone, Strathmore University.

## Repository layout

| Folder | Contents |
|---|---|
| `data/` | Raw and processed datasets. **Not committed.** See `data/README.md`. |
| `ml/` | Data loading, ECDI2030 scoring, model training (XGBoost risk model, Isolation Forest anomaly flag, SHAP domain explanations), model releases, and the under-24-month WHO motor milestone check. |
| `backend/` | FastAPI service: sign-in and roles, child profiles, assessments, CHW cases and outcomes, administrator endpoints, PostgreSQL access. Includes a throwaway test UI. See `backend/README.md`. |
| `app/` | Flutter Android application. |
| `docs/` | Chapter drafts, diagram sources (PlantUML, Mermaid, draw.io), wireframes and test records. |

## Data sources

| Dataset | Use |
|---|---|
| Kenya DHS 2022 Children's Recode (KEKR8C) | Primary training data, ECDI2030, 24 to 59 months |
| MICS6 Eswatini 2021 and Comoros 2022 | External validation, ECDI2030 |
| WHO Motor Development Study (2006), published windows | Rule-based gross motor check, 4 to 23 months (no dataset needed) |

The childdevdata `gcdg_zaf` (Birth to Twenty) loader remains, but those items are
assessor-administered rather than caregiver-reported, so they are not used for norms.
Under-24-month language, cognitive and social-emotional checks are future work.

## From data to a running system

1. **ML** (from `ml/`): set up the environment and data (below), then

   ```bash
   python -m hatua_ml.features.build_table          # feature table
   python -m hatua_ml.models.train_xgboost          # risk models
   python -m hatua_ml.models.anomaly                # anomaly flaggers
   python -m hatua_ml.export 1.1.0                  # versioned release for the API
   ```

2. **Backend**: follow `backend/README.md` (database, migrations, first administrator,
   `uvicorn`). Point `MODEL_RELEASE` at the release from step 1.

3. **Try it**: open http://127.0.0.1:8000/ for the test UI (development mode), or
   http://127.0.0.1:8000/docs for the API.

## ML setup

```bash
cd ml
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

## Data

Place the raw data files as described in `data/README.md`.

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

Every loaded sample is validated (age range, weights, item coding, target). Tests that need the real survey files are skipped when the files are not present.

Backend tests: `python -m pytest -q` from `backend/` (needs the Docker database only).
