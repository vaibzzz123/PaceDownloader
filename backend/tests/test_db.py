import sqlite3

import pytest

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


def test_get_settings_can_return_sqlite_values_without_env_overrides(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.sqlite3"))
    monkeypatch.setenv("MEDIA_DATA_LOCATION", "/env/media")
    db.initialize_db()
    db.save_settings(
        media_data_location="/stored/media",
        qbt_hostname="http://stored-qbt:8080",
        qbt_username="admin",
        qbt_password="secret",
        qbt_polling_rate=8,
        log_level="INFO",
    )

    stored = db.get_settings(with_env_overrides=False)
    effective = db.get_settings()

    assert stored is not None
    assert stored["media_data_location"] == {
        "value": "/stored/media",
        "env_override": False,
    }
    assert effective is not None
    assert effective["media_data_location"] == {
        "value": "/env/media",
        "env_override": True,
    }


def test_get_settings_rejects_positional_with_env_overrides_argument():
    with pytest.raises(TypeError):
        db.get_settings(False)


def test_invalid_qbt_polling_rate_env_falls_back_to_stored_value(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.sqlite3"))
    monkeypatch.setenv("QBT_POLLING_RATE", "definitely-not-an-int")
    db.initialize_db()
    db.save_settings(
        media_data_location="/media",
        qbt_hostname="http://qbittorrent:8080",
        qbt_username="admin",
        qbt_password="secret",
        qbt_polling_rate=12,
        log_level="INFO",
    )

    settings = db.get_settings()

    assert settings is not None
    assert settings["qbt_polling_rate"] == {
        "value": 12,
        "env_override": False,
    }


def test_download_lists_are_newest_first_with_deterministic_ties(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.sqlite3"))
    db.initialize_db()

    db.create_torrent_download("z-hash", name="Older")
    db.create_torrent_download("b-hash", name="Newest B")
    db.create_torrent_download("a-hash", name="Newest A")
    db.create_episode_download(ep_id="9", crc32="00000009")
    db.create_episode_download(ep_id="11", crc32="00000011")
    db.create_episode_download(ep_id="100", crc32="00000100")

    with db.get_db() as con:
        con.execute("UPDATE torrent_download SET created_at = '2026-07-23 12:00:00' WHERE infohash = 'z-hash'")
        con.execute("UPDATE torrent_download SET created_at = '2026-07-24 12:00:00' WHERE infohash IN ('a-hash', 'b-hash')")
        con.execute("UPDATE episode_download SET created_at = '2026-07-23 12:00:00' WHERE ep_id = '9'")
        con.execute("UPDATE episode_download SET created_at = '2026-07-24 12:00:00' WHERE ep_id IN ('11', '100')")
        con.commit()

    assert [torrent["infohash"] for torrent in db.get_all_torrent_downloads()] == [
        "a-hash",
        "b-hash",
        "z-hash",
    ]
    assert [episode["ep_id"] for episode in db.get_all_episode_downloads()] == [
        "100",
        "11",
        "9",
    ]
