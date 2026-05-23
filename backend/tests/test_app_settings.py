from unittest.mock import patch

import app_settings


def _settings(password: str = "real-password") -> dict:
    return {
        "media_data_location": {"value": "/media", "env_override": False},
        "prefer_extended": {"value": True, "env_override": False},
        "qbt_hostname": {"value": "http://qbittorrent:8080", "env_override": False},
        "qbt_username": {"value": "admin", "env_override": False},
        "qbt_password": {"value": password, "env_override": False},
        "qbt_path_local": {"value": None, "env_override": False},
        "qbt_path_remote": {"value": None, "env_override": False},
        "qbt_category": {"value": None, "env_override": False},
        "qbt_download_location": {"value": None, "env_override": False},
        "qbt_polling_rate": {"value": 8, "env_override": False},
        "log_level": {"value": "INFO", "env_override": False},
    }


def _save_settings():
    return app_settings.save_settings(
        media_data_location="/media",
        prefer_extended=True,
        qbt_hostname="http://qbittorrent:8080",
        qbt_username="admin",
        qbt_password="real-password",
        qbt_polling_rate=8,
        log_level="INFO",
    )


@patch("app_settings.db")
def test_save_settings_marks_restart_required_when_initial_setup_becomes_complete(mock_db):
    incomplete_settings = _settings()
    incomplete_settings["media_data_location"]["value"] = ""
    complete_settings = _settings()
    mock_db.get_settings.side_effect = [incomplete_settings, _settings(), complete_settings]
    mock_db.get_app_state.return_value = {"initial_setup_complete": False, "restart_required": False}

    result = _save_settings()

    assert result == complete_settings
    mock_db.set_app_state.assert_called_once_with(initial_setup_complete=False, restart_required=True)


@patch("app_settings.db")
def test_save_settings_keeps_initial_setup_pending_when_configuration_is_incomplete(mock_db):
    incomplete_settings = _settings()
    incomplete_settings["qbt_hostname"]["value"] = ""
    mock_db.get_settings.side_effect = [incomplete_settings, _settings(), incomplete_settings]
    mock_db.get_app_state.return_value = {"initial_setup_complete": False, "restart_required": False}

    _save_settings()

    mock_db.set_app_state.assert_called_once_with(initial_setup_complete=False, restart_required=False)


@patch("app_settings.db")
def test_save_settings_marks_restart_required_when_restart_applied_setting_changes(mock_db):
    before = _settings("old-password")
    after = _settings("new-password")
    mock_db.get_settings.side_effect = [before, _settings("old-password"), after]
    mock_db.get_app_state.return_value = {"initial_setup_complete": True, "restart_required": False}

    _save_settings()

    mock_db.set_restart_required.assert_called_once_with(True)


@patch("app_settings.db")
def test_save_settings_does_not_require_restart_for_prefer_extended_only_change(mock_db):
    before = _settings()
    after = _settings()
    after["prefer_extended"]["value"] = False
    mock_db.get_settings.side_effect = [before, _settings(), after]
    mock_db.get_app_state.return_value = {"initial_setup_complete": True, "restart_required": False}

    _save_settings()

    mock_db.set_restart_required.assert_not_called()


@patch("app_settings.db")
def test_save_settings_preserves_stored_db_values_for_env_overridden_fields(mock_db):
    before = _settings()
    before["media_data_location"] = {"value": "/env/media", "env_override": True}
    before["qbt_hostname"] = {"value": "http://env-qbt:8080", "env_override": True}
    after = _settings()
    after["media_data_location"] = {"value": "/env/media", "env_override": True}
    after["qbt_hostname"] = {"value": "http://env-qbt:8080", "env_override": True}
    stored = _settings()
    stored["media_data_location"] = {"value": "/stored/media", "env_override": False}
    stored["qbt_hostname"] = {"value": "http://stored-qbt:8080", "env_override": False}
    mock_db.get_settings.side_effect = [before, stored, after]
    mock_db.get_app_state.return_value = {"initial_setup_complete": True, "restart_required": False}

    app_settings.save_settings(
        media_data_location="/env/media",
        prefer_extended=True,
        qbt_hostname="http://env-qbt:8080",
        qbt_username="admin",
        qbt_password="real-password",
        qbt_polling_rate=8,
        log_level="INFO",
    )

    assert mock_db.save_settings.call_args.kwargs["media_data_location"] == "/stored/media"
    assert mock_db.save_settings.call_args.kwargs["qbt_hostname"] == "http://stored-qbt:8080"
    assert mock_db.get_settings.call_args_list[1].kwargs == {"with_env_overrides": False}
