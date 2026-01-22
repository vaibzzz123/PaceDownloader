"""FastAPI dependency injection for services and repositories."""

from functools import lru_cache

from repositories.settings_repo import SettingsRepository
from repositories.episode_download_repo import EpisodeDownloadRepository
from repositories.torrent_download_repo import TorrentDownloadRepository
from services.qbittorrent_client import QBittorrentClient
from services.path_mapper import PathMapper
from services.file_manager import FileManager
from services.download_manager import DownloadManager


@lru_cache()
def get_settings_repo() -> SettingsRepository:
    """Get settings repository (singleton)."""
    return SettingsRepository()


@lru_cache()
def get_episode_download_repo() -> EpisodeDownloadRepository:
    """Get episode download repository (singleton)."""
    return EpisodeDownloadRepository()


@lru_cache()
def get_torrent_download_repo() -> TorrentDownloadRepository:
    """Get torrent download repository (singleton)."""
    return TorrentDownloadRepository()


def get_qbt_client() -> QBittorrentClient:
    """
    Get qBittorrent client.

    Not cached because settings might change.
    """
    settings_repo = get_settings_repo()
    settings = settings_repo.get_settings()

    if not settings:
        raise RuntimeError("Settings not configured")

    return QBittorrentClient(
        hostname=settings["qbt_hostname"]["value"] or "",
        username=settings["qbt_username"]["value"] or "",
        password=settings["qbt_password"]["value"] or "",
        category=settings["qbt_category"]["value"],
        download_location=settings["qbt_download_location"]["value"],
    )


def get_path_mapper() -> PathMapper:
    """
    Get path mapper.

    Not cached because settings might change.
    """
    settings_repo = get_settings_repo()
    settings = settings_repo.get_settings()

    path_mapping = settings["qbt_path_mapping"]["value"] if settings else None
    return PathMapper(path_mapping)


@lru_cache()
def get_file_manager() -> FileManager:
    """Get file manager (singleton)."""
    return FileManager()


def get_download_manager() -> DownloadManager:
    """
    Get download manager instance.

    Not cached because it depends on services that might change.
    """
    return DownloadManager(
        qbt_client=get_qbt_client(),
        path_mapper=get_path_mapper(),
        file_manager=get_file_manager(),
        episode_repo=get_episode_download_repo(),
        torrent_repo=get_torrent_download_repo(),
    )
