import os
import sqlite3

from logging_config import get_logger

logger = get_logger(__name__)

con = sqlite3.connect("backend.sqlite3")
cur = con.cursor()

SETTINGS_FIELDS = [
    "media_data_location",
    "prefer_extended",
    "qbt_hostname",
    "qbt_username",
    "qbt_password",
    "qbt_path_mapping",
    "qbt_category",
    "qbt_download_location",
    "qbt_polling_rate",
    "log_level",
]


def initialize_db():
    """Initialize the database and create necessary tables."""
    logger.info("Initializing database")
    initialize_settings_table()
    initialize_torrent_download_table()
    initialize_episode_download_table()
    logger.info("Database initialized")


def initialize_settings_table():
    logger.debug("Creating settings table if not exists")
    cur.execute("""
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
    
    try:
        cur.execute("ALTER TABLE settings ADD COLUMN qbt_polling_rate INTEGER NOT NULL DEFAULT 10")
        logger.debug("Added qbt_polling_rate column to settings table")
    except sqlite3.OperationalError:
        # Column already exists
        pass
    
    cur.execute("""
        INSERT OR IGNORE INTO settings (singleton) VALUES (1)
    """)
    con.commit()


def initialize_torrent_download_table():
    logger.debug("Creating torrent_download table if not exists")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS torrent_download (
            infohash TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    con.commit()


def initialize_episode_download_table():
    logger.debug("Creating episode_download table if not exists")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS episode_download (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ep_id TEXT NOT NULL,
            torrent_infohash TEXT NOT NULL REFERENCES torrent_download(infohash),
            crc32 TEXT NOT NULL,
            prefer_extended INTEGER NOT NULL DEFAULT 0,
            file_path_torrent TEXT,
            file_path_disk TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    con.commit()


# --- torrent_download helpers ---


def create_torrent_download(infohash: str):
    cur.execute(
        "INSERT OR IGNORE INTO torrent_download (infohash) VALUES (?)",
        (infohash,),
    )
    con.commit()


def get_torrent_download(infohash: str) -> dict | None:
    cur.execute("SELECT * FROM torrent_download WHERE infohash = ?", (infohash,))
    row = cur.fetchone()
    if not row:
        return None
    columns = [desc[0] for desc in cur.description]
    return dict(zip(columns, row))


def delete_torrent_download(infohash: str):
    cur.execute("DELETE FROM torrent_download WHERE infohash = ?", (infohash,))
    con.commit()


# --- episode_download helpers ---


def create_episode_download(
    ep_id: str,
    torrent_infohash: str,
    crc32: str,
    prefer_extended: bool = False,
    file_path_torrent: str | None = None,
    file_path_disk: str | None = None,
    status: str = "pending",
) -> int:
    cur.execute(
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
    cur.execute("SELECT * FROM episode_download WHERE id = ?", (download_id,))
    row = cur.fetchone()
    if not row:
        return None
    columns = [desc[0] for desc in cur.description]
    return dict(zip(columns, row))


def get_episode_downloads_by_torrent(torrent_infohash: str) -> list[dict]:
    cur.execute(
        "SELECT * FROM episode_download WHERE torrent_infohash = ?",
        (torrent_infohash,),
    )
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in rows]


def get_episode_downloads_by_status(status: str) -> list[dict]:
    cur.execute("SELECT * FROM episode_download WHERE status = ?", (status,))
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in rows]


def update_episode_download_status(download_id: int, status: str):
    cur.execute(
        "UPDATE episode_download SET status = ? WHERE id = ?",
        (status, download_id),
    )
    con.commit()


def update_episode_download_paths(
    download_id: int,
    file_path_torrent: str | None = None,
    file_path_disk: str | None = None,
):
    if file_path_torrent is not None:
        cur.execute(
            "UPDATE episode_download SET file_path_torrent = ? WHERE id = ?",
            (file_path_torrent, download_id),
        )
    if file_path_disk is not None:
        cur.execute(
            "UPDATE episode_download SET file_path_disk = ? WHERE id = ?",
            (file_path_disk, download_id),
        )
    con.commit()


def delete_episode_download(download_id: int):
    cur.execute("DELETE FROM episode_download WHERE id = ?", (download_id,))
    con.commit()


def delete_episode_downloads_by_torrent(torrent_infohash: str):
    cur.execute(
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
    cur.execute("SELECT * FROM settings WHERE singleton = 1")
    row = cur.fetchone()
    if not row:
        logger.warning("No settings found in database")
        return None

    columns = [desc[0] for desc in cur.description]
    db_settings = dict(zip(columns, row))

    result = {}
    for field in SETTINGS_FIELDS:
        db_value = db_settings.get(field)
        env_value = _get_env_value(field)

        if env_value is not None:
            result[field] = {"value": env_value, "env_override": True}
        else:
            result[field] = {"value": db_value, "env_override": False}

    return result


def save_settings(
    media_data_location: str,
    qbt_hostname: str,
    qbt_username: str,
    qbt_password: str,
    prefer_extended: bool = True,
    qbt_path_mapping: str | None = None,
    qbt_category: str | None = None,
    qbt_download_location: str | None = None,
    qbt_polling_rate: int = 10,
    log_level: str = "INFO",
):
    cur.execute(
        """
        INSERT INTO settings (
            singleton, media_data_location, prefer_extended, qbt_hostname,
            qbt_username, qbt_password, qbt_path_mapping, qbt_category,
            qbt_download_location, qbt_polling_rate, log_level
        ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(singleton) DO UPDATE SET
            media_data_location = excluded.media_data_location,
            prefer_extended = excluded.prefer_extended,
            qbt_hostname = excluded.qbt_hostname,
            qbt_username = excluded.qbt_username,
            qbt_password = excluded.qbt_password,
            qbt_path_mapping = excluded.qbt_path_mapping,
            qbt_category = excluded.qbt_category,
            qbt_download_location = excluded.qbt_download_location,
            log_level = excluded.log_level
        """,
        (
            media_data_location,
            int(prefer_extended),
            qbt_hostname,
            qbt_username,
            qbt_password,
            qbt_path_mapping,
            qbt_category,
            qbt_download_location,
            qbt_polling_rate,
            log_level,
        ),
    )
    con.commit()
    logger.info("Settings saved successfully")
