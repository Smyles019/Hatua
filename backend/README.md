# Hatua backend (FastAPI)

## First-time setup

Needs Docker Desktop (running) and Python 3.14. From the repository root:

```powershell
docker compose up -d                      # PostgreSQL 16 on localhost:5432
cd backend
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env                    # then edit JWT_SECRET
alembic upgrade head                      # create the five tables
```

## Everyday use

```powershell
docker compose up -d                      # from the repository root, if not running
uvicorn app.main:app --reload             # from backend/
python -m pytest -q                       # tests use the separate hatua_test database
```

Health check: http://127.0.0.1:8000/health

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
