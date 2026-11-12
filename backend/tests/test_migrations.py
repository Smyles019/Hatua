"""Migrations build the five-table schema on a clean test database (#10).

Needs the Docker database: docker compose up -d. Uses hatua_test only.
"""
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError, OperationalError

from app.core.config import settings
from app.db.models import Base

BACKEND = Path(__file__).resolve().parents[1]
TABLES = {"users", "children", "caregiver_inputs", "prediction_results", "milestone_summaries"}


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(settings.test_database_url)
    try:
        with eng.connect():
            pass
    except OperationalError:
        pytest.skip("test database not running (docker compose up -d)")
    yield eng
    eng.dispose()


def alembic_config() -> Config:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    cfg.attributes["database_url"] = settings.test_database_url
    return cfg


@pytest.fixture(scope="module")
def migrated(engine):
    """Wipe the test database, then apply every migration."""
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    command.upgrade(alembic_config(), "head")
    return engine


def test_upgrade_creates_the_five_tables(migrated):
    assert TABLES <= set(inspect(migrated).get_table_names())


def test_migrations_match_the_models_exactly(migrated):
    with migrated.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}),
                                Base.metadata)
    assert diff == [], f"models and migrations differ; write a migration: {diff}"


def test_database_refuses_invalid_values(migrated):
    with migrated.connect() as conn:
        with pytest.raises(IntegrityError, match="ck_users_role_valid"):
            conn.execute(text("INSERT INTO users (user_id, full_name, phone_number, "
                              "password_hash, role) VALUES (gen_random_uuid(), 'A', "
                              "'0700000000', 'x', 'superuser')"))
        conn.rollback()


def test_downgrade_removes_everything_and_upgrade_restores_it(migrated):
    cfg = alembic_config()
    command.downgrade(cfg, "base")
    assert not TABLES & set(inspect(migrated).get_table_names())
    command.upgrade(cfg, "head")
    assert TABLES <= set(inspect(migrated).get_table_names())
