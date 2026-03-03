from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from dotenv import load_dotenv

load_dotenv()

import db
from logging_config import get_logger, setup_logging

# Initialize database and logging before other imports that may log
db.initialize_db()
settings = db.get_settings()
log_level = settings["log_level"]["value"] if settings else "INFO"
setup_logging(log_level)

logger = get_logger(__name__)

from qbittorrent import QbittorrentClient
from download_manager import DownloadManager
from dependencies import set_download_manager
from api import router as api_router
from metadata import refresh_and_build_mapping
from events import downloads_broadcaster, metadata_broadcaster

logger.info("Starting One Pace Jellyfin backend")

refresh_and_build_mapping(Path(settings["media_data_location"]["value"]), force_refresh=False, save_mapping=True)

qbt_client = QbittorrentClient()
download_manager = DownloadManager(qbt_client)
set_download_manager(download_manager)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await download_manager.start_polling()
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
