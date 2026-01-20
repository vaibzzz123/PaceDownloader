import os
import zlib
from pathlib import Path

from dotenv import load_dotenv

from data_sources import initialize_media, refresh_episode_metadata, refresh_onepace_sheet 
from metadata import build_episode_mapping, save_metadata_mapping

load_dotenv()


def calculate_crc32(filepath: str) -> str:
    """Calculate CRC32 checksum of a file."""
    crc = 0
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            crc = zlib.crc32(chunk, crc)
    return format(crc & 0xFFFFFFFF, "08x")


if __name__ == "__main__":
    media_data_location = Path(os.getenv("MEDIA_DATA_LOCATION", "data/media"))
    initialize_media(media_data_location)
    refresh_episode_metadata()
    refresh_onepace_sheet()
    metadata_mapping = build_episode_mapping(media_data_location)
    print(f"Built metadata mapping for {len(metadata_mapping)} episodes.")
    save_metadata_mapping(metadata_mapping, media_data_location)
