from typing import Any

import db
from setup_validation import is_initial_setup_configuration_complete

# Changes to these settings only take effect after the backend process restarts.
# prefer_extended is intentionally omitted because download requests read it when they start.
SETTINGS_REQUIRING_RESTART = (
    "media_data_location",
    "qbt_hostname",
    "qbt_username",
    "qbt_password",
    "qbt_path_local",
    "qbt_path_remote",
    "qbt_category",
    "qbt_download_location",
    "qbt_polling_rate",
    "log_level",
)


def get_settings(*, with_env_overrides: bool = True) -> dict | None:
    return db.get_settings(with_env_overrides=with_env_overrides)


def get_setting_value(field: str) -> Any:
    settings = get_settings()
    return _setting_value(settings, field)


def get_stored_setting_value(field: str) -> Any:
    return db.get_stored_setting_value(field)


def is_initial_setup_required() -> bool:
    settings = get_settings()
    return not is_initial_setup_configuration_complete(settings)


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
    settings_before = get_settings()
    stored_settings_before = db.get_settings(with_env_overrides=False) or {}
    submitted_settings = {
        "media_data_location": media_data_location,
        "qbt_hostname": qbt_hostname,
        "qbt_username": qbt_username,
        "qbt_password": qbt_password,
        "prefer_extended": prefer_extended,
        "qbt_path_local": qbt_path_local,
        "qbt_path_remote": qbt_path_remote,
        "qbt_category": qbt_category,
        "qbt_download_location": qbt_download_location,
        "qbt_polling_rate": qbt_polling_rate,
        "log_level": log_level,
    }
    settings_to_save = {
        field: (
            _setting_value(stored_settings_before, field)
            if _setting_env_override(settings_before, field)
            else value
        )
        for field, value in submitted_settings.items()
    }
    db.save_settings(
        **settings_to_save,
    )
    settings_after = get_settings()
    _update_app_state_after_settings_save(settings_before, settings_after)
    return settings_after


def _setting_env_override(settings: dict[str, Any] | None, field: str) -> bool:
    if not settings:
        return False

    field_data = settings.get(field)
    if isinstance(field_data, dict):
        return bool(field_data.get("env_override"))
    return False


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


def _restart_required_setting_changed(
    settings_before: dict[str, Any] | None,
    settings_after: dict[str, Any] | None,
) -> bool:
    return any(
        _setting_value(settings_before, field) != _setting_value(settings_after, field)
        for field in SETTINGS_REQUIRING_RESTART
    )


def _update_app_state_after_settings_save(
    settings_before: dict[str, Any] | None,
    settings_after: dict[str, Any] | None,
):
    current_state = db.get_app_state()
    initial_setup_complete = current_state["initial_setup_complete"]

    if not initial_setup_complete:
        setup_complete_after_save = is_initial_setup_configuration_complete(settings_after)
        db.set_app_state(
            initial_setup_complete=False,
            restart_required=setup_complete_after_save,
        )
        return

    if _restart_required_setting_changed(settings_before, settings_after):
        db.set_restart_required(True)
