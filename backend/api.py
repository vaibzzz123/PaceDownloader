import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse
from models import SeasonResponse, EpisodeResponse
from metadata import get_seasons, get_episodes
from dependencies import get_download_manager
from download_manager import DownloadManager
from logging_config import get_logger
import db
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

@router.get("/health")
async def health():
    checks = {}
    
    # Check DB
    try:
        with db.get_db() as con:
            con.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"
    
    # Check qBittorrent (non-fatal if down)
    try:
        dm = get_download_manager()
        dm.qbt_client._client.app_version()
        checks["qbittorrent"] = "ok"
    except Exception as e:
        checks["qbittorrent"] = f"error: {e}"
    
    status = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    code = 200 if status == "ok" else 503
    return JSONResponse({"status": status, "checks": checks}, status_code=code)

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

@router.post("/episode/{episode_id}/download", response_model=EpisodeResponse)
def download_episode_route(episode_id: int, dm: DownloadManager = Depends(get_download_manager)):
    ep = next((ep for ep in get_episodes() if ep["id"] == episode_id), None)
    if ep is None:
        raise HTTPException(status_code=404, detail=f"Episode {episode_id} not found")

    info = dm.get_episode_info(episode_id)
    if info and info["status"] in ("downloading", "pending"):
        raise HTTPException(status_code=409, detail=f"Episode {episode_id} is already downloading")

    try:
        settings = db.get_settings()
        prefer_extended = settings["prefer_extended"]["value"] if settings else True
        dm.download_episode(episode_id, prefer_extended=prefer_extended)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    info = dm.get_episode_info(episode_id)
    status = _STATUS_MAP.get(info["status"], info["status"]) if info else "Not Downloaded"
    return EpisodeResponse(ep_id=ep["id"], season=ep["season"], number=ep["ep_number"], title=ep["title"], duration=ep["duration"], status=status)


@router.post("/episode/{episode_id}/pause", response_model=EpisodeResponse)
def pause_episode_route(episode_id: int, dm: DownloadManager = Depends(get_download_manager)):
    ep = next((ep for ep in get_episodes() if ep["id"] == episode_id), None)
    if ep is None:
        raise HTTPException(status_code=404, detail=f"Episode {episode_id} not found")

    try:
        dm.pause_episode(episode_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    info = dm.get_episode_info(episode_id)
    status = _STATUS_MAP.get(info["status"], info["status"]) if info else "Not Downloaded"
    return EpisodeResponse(ep_id=ep["id"], season=ep["season"], number=ep["ep_number"], title=ep["title"], duration=ep["duration"], status=status)


@router.post("/episode/{episode_id}/resume", response_model=EpisodeResponse)
def resume_episode_route(episode_id: int, dm: DownloadManager = Depends(get_download_manager)):
    ep = next((ep for ep in get_episodes() if ep["id"] == episode_id), None)
    if ep is None:
        raise HTTPException(status_code=404, detail=f"Episode {episode_id} not found")

    try:
        dm.resume_episode(episode_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    info = dm.get_episode_info(episode_id)
    status = _STATUS_MAP.get(info["status"], info["status"]) if info else "Not Downloaded"
    return EpisodeResponse(ep_id=ep["id"], season=ep["season"], number=ep["ep_number"], title=ep["title"], duration=ep["duration"], status=status)


@router.delete("/episode/{episode_id}", status_code=204)
def remove_episode_route(episode_id: int, dm: DownloadManager = Depends(get_download_manager)):
    ep = next((ep for ep in get_episodes() if ep["id"] == episode_id), None)
    if ep is None:
        raise HTTPException(status_code=404, detail=f"Episode {episode_id} not found")

    try:
        dm.remove_episode(episode_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return Response(status_code=204)


@router.post("/torrent/{infohash}/pause", status_code=204)
def pause_torrent_route(infohash: str, dm: DownloadManager = Depends(get_download_manager)):
    try:
        dm.pause_torrent(infohash)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return Response(status_code=204)


@router.post("/torrent/{infohash}/resume", status_code=204)
def resume_torrent_route(infohash: str, dm: DownloadManager = Depends(get_download_manager)):
    try:
        dm.resume_torrent(infohash)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return Response(status_code=204)


@router.delete("/torrent/{infohash}", status_code=204)
def remove_torrent_route(infohash: str, dm: DownloadManager = Depends(get_download_manager)):
    try:
        dm.remove_torrent(infohash)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return Response(status_code=204)


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
