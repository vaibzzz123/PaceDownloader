from unittest.mock import MagicMock, patch

import requests

from models import SetupMediaValidationRequest
from setup_validation import (
    QBT_VALIDATION_TIMEOUT_SECONDS,
    build_setup_status,
    is_initial_setup_configuration_complete,
    validate_media_location,
    validate_path_mapping,
    validate_qbittorrent_connection,
)


def _field(value):
    return {"value": value, "env_override": False}


def test_build_setup_status_reports_missing_required_fields():
    status = build_setup_status({})

    assert status.complete is False
    assert status.required is True
    assert set(status.missing_fields) == {"media_data_location", "qbt_hostname"}
    assert [step.id for step in status.steps] == ["media", "qbt", "paths", "preferences"]


def test_build_setup_status_reports_complete_setup():
    status = build_setup_status(
        {
            "media_data_location": _field("/media"),
            "qbt_hostname": _field("http://qbittorrent:8080"),
            "qbt_path_local": _field(""),
            "qbt_path_remote": _field(""),
        }
    )

    assert status.complete is True
    assert status.required is False
    assert status.missing_fields == []
    assert all(step.complete for step in status.steps)


def test_build_setup_status_reports_one_sided_path_mapping():
    status = build_setup_status(
        {
            "media_data_location": _field("/media"),
            "qbt_hostname": _field("http://qbittorrent:8080"),
            "qbt_path_local": _field("/downloads"),
            "qbt_path_remote": _field(""),
        }
    )

    paths_step = next(step for step in status.steps if step.id == "paths")
    assert status.complete is False
    assert paths_step.complete is False
    assert paths_step.errors == ["qbt_path_local and qbt_path_remote must be set together"]


def test_initial_setup_configuration_requires_media_and_qbittorrent_hostname():
    assert is_initial_setup_configuration_complete({}) is False


def test_initial_setup_configuration_accepts_env_style_effective_settings():
    assert is_initial_setup_configuration_complete(
        {
            "media_data_location": {"value": "/media", "env_override": True},
            "qbt_hostname": {"value": "http://qbittorrent:8080", "env_override": True},
            "qbt_path_local": {"value": "", "env_override": False},
            "qbt_path_remote": {"value": "", "env_override": False},
        }
    ) is True


def test_initial_setup_configuration_rejects_one_sided_path_mapping():
    assert is_initial_setup_configuration_complete(
        {
            "media_data_location": {"value": "/media", "env_override": False},
            "qbt_hostname": {"value": "http://qbittorrent:8080", "env_override": False},
            "qbt_path_local": {"value": "/downloads", "env_override": False},
            "qbt_path_remote": {"value": "", "env_override": False},
        }
    ) is False


def test_validate_media_location_accepts_writable_directory(tmp_path):
    result = validate_media_location(str(tmp_path))

    assert result.ok is True
    assert result.details["path"] == str(tmp_path)
    assert result.details["exists"] is True
    assert result.details["is_dir"] is True
    assert result.details["writable"] is True


def test_validate_media_location_rejects_blank_path():
    result = validate_media_location("   ")

    assert result.ok is False
    assert result.message == "Media data location is required"


def test_validate_media_location_rejects_missing_path(tmp_path):
    result = validate_media_location(str(tmp_path / "missing"))

    assert result.ok is False
    assert result.message == "Media data location does not exist"


def test_validate_media_location_rejects_file_path(tmp_path):
    file_path = tmp_path / "episode.mkv"
    file_path.write_text("not a directory")

    result = validate_media_location(str(file_path))

    assert result.ok is False
    assert result.message == "Media data location must be a directory"


def test_validate_path_mapping_accepts_empty_mapping():
    result = validate_path_mapping(qbt_path_local="", qbt_path_remote="")

    assert result.ok is True
    assert result.message == "No qBittorrent path mapping configured"
    assert result.details["mapping_required"] is False


def test_validate_path_mapping_accepts_existing_local_directory(tmp_path):
    result = validate_path_mapping(qbt_path_local=str(tmp_path), qbt_path_remote="/downloads/")

    assert result.ok is True
    assert result.message == "qBittorrent path mapping is valid"
    assert result.details["local_path"] == str(tmp_path)
    assert result.details["remote_path"] == "/downloads"
    assert result.details["local_exists"] is True
    assert result.details["local_is_dir"] is True


def test_validate_path_mapping_rejects_one_sided_mapping(tmp_path):
    result = validate_path_mapping(qbt_path_local=str(tmp_path), qbt_path_remote="")

    assert result.ok is False
    assert result.message == "Local and remote qBittorrent paths must be set together"


def test_validate_path_mapping_rejects_missing_local_directory(tmp_path):
    result = validate_path_mapping(qbt_path_local=str(tmp_path / "missing"), qbt_path_remote="/downloads")

    assert result.ok is False
    assert result.message == "Local qBittorrent path does not exist"


def test_validate_qbittorrent_connection_rejects_blank_hostname():
    result = validate_qbittorrent_connection("   ")

    assert result.ok is False
    assert result.message == "qBittorrent hostname is required"


