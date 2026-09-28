# Hatua

Developmental risk prediction and milestone monitoring for children under five in Kenya.
Final-year ICS capstone, Strathmore University.

## Repository layout

| Folder | Contents |
|---|---|
| `data/` | Raw and processed datasets. **Not committed.** See `data/README.md`. |
| `ml/` | Data loading, ECDI2030 scoring, model training (XGBoost, Deep Isolation Forest, SHAP) and under-24-month norms. |
| `backend/` | FastAPI service: authentication, validation, inference endpoint, PostgreSQL access. |
| `app/` | Flutter Android application. |
| `docs/` | Chapter drafts, diagram sources (PlantUML, Mermaid, draw.io) and wireframes. |

## Data sources

| Dataset | Use |
|---|---|
| Kenya DHS 2022 Children's Recode (KEKR8C) | Primary training data, ECDI2030, 24 to 59 months |
| MICS6 Eswatini 2021 and Comoros 2022 | External validation, ECDI2030 |
| childdevdata `gcdg_zaf` (Birth to Twenty) | Indicative under-24-month milestone norms |
| WHO Motor Development Study | Gross motor norms, under 24 months |

## Setup

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
