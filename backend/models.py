from typing import Any
from pydantic import BaseModel, Field

# specific season with season title, season number, season description, and base64 encoded image
class SeasonResponse(BaseModel):
    num: int
    title: str
    description: str
    image: str


class EpisodeResponse(BaseModel):
    ep_id: int
    season: int
    number: int
    title: str
    duration: str | None
    status: str


class EpisodeDownloadResponse(BaseModel):
    ep_id: int
    season: int
    title: str
    extended: bool
    status: str
    progress: float
    torrent_infohash: str | None
    torrent_name: str | None


class ScanEpisodeInfo(BaseModel):
    ep_id: int
    title: str
    season: int
    status: str | None = None  # set for found items
    error: str | None = None   # set for error items


class ScanResultResponse(BaseModel):
    found: list[ScanEpisodeInfo] = Field(default_factory=list)
    already_tracked: list[ScanEpisodeInfo] = Field(default_factory=list)
    errors: list[ScanEpisodeInfo] = Field(default_factory=list)


class MetadataSyncResponse(BaseModel):
    copied_files: int
    removed_files: int
    removed_directories: int
    skipped_files: int
    active_seasons: list[int] = Field(default_factory=list)
    enabled_backdrops: list[str] = Field(default_factory=list)


class TorrentDownloadResponse(BaseModel):
    infohash: str
    name: str
    status: str
    progress: float
    ep_ids: list[int] = Field(default_factory=list)


class SettingField(BaseModel):
    value: Any
    env_override: bool


class SettingsResponse(BaseModel):
    media_data_location: SettingField
    prefer_extended: SettingField
    qbt_hostname: SettingField
    qbt_username: SettingField
    qbt_password: SettingField
    qbt_path_local: SettingField
    qbt_path_remote: SettingField
    qbt_category: SettingField
    qbt_download_location: SettingField
    qbt_polling_rate: SettingField
    log_level: SettingField


class AppStateResponse(BaseModel):
    initial_setup_complete: bool
    restart_required: bool


class SettingsSaveRequest(BaseModel):
    media_data_location: str
    prefer_extended: bool
    qbt_hostname: str
    qbt_username: str
    qbt_password: str
    qbt_path_local: str | None = None
    qbt_path_remote: str | None = None
    qbt_category: str | None = None
    qbt_download_location: str | None = None
    qbt_polling_rate: int = 8
    log_level: str = "INFO"


class SetupStepStatus(BaseModel):
    id: str
    complete: bool
    required: bool = True
    missing_fields: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class SetupStatusResponse(BaseModel):
    required: bool
    complete: bool
    missing_fields: list[str] = Field(default_factory=list)
    steps: list[SetupStepStatus] = Field(default_factory=list)


class SetupValidationResponse(BaseModel):
    ok: bool
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class SetupMediaValidationRequest(BaseModel):
    media_data_location: str


class SetupQbittorrentValidationRequest(BaseModel):
    qbt_hostname: str
    qbt_username: str = ""
    qbt_password: str = ""


class SetupPathMappingValidationRequest(BaseModel):
    qbt_path_local: str | None = None
    qbt_path_remote: str | None = None
