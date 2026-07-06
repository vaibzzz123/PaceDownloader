"""Application-level workflows for the metadata subsystem."""

from pathlib import Path
from typing import Any

from logging_config import get_logger

from . import file_synchronizer, metadata_constructor

logger = get_logger(__name__)


def refresh_build_and_sync_media(
    media_location: Path | None,
    force_refresh: bool = False,
    save_mapping: bool = False,
) -> dict[str, Any]:
    """Refresh sources, rebuild Constructed Metadata, and sync Managed Metadata Files."""
    episodes = metadata_constructor.refresh_and_build_mapping(
        media_location=media_location,
        force_refresh=force_refresh,
        save_mapping=save_mapping,
    )
    if media_location is None:
        logger.info("Skipping media metadata sync because media_data_location is not configured")
        return file_synchronizer.empty_sync_summary()

    return file_synchronizer.sync_media_metadata(media_location, episodes)
