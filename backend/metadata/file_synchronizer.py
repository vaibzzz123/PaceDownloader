"""Synchronize Managed Metadata Files under the Media Data Location."""

import math
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any

from data_sources import METADATA_CONTENT_DIR, fetch_episode_metadata
from logging_config import get_logger

logger = get_logger(__name__)

ASSETS_DIR = Path(__file__).parents[1] / "assets"
ROOT_METADATA_FILES = (
    "logo.png",
    "poster.png",
    "poster-2.png",
    "tvshow.nfo",
)
BACKDROP_RULES = (
    {"name": "backdrop.jpg", "source": "metadata", "mode": "whole", "season": 36},
    {"name": "backdrop-2.jpg", "source": "metadata", "mode": "whole", "season": 29},
    {"name": "backdrop-3.jpg", "source": "metadata", "mode": "always"},
    {"name": "backdrop-4.jpg", "source": "metadata", "mode": "whole", "season": 29},
    {"name": "backdrop-5.jpg", "source": "assets", "mode": "whole", "season": 14},
    {"name": "backdrop-6.jpg", "source": "assets", "mode": "whole", "season": 14},
    {"name": "backdrop-7.jpg", "source": "assets", "mode": "half", "season": 16},
    {"name": "backdrop-8.jpg", "source": "assets", "mode": "half", "season": 19},
)


def empty_sync_summary() -> dict[str, Any]:
    """Return an empty Media Metadata Synchronization result."""
    return {
        "copied_files": 0,
        "removed_files": 0,
        "removed_directories": 0,
        "skipped_files": 0,
        "active_seasons": [],
        "enabled_backdrops": [],
    }


def _copy_file_if_needed(src_file: Path, dst_file: Path) -> str:
    dst_file.parent.mkdir(parents=True, exist_ok=True)
    if dst_file.exists():
        src_stat = src_file.stat()
        dst_stat = dst_file.stat()
        if src_stat.st_size == dst_stat.st_size and abs(src_stat.st_mtime - dst_stat.st_mtime) < 1:
            return "skipped"

    shutil.copy2(src_file, dst_file)
    return "copied"


def _get_backdrop_source_file_path(rule: dict[str, Any]) -> Path:
    base_dir = METADATA_CONTENT_DIR if rule["source"] == "metadata" else ASSETS_DIR
    return base_dir / rule["name"]


def create_episode_disk_presence_summary(episodes: list[dict]) -> dict[str, Any]:
    known_seasons = sorted({int(ep["season"]) for ep in episodes})
    episodes_by_season: dict[int, list[dict]] = defaultdict(list)
    present_episodes_by_season: dict[int, list[dict]] = defaultdict(list)
    present_episode_numbers_by_season: dict[int, set[int]] = defaultdict(set)
    total_episode_counts: dict[int, int] = defaultdict(int)
    last_episode_by_season: dict[int, int] = {}

    for ep in episodes:
        season = int(ep["season"])
        ep_number = int(ep["ep_number"])
        episodes_by_season[season].append(ep)
        total_episode_counts[season] += 1
        last_episode_by_season[season] = max(last_episode_by_season.get(season, 0), ep_number)

        file_path = ep.get("file_location_media") or ""
        if file_path and Path(file_path).exists():
            present_episodes_by_season[season].append(ep)
            present_episode_numbers_by_season[season].add(ep_number)

    active_seasons = sorted(
        season for season, season_episodes in present_episodes_by_season.items() if season_episodes
    )
    latest_season = max(known_seasons, default=None)

    return {
        "known_seasons": known_seasons,
        "episodes_by_season": dict(episodes_by_season),
        "present_episodes_by_season": dict(present_episodes_by_season),
        "present_episode_numbers_by_season": dict(present_episode_numbers_by_season),
        "total_episode_counts": dict(total_episode_counts),
        "last_episode_by_season": last_episode_by_season,
        "active_seasons": active_seasons,
        "latest_season": latest_season,
    }


def _is_backdrop_enabled(rule: dict[str, Any], presence: dict[str, Any]) -> bool:
    mode = rule["mode"]
    if mode == "always":
        return True

    threshold = int(rule["season"])
    active_seasons = presence["active_seasons"]
    if any(season > threshold for season in active_seasons):
        return True

    if mode == "half":
        total = presence["total_episode_counts"].get(threshold, 0)
        if total == 0:
            return False
        present_count = len(presence["present_episode_numbers_by_season"].get(threshold, set()))
        return present_count >= math.ceil(total / 2)

    if mode == "whole" and presence["latest_season"] == threshold:
        final_episode = presence["last_episode_by_season"].get(threshold)
        if final_episode is None:
            return False
        return final_episode in presence["present_episode_numbers_by_season"].get(threshold, set())

    return False


