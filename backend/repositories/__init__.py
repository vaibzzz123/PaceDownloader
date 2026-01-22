"""Repository classes for database access."""

from repositories.settings_repo import SettingsRepository
from repositories.episode_download_repo import EpisodeDownloadRepository
from repositories.torrent_download_repo import TorrentDownloadRepository

__all__ = [
    "SettingsRepository",
    "EpisodeDownloadRepository",
    "TorrentDownloadRepository",
]
