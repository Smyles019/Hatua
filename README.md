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
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r ml/requirements.txt
```

Place the raw data files as described in `data/README.md`, then:

```bash
cd ml
python -m hatua_ml.data.load_kdhs     # prints a summary of the KDHS ECD sample
```
