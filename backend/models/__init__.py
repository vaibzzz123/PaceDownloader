"""Pydantic models for API request/response."""

from models.episode import (
    EpisodeMetadata,
    EpisodeWithStatus,
)
from models.torrent import (
    TorrentStatus,
    TorrentFileInfo,
)
from models.download import (
    StartDownloadRequest,
    StartDownloadResponse,
    DownloadStatusResponse,
    PauseResumeResponse,
    RemoveDownloadRequest,
    RemoveDownloadResponse,
)
from models.settings import (
    SettingsResponse,
    SettingsUpdateRequest,
    QbtConnectionTestResponse,
)

__all__ = [
    "EpisodeMetadata",
    "EpisodeWithStatus",
    "TorrentStatus",
    "TorrentFileInfo",
    "StartDownloadRequest",
    "StartDownloadResponse",
    "DownloadStatusResponse",
    "PauseResumeResponse",
    "RemoveDownloadRequest",
    "RemoveDownloadResponse",
    "SettingsResponse",
    "SettingsUpdateRequest",
    "QbtConnectionTestResponse",
]
