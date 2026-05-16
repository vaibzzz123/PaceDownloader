import os
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from requests.adapters import HTTPAdapter

from models import SetupStatusResponse, SetupStepStatus, SetupValidationResponse

QBT_VALIDATION_TIMEOUT_SECONDS = 2


STEP_DEFINITIONS = [
    ("media", ["media_data_location"]),
    ("qbt", ["qbt_hostname"]),
    ("paths", []),
    ("preferences", []),
]


def _setting_value(settings: dict[str, Any] | None, field: str) -> Any:
    if not settings:
        return None
    field_data = settings.get(field)
    if isinstance(field_data, dict):
        return field_data.get("value")
    return field_data


def _is_populated(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def build_setup_status(settings: dict[str, Any] | None) -> SetupStatusResponse:
    steps: list[SetupStepStatus] = []

    for step_id, required_fields in STEP_DEFINITIONS:
        missing_fields = [
            field
            for field in required_fields
            if not _is_populated(_setting_value(settings, field))
        ]
        errors: list[str] = []

        if step_id == "paths":
            local_path = _setting_value(settings, "qbt_path_local")
            remote_path = _setting_value(settings, "qbt_path_remote")
            has_local = _is_populated(local_path)
            has_remote = _is_populated(remote_path)
            if has_local != has_remote:
                errors.append("qbt_path_local and qbt_path_remote must be set together")

        steps.append(
            SetupStepStatus(
                id=step_id,
                complete=not missing_fields and not errors,
                missing_fields=missing_fields,
                errors=errors,
            )
        )

    all_missing_fields = [
        field
        for step in steps
        for field in step.missing_fields
    ]
    complete = all(step.complete for step in steps)
    return SetupStatusResponse(
        required=not complete,
        complete=complete,
        missing_fields=all_missing_fields,
        steps=steps,
    )


def validate_media_location(
    media_data_location: str,
) -> SetupValidationResponse:
    path_text = media_data_location.strip()
    if not path_text:
        return SetupValidationResponse(
            ok=False,
            message="Media data location is required",
        )

    path = Path(path_text).expanduser()
    exists = path.exists()
    is_dir = path.is_dir() if exists else False
    writable = os.access(path, os.W_OK) if exists and is_dir else False
    details = {
        "path": str(path),
        "exists": exists,
        "is_dir": is_dir,
        "writable": writable,
    }

    if not exists:
        return SetupValidationResponse(
            ok=False,
            message="Media data location does not exist",
            details=details,
        )
    if not is_dir:
        return SetupValidationResponse(
            ok=False,
            message="Media data location must be a directory",
            details=details,
        )
    if not writable:
        return SetupValidationResponse(
            ok=False,
            message="Media data location is not writable by the backend",
            details=details,
        )

    return SetupValidationResponse(
        ok=True,
        message="Media data location is valid",
        details=details,
    )


def validate_qbittorrent_connection(
    qbt_hostname: str,
    qbt_username: str = "",
    qbt_password: str = "",
) -> SetupValidationResponse:
    hostname = qbt_hostname.strip()
    if not hostname:
        return SetupValidationResponse(
            ok=False,
            message="qBittorrent hostname is required",
        )
    if "://" not in hostname:
        hostname = f"http://{hostname}"
    parsed_hostname = urlparse(hostname)
    if parsed_hostname.scheme not in {"http", "https"} or not parsed_hostname.netloc:
        return SetupValidationResponse(
            ok=False,
            message="qBittorrent Web UI URL must be a host or an http(s) URL",
            details={"error_type": "InvalidURL"},
        )

    try:
        session = requests.Session()
        adapter = HTTPAdapter(max_retries=0)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        login_response = session.post(
            urljoin(f"{hostname.rstrip('/')}/", "api/v2/auth/login"),
            data={"username": qbt_username, "password": qbt_password},
            timeout=QBT_VALIDATION_TIMEOUT_SECONDS,
        )
        if login_response.status_code in {401, 403}:
            if "banned" in login_response.text.lower():
                return SetupValidationResponse(
                    ok=False,
                    message="qBittorrent temporarily banned this client after failed login attempts. Wait for the ban to expire or restart qBittorrent, then try again.",
                    details={"status_code": login_response.status_code},
                )
            return SetupValidationResponse(
                ok=False,
                message="Could not connect to qBittorrent: login failed",
                details={"status_code": login_response.status_code},
            )
        login_response.raise_for_status()

        if login_response.text.strip() != "Ok.":
            return SetupValidationResponse(
                ok=False,
                message="Could not connect to qBittorrent: login failed",
                details={"status_code": login_response.status_code},
            )

        version_response = session.get(
            urljoin(f"{hostname.rstrip('/')}/", "api/v2/app/version"),
            timeout=QBT_VALIDATION_TIMEOUT_SECONDS,
        )
        version_response.raise_for_status()
        version = version_response.text.strip()
    except requests.Timeout:
        return SetupValidationResponse(
            ok=False,
            message="Timed out connecting to qBittorrent. Check the URL, port, and Web UI status.",
            details={"error_type": "Timeout"},
        )
    except requests.ConnectionError:
        return SetupValidationResponse(
            ok=False,
            message="Could not reach qBittorrent. Check the URL, port, and that the Web UI is enabled.",
            details={"error_type": "ConnectionError"},
        )
    except requests.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else None
        return SetupValidationResponse(
            ok=False,
            message="qBittorrent Web UI returned an error. Check the URL and Web UI status.",
            details={"error_type": "HTTPError", "status_code": status_code},
        )
    except requests.RequestException as e:
        return SetupValidationResponse(
            ok=False,
            message="Could not validate qBittorrent Web UI URL. Check the URL and try again.",
            details={"error_type": type(e).__name__},
        )

    return SetupValidationResponse(
        ok=True,
        message="qBittorrent connection is valid",
        details={"version": version},
    )


def _normalize_remote_path(remote_path: str) -> str:
    normalized = remote_path.strip()
    if normalized != "/":
        normalized = normalized.rstrip("/")
    return normalized


def validate_path_mapping(
    qbt_path_local: str | None = None,
    qbt_path_remote: str | None = None,
) -> SetupValidationResponse:
    local_text = (qbt_path_local or "").strip()
    remote_text = (qbt_path_remote or "").strip()

    if not local_text and not remote_text:
        return SetupValidationResponse(
            ok=True,
            message="No qBittorrent path mapping configured",
            details={"mapping_required": False},
        )

    if not local_text or not remote_text:
        return SetupValidationResponse(
            ok=False,
            message="Local and remote qBittorrent paths must be set together",
            details={
                "has_local_path": bool(local_text),
                "has_remote_path": bool(remote_text),
            },
        )

    local_path = Path(local_text).expanduser()
    remote_path = _normalize_remote_path(remote_text)
    local_exists = local_path.exists()
    local_is_dir = local_path.is_dir() if local_exists else False
    details: dict[str, Any] = {
        "mapping_required": True,
        "local_path": str(local_path),
        "remote_path": remote_path,
        "local_exists": local_exists,
        "local_is_dir": local_is_dir,
    }

    if not local_exists:
        return SetupValidationResponse(
            ok=False,
            message="Local qBittorrent path does not exist",
            details=details,
        )
    if not local_is_dir:
        return SetupValidationResponse(
            ok=False,
            message="Local qBittorrent path must be a directory",
            details=details,
        )

    return SetupValidationResponse(
        ok=True,
        message="qBittorrent path mapping is valid",
        details=details,
    )
