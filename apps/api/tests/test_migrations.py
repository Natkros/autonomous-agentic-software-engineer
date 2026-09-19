"""Tests for app.main.run_migrations — real Alembic runs against real
throwaway SQLite databases (not mocked), including a regression test for
a real failure hit deploying this exact change to this project's own
live Render database: every deployment before this one used
`Base.metadata.create_all`, so upgrading a database that already has
every table but no `alembic_version` row must adopt Alembic in place
(stamp), not crash with "relation already exists".
"""
from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, inspect

from app.database import Base
from app.main import run_migrations


@pytest.fixture()
def sqlite_db_url(tmp_path, monkeypatch):
    db_path = tmp_path / "migrations_test.db"
    url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", url)
    # app.config.get_settings() is lru_cache'd — migrations/env.py calls it
    # fresh, but this process may have already cached a different value
    # from an earlier import (conftest.py sets DATABASE_URL to :memory:).
    from app.config import get_settings
    get_settings.cache_clear()
    yield url
    get_settings.cache_clear()


def test_run_migrations_creates_every_table_on_a_fresh_database(sqlite_db_url):
    run_migrations()

    engine = create_engine(sqlite_db_url)
    tables = set(inspect(engine).get_table_names())
    assert {"users", "repositories", "repository_analyses", "tasks", "alembic_version"} <= tables


def test_run_migrations_adopts_a_database_created_by_the_old_create_all_path(sqlite_db_url):
    """Regression test: simulates every pre-Phase-11 deployment's startup
    behavior (`Base.metadata.create_all`) on a fresh database, then runs
    the new `run_migrations()` against it — this must stamp the database
    at head instead of trying (and failing) to re-run the CREATE TABLE
    statements the initial migration also contains.
    """
    engine = create_engine(sqlite_db_url)
    Base.metadata.create_all(bind=engine)
    assert "alembic_version" not in set(inspect(engine).get_table_names())

    run_migrations()  # must not raise

    tables = set(inspect(engine).get_table_names())
    assert "alembic_version" in tables
    with engine.connect() as conn:
        version = conn.exec_driver_sql("SELECT version_num FROM alembic_version").scalar()
    assert version == "eca74b6ad778"


def test_run_migrations_is_idempotent(sqlite_db_url):
    run_migrations()
    run_migrations()  # must not raise the second time either

    engine = create_engine(sqlite_db_url)
    with engine.connect() as conn:
        version = conn.exec_driver_sql("SELECT version_num FROM alembic_version").scalar()
    assert version == "eca74b6ad778"
