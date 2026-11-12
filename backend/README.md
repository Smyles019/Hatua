# Hatua backend (FastAPI)

## First-time setup

Needs Docker Desktop (running) and Python 3.14. From the repository root:

```powershell
docker compose up -d                      # PostgreSQL 16 on localhost:5432
cd backend
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env                    # DEV_MODE=true is set for local work
alembic upgrade head                      # create the five tables
python -m app.cli create-admin --name "Your Name" --phone 07XXXXXXXX
```

The model release must exist in `ml/artefacts/release/<MODEL_RELEASE>` (see `ml/`):

```powershell
cd ..\ml
python -m hatua_ml.export 1.1.0           # adds the high-risk cut-off; 1.0.0 stays as it was
```

then set `MODEL_RELEASE=1.1.0` in `backend/.env`. With release 1.0.0 the API still runs,
but splits medium from high risk at a provisional probability of 0.70 and labels results
with `high_threshold_source: "provisional"`.

## Everyday use

```powershell
docker compose up -d                      # from the repository root, if not running
uvicorn app.main:app --reload             # from backend/
python -m pytest -q                       # tests use the separate hatua_test database
```

- Health check: http://127.0.0.1:8000/health
- API docs: http://127.0.0.1:8000/docs (Authorize: username is the phone number)
- Test UI: http://127.0.0.1:8000/ (only with `DEV_MODE=true`)

## Accounts and access

| Role | Gets an account by | Can |
|---|---|---|
| Caregiver | registering (`POST /auth/register`), or enrolment by a CHW | add and see their own children, submit assessments, see results and the CHW's message |
| CHW | an administrator (`POST /admin/users`) | enrol or link caregivers, add children for them, see their medium, high and flagged cases, record outcomes |
| Administrator | the command line (first one), then other administrators | create accounts, link or move caregivers between CHWs, deactivate accounts, usage summary |

Sign in with `POST /auth/login` (phone number and password). Every other route except
`/health` needs the returned token as `Authorization: Bearer <token>`. Phone numbers are
stored as `+2547XXXXXXXX`; `07...`, `2547...` and spaced forms are all accepted.

Accounts are deactivated, never deleted, so a CHW's recorded outcomes keep their reviewer.
A CHW who still has linked caregivers cannot be deactivated until they are moved.

## Endpoints

| Area | Method and path | Who |
|---|---|---|
| Auth | `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `PUT /auth/password` | anyone / signed in |
| Children | `POST /children`, `GET /children`, `GET /children/{id}` | caregiver, CHW, admin |
| | `GET /children/{id}/assessments`, `GET /children/{id}/milestones` | caregiver, CHW, admin |
| Assessments | `GET /assessments/questions?child_id=`, `POST /assessments` | caregiver of the child |
| CHW | `GET /chw/caregivers`, `POST /chw/caregivers`, `POST /chw/caregivers/link` | CHW |
| | `GET /chw/cases`, `POST /chw/cases/{prediction_id}/outcome` | CHW |
| Admin | `POST /admin/users`, `GET /admin/users`, `PATCH /admin/users/{id}` | admin |
| | `PUT /admin/users/{caregiver_id}/chw`, `GET /admin/summary?start=&end=` | admin |

Someone else's child or case answers 404, not 403, so ids cannot be used to probe.

## How an assessment is scored

| Child's age | Method | Questions | Result |
|---|---|---|---|
| 0 to 23 months | Under-24 XGBoost model (`UNDER2_MODEL_DIR`), odd-answer check, SHAP | 2 to 15, chosen by the child's month from the 30-question short form | movement and language with top 3 reasons; thinking and social areas `not_assessed` |
| 24 to 59 months | XGBoost release (`MODEL_RELEASE`), Isolation Forest flag, SHAP domains | the 13-question short form | four domains, top 3 reasons |

If the under-24 model folder is missing, 4 to 23 months use the WHO motor milestone check
(rule-based, up to 6 movement questions, overdue milestones as reasons) and 0 to 3 months
are refused with a message to check from 4 months.

Under 24 months the app does not ask for gestational age yet, so the model assumes a
full-term birth (40 weeks); results record this as `gest_weeks_assumed`. "Don't know" is
left blank for this model, which reads blank as "not asked".

Risk levels for the models: below the screening cut-off is low; between the screening and
high-risk cut-offs is medium; at or above the high-risk cut-off is high. For the milestone
check: no overdue milestone is low, one is medium, two or more is high. Medium, high and
flagged results go to the linked CHW. A `not_assessed` domain never overwrites an earlier
result in the child's milestone summary.

## Database

| Command (repository root) | Effect |
|---|---|
| `docker compose up -d` | Start PostgreSQL |
| `docker compose down` | Stop it; data is kept |
| `docker compose down -v` | Stop it and delete all local data |

Schema changes: edit `app/db/models.py`, then from `backend/` run
`alembic revision --autogenerate -m "describe the change"`, review the generated file in
`migrations/versions/`, and `alembic upgrade head`. The test
`test_migrations_match_the_models_exactly` fails if a model changes without a migration.

Migration 0002 adds `users.is_active` and rewrites phone numbers saved as `07...` into
`+2547...`, so accounts made before it can still sign in.

## Tests

`python -m pytest -q` from `backend/`. Tests need the Docker database but not the survey
data or a trained release: they build a small synthetic release on the fly
(`hatua_ml.synthetic`). The API refuses to serve a synthetic release unless
`DEV_MODE=true`.

## Response time (#20)

With the API running:

```powershell
python scripts/measure_latency.py --runs 100
```

Writes `docs/testing/latency_<date>.csv` and `.md`: round-trip times for both assessment
paths, response sizes, and an estimate of the extra time on Slow 3G and Fast 3G links.

## Running the API in a container

```powershell
$env:JWT_SECRET = python -c "import secrets; print(secrets.token_urlsafe(48))"
docker compose --profile api up -d --build      # API on http://127.0.0.1:8001
```

The container runs with `DEV_MODE=false` (no test UI), applies migrations on start, and
reads the model release from `ml/artefacts` mounted read-only.

## Test UI (throwaway)

A plain page for testing the whole flow before the Flutter app exists. Needs
`DEV_MODE=true`. It signs itself in as a development administrator for setup and signs in
as the chosen caregiver or CHW (password `test123`, which it gives every account it
creates) for the other tabs.

1. **Setup**: "Create demo data" makes a CHW, a linked caregiver and three children
   (about 18, 30 and 48 months). Also: add users, link, add children, usage summary.
2. **Caregiver**: pick a child, answer the questions (or use the Fill buttons), see the result.
3. **CHW**: medium or high risk and flagged results from linked caregivers; record an outcome.
   The caregiver's history then shows the fixed message.
