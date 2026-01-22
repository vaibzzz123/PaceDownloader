"""Settings-related Pydantic models."""

from pydantic import BaseModel


class SettingValue(BaseModel):
    """A single setting with its value and env override status."""

    value: str | int | bool | None
    env_override: bool


class SettingsResponse(BaseModel):
    """All settings response."""

    media_data_location: SettingValue
    prefer_extended: SettingValue
    qbt_hostname: SettingValue
    qbt_username: SettingValue
    qbt_password: SettingValue
    qbt_path_mapping: SettingValue
    qbt_category: SettingValue
    qbt_download_location: SettingValue
    qbt_polling_rate: SettingValue
    log_level: SettingValue


class SettingsUpdateRequest(BaseModel):
    """Request to update settings."""

    media_data_location: str | None = None
    prefer_extended: bool | None = None
    qbt_hostname: str | None = None
    qbt_username: str | None = None
    qbt_password: str | None = None
    qbt_path_mapping: str | None = None
    qbt_category: str | None = None
    qbt_download_location: str | None = None
    qbt_polling_rate: int | None = None
    log_level: str | None = None


class QbtConnectionTestResponse(BaseModel):
    """Response for qBittorrent connection test."""

    success: bool
    message: str
