import os
from pathlib import Path
from typing import Any

import qbittorrentapi

from models import SetupStatusResponse, SetupStepStatus, SetupValidationResponse


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

    try:
        client = qbittorrentapi.Client(
            host=hostname,
            username=qbt_username,
            password=qbt_password,
            REQUESTS_ARGS={"timeout": 10},
        )
        client.auth_log_in()
        version = client.app_version()
    except Exception as e:
        return SetupValidationResponse(
            ok=False,
            message=f"Could not connect to qBittorrent: {e}",
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
