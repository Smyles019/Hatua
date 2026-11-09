"""Shared fixtures for the backend tests (#18).

Tests run against the hatua_test database (docker compose up -d) and a small synthetic
model release built on the fly, so they need neither the survey data nor the trained
artefacts. The real release is tested in ml/tests/test_export.py.
"""
import os

# Before anything imports app.core.config: tests always run in development mode, which
# also allows the synthetic release to be served.
os.environ["DEV_MODE"] = "true"

from datetime import date  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.models import User  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services import inference  # noqa: E402

BACKEND = Path(__file__).resolve().parents[1]
PASSWORD = "secret123"


@pytest.fixture(scope="session")
def synthetic_release(tmp_path_factory):
    from hatua_ml.synthetic import build

    root = tmp_path_factory.mktemp("artefacts")
    path = build(root / "release")
    saved = settings.model_dir, settings.model_release
    settings.model_dir, settings.model_release = str(root), path.name
    inference.get_release.cache_clear()
    yield path
    settings.model_dir, settings.model_release = saved
    inference.get_release.cache_clear()


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(settings.test_database_url)
    try:
        with eng.connect():
            pass
    except OperationalError:
        pytest.skip("test database not running (docker compose up -d)")
    yield eng
    eng.dispose()


def migrate_clean(engine):
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    cfg.attributes["database_url"] = settings.test_database_url
    command.upgrade(cfg, "head")


@pytest.fixture(scope="module")
def db_session(engine):
    """A fresh, fully migrated test database for each test module."""
    migrate_clean(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture(scope="module")
def client(db_session, synthetic_release):
    def test_db():
        db = db_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = test_db
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------- helpers ----------

_phone = iter(range(10_000_000, 99_999_999))


def new_phone() -> str:
    return f"07{next(_phone):08d}"


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def register_caregiver(client, name="Achieng") -> tuple[dict, dict]:
    r = client.post("/auth/register", json={"full_name": name, "phone_number": new_phone(),
                                            "password": PASSWORD})
    assert r.status_code == 201, r.text
    return r.json()["user"], auth(r.json()["access_token"])


def make_user(db_session, role: str, name: str | None = None) -> tuple[User, str]:
    """Create a user straight in the database (how the first admin is made). Returns user, phone."""
    phone = "+254" + new_phone()[1:]
    with db_session() as db:
        user = User(full_name=name or role, phone_number=phone,
                    password_hash=hash_password(PASSWORD), role=role)
        db.add(user)
        db.commit()
        return user, phone


def login(client, phone: str) -> dict:
    r = client.post("/auth/login", json={"phone_number": phone, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return auth(r.json()["access_token"])


def months_ago(n: int) -> str:
    today = date.today()
    y, m = divmod(today.year * 12 + today.month - 1 - n, 12)
    return date(y, m + 1, 1).isoformat()


def add_child(client, headers, months: int, name="Imani", **extra) -> dict:
    r = client.post("/children", headers=headers,
                    json={"first_name": name, "date_of_birth": months_ago(months),
                          "sex": "female", "location": "Kibra", **extra})
    assert r.status_code == 201, r.text
    return r.json()


GOOD = {"yes", "few_times_year", "never", "not_at_all", "same_or_less"}


def answers(client, headers, child_id: str, achieved: bool) -> dict:
    r = client.get("/assessments/questions", params={"child_id": child_id}, headers=headers)
    assert r.status_code == 200, r.text
    return {q["item"]: next(o["value"] for o in q["options"]
                            if (o["value"] in GOOD) == achieved and o["value"] != "dont_know")
            for q in r.json()["questions"]}


def submit(client, headers, child_id: str, responses: dict) -> dict:
    r = client.post("/assessments", headers=headers,
                    json={"child_id": child_id, "responses": responses})
    assert r.status_code == 201, r.text
    return r.json()
