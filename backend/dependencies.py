from download_manager import DownloadManager

_download_manager: DownloadManager | None = None


def set_download_manager(dm: DownloadManager):
    global _download_manager
    _download_manager = dm


def get_download_manager() -> DownloadManager:
    if _download_manager is None:
        raise RuntimeError("DownloadManager not initialized")
    return _download_manager
