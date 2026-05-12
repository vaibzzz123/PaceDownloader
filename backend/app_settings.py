from typing import Any

import db


def get_settings() -> dict | None:
    return db.get_settings()


def get_setting_value(field: str) -> Any:
    settings = get_settings()
    return _setting_value(settings, field)


def is_initial_setup_required() -> bool:
    settings = get_settings()
    media_location_value = _setting_value(settings, "media_data_location")
    qbt_hostname_value = _setting_value(settings, "qbt_hostname")
    return not media_location_value or not qbt_hostname_value


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
    db.save_settings(
        media_data_location=media_data_location,
        qbt_hostname=qbt_hostname,
        qbt_username=qbt_username,
        qbt_password=qbt_password,
        prefer_extended=prefer_extended,
        qbt_path_local=qbt_path_local,
        qbt_path_remote=qbt_path_remote,
        qbt_category=qbt_category,
        qbt_download_location=qbt_download_location,
        qbt_polling_rate=qbt_polling_rate,
        log_level=log_level,
    )


# May merge into get_setting_value, but doing so duplicates db calls
# Leaving as is for now
def _setting_value(settings: dict[str, Any] | None, field: str) -> Any:
    if not settings:
        return None

    field_data = settings.get(field)
    if isinstance(field_data, dict):
        value = field_data.get("value")
    else:
        value = field_data

    return value
