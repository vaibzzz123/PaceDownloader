"""Settings repository for database access."""

import os
from typing import Any

from db import con, cur, SETTINGS_FIELDS
from logging_config import get_logger

logger = get_logger(__name__)


class SettingsRepository:
    """Repository for settings database operations."""

    def _get_env_value(self, field: str) -> Any | None:
        """Get environment variable value for a setting field."""
        env_name = field.upper()
        env_val = os.environ.get(env_name)
        if env_val is None:
            return None
        logger.debug(
            "Environment override for %s: %s",
            field,
            env_val if field != "qbt_password" else "***",
        )
        if field == "prefer_extended":
            return env_val.lower() in ("1", "true", "yes")
        if field == "qbt_polling_rate":
            try:
                return int(env_val)
            except ValueError:
                logger.warning("Invalid QBT_POLLING_RATE value: %s, using default", env_val)
                return None
        return env_val

    def get_settings(self) -> dict | None:
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
            env_value = self._get_env_value(field)

            if env_value is not None:
                result[field] = {"value": env_value, "env_override": True}
            else:
                result[field] = {"value": db_value, "env_override": False}

        return result

    def get_setting(self, field: str) -> Any | None:
        """
        Get a single setting value.

        Returns the effective value (env override if set, else db value).
        """
        if field not in SETTINGS_FIELDS:
            logger.warning("Unknown setting field: %s", field)
            return None

        settings = self.get_settings()
        if settings and field in settings:
            return settings[field]["value"]
        return None

    def save_settings(
        self,
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
    ) -> None:
        """Save settings to the database."""
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
