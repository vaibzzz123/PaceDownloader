import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse, JSONResponse
from models import SeasonResponse, EpisodeResponse, EpisodeDownloadResponse, TorrentDownloadResponse, SettingField, SettingsResponse, SettingsSaveRequest
from metadata import get_seasons, get_episodes
from dependencies import get_download_manager
from download_manager import DownloadManager
from events import downloads_broadcaster
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
    "completed":   "Completed",
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

@router.get("/episode", response_model=list[EpisodeDownloadResponse])
def list_episode_downloads_route(dm: DownloadManager = Depends(get_download_manager)):
    metadata_map = {ep["id"]: ep for ep in get_episodes()}
    return [
        EpisodeDownloadResponse(
            ep_id=dl["ep_id"],
            season=metadata_map.get(dl["ep_id"], {}).get("season", 0),
            title=metadata_map.get(dl["ep_id"], {}).get("title", f"Episode {dl['ep_id']}"),
            extended=bool(dl["prefer_extended"]),
            status=_STATUS_MAP.get(dl["status"], dl["status"]),
            progress=dl["progress"],
            torrent_infohash=dl["torrent_infohash"],
            torrent_name=dl["torrent_name"],
        )
        for dl in dm.list_episode_downloads_with_progress()
    ]


@router.get("/torrent", response_model=list[TorrentDownloadResponse])
def list_torrent_downloads_route(dm: DownloadManager = Depends(get_download_manager)):
    return [
        TorrentDownloadResponse(
            infohash=dl["infohash"],
            name=dl["name"],
            status=_STATUS_MAP.get(dl["status"], dl["status"]),
            progress=dl["progress"],
            ep_ids=dl["ep_ids"],
        )
        for dl in dm.list_torrent_downloads_with_progress()
    ]


@router.post("/episode/{episode_id}/download", response_model=EpisodeResponse)
async def download_episode_route(episode_id: int, dm: DownloadManager = Depends(get_download_manager)):
    ep = next((ep for ep in get_episodes() if ep["id"] == episode_id), None)
    if ep is None:
        raise HTTPException(status_code=404, detail=f"Episode {episode_id} not found")

    info = dm.get_episode_info(episode_id)
    if info and info["status"] in ("downloading", "pending"):
        raise HTTPException(status_code=409, detail=f"Episode {episode_id} is already downloading")

    try:
        settings = db.get_settings()
        prefer_extended = settings["prefer_extended"]["value"] if settings else True
        await asyncio.to_thread(dm.download_episode, episode_id, prefer_extended)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    downloads_broadcaster.publish({"type": "episode_download_started", "ep_id": episode_id, "status": "downloading"})

    info = dm.get_episode_info(episode_id)
    status = _STATUS_MAP.get(info["status"], info["status"]) if info else "Not Downloaded"
    return EpisodeResponse(ep_id=ep["id"], season=ep["season"], number=ep["ep_number"], title=ep["title"], duration=ep["duration"], status=status)


