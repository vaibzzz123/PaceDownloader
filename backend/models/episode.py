"""Episode-related Pydantic models."""

from pydantic import BaseModel


class EpisodeMetadata(BaseModel):
    """Episode metadata from the generated JSON."""

    id: int
    ep_name: str
    season: int
    ep_number: int
    file_location_media: str
    torrent_link: str | None = None
    crc32: str | None = None
    torrent_link_extended: str | None = None
    crc32_extended: str | None = None


class EpisodeWithStatus(EpisodeMetadata):
    """Episode with download status information."""

    download_status: str | None = None  # pending, downloading, paused, completed, error, None
    download_progress: float | None = None  # 0.0 to 1.0
    file_exists: bool = False
    prefer_extended: bool | None = None
    file_type: str | None = None  # hardlink or copy
