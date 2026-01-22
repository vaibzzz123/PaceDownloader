"""Torrent-related Pydantic models."""

from pydantic import BaseModel


class TorrentStatus(BaseModel):
    """Torrent status information."""

    hash: str
    name: str
    state: str
    progress: float
    save_path: str
    total_size: int
    downloaded: int
    episode_ids: list[int]


class TorrentFileInfo(BaseModel):
    """File within a torrent."""

    index: int
    name: str
    size: int
    progress: float
    priority: int
    selected: bool  # priority > 0
