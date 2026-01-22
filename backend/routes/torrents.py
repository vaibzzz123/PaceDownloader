"""Torrent status and management API endpoints."""

from fastapi import APIRouter, HTTPException, Depends

from dependencies import get_qbt_client, get_torrent_download_repo
from models.torrent import TorrentStatus, TorrentFileInfo
from models.settings import QbtConnectionTestResponse
from repositories.torrent_download_repo import TorrentDownloadRepository
from services.qbittorrent_client import QBittorrentClient

router = APIRouter()


@router.get("/", response_model=list[TorrentStatus])
async def list_tracked_torrents(
    qbt_client: QBittorrentClient = Depends(get_qbt_client),
    torrent_repo: TorrentDownloadRepository = Depends(get_torrent_download_repo),
):
    """List all torrents being tracked for One Pace downloads."""
    tracked_torrents = torrent_repo.get_all()

    results = []
    for tracked in tracked_torrents:
        torrent_info = qbt_client.get_torrent(tracked.qbt_torrent_id)
        if torrent_info:
            episode_ids = torrent_repo.get_episode_ids(tracked.qbt_torrent_id)
            results.append(
                TorrentStatus(
                    hash=torrent_info.hash,
                    name=torrent_info.name,
                    state=torrent_info.state,
                    progress=torrent_info.progress,
                    save_path=torrent_info.save_path,
                    total_size=torrent_info.total_size,
                    downloaded=torrent_info.downloaded,
                    episode_ids=episode_ids,
                )
            )

    return results


@router.get("/{torrent_hash}", response_model=TorrentStatus)
async def get_torrent(
    torrent_hash: str,
    qbt_client: QBittorrentClient = Depends(get_qbt_client),
    torrent_repo: TorrentDownloadRepository = Depends(get_torrent_download_repo),
):
    """Get status of a specific torrent."""
    torrent_info = qbt_client.get_torrent(torrent_hash)
    if not torrent_info:
        raise HTTPException(status_code=404, detail="Torrent not found")

    episode_ids = torrent_repo.get_episode_ids(torrent_hash)

    return TorrentStatus(
        hash=torrent_info.hash,
        name=torrent_info.name,
        state=torrent_info.state,
        progress=torrent_info.progress,
        save_path=torrent_info.save_path,
        total_size=torrent_info.total_size,
        downloaded=torrent_info.downloaded,
        episode_ids=episode_ids,
    )


@router.get("/{torrent_hash}/files", response_model=list[TorrentFileInfo])
async def get_torrent_files(
    torrent_hash: str,
    qbt_client: QBittorrentClient = Depends(get_qbt_client),
):
    """Get files within a torrent."""
    files = qbt_client.get_torrent_files(torrent_hash)

    if not files:
        raise HTTPException(
            status_code=404,
            detail="Torrent not found or has no files",
        )

    return [
        TorrentFileInfo(
            index=f.index,
            name=f.name,
            size=f.size,
            progress=f.progress,
            priority=f.priority,
            selected=f.priority > 0,
        )
        for f in files
    ]


@router.post("/test-connection", response_model=QbtConnectionTestResponse)
async def test_qbt_connection(
    qbt_client: QBittorrentClient = Depends(get_qbt_client),
):
    """Test connection to qBittorrent."""
    success, message = qbt_client.test_connection()

    if not success:
        raise HTTPException(status_code=502, detail=message)

    return QbtConnectionTestResponse(success=True, message=message)
