"""Settings API endpoints."""

from fastapi import APIRouter, HTTPException, Depends

from dependencies import get_settings_repo
from models.settings import SettingsResponse, SettingsUpdateRequest, SettingValue
from repositories.settings_repo import SettingsRepository

router = APIRouter()


@router.get("/", response_model=SettingsResponse)
async def get_settings(
    settings_repo: SettingsRepository = Depends(get_settings_repo),
):
    """Get all settings with environment override information."""
    settings = settings_repo.get_settings()

    if not settings:
        raise HTTPException(status_code=500, detail="Settings not found")

    return SettingsResponse(
        media_data_location=SettingValue(**settings["media_data_location"]),
        prefer_extended=SettingValue(**settings["prefer_extended"]),
        qbt_hostname=SettingValue(**settings["qbt_hostname"]),
        qbt_username=SettingValue(**settings["qbt_username"]),
        qbt_password=SettingValue(
            value="***" if settings["qbt_password"]["value"] else None,
            env_override=settings["qbt_password"]["env_override"],
        ),
        qbt_path_mapping=SettingValue(**settings["qbt_path_mapping"]),
        qbt_category=SettingValue(**settings["qbt_category"]),
        qbt_download_location=SettingValue(**settings["qbt_download_location"]),
        qbt_polling_rate=SettingValue(**settings["qbt_polling_rate"]),
        log_level=SettingValue(**settings["log_level"]),
    )


@router.put("/")
async def update_settings(
    request: SettingsUpdateRequest,
    settings_repo: SettingsRepository = Depends(get_settings_repo),
):
    """
    Update settings.

    Only provided fields will be updated. Fields with environment overrides
    cannot be changed via this endpoint.
    """
    current_settings = settings_repo.get_settings()
    if not current_settings:
        raise HTTPException(status_code=500, detail="Settings not found")

    # Build updated values, using current values for non-provided fields
    updated = {
        "media_data_location": (
            request.media_data_location
            if request.media_data_location is not None
            else current_settings["media_data_location"]["value"]
        ),
        "prefer_extended": (
            request.prefer_extended
            if request.prefer_extended is not None
            else current_settings["prefer_extended"]["value"]
        ),
        "qbt_hostname": (
            request.qbt_hostname
            if request.qbt_hostname is not None
            else current_settings["qbt_hostname"]["value"]
        ),
        "qbt_username": (
            request.qbt_username
            if request.qbt_username is not None
            else current_settings["qbt_username"]["value"]
        ),
        "qbt_password": (
            request.qbt_password
            if request.qbt_password is not None
            else current_settings["qbt_password"]["value"]
        ),
        "qbt_path_mapping": (
            request.qbt_path_mapping
            if request.qbt_path_mapping is not None
            else current_settings["qbt_path_mapping"]["value"]
        ),
        "qbt_category": (
            request.qbt_category
            if request.qbt_category is not None
            else current_settings["qbt_category"]["value"]
        ),
        "qbt_download_location": (
            request.qbt_download_location
            if request.qbt_download_location is not None
            else current_settings["qbt_download_location"]["value"]
        ),
        "qbt_polling_rate": (
            request.qbt_polling_rate
            if request.qbt_polling_rate is not None
            else current_settings["qbt_polling_rate"]["value"]
        ),
        "log_level": (
            request.log_level
            if request.log_level is not None
            else current_settings["log_level"]["value"]
        ),
    }

    settings_repo.save_settings(
        media_data_location=updated["media_data_location"] or "",
        qbt_hostname=updated["qbt_hostname"] or "",
        qbt_username=updated["qbt_username"] or "",
        qbt_password=updated["qbt_password"] or "",
        prefer_extended=bool(updated["prefer_extended"]),
        qbt_path_mapping=updated["qbt_path_mapping"],
        qbt_category=updated["qbt_category"],
        qbt_download_location=updated["qbt_download_location"],
        qbt_polling_rate=updated["qbt_polling_rate"] or 10,
        log_level=updated["log_level"] or "INFO",
    )

    return {"success": True, "message": "Settings updated"}
