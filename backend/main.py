import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from setup_validation import is_initial_setup_configuration_complete
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from dotenv import load_dotenv

load_dotenv()

import db
import app_settings
from logging_config import get_logger, setup_logging

# Initialize database and logging before other imports that may log
db.initialize_db()
initial_setup_complete = is_initial_setup_configuration_complete(app_settings.get_settings())
db.set_app_state(initial_setup_complete=initial_setup_complete, restart_required=False)
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

download_manager: DownloadManager | None = None

if not initial_setup_complete:
    logger.warning("Initial setup is required; skipping qBittorrent client, download manager, polling, and startup scan")
else:
    logger.info("Initial setup is complete; initializing episode metadata")
    try:
        media_location_value = app_settings.get_setting_value("media_data_location")
        media_location = Path(media_location_value) if media_location_value else None
        refresh_build_and_sync_media(media_location, force_refresh=False, save_mapping=True)
    except Exception as e:
        logger.warning("Episode metadata is unavailable; browse routes will return 503: %s", e)
    else:
        logger.info("Episode metadata is ready; initializing qBittorrent client and download manager")
        try:
            qbt_client = QbittorrentClient()
            download_manager = DownloadManager(qbt_client)
            set_download_manager(download_manager)
        except Exception as e:
            logger.warning("Download services are unavailable; setup and settings routes remain available: %s", e)


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
    # This accounts for case where initial setup is done but qbt is unreachable
    if download_manager is not None:
        await download_manager.start_polling()
        asyncio.create_task(_startup_scan())
    yield
    downloads_broadcaster.close()
    metadata_broadcaster.close()


app = FastAPI(lifespan=lifespan)
app.include_router(api_router)

posters_dir = Path("data/eps-metadata/One Pace")
posters_dir.mkdir(parents=True, exist_ok=True)
app.mount("/posters", StaticFiles(directory=posters_dir), name="posters")
