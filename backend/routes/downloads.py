"""Download management API endpoints."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, Query

from dependencies import get_settings_repo, get_download_manager
from metadata import build_episode_mapping
from models.download import (
    StartDownloadRequest,
    StartDownloadResponse,
    DownloadStatusResponse,
    PauseResumeResponse,
    RemoveDownloadResponse,
)
from nyaa_utils import get_nyaa_resource_for_episode, get_magnet_link
from repositories.settings_repo import SettingsRepository
from services.download_manager import DownloadManager, DownloadRequest

router = APIRouter()


@router.post("/start", response_model=StartDownloadResponse)
async def start_download(
    request: StartDownloadRequest,
    settings_repo: SettingsRepository = Depends(get_settings_repo),
    download_manager: DownloadManager = Depends(get_download_manager),
):
    """
    Start downloading an episode.

    This endpoint:
    1. Looks up episode metadata to get torrent link and CRC32
    2. Fetches magnet link from Nyaa
    3. Checks if torrent already exists
    4. Adds torrent if needed, selects only the required file
    5. Starts the download
    """
    settings = settings_repo.get_settings()
    if not settings:
        raise HTTPException(status_code=500, detail="Settings not configured")

    media_location = Path(settings["media_data_location"]["value"])
    episodes = build_episode_mapping(media_location)

    # Find episode in metadata
    episode = next((e for e in episodes if e["id"] == request.ep_id), None)
    if not episode:
        raise HTTPException(status_code=404, detail=f"Episode {request.ep_id} not found")

    # Determine which torrent link and CRC32 to use
    if request.prefer_extended and episode.get("torrent_link_extended"):
        torrent_link = episode["torrent_link_extended"]
        crc32 = episode["crc32_extended"]
    else:
        torrent_link = episode.get("torrent_link")
        crc32 = episode.get("crc32")

    if not torrent_link or not crc32:
        raise HTTPException(
            status_code=400,
            detail="Episode has no torrent information",
        )

    # Get magnet link from Nyaa
    # Build episode dict with the selected torrent link for get_nyaa_resource_for_episode
    episode_for_nyaa = {
        "torrent_link": torrent_link if not request.prefer_extended else None,
        "torrent_link_extended": torrent_link if request.prefer_extended else None,
    }
    # Override with actual values
    episode_for_nyaa["torrent_link"] = episode.get("torrent_link")
    episode_for_nyaa["torrent_link_extended"] = episode.get("torrent_link_extended")

    nyaa_resource = get_nyaa_resource_for_episode(episode_for_nyaa)
    magnet_link = get_magnet_link(nyaa_resource)

    if not magnet_link:
        raise HTTPException(
            status_code=502,
            detail="Failed to get magnet link from Nyaa",
        )

    # Create download request
    download_request = DownloadRequest(
        ep_id=request.ep_id,
        magnet_link=magnet_link,
        crc32=crc32,
        prefer_extended=request.prefer_extended,
        destination_path=episode["file_location_media"],
    )

    result = download_manager.download_episode(download_request)

    return StartDownloadResponse(
        success=result.success,
        message=result.message,
        episode_download_id=result.episode_download_id,
        torrent_hash=result.torrent_hash,
    )


@router.get("/{ep_id}", response_model=DownloadStatusResponse)
async def get_download_status(
    ep_id: int,
    download_manager: DownloadManager = Depends(get_download_manager),
):
    """Get detailed status of an episode download."""
    status = download_manager.get_episode_status(ep_id)

    if not status:
        raise HTTPException(
            status_code=404,
            detail=f"No download found for episode {ep_id}",
        )

    return DownloadStatusResponse(**status)


@router.post("/{ep_id}/pause", response_model=PauseResumeResponse)
async def pause_download(
    ep_id: int,
    download_manager: DownloadManager = Depends(get_download_manager),
):
    """
    Pause an episode download.

    Note: This pauses the entire torrent, affecting all episodes
    sharing the same torrent.
    """
    result = download_manager.pause_episode(ep_id)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)

    return PauseResumeResponse(success=True, message=result.message)


@router.post("/{ep_id}/resume", response_model=PauseResumeResponse)
async def resume_download(
    ep_id: int,
    download_manager: DownloadManager = Depends(get_download_manager),
):
    """
    Resume an episode download.

    Note: This resumes the entire torrent, affecting all episodes
    sharing the same torrent.
    """
    result = download_manager.resume_episode(ep_id)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)

    return PauseResumeResponse(success=True, message=result.message)


@router.delete("/{ep_id}", response_model=RemoveDownloadResponse)
async def remove_download(
    ep_id: int,
    delete_torrent_if_empty: bool = Query(
        False,
        description="Delete the torrent if no other episodes are using it",
    ),
    download_manager: DownloadManager = Depends(get_download_manager),
):
    """
    Remove an episode download.

    This will:
    1. Delete the hardlink/copy at the destination
    2. Deselect the file in qBittorrent
    3. Remove tracking records
    4. Optionally delete the entire torrent if no other episodes need it
    """
    result = download_manager.remove_episode(
        ep_id=ep_id,
        delete_torrent_if_empty=delete_torrent_if_empty,
    )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)

    return RemoveDownloadResponse(
        success=True,
        message=result.message,
        torrent_deleted="torrent deleted" in result.message.lower(),
    )


@router.post("/{ep_id}/complete", response_model=PauseResumeResponse)
async def mark_download_complete(
    ep_id: int,
    download_manager: DownloadManager = Depends(get_download_manager),
):
    """
    Mark an episode download as complete and create the destination file.

    This is called when qBittorrent reports the file is finished downloading.
    Creates a hardlink (preferred) or copy to the final media location.
    """
    result = download_manager.handle_download_complete(ep_id)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)

    return PauseResumeResponse(success=True, message=result.message)
