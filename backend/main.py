import os
import signal
import time
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

logger.info("Starting One Pace Jellyfin backend")

refresh_and_build_mapping(Path(settings["media_data_location"]["value"]), force_refresh=False, save_mapping=True)

qbt_client = QbittorrentClient()
download_manager = DownloadManager(qbt_client)
set_download_manager(download_manager)


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)
app.mount("/posters", StaticFiles(directory="data/eps-metadata/One Pace"), name="posters")

if __name__ == "__main__":    
    def shutdown(signum, frame):
        logger.info("Received signal %s, shutting down", signum)
        download_manager.stop_polling()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        signal.pause()
    except AttributeError:
        # signal.pause() not available on Windows
        while download_manager._polling:
            time.sleep(1)
