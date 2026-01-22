"""Download-related Pydantic models."""

from pydantic import BaseModel


class StartDownloadRequest(BaseModel):
    """Request body for starting a download."""

    ep_id: int
    prefer_extended: bool = False


class StartDownloadResponse(BaseModel):
    """Response for start download."""

    success: bool
    message: str
    episode_download_id: int | None = None
    torrent_hash: str | None = None


class DownloadStatusResponse(BaseModel):
    """Detailed status of an episode download."""

    ep_id: int
    status: str
    progress: float
    is_complete: bool
    prefer_extended: bool
    file_path_torrent: str | None = None
    file_path_disk: str | None = None
    file_type: str | None = None
    torrent_hash: str | None = None


class PauseResumeResponse(BaseModel):
    """Response for pause/resume operations."""

    success: bool
    message: str


class RemoveDownloadRequest(BaseModel):
    """Request body for removing a download."""

    delete_torrent_if_empty: bool = False


class RemoveDownloadResponse(BaseModel):
    """Response for remove download."""

    success: bool
    message: str
    torrent_deleted: bool = False
