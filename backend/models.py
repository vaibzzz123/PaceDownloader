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
