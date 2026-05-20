import os
import sqlite3
from contextlib import contextmanager

from logging_config import get_logger

logger = get_logger(__name__)

DB_PATH = "backend.sqlite3"

SETTINGS_FIELDS = [
    "media_data_location",
    "prefer_extended",
    "qbt_hostname",
    "qbt_username",
    "qbt_password",
    "qbt_path_local",
    "qbt_path_remote",
    "qbt_category",
    "qbt_download_location",
    "qbt_polling_rate",
    "log_level",
]


@contextmanager
def get_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
    finally:
        con.close()


def initialize_db():
    """Initialize the database and create necessary tables."""
    logger.info("Initializing database")
    initialize_app_state_table()
    initialize_settings_table()
    initialize_torrent_download_table()
    initialize_episode_download_table()
    logger.info("Database initialized")


def initialize_app_state_table():
    logger.debug("Creating app_state table if not exists")
    with get_db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS app_state (
                singleton INTEGER PRIMARY KEY CHECK (singleton = 1) DEFAULT 1,
                restart_required INTEGER NOT NULL DEFAULT 0,
                initial_setup_complete INTEGER NOT NULL DEFAULT 0
            )
        """)

        for col, definition in [
            ("restart_required", "INTEGER NOT NULL DEFAULT 0"),
            ("initial_setup_complete", "INTEGER NOT NULL DEFAULT 0"),
        ]:
            try:
                con.execute(f"ALTER TABLE app_state ADD COLUMN {col} {definition}")
                logger.debug("Added %s column to app_state table", col)
            except sqlite3.OperationalError:
                pass  # column already exists

        con.execute("""
            INSERT OR IGNORE INTO app_state (singleton) VALUES (1)
        """)
        con.commit()


def initialize_settings_table():
    logger.debug("Creating settings table if not exists")
    with get_db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                singleton INTEGER PRIMARY KEY CHECK (singleton = 1) DEFAULT 1,
                media_data_location TEXT NOT NULL DEFAULT '',
                prefer_extended INTEGER NOT NULL DEFAULT 1,
                qbt_hostname TEXT NOT NULL DEFAULT '',
                qbt_username TEXT NOT NULL DEFAULT '',
                qbt_password TEXT NOT NULL DEFAULT '',
                qbt_path_mapping TEXT,
                qbt_category TEXT,
                qbt_download_location TEXT,
                qbt_polling_rate INTEGER NOT NULL DEFAULT 10,
                log_level TEXT NOT NULL DEFAULT 'INFO'
            )
        """)

        for col, definition in [
            ("qbt_polling_rate", "INTEGER NOT NULL DEFAULT 10"),
            ("qbt_path_local", "TEXT"),
            ("qbt_path_remote", "TEXT"),
        ]:
            try:
                con.execute(f"ALTER TABLE settings ADD COLUMN {col} {definition}")
                logger.debug("Added %s column to settings table", col)
            except sqlite3.OperationalError:
                pass  # column already exists

        # Migrate existing qbt_path_mapping data into the two new columns
        con.execute("""
            UPDATE settings
            SET
                qbt_path_local = CASE
                    WHEN instr(qbt_path_mapping, ':') > 0
                    THEN substr(qbt_path_mapping, 1, instr(qbt_path_mapping, ':') - 1)
                    ELSE qbt_path_mapping
                END,
                qbt_path_remote = CASE
                    WHEN instr(qbt_path_mapping, ':') > 0
                    THEN substr(qbt_path_mapping, instr(qbt_path_mapping, ':') + 1)
                    ELSE ''
                END
            WHERE qbt_path_local IS NULL AND qbt_path_mapping IS NOT NULL
        """)

        con.execute("""
            INSERT OR IGNORE INTO settings (singleton) VALUES (1)
        """)
        con.commit()