@patch("setup_validation.requests.Session")
def test_validate_qbittorrent_connection_defaults_url_without_scheme_to_http(mock_session_class):
    mock_session = MagicMock()
    mock_session_class.return_value = mock_session
    login_response = MagicMock(status_code=200, text="Ok.")
    version_response = MagicMock(text="v5.0.0")
    mock_session.post.return_value = login_response
    mock_session.get.return_value = version_response

    result = validate_qbittorrent_connection("10.0.0.167:8080")

    assert result.ok is True
    mock_session.post.assert_called_once_with(
        "http://10.0.0.167:8080/api/v2/auth/login",
        data={"username": "", "password": ""},
        timeout=QBT_VALIDATION_TIMEOUT_SECONDS,
    )


@patch("setup_validation.HTTPAdapter")
@patch("setup_validation.requests.Session")
def test_validate_qbittorrent_connection_logs_in_and_returns_version(
    mock_session_class,
    mock_adapter_class,
):
    mock_adapter = MagicMock()
    mock_adapter_class.return_value = mock_adapter
    mock_session = MagicMock()
    mock_session_class.return_value = mock_session
    login_response = MagicMock(status_code=200, text="Ok.")
    version_response = MagicMock(text="v5.0.0")
    mock_session.post.return_value = login_response
    mock_session.get.return_value = version_response

    result = validate_qbittorrent_connection(
        " http://qbittorrent:8080 ",
        qbt_username="admin",
        qbt_password="password",
    )

    assert result.ok is True
    assert result.details["version"] == "v5.0.0"
    mock_adapter_class.assert_called_once_with(max_retries=0)
    mock_session.mount.assert_any_call("http://", mock_adapter)
    mock_session.mount.assert_any_call("https://", mock_adapter)
    mock_session.post.assert_called_once_with(
        "http://qbittorrent:8080/api/v2/auth/login",
        data={"username": "admin", "password": "password"},
        timeout=QBT_VALIDATION_TIMEOUT_SECONDS,
    )
    mock_session.get.assert_called_once_with(
        "http://qbittorrent:8080/api/v2/app/version",
        timeout=QBT_VALIDATION_TIMEOUT_SECONDS,
    )
    login_response.raise_for_status.assert_called_once()
    version_response.raise_for_status.assert_called_once()


@patch("setup_validation.requests.Session")
def test_validate_qbittorrent_connection_returns_validation_error(mock_session_class):
    mock_session = MagicMock()
    mock_session_class.return_value = mock_session
    mock_session.post.side_effect = requests.ConnectionError("connection refused")

    result = validate_qbittorrent_connection("http://qbittorrent:8080")

    assert result.ok is False
    assert result.message == "Could not reach qBittorrent. Check the URL, port, and that the Web UI is enabled."
    assert result.details["error_type"] == "ConnectionError"


@patch("setup_validation.requests.Session")
def test_validate_qbittorrent_connection_returns_timeout_error(mock_session_class):
    mock_session = MagicMock()
    mock_session_class.return_value = mock_session
    mock_session.post.side_effect = requests.Timeout("timed out")

    result = validate_qbittorrent_connection("http://qbittorrent:8080")

    assert result.ok is False
    assert result.message == "Timed out connecting to qBittorrent. Check the URL, port, and Web UI status."
    assert result.details["error_type"] == "Timeout"


@patch("setup_validation.requests.Session")
def test_validate_qbittorrent_connection_rejects_failed_login(mock_session_class):
    mock_session = MagicMock()
    mock_session_class.return_value = mock_session
    login_response = MagicMock(status_code=200, text="Fails.")
    mock_session.post.return_value = login_response

    result = validate_qbittorrent_connection("http://qbittorrent:8080")

    assert result.ok is False
    assert result.message == "Could not connect to qBittorrent: login failed"
    assert result.details["status_code"] == 200
    mock_session.get.assert_not_called()


@patch("setup_validation.requests.Session")
def test_validate_qbittorrent_connection_rejects_failed_login_status(mock_session_class):
    mock_session = MagicMock()
    mock_session_class.return_value = mock_session
    login_response = MagicMock(status_code=401, text="")
    mock_session.post.return_value = login_response

    result = validate_qbittorrent_connection("http://qbittorrent:8080")

    assert result.ok is False
    assert result.message == "Could not connect to qBittorrent: login failed"
    assert result.details["status_code"] == 401
    login_response.raise_for_status.assert_not_called()
    mock_session.get.assert_not_called()


@patch("setup_validation.requests.Session")
def test_validate_qbittorrent_connection_reports_banned_client(mock_session_class):
    mock_session = MagicMock()
    mock_session_class.return_value = mock_session
    login_response = MagicMock(
        status_code=403,
        text="Your IP address has been banned after too many failed authentication attempts.",
    )
    mock_session.post.return_value = login_response

    result = validate_qbittorrent_connection("http://qbittorrent:8080")

    assert result.ok is False
    assert result.message == (
        "qBittorrent temporarily banned this client after failed login attempts. "
        "Wait for the ban to expire or restart qBittorrent, then try again."
    )
    assert result.details["status_code"] == 403
    login_response.raise_for_status.assert_not_called()
    mock_session.get.assert_not_called()


def test_validate_setup_media_route_matches_request_model(tmp_path):
    from api import validate_setup_media_route

    result = validate_setup_media_route(
        SetupMediaValidationRequest(media_data_location=str(tmp_path))
    )

    assert result.ok is True
