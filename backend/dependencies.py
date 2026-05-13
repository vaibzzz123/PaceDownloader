from fastapi import HTTPException, status

from download_manager import DownloadManager

_download_manager: DownloadManager | None = None


def set_download_manager(dm: DownloadManager):
    global _download_manager
    _download_manager = dm


def get_download_manager() -> DownloadManager:
    if _download_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Download services are unavailable until setup is complete, qBittorrent is reachable, and the backend has restarted",
        )
    return _download_manager
