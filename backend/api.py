import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from models import SeasonResponse, EpisodeResponse
from metadata import get_seasons, get_episodes
from dependencies import get_download_manager
from download_manager import DownloadManager
from logging_config import get_logger
router = APIRouter()
logger = get_logger(__name__)

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
def get_season_episodes(season_num: int, dm: DownloadManager = Depends(get_download_manager)):
    season_episodes = [ep for ep in get_episodes() if ep["season"] == season_num]
    if not season_episodes:
        raise HTTPException(status_code=404, detail=f"No episodes found for season {season_num}")

    result = []
    for ep in season_episodes:
        info = dm.get_episode_info(ep["id"])
        status = _STATUS_MAP.get(info["status"], info["status"]) if info else "Not Downloaded"
        result.append(EpisodeResponse(
            ep_id=ep["id"],
            season=ep["season"],
            number=ep["ep_number"],
            title=ep["title"],
            duration=ep["duration"],
            status=status,
        ))
    return result

progress = 0

async def event_generator(request: Request):
    global progress
    while True:
        # Check if client disconnected
        if await request.is_disconnected():
            break

        # Yield a named event
        data = {"status": "downloading", "progress": progress}
        yield f"event: download_update\ndata: {json.dumps(data)}\n\n"

        progress += 1
        await asyncio.sleep(2)  # wait before next update

@router.get("/events")
async def sse_endpoint(request: Request):
    return StreamingResponse(
        event_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        }
    )
