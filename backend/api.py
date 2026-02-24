from fastapi import APIRouter, HTTPException
from models import SeasonResponse, EpisodeResponse
from metadata import get_seasons, get_episodes
from db import get_episode_download_by_ep_id

router = APIRouter()

_STATUS_MAP = {
    "pending":     "Pending",
    "downloading": "Downloading",
    "paused":      "Paused",
    "hardlink":    "Hardlinked",
    "copy":        "Copied",
    "error":       "Error",
}

@router.get("/")
async def root():
    return "test"

@router.get("/season", response_model=list[SeasonResponse])
def get_seasons_route():
    return [SeasonResponse(**s) for s in get_seasons()]

@router.get("/season/{season_num}", response_model=SeasonResponse)
def get_season(season_num: int):
    match = next((s for s in get_seasons() if s["num"] == season_num), None)
    if match is None:
        raise HTTPException(status_code=404, detail=f"Season {season_num} not found")
    return SeasonResponse(**match)

@router.get("/season/{season_num}/episodes", response_model=list[EpisodeResponse])
def get_season_episodes(season_num: int):
    season_episodes = [ep for ep in get_episodes() if ep["season"] == season_num]
    if not season_episodes:
        raise HTTPException(status_code=404, detail=f"No episodes found for season {season_num}")

    result = []
    for ep in season_episodes:
        download = get_episode_download_by_ep_id(str(ep["id"]))
        status = _STATUS_MAP.get(download["status"], download["status"]) if download else "Not Downloaded"
        result.append(EpisodeResponse(
            ep_id=ep["id"],
            season=ep["season"],
            number=ep["ep_number"],
            title=ep["title"],
            duration=ep["duration"],
            status=status,
        ))
    return result
