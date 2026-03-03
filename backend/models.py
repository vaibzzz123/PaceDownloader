from pydantic import BaseModel

# specific season with season title, season number, season description, and base64 encoded image
class SeasonResponse(BaseModel):
    num: int
    title: str
    description: str
    image: str


class EpisodeResponse(BaseModel):
    ep_id: int
    season: int
    number: int
    title: str
    duration: str | None
    status: str


class EpisodeDownloadResponse(BaseModel):
    ep_id: int
    season: int
    title: str
    extended: bool
    status: str
    progress: float
    torrent_infohash: str
    torrent_name: str


class TorrentDownloadResponse(BaseModel):
    infohash: str
    name: str
    status: str
    progress: float
    ep_ids: list[int]
