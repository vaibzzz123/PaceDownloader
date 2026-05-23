import asyncio
from unittest.mock import patch

from models import SettingsSaveRequest, SetupQbittorrentValidationRequest


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


def _save_request(qbt_password: str = "********") -> SettingsSaveRequest:
    return SettingsSaveRequest(
        media_data_location="/media",
        prefer_extended=True,
        qbt_hostname="http://qbittorrent:8080",
        qbt_username="admin",
        qbt_password=qbt_password,
        qbt_polling_rate=8,
        log_level="INFO",
    )


@patch("api.app_settings")
def test_get_settings_route_masks_qbittorrent_password(mock_app_settings):
    from api import get_settings_route

    mock_app_settings.get_settings.return_value = _settings("real-password")

    result = get_settings_route()

    assert result.qbt_password.value == "********"


@patch("api.app_settings")
def test_save_settings_route_preserves_password_when_mask_is_submitted(mock_app_settings):
    from api import save_settings_route

    mock_app_settings.get_stored_setting_value.return_value = "real-password"
    mock_app_settings.save_settings.return_value = _settings("real-password")

    result = save_settings_route(_save_request())

    assert mock_app_settings.save_settings.call_args.kwargs["qbt_password"] == "real-password"
    assert result.qbt_password.value == "********"


@patch("api.app_settings")
def test_save_settings_route_saves_new_password_when_changed(mock_app_settings):
    from api import save_settings_route

    mock_app_settings.save_settings.return_value = _settings("new-password")

    result = save_settings_route(_save_request("new-password"))

    assert mock_app_settings.save_settings.call_args.kwargs["qbt_password"] == "new-password"
    assert result.qbt_password.value == "********"


@patch("api.db")
def test_get_app_state_route_returns_lifecycle_flags(mock_db):
    from api import get_app_state_route

    mock_db.get_app_state.return_value = {"initial_setup_complete": False, "restart_required": True}

    result = get_app_state_route()

    assert result.initial_setup_complete is False
    assert result.restart_required is True


@patch("api.validate_qbittorrent_connection")
@patch("api.asyncio.to_thread")
@patch("api.app_settings")
def test_validate_setup_qbittorrent_route_uses_existing_password_for_mask(
    mock_app_settings,
    mock_to_thread,
    mock_validate_qbittorrent_connection,
):
    from api import validate_setup_qbittorrent_route

    mock_app_settings.get_setting_value.return_value = "real-password"
    mock_to_thread.return_value = "validation-result"

    result = asyncio.run(
        validate_setup_qbittorrent_route(
            SetupQbittorrentValidationRequest(
                qbt_hostname="http://qbittorrent:8080",
                qbt_username="admin",
                qbt_password="********",
            )
        )
    )

    assert result == "validation-result"
    mock_to_thread.assert_called_once_with(
        mock_validate_qbittorrent_connection,
        "http://qbittorrent:8080",
        "admin",
        "real-password",
    )