@router.post("/episode/{episode_id}/pause", response_model=EpisodeResponse)
async def pause_episode_route(episode_id: int, dm: DownloadManager = Depends(get_download_manager)):
    ep = next((ep for ep in get_episodes() if ep["id"] == episode_id), None)
    if ep is None:
        raise HTTPException(status_code=404, detail=f"Episode {episode_id} not found")

    try:
        await asyncio.to_thread(dm.pause_episode, episode_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    downloads_broadcaster.publish({"type": "episode_status_changed", "ep_id": episode_id, "status": "paused"})

    info = dm.get_episode_info(episode_id)
    status = _STATUS_MAP.get(info["status"], info["status"]) if info else "Not Downloaded"
    return EpisodeResponse(ep_id=ep["id"], season=ep["season"], number=ep["ep_number"], title=ep["title"], duration=ep["duration"], status=status)


@router.post("/episode/{episode_id}/resume", response_model=EpisodeResponse)
async def resume_episode_route(episode_id: int, dm: DownloadManager = Depends(get_download_manager)):
    ep = next((ep for ep in get_episodes() if ep["id"] == episode_id), None)
    if ep is None:
        raise HTTPException(status_code=404, detail=f"Episode {episode_id} not found")

    try:
        await asyncio.to_thread(dm.resume_episode, episode_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    downloads_broadcaster.publish({"type": "episode_status_changed", "ep_id": episode_id, "status": "downloading"})

    info = dm.get_episode_info(episode_id)
    status = _STATUS_MAP.get(info["status"], info["status"]) if info else "Not Downloaded"
    return EpisodeResponse(ep_id=ep["id"], season=ep["season"], number=ep["ep_number"], title=ep["title"], duration=ep["duration"], status=status)


@router.delete("/episode/{episode_id}", status_code=204)
async def remove_episode_route(episode_id: int, dm: DownloadManager = Depends(get_download_manager)):
    ep = next((ep for ep in get_episodes() if ep["id"] == episode_id), None)
    if ep is None:
        raise HTTPException(status_code=404, detail=f"Episode {episode_id} not found")

    try:
        torrent_change = await asyncio.to_thread(dm.remove_episode, episode_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    downloads_broadcaster.publish({"type": "episode_status_changed", "ep_id": episode_id, "status": "removed"})
    if torrent_change:
        infohash, new_status = torrent_change
        downloads_broadcaster.publish({"type": "episode_status_changed", "infohash": infohash, "status": new_status})
    return Response(status_code=204)


@router.post("/torrent/{infohash}/pause", status_code=204)
async def pause_torrent_route(infohash: str, dm: DownloadManager = Depends(get_download_manager)):
    try:
        await asyncio.to_thread(dm.pause_torrent, infohash)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    downloads_broadcaster.publish({"type": "episode_status_changed", "infohash": infohash, "status": "paused"})
    return Response(status_code=204)


@router.post("/torrent/{infohash}/resume", status_code=204)
async def resume_torrent_route(infohash: str, dm: DownloadManager = Depends(get_download_manager)):
    try:
        await asyncio.to_thread(dm.resume_torrent, infohash)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    downloads_broadcaster.publish({"type": "episode_status_changed", "infohash": infohash, "status": "downloading"})
    return Response(status_code=204)


@router.delete("/torrent/{infohash}", status_code=204)
async def remove_torrent_route(infohash: str, dm: DownloadManager = Depends(get_download_manager)):
    try:
        await asyncio.to_thread(dm.remove_torrent, infohash)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    downloads_broadcaster.publish({"type": "episode_status_changed", "infohash": infohash, "status": "removed"})
    return Response(status_code=204)


@router.get("/settings", response_model=SettingsResponse)
def get_settings_route():
    settings = db.get_settings()
    if settings is None:
        raise HTTPException(status_code=500, detail="Settings not found")
    return SettingsResponse(**{k: SettingField(**v) for k, v in settings.items()})


@router.put("/settings", response_model=SettingsResponse)
def save_settings_route(req: SettingsSaveRequest):
    if req.qbt_polling_rate < 5:
        raise HTTPException(status_code=422, detail="Polling rate must be at least 5 seconds")
    db.save_settings(
        media_data_location=req.media_data_location,
        qbt_hostname=req.qbt_hostname,
        qbt_username=req.qbt_username,
        qbt_password=req.qbt_password,
        prefer_extended=req.prefer_extended,
        qbt_path_local=req.qbt_path_local,
        qbt_path_remote=req.qbt_path_remote,
        qbt_category=req.qbt_category,
        qbt_download_location=req.qbt_download_location,
        qbt_polling_rate=req.qbt_polling_rate,
        log_level=req.log_level,
    )
    settings = db.get_settings()
    return SettingsResponse(**{k: SettingField(**v) for k, v in settings.items()})


@router.get("/events/downloads")
async def downloads_sse():
    q = downloads_broadcaster.subscribe()

    async def event_stream():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=15)
                    if event is None:  # shutdown sentinel from broadcaster.close()
                        break
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            downloads_broadcaster.unsubscribe(q)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
