import os
import signal
import time
import zlib
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import db
from logging_config import get_logger, setup_logging
from qbittorrent import QbittorrentClient
from download_manager import DownloadManager

# Initialize database and logging before other imports that may log
db.initialize_db()
settings = db.get_settings()
log_level = settings["log_level"]["value"] if settings else "INFO"
setup_logging(log_level)

logger = get_logger(__name__)

from data_sources import (
    initialize_media,
    refresh_episode_metadata,
    refresh_onepace_sheet,
)
from metadata import build_episode_mapping, save_metadata_mapping
from nyaa_utils import extract_nyaa_id, get_nyaa_resource_for_episode


def calculate_crc32(filepath: str) -> str:
    """Calculate CRC32 checksum of a file."""
    crc = 0
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            crc = zlib.crc32(chunk, crc)
    return format(crc & 0xFFFFFFFF, "08x")


def reset_all(qbt_client: QbittorrentClient):
    """Remove all tracked torrents from qBittorrent (with files) and clear the DB."""
    torrent_downloads = db.get_all_torrent_downloads()
    for torrent in torrent_downloads:
        try:
            qbt_client.stop_torrent(torrent["infohash"])
            logger.info("Removed torrent %s from qBittorrent", torrent["infohash"])
        except Exception as e:
            logger.warning("Failed to remove torrent %s from qBittorrent: %s", torrent["infohash"], e)
    db.clear_all_downloads()
    logger.info("Reset complete: all downloads cleared")


if __name__ == "__main__":
    logger.info("Starting One Pace Jellyfin backend")
    media_data_location = Path(os.getenv("MEDIA_DATA_LOCATION", "data/media"))
    # initialize_media(media_data_location)
    metadata_mapping = build_episode_mapping(media_data_location)
    logger.info("Built metadata mapping for %d episodes", len(metadata_mapping))
    qbt_client = QbittorrentClient()
    reset_all(qbt_client)
    # torrent_info = qbt_client.create_torrent(
    #     os.getenv("TEST_MAGNET_LINK", "")
    # )
    # logger.debug("Created torrent: %s", torrent_info)
    # info_hash = torrent_info.hash
    # qbt_client.pause_torrent(info_hash)
    # qbt_client.change_file_priority(
    #     info_hash, None, qbt_client.FilePriority.DONT_DOWNLOAD)
    # file = qbt_client.get_file_by_crc32(info_hash, metadata_mapping[1]['crc32'])
    # qbt_client.change_file_priority(
    #     info_hash, file, qbt_client.FilePriority.NORMAL
    # )
    # qbt_client.start_torrent(info_hash)
    
    download_manager = DownloadManager(qbt_client, metadata_mapping)
    download_manager.download_episode(metadata_mapping[1]['id'])
    download_manager.start_polling()

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
