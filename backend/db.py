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

    # Add qbt_polling_rate column if it doesn't exist (for existing databases)
    try:
        cur.execute("ALTER TABLE settings ADD COLUMN qbt_polling_rate INTEGER NOT NULL DEFAULT 10")
        logger.debug("Added qbt_polling_rate column to settings table")
    except sqlite3.OperationalError:
        # Column already exists
        pass

    cur.execute("""
        INSERT OR IGNORE INTO settings (singleton) VALUES (1)
    """)

    # Create torrent_download table
    logger.debug("Creating torrent_download table if not exists")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS torrent_download (
            qbt_torrent_id TEXT PRIMARY KEY,
            torrent_magnet_link TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'pending',
            download_path TEXT,
            total_files INTEGER,
            selected_files INTEGER DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)

    # Create episode_download table
    logger.debug("Creating episode_download table if not exists")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS episode_download (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ep_id INTEGER NOT NULL UNIQUE,
            torrent_magnet_link TEXT NOT NULL,
            qbt_torrent_id TEXT NOT NULL,
            prefer_extended INTEGER NOT NULL DEFAULT 0,
            file_path_torrent TEXT,
            file_path_disk TEXT,
            file_type TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (qbt_torrent_id) REFERENCES torrent_download(qbt_torrent_id)
        )
    """)

    # Create torrent_episode junction table
    logger.debug("Creating torrent_episode table if not exists")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS torrent_episode (
            torrent_id TEXT NOT NULL,
            ep_id INTEGER NOT NULL,
            PRIMARY KEY (torrent_id, ep_id),
            FOREIGN KEY (torrent_id) REFERENCES torrent_download(qbt_torrent_id),
            FOREIGN KEY (ep_id) REFERENCES episode_download(ep_id)
        )
    """)

    # Create indexes for common queries
    cur.execute("CREATE INDEX IF NOT EXISTS idx_episode_download_status ON episode_download(status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_episode_download_qbt_torrent_id ON episode_download(qbt_torrent_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_torrent_download_status ON torrent_download(status)")

    con.commit()
    logger.info("Database initialized")


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
            logger.warning("Invalid QBT_POLLING_RATE value: %s, using default", env_val)
            return None
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
            qbt_polling_rate = excluded.qbt_polling_rate,
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
