import sqlite3

import db


def test_initialize_db_creates_app_state_singleton(monkeypatch, tmp_path):
    db_path = tmp_path / "test.sqlite3"
    monkeypatch.setattr(db, "DB_PATH", str(db_path))

    db.initialize_db()

    with sqlite3.connect(db_path) as con:
        row = con.execute("SELECT singleton, restart_required, initial_setup_complete FROM app_state").fetchone()

    assert row == (1, 0, 0)


def test_restart_required_helpers_round_trip_boolean(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.sqlite3"))
    db.initialize_db()

    assert db.is_restart_required() is False

    db.set_restart_required(True)
    assert db.is_restart_required() is True

    db.set_restart_required(False)
    assert db.is_restart_required() is False


def test_app_state_helpers_round_trip_boolean(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.sqlite3"))
    db.initialize_db()

    assert db.get_app_state() == {
        "initial_setup_complete": False,
        "restart_required": False,
    }

    db.set_app_state(initial_setup_complete=True, restart_required=True)

    assert db.get_app_state() == {
        "initial_setup_complete": True,
        "restart_required": True,
    }


def test_initial_setup_complete_helpers_round_trip_boolean(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.sqlite3"))
    db.initialize_db()

    assert db.is_initial_setup_complete() is False

    db.set_initial_setup_complete(True)
    assert db.is_initial_setup_complete() is True

    db.set_initial_setup_complete(False)
    assert db.is_initial_setup_complete() is False
