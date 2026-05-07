from unittest.mock import MagicMock, patch

from models import SetupMediaValidationRequest
from setup_validation import (
    build_setup_status,
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


def test_validate_media_location_accepts_writable_directory(tmp_path):
    result = validate_media_location(str(tmp_path))

    assert result.ok is True
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


@patch("setup_validation.qbittorrentapi.Client")
def test_validate_qbittorrent_connection_logs_in_and_returns_version(mock_client_class):
    mock_client = MagicMock()
    mock_client.app_version.return_value = "v5.0.0"
    mock_client_class.return_value = mock_client

    result = validate_qbittorrent_connection(
        " http://qbittorrent:8080 ",
        qbt_username="admin",
        qbt_password="password",
    )

    assert result.ok is True
    assert result.details["version"] == "v5.0.0"
    mock_client_class.assert_called_once_with(
        host="http://qbittorrent:8080",
        username="admin",
        password="password",
        REQUESTS_ARGS={"timeout": 10},
    )
    mock_client.auth_log_in.assert_called_once()


@patch("setup_validation.qbittorrentapi.Client")
def test_validate_qbittorrent_connection_returns_validation_error(mock_client_class):
    mock_client_class.side_effect = RuntimeError("connection refused")

    result = validate_qbittorrent_connection("http://qbittorrent:8080")

    assert result.ok is False
    assert result.message == "Could not connect to qBittorrent: connection refused"
    assert result.details["error_type"] == "RuntimeError"


def test_validate_setup_media_route_matches_request_model(tmp_path):
    from api import validate_setup_media_route

    result = validate_setup_media_route(
        SetupMediaValidationRequest(media_data_location=str(tmp_path))
    )

    assert result.ok is True
