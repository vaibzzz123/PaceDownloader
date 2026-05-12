import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from dotenv import load_dotenv

load_dotenv()

import db
import app_settings
from logging_config import get_logger, setup_logging

# Initialize database and logging before other imports that may log
db.initialize_db()
log_level = app_settings.get_setting_value("log_level") or "INFO"
setup_logging(log_level)

logger = get_logger(__name__)

from qbittorrent import QbittorrentClient
from download_manager import DownloadManager
from dependencies import set_download_manager
from api import router as api_router
from metadata import refresh_build_and_sync_media
from events import downloads_broadcaster, metadata_broadcaster

logger.info("Starting Pace Downloader backend")

initial_setup_required = app_settings.is_initial_setup_required()

if initial_setup_required:
    logger.warning("Initial setup is required; skipping qBittorrent client, download manager, polling, and startup scan")
else:
    logger.info("Initial setup is complete; initializing qBittorrent client and download manager")
    media_location_value = app_settings.get_setting_value("media_data_location")
    media_location = Path(media_location_value) if media_location_value else None
    refresh_build_and_sync_media(media_location, force_refresh=False, save_mapping=True)
    qbt_client = QbittorrentClient()
    download_manager = DownloadManager(qbt_client)
    set_download_manager(download_manager)


async def _startup_scan():
    try:
        result = await asyncio.to_thread(download_manager.scan_existing_episodes)
        found = len(result.get("found", []))
        already_tracked = len(result.get("already_tracked", []))
        errors = len(result.get("errors", []))
        logger.info("Startup scan complete: found=%d, already_tracked=%d, errors=%d", found, already_tracked, errors)
        if found:
            downloads_broadcaster.publish({"type": "scan_complete"})
    except Exception as e:
        logger.warning("Startup scan failed: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not initial_setup_required:
        await download_manager.start_polling()
        asyncio.create_task(_startup_scan())
    yield
    downloads_broadcaster.close()
    metadata_broadcaster.close()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)
app.mount("/posters", StaticFiles(directory="data/eps-metadata/One Pace"), name="posters")
