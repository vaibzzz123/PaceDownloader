"""Episode API endpoints."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, Query

from dependencies import get_settings_repo, get_episode_download_repo, get_download_manager
from metadata import build_episode_mapping
from models.episode import EpisodeMetadata, EpisodeWithStatus
from repositories.settings_repo import SettingsRepository
from repositories.episode_download_repo import EpisodeDownloadRepository
from services.download_manager import DownloadManager

router = APIRouter()


@router.get("/", response_model=list[EpisodeWithStatus])
async def list_episodes(
    season: int | None = Query(None, description="Filter by season"),
    status: str | None = Query(None, description="Filter by download status"),
    settings_repo: SettingsRepository = Depends(get_settings_repo),
    episode_repo: EpisodeDownloadRepository = Depends(get_episode_download_repo),
    download_manager: DownloadManager = Depends(get_download_manager),
):
    """
    List all episodes with their download status.

    Optional filters:
    - season: Filter by season number
    - status: Filter by download status (pending, downloading, paused, completed, error)
    """
    settings = settings_repo.get_settings()
    if not settings:
        raise HTTPException(status_code=500, detail="Settings not configured")

    media_location = Path(settings["media_data_location"]["value"])
    episodes = build_episode_mapping(media_location)

    results = []
    for ep in episodes:
        # Apply season filter
        if season is not None and ep["season"] != season:
            continue

        # Get download info if exists
        download = episode_repo.get_by_ep_id(ep["id"])
        download_status = download.status if download else None

        # Apply status filter
        if status is not None and download_status != status:
            continue

        # Get progress if downloading
        progress = None
        if download and download.status == "downloading":
            progress, _ = download_manager.check_episode_progress(ep["id"])

        # Check if file exists on disk
        file_exists = Path(ep["file_location_media"]).exists()

        results.append(
            EpisodeWithStatus(
                id=ep["id"],
                ep_name=ep["ep_name"],
                season=ep["season"],
                ep_number=ep["ep_number"],
                file_location_media=ep["file_location_media"],
                torrent_link=ep.get("torrent_link"),
                crc32=ep.get("crc32"),
                torrent_link_extended=ep.get("torrent_link_extended"),
                crc32_extended=ep.get("crc32_extended"),
                download_status=download_status,
                download_progress=progress,
                file_exists=file_exists,
                prefer_extended=download.prefer_extended if download else None,
                file_type=download.file_type if download else None,
            )
        )

    return results


@router.get("/{ep_id}", response_model=EpisodeWithStatus)
async def get_episode(
    ep_id: int,
    settings_repo: SettingsRepository = Depends(get_settings_repo),
    episode_repo: EpisodeDownloadRepository = Depends(get_episode_download_repo),
    download_manager: DownloadManager = Depends(get_download_manager),
):
    """Get a single episode by ID with download status."""
    settings = settings_repo.get_settings()
    if not settings:
        raise HTTPException(status_code=500, detail="Settings not configured")

    media_location = Path(settings["media_data_location"]["value"])
    episodes = build_episode_mapping(media_location)

    # Find the episode
    episode = next((e for e in episodes if e["id"] == ep_id), None)
    if not episode:
        raise HTTPException(status_code=404, detail=f"Episode {ep_id} not found")

    # Get download info
    download = episode_repo.get_by_ep_id(ep_id)
    download_status = download.status if download else None

    # Get progress if downloading
    progress = None
    if download and download.status == "downloading":
        progress, _ = download_manager.check_episode_progress(ep_id)

    return EpisodeWithStatus(
        id=episode["id"],
        ep_name=episode["ep_name"],
        season=episode["season"],
        ep_number=episode["ep_number"],
        file_location_media=episode["file_location_media"],
        torrent_link=episode.get("torrent_link"),
        crc32=episode.get("crc32"),
        torrent_link_extended=episode.get("torrent_link_extended"),
        crc32_extended=episode.get("crc32_extended"),
        download_status=download_status,
        download_progress=progress,
        file_exists=Path(episode["file_location_media"]).exists(),
        prefer_extended=download.prefer_extended if download else None,
        file_type=download.file_type if download else None,
    )
