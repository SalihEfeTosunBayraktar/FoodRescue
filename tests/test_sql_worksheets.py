"""Keeps the teaching worksheets honest: every .sql file must run against the real schema.

If a student renames a column and forgets a worksheet, this test fails and says which statement broke.
"""
from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path

import pytest

from app.seed import seed_demo

ROOT = Path(__file__).resolve().parents[1]
WORKSHEETS = sorted(ROOT.glob("app/modules/*/sql/*.sql"))

_spec = importlib.util.spec_from_file_location("sqlshell", ROOT / "tools" / "sqlshell.py")
sqlshell = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sqlshell)


@pytest.fixture()
def seeded_connection(tmp_path):
    from dataclasses import replace

    from app.config.settings import load_settings
    from app.main import create_app

    db_file = tmp_path / "ws.db"
    settings = replace(
        load_settings(secret_key="worksheet-secret-key-with-32-bytes!!"),
        database_url=f"sqlite:///{db_file.as_posix()}",
        upload_dir=tmp_path / "uploads",
        maintenance_interval_seconds=0,
    )
    app = create_app(settings)
    with app.state.db.session() as session:
        seed_demo(session)
    app.state.db.engine.dispose()
    connection = sqlite3.connect(db_file, isolation_level=None)
    yield connection
    connection.close()


def test_every_module_has_a_worksheet():
    modules = {p.parent.parent.name for p in WORKSHEETS}
    assert modules == {"identity", "inventory", "reservation", "notification", "impact"}


@pytest.mark.parametrize("path", WORKSHEETS, ids=lambda p: p.parent.parent.name)
def test_worksheet_runs_and_leaves_data_unchanged(path, seeded_connection):
    before = seeded_connection.execute("SELECT (SELECT COUNT(*) FROM users), (SELECT SUM(portions_left) FROM food_items), "
                                       "(SELECT COUNT(*) FROM notifications WHERE read_at IS NULL)").fetchone()
    statements = sqlshell.split_statements(path.read_text(encoding="utf-8"))
    assert len(statements) >= 5
    for statement in statements:
        try:
            seeded_connection.execute(statement).fetchall()
        except sqlite3.Error as exc:  # pragma: no cover - failure path
            pytest.fail(f"{path.name}: {exc}\n--- statement ---\n{statement}")
    after = seeded_connection.execute("SELECT (SELECT COUNT(*) FROM users), (SELECT SUM(portions_left) FROM food_items), "
                                      "(SELECT COUNT(*) FROM notifications WHERE read_at IS NULL)").fetchone()
    assert before == after
