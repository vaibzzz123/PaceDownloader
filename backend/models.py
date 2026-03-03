from typing import Any
from pydantic import BaseModel

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
    torrent_infohash: str
    torrent_name: str


class TorrentDownloadResponse(BaseModel):
    infohash: str
    name: str
    status: str
    progress: float
    ep_ids: list[int]


class SettingField(BaseModel):
    value: Any
    env_override: bool


class SettingsResponse(BaseModel):
    media_data_location: SettingField
    prefer_extended: SettingField
    qbt_hostname: SettingField
    qbt_username: SettingField
    qbt_password: SettingField
    qbt_path_mapping: SettingField
    qbt_category: SettingField
    qbt_download_location: SettingField
    qbt_polling_rate: SettingField
    log_level: SettingField


class SettingsSaveRequest(BaseModel):
    media_data_location: str
    prefer_extended: bool
    qbt_hostname: str
    qbt_username: str
    qbt_password: str
    qbt_path_mapping: str | None = None
    qbt_category: str | None = None
    qbt_download_location: str | None = None
    qbt_polling_rate: int = 10
    log_level: str = "INFO"