def initialize_torrent_download_table():
    logger.debug("Creating torrent_download table if not exists")
    with get_db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS torrent_download (
                infohash TEXT PRIMARY KEY,
                name TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'downloading',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        for col, definition in [("name", "TEXT NOT NULL DEFAULT ''"), ("status", "TEXT NOT NULL DEFAULT 'downloading'")]:
            try:
                con.execute(f"ALTER TABLE torrent_download ADD COLUMN {col} {definition}")
                logger.debug("Added %s column to torrent_download table", col)
            except Exception:
                pass  # column already exists

        con.commit()


def initialize_episode_download_table():
    logger.debug("Creating episode_download table if not exists")
    with get_db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS episode_download (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ep_id TEXT NOT NULL,
                torrent_infohash TEXT REFERENCES torrent_download(infohash),
                crc32 TEXT NOT NULL,
                prefer_extended INTEGER NOT NULL DEFAULT 0,
                file_path_torrent TEXT,
                file_path_disk TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Migration: remove NOT NULL constraint from torrent_infohash if present
        cols = {row["name"]: row for row in con.execute("PRAGMA table_info(episode_download)").fetchall()}
        torrent_col = cols.get("torrent_infohash")
        if torrent_col and torrent_col["notnull"] == 1:
            logger.info("Migrating episode_download: making torrent_infohash nullable")
            con.execute("""
                CREATE TABLE episode_download_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ep_id TEXT NOT NULL,
                    torrent_infohash TEXT REFERENCES torrent_download(infohash),
                    crc32 TEXT NOT NULL,
                    prefer_extended INTEGER NOT NULL DEFAULT 0,
                    file_path_torrent TEXT,
                    file_path_disk TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            con.execute("INSERT INTO episode_download_new SELECT * FROM episode_download")
            con.execute("DROP TABLE episode_download")
            con.execute("ALTER TABLE episode_download_new RENAME TO episode_download")
            logger.info("Migration complete: torrent_infohash is now nullable")

        con.commit()


# --- app_state helpers ---


def is_restart_required() -> bool:
    with get_db() as con:
        row = con.execute("SELECT restart_required FROM app_state WHERE singleton = 1").fetchone()
        if not row:
            return False
        return bool(row["restart_required"])


def set_restart_required(required: bool):
    with get_db() as con:
        con.execute(
            """
            INSERT INTO app_state (singleton, restart_required)
            VALUES (1, ?)
            ON CONFLICT(singleton) DO UPDATE SET
                restart_required = excluded.restart_required
            """,
            (int(required),),
        )
        con.commit()


def is_initial_setup_complete() -> bool:
    with get_db() as con:
        row = con.execute("SELECT initial_setup_complete FROM app_state WHERE singleton = 1").fetchone()
        if not row:
            return False
        return bool(row["initial_setup_complete"])


def set_initial_setup_complete(complete: bool):
    with get_db() as con:
        con.execute(
            """
            INSERT INTO app_state (singleton, initial_setup_complete)
            VALUES (1, ?)
            ON CONFLICT(singleton) DO UPDATE SET
                initial_setup_complete = excluded.initial_setup_complete
            """,
            (int(complete),),
        )
        con.commit()


# --- torrent_download helpers ---


def create_torrent_download(infohash: str, name: str = "", status: str = "downloading"):
    with get_db() as con:
        con.execute(
            "INSERT OR IGNORE INTO torrent_download (infohash, name, status) VALUES (?, ?, ?)",
            (infohash, name, status),
        )
        con.commit()


def update_torrent_download_status(infohash: str, status: str):
    with get_db() as con:
        con.execute(
            "UPDATE torrent_download SET status = ? WHERE infohash = ?",
            (status, infohash),
        )
        con.commit()


def get_torrent_download(infohash: str) -> dict | None:
    with get_db() as con:
        row = con.execute("SELECT * FROM torrent_download WHERE infohash = ?", (infohash,)).fetchone()
        if not row:
            return None
        return dict(row)


def get_all_torrent_downloads() -> list[dict]:
    with get_db() as con:
        rows = con.execute("SELECT * FROM torrent_download").fetchall()
        return [dict(row) for row in rows]


def delete_torrent_download(infohash: str):
    with get_db() as con:
        con.execute("DELETE FROM torrent_download WHERE infohash = ?", (infohash,))
        con.commit()


def clear_all_downloads():
    with get_db() as con:
        con.execute("DELETE FROM episode_download")
        con.execute("DELETE FROM torrent_download")
        con.commit()


# --- episode_download helpers ---


def create_episode_download(
    ep_id: str,
    crc32: str,
    torrent_infohash: str | None = None,
    prefer_extended: bool = False,
    file_path_torrent: str | None = None,
    file_path_disk: str | None = None,
    status: str = "pending",
) -> int:
    with get_db() as con:
        cur = con.execute(
            """
            INSERT INTO episode_download (
                ep_id, torrent_infohash, crc32, prefer_extended,
                file_path_torrent, file_path_disk, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ep_id,
                torrent_infohash,
                crc32,
                int(prefer_extended),
                file_path_torrent,
                file_path_disk,
                status,
            ),
        )
        con.commit()
        return cur.lastrowid


def get_episode_download(download_id: int) -> dict | None:
    with get_db() as con:
        row = con.execute("SELECT * FROM episode_download WHERE id = ?", (download_id,)).fetchone()
        if not row:
            return None
        return dict(row)


def get_episode_download_by_ep_id(ep_id: str) -> dict | None:
    with get_db() as con:
        row = con.execute("SELECT * FROM episode_download WHERE ep_id = ?", (ep_id,)).fetchone()
        if not row:
            return None
        return dict(row)


def get_episode_downloads_by_torrent(torrent_infohash: str) -> list[dict]:
    with get_db() as con:
        rows = con.execute(
            "SELECT * FROM episode_download WHERE torrent_infohash = ?",
            (torrent_infohash,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_all_episode_downloads() -> list[dict]:
    with get_db() as con:
        rows = con.execute("SELECT * FROM episode_download").fetchall()
        return [dict(row) for row in rows]


def get_episode_downloads_by_status(status: str) -> list[dict]:
    with get_db() as con:
        rows = con.execute("SELECT * FROM episode_download WHERE status = ?", (status,)).fetchall()
        return [dict(row) for row in rows]


def update_episode_download_status(download_id: int, status: str):
    with get_db() as con:
        con.execute(
            "UPDATE episode_download SET status = ? WHERE id = ?",
            (status, download_id),
        )
        con.commit()


def update_episode_download_paths(
    download_id: int,
    file_path_torrent: str | None = None,
    file_path_disk: str | None = None,
):
    with get_db() as con:
        if file_path_torrent is not None:
            con.execute(
                "UPDATE episode_download SET file_path_torrent = ? WHERE id = ?",
                (file_path_torrent, download_id),
            )
        if file_path_disk is not None:
            con.execute(
                "UPDATE episode_download SET file_path_disk = ? WHERE id = ?",
                (file_path_disk, download_id),
            )
        con.commit()


def delete_episode_download(download_id: int):
    with get_db() as con:
        con.execute("DELETE FROM episode_download WHERE id = ?", (download_id,))
        con.commit()


def delete_episode_downloads_by_torrent(torrent_infohash: str):
    with get_db() as con:
        con.execute(
            "DELETE FROM episode_download WHERE torrent_infohash = ?",
            (torrent_infohash,),
        )
        con.commit()


def _get_env_value(field: str):
    """Get environment variable value for a setting field."""
    env_name = field.upper()
    env_val = os.environ.get(env_name)
    if env_val is None:
        return None
    logger.debug("Environment override for %s: %s", field, env_val if field != "qbt_password" else "***")
    if field == "prefer_extended":
        return env_val.lower() in ("1", "true", "yes")
    if field == "qbt_polling_rate":
        try:
            return int(env_val)
        except ValueError:
            logger.warning("Invalid QBT_POLLING_RATE value %s, using default", env_val)
    return env_val


def get_settings() -> dict | None:
    """
    Get settings with environment variable overrides.

    Returns a dict where each setting has:
      - value: the effective value (env override if set, else db value)
      - env_override: True if an environment variable is overriding the db value
    """
    logger.debug("Fetching settings from database")
    with get_db() as con:
        row = con.execute("SELECT * FROM settings WHERE singleton = 1").fetchone()
        if not row:
            logger.warning("No settings found in database")
            return None

        db_settings = dict(row)

    result = {}
    for field in SETTINGS_FIELDS:
        db_value = db_settings.get(field)
        env_value = _get_env_value(field)

        if env_value is not None:
            result[field] = {"value": env_value, "env_override": True}
        else:
            result[field] = {"value": db_value, "env_override": False}

    return result


def get_stored_setting_value(field: str) -> Any:
    if field not in SETTINGS_FIELDS:
        raise ValueError(f"Unknown setting field: {field}")

    with get_db() as con:
        row = con.execute("SELECT * FROM settings WHERE singleton = 1").fetchone()
        if not row:
            return None
        return row[field]


def save_settings(
    media_data_location: str,
    qbt_hostname: str,
    qbt_username: str,
    qbt_password: str,
    prefer_extended: bool = True,
    qbt_path_local: str | None = None,
    qbt_path_remote: str | None = None,
    qbt_category: str | None = None,
    qbt_download_location: str | None = None,
    qbt_polling_rate: int = 8,
    log_level: str = "INFO",
):
    with get_db() as con:
        con.execute(
            """
            INSERT INTO settings (
                singleton, media_data_location, prefer_extended, qbt_hostname,
                qbt_username, qbt_password, qbt_path_local, qbt_path_remote,
                qbt_category, qbt_download_location, qbt_polling_rate, log_level
            ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(singleton) DO UPDATE SET
                media_data_location = excluded.media_data_location,
                prefer_extended = excluded.prefer_extended,
                qbt_hostname = excluded.qbt_hostname,
                qbt_username = excluded.qbt_username,
                qbt_password = excluded.qbt_password,
                qbt_path_local = excluded.qbt_path_local,
                qbt_path_remote = excluded.qbt_path_remote,
                qbt_category = excluded.qbt_category,
                qbt_download_location = excluded.qbt_download_location,
                qbt_polling_rate = excluded.qbt_polling_rate,
                log_level = excluded.log_level
            """,
            (
                media_data_location,
                int(prefer_extended),
                qbt_hostname,
                qbt_username,
                qbt_password,
                qbt_path_local,
                qbt_path_remote,
                qbt_category,
                qbt_download_location,
                qbt_polling_rate,
                log_level,
            ),
        )
        con.commit()
        logger.info("Settings saved successfully")
