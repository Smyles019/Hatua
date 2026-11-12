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

from app.core import mailer  # noqa: E402
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


UNDER2_DIR = BACKEND.parent / "ml" / "artefacts" / "xgboost_under2" / "short_30"


@pytest.fixture(scope="session", autouse=True)
def no_under2_model_by_default(tmp_path_factory):
    """Most tests check the WHO motor fallback for under-24 children, so point the
    under-24 model at an empty folder unless a test asks for it (under2_model)."""
    saved = settings.under2_model_dir
    settings.under2_model_dir = str(tmp_path_factory.mktemp("no_under2"))
    inference.get_under2.cache_clear()
    yield
    settings.under2_model_dir = saved
    inference.get_under2.cache_clear()


@pytest.fixture
def under2_model():
    """The real under-24 model artefacts (ml/artefacts/xgboost_under2/short_30)."""
    if not (UNDER2_DIR / "items_by_month.json").is_file():
        pytest.skip("under-24 model artefacts not built (python -m hatua_ml.models.train_under2)")
    saved = settings.under2_model_dir
    settings.under2_model_dir = str(UNDER2_DIR)
    inference.get_under2.cache_clear()
    yield inference.get_under2()
    settings.under2_model_dir = saved
    inference.get_under2.cache_clear()


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


def email_for(phone: str) -> str:
    """The email the tests give the account with this phone number (any spelling of it)."""
    return f"u{''.join(ch for ch in phone if ch.isdigit())[-9:]}@example.com"


def confirm_email(client, email: str) -> None:
    """Open the newest confirmation link 'sent' to this address (see app.core.mailer)."""
    sent = next(m for m in reversed(mailer.outbox) if m.to == email and "/auth/verify" in m.body)
    link = next(w for w in sent.body.split() if "/auth/verify?token=" in w)
    r = client.get(link.removeprefix(settings.public_base_url))
    assert r.status_code == 200, r.text


def register_caregiver(client, name="Achieng") -> tuple[dict, dict]:
    """Register, confirm the email and sign in. Returns the user and their auth headers."""
    phone = new_phone()
    email = email_for(phone)
    r = client.post("/auth/register", json={"full_name": name, "email": email,
                                            "phone_number": phone, "password": PASSWORD})
    assert r.status_code == 201, r.text
    confirm_email(client, email)
    r = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["user"], auth(r.json()["access_token"])


def make_user(db_session, role: str, name: str | None = None) -> tuple[User, str]:
    """Create a user straight in the database (how the first admin is made). Returns user, phone."""
    phone = "+254" + new_phone()[1:]
    with db_session() as db:
        user = User(full_name=name or role, phone_number=phone, email=email_for(phone),
                    email_verified=True, password_hash=hash_password(PASSWORD), role=role)
        db.add(user)
        db.commit()
        return user, phone


def login(client, phone: str) -> dict:
    """Sign in the account the tests made with this phone number (its email is email_for)."""
    r = client.post("/auth/login", json={"email": email_for(phone), "password": PASSWORD})
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
