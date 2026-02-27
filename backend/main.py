import os
import signal
import time
from pathlib import Path
from fastapi import FastAPI
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
app.include_router(api_router)
app.mount("/posters", StaticFiles(directory="data/eps-metadata/One Pace"), name="posters")

if __name__ == "__main__":
    # media_data_location = Path(os.getenv("MEDIA_DATA_LOCATION", "data/media"))
    # # initialize_media(media_data_location)
    # metadata_mapping = build_episode_mapping(media_data_location)
    # logger.info("Built metadata mapping for %d episodes", len(metadata_mapping))
    # qbt_client = QbittorrentClient()
    # reset_all(qbt_client)
    # # torrent_info = qbt_client.create_torrent(
    # #     os.getenv("TEST_MAGNET_LINK", "")
    # # )
    # # logger.debug("Created torrent: %s", torrent_info)
    # # info_hash = torrent_info.hash
    # # qbt_client.pause_torrent(info_hash)
    # # qbt_client.change_file_priority(
    # #     info_hash, None, qbt_client.FilePriority.DONT_DOWNLOAD)
    # # file = qbt_client.get_file_by_crc32(info_hash, metadata_mapping[1]['crc32'])
    # # qbt_client.change_file_priority(
    # #     info_hash, file, qbt_client.FilePriority.NORMAL
    # # )
    # # qbt_client.start_torrent(info_hash)
    
    # download_manager = DownloadManager(qbt_client, metadata_mapping)
    # download_manager.download_episode(metadata_mapping[1]['id'])
    # download_manager.start_polling()
    
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
