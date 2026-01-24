import os
import zlib
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from db import get_settings, initialize_db
from logging_config import get_logger, setup_logging
from qbittorrent import QbittorrentClient

# Initialize database and logging before other imports that may log
initialize_db()
settings = get_settings()
log_level = settings["log_level"]["value"] if settings else "INFO"
setup_logging(log_level)

logger = get_logger(__name__)

from data_sources import (
    initialize_media,
    refresh_episode_metadata,
    refresh_onepace_sheet,
)
from metadata import build_episode_mapping, save_metadata_mapping
from nyaa_utils import extract_nyaa_id, get_magnet_link, get_nyaa_resource_for_episode


def calculate_crc32(filepath: str) -> str:
    """Calculate CRC32 checksum of a file."""
    crc = 0
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            crc = zlib.crc32(chunk, crc)
    return format(crc & 0xFFFFFFFF, "08x")


if __name__ == "__main__":
    logger.info("Starting One Pace Jellyfin backend")
    media_data_location = Path(os.getenv("MEDIA_DATA_LOCATION", "data/media"))
    initialize_media(media_data_location)
    metadata_mapping = build_episode_mapping(media_data_location)
    logger.info("Built metadata mapping for %d episodes", len(metadata_mapping))
    qbt_client = QbittorrentClient()
    resp = qbt_client.create_torrent(
        os.getenv("TEST_MAGNET_LINK", "")
    )
    logger.debug("qBittorrent add torrent response: %s", resp)
    # example_episode = metadata_mapping[0]
    # example_episode = metadata_mapping[0]
    # nyaa_resource = get_nyaa_resource_for_episode(example_episode)
    # logger.debug("Magnet link: %s", get_magnet_link(nyaa_resource))
    # example_episode = metadata_mapping[33]
    # nyaa_resource = get_nyaa_resource_for_episode(example_episode)
    # logger.debug("Magnet link: %s", get_magnet_link(nyaa_resource))
    # logger.debug(example_episode)
    # nyaa_id = extract_nyaa_id(example_episode)
    # logger.debug("Example episode NyaaSi ID: %s", nyaa_id)
    # save_metadata_mapping(metadata_mapping, media_data_location)