def _build_desired_metadata_file_mapping(
    media_data_location: Path,
    presence: dict[str, Any],
) -> tuple[dict[Path, Path], list[str]]:
    desired_files: dict[Path, Path] = {}

    for filename in ROOT_METADATA_FILES:
        src_file = METADATA_CONTENT_DIR / filename
        if src_file.exists():
            desired_files[media_data_location / filename] = src_file
        else:
            logger.warning("Managed metadata source file missing: %s", src_file)

    enabled_backdrops: list[str] = []
    for rule in BACKDROP_RULES:
        if not _is_backdrop_enabled(rule, presence):
            continue

        src_file = _get_backdrop_source_file_path(rule)
        enabled_backdrops.append(rule["name"])
        if src_file.exists():
            desired_files[media_data_location / rule["name"]] = src_file
        else:
            logger.warning("Managed backdrop source file missing: %s", src_file)

    for season in presence["active_seasons"]:
        season_dir_name = f"Season {season}"
        season_src_dir = METADATA_CONTENT_DIR / season_dir_name

        for filename in ("poster.png", "season.nfo"):
            src_file = season_src_dir / filename
            if src_file.exists():
                desired_files[media_data_location / season_dir_name / filename] = src_file
            else:
                logger.warning("Managed season metadata source file missing: %s", src_file)

        for ep in presence["present_episodes_by_season"].get(season, []):
            src_file = season_src_dir / f"{ep['ep_name']}.nfo"
            if src_file.exists():
                desired_files[media_data_location / season_dir_name / f"{ep['ep_name']}.nfo"] = src_file
            else:
                logger.warning("Managed episode metadata source file missing: %s", src_file)

    return desired_files, enabled_backdrops


def _build_managed_metadata_cleanup_candidate_paths(media_data_location: Path) -> set[Path]:
    cleanup_candidate_paths = {media_data_location / filename for filename in ROOT_METADATA_FILES}
    cleanup_candidate_paths.update(media_data_location / rule["name"] for rule in BACKDROP_RULES)

    for season_src_dir in METADATA_CONTENT_DIR.glob("Season *"):
        if not season_src_dir.is_dir():
            continue
        season_dir = media_data_location / season_src_dir.name

        for filename in ("poster.png", "season.nfo"):
            if (season_src_dir / filename).exists():
                cleanup_candidate_paths.add(season_dir / filename)

        # Manage all season NFOs from source so stale files like skipped "(Extended)" variants
        # do not keep an otherwise empty season directory alive.
        for episode_nfo in season_src_dir.glob("One Pace - S*E* - *.nfo"):
            cleanup_candidate_paths.add(season_dir / episode_nfo.name)

    return cleanup_candidate_paths


def sync_media_metadata(media_data_location: Path, episodes: list[dict]) -> dict[str, Any]:
    """Synchronize Managed Metadata Files for Constructed Metadata episodes present on disk."""
    if not METADATA_CONTENT_DIR.exists():
        logger.debug("Source directory not found, fetching episode metadata")
        fetch_episode_metadata()

    media_data_location.mkdir(parents=True, exist_ok=True)
    presence = create_episode_disk_presence_summary(episodes)
    desired_files, enabled_backdrops = _build_desired_metadata_file_mapping(media_data_location, presence)
    cleanup_candidate_paths = _build_managed_metadata_cleanup_candidate_paths(media_data_location)

    copied = removed = skipped = removed_directories = 0

    for stale_path in sorted(cleanup_candidate_paths - set(desired_files)):
        if not stale_path.exists():
            continue
        if stale_path.is_file():
            stale_path.unlink()
            removed += 1
            continue

        logger.warning("Expected managed file path is not a file, leaving in place: %s", stale_path)

    for dst_file, src_file in sorted(desired_files.items()):
        result = _copy_file_if_needed(src_file, dst_file)
        if result == "copied":
            copied += 1
        else:
            skipped += 1

    active_seasons = set(presence["active_seasons"])
    for season in presence["known_seasons"]:
        if season in active_seasons:
            continue
        season_dir = media_data_location / f"Season {season}"
        if not season_dir.exists() or not season_dir.is_dir():
            continue
        try:
            season_dir.rmdir()
            removed_directories += 1
        except OSError:
            logger.info(
                "Leaving season directory '%s' in place because it still contains non-managed files",
                season_dir,
            )

    summary = {
        "copied_files": copied,
        "removed_files": removed,
        "removed_directories": removed_directories,
        "skipped_files": skipped,
        "active_seasons": presence["active_seasons"],
        "enabled_backdrops": enabled_backdrops,
    }

    logger.info(
        "Metadata sync: copied=%d skipped=%d removed=%d removed_dirs=%d seasons=%s backdrops=%s",
        copied,
        skipped,
        removed,
        removed_directories,
        presence["active_seasons"],
        enabled_backdrops,
    )
    return summary
