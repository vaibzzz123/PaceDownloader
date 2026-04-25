"""Episode metadata parsing and mapping logic for One Pace."""

import math
import json
import re
import shutil
import time
from collections import defaultdict
from pathlib import Path
from typing import Any
import defusedxml.ElementTree as ET
from data_sources import (
    fetch_episode_metadata,
    fetch_onepace_sheet,
    METADATA_DIR,
    SHEETS_DIR,
)
from logging_config import get_logger

logger = get_logger(__name__)

METADATA_CONTENT_DIR = METADATA_DIR / "One Pace"
ASSETS_DIR = Path(__file__).parent / "assets"
DEFAULT_MAX_AGE_HOURS = 24
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

# Module-level caches — populated by refresh_and_build_mapping(), read via accessors
_episode_cache: list[dict] | None = None
_season_cache: list[dict] | None = None


def get_episodes() -> list[dict]:
    if _episode_cache is None:
        raise RuntimeError("Metadata not initialized — call refresh_and_build_mapping first")
    return _episode_cache


def get_seasons() -> list[dict]:
    if _season_cache is None:
        raise RuntimeError("Metadata not initialized — call refresh_and_build_mapping first")
    return _season_cache


def _is_metadata_fresh(max_age_hours: int = DEFAULT_MAX_AGE_HOURS) -> bool:
    fetch_head = METADATA_DIR / ".git" / "FETCH_HEAD"
    if not fetch_head.exists():
        return False
    age_hours = (time.time() - fetch_head.stat().st_mtime) / 3600
    return age_hours < max_age_hours


def _is_sheets_fresh(max_age_hours: int = DEFAULT_MAX_AGE_HOURS) -> bool:
    if not SHEETS_DIR.exists():
        return False
    json_files = list(SHEETS_DIR.glob("*.json"))
    if not json_files:
        return False
    newest = max(json_files, key=lambda f: f.stat().st_mtime)
    age_hours = (time.time() - newest.stat().st_mtime) / 3600
    return age_hours < max_age_hours


def _refresh_data(
    force: bool = False,
    max_age_hours: int = DEFAULT_MAX_AGE_HOURS,
):
    """Refresh episode metadata and sheets data if stale.

    Args:
        force: Force refresh regardless of age.
        max_age_hours: Maximum age in hours before data is considered stale.
    """
    if force or not _is_metadata_fresh(max_age_hours):
        fetch_episode_metadata()
    else:
        logger.info("Episode metadata is fresh, skipping refresh")

    if force or not _is_sheets_fresh(max_age_hours):
        fetch_onepace_sheet()
    else:
        logger.info("Sheets data is fresh, skipping refresh")


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


def sync_media_metadata(media_data_location: Path, episodes: list[dict] | None = None) -> dict[str, Any]:
    """Sync only relevant metadata into the media library and remove stale managed files."""
    if not METADATA_CONTENT_DIR.exists():
        logger.debug("Source directory not found, fetching episode metadata")
        fetch_episode_metadata()

    if episodes is None:
        episodes = get_episodes()

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


def _build_season_to_arc_map(arc_overview: list[dict]) -> dict[int, dict]:
    """
    Build a mapping from integer season numbers to arc information.

    The NFO files use integer seasons (1-36), but arc_overview.json uses
    fractional arc numbers (1.0, 6.5, 9.5, etc.). This function sorts arcs
    by their number and assigns sequential integer season numbers.

    Args:
        arc_overview: List of arc data from arc_overview.json

    Returns:
        Dict mapping season number to arc info with keys:
        - arc_name: Cleaned arc name (without TBR/WIP suffixes)
        - arc_no: Original arc number from sheets
        - json_filename: Expected JSON filename for this arc's episodes
    """
    # Filter out rows with null or non-numeric "No." (totals/notes rows)
    valid_arcs = [
        arc for arc in arc_overview
        if arc.get("No.") is not None and isinstance(arc.get("No."), (int, float))
    ]

    # Sort by arc number
    sorted_arcs = sorted(valid_arcs, key=lambda x: float(x["No."]))

    season_map = {}
    logger.debug("Building season map from %d valid arcs", len(sorted_arcs))
    for season_num, arc in enumerate(sorted_arcs, start=1):
        # Handle both dict format {"text": "...", "link": ...} and plain string
        arc_name_raw = arc["Arcs"]["text"] if isinstance(arc["Arcs"], dict) else arc["Arcs"]

        # Clean arc name: remove (TBR), (WIP), extra spaces
        arc_name_clean = re.sub(r'\s*\((TBR|WIP)\)\s*', '', arc_name_raw).strip()

        # Generate JSON filename matching refresh_onepace_sheet() logic
        # Note: sheet names may differ slightly from arc overview names
        json_filename = (
            arc_name_clean
            .replace("/", "-")
            .replace(" ", "_")
            .replace("'", "")  # Apostrophes are stripped
            .lower()
            + ".json"
        )

        season_map[season_num] = {
            "arc_name": arc_name_clean,
            "arc_no": arc["No."],
            "json_filename": json_filename
        }

    return season_map


def _parse_episode_number(ep_value: str) -> int:
    """
    Extract episode number from "Arc Name ##" format.

    Args:
        ep_value: Episode identifier like "Romance Dawn 01" or "Egghead 08"

    Returns:
        Episode number as integer, or 1 for single-episode arcs without number
    """
    ep_value = ep_value.strip()

    # Match first digit sequence (handles "Arc 01", "Arc 25 (G8)", "Arc 59 Forward", etc.)
    match = re.search(r'(\d+)', ep_value)
    if match:
        return int(match.group(1))

    # Single-episode arc (no number at all)
    return 1


def _find_arc_json_file(sheets_dir: Path, json_filename: str) -> Path | None:
    """
    Find the JSON file for an arc, handling naming mismatches.

    Some arc names in arc_overview.json don't exactly match the sheet tab names,
    e.g., "The Adventures of the Straw Hats" vs "The Adventures of the Straw Hat".

    Note: This is caused by a Google Sheets XLSX export bug that corrupts sheet tab
    names - dropping trailing 's' and apostrophes. The arc_overview cell content is
    correct, but the exported tab names lose these characters.
    """
    json_path = sheets_dir / json_filename
    if json_path.exists():
        return json_path

    # Try common variations
    base_name = json_filename[:-5]  # Remove .json

    # Try removing trailing 's' (Straw Hats -> Straw Hat)
    if base_name.endswith("s"):
        alt_path = sheets_dir / f"{base_name[:-1]}.json"
        if alt_path.exists():
            return alt_path

    # Try adding trailing 's'
    alt_path = sheets_dir / f"{base_name}s.json"
    if alt_path.exists():
        return alt_path

    return None


def _load_arc_episodes(sheets_dir: Path, season_map: dict[int, dict]) -> dict[tuple[str, int], dict]:
    """
    Load all arc JSON files and create a mapping from (arc_name, ep_num) to row data.

    Args:
        sheets_dir: Path to the sheets directory containing arc JSON files
        season_map: Mapping from season number to arc info

    Returns:
        Dict mapping (arc_name, episode_number) tuples to sheet row data
    """
    arc_episode_map = {}

    for arc_info in season_map.values():
        json_path = _find_arc_json_file(sheets_dir, arc_info["json_filename"])

        if json_path is None:
            logger.warning(
                "Missing JSON file for arc '%s': %s",
                arc_info["arc_name"],
                arc_info["json_filename"],
            )
            continue

        with open(json_path) as f:
            episodes = json.load(f)

        for row in episodes:
            # Find the "One Pace Episode" column (may have leading space)
            ep_col_value = None
            for key in row:
                if key is not None and key.strip() == "One Pace Episode":
                    ep_col_value = row[key]
                    break

            if ep_col_value is None or not isinstance(ep_col_value, str):
                continue

            ep_num = _parse_episode_number(ep_col_value)
            key = (arc_info["arc_name"], ep_num)
            if key not in arc_episode_map:
                arc_episode_map[key] = row

    return arc_episode_map


def _parse_nfo_files(metadata_dir: Path) -> list[dict]:
    """
    Parse all episode NFO files and extract metadata from filenames.

    Filename format: "One Pace - S##E## - Title.nfo"

    Args:
        metadata_dir: Path to the "One Pace" metadata directory

    Returns:
        List of dicts with keys: filename, season, episode, title
    """
    episodes = []
    seasons = []
    filename_pattern = re.compile(r"One Pace - S(\d+)E(\d+) - (.+)")

    # Load season descriptions
    descriptions_path = Path(__file__).parent / "season_descriptions.json"
    if descriptions_path.exists():
        with open(descriptions_path) as f:
            season_descriptions = json.load(f)
    else:
        logger.warning("Season descriptions file not found: %s", descriptions_path)
        season_descriptions = {}

    # Sort season dirs numerically (Season 2 before Season 10)
    season_dirs = sorted(
        metadata_dir.glob("Season *"),
        key=lambda p: int(p.name.split()[-1])
    )
    # Skip extended episode files that are handled by the normal episode's extended fields
    skip_files = {
        "One Pace - S06E05 - Live (Extended)",
    }

    for season_dir in season_dirs:
        season_nfo = season_dir / "season.nfo"
        if season_nfo.exists():
            # Parse season NFO to get season title
            try:
                tree = ET.parse(season_nfo)
                root = tree.getroot()
                title_elem = root.find("title")
                if title_elem is not None and title_elem.text:
                    season_number, season_title = title_elem.text.split(".")
                    season_num_str = season_dir.name  # e.g. "Season 1"
                    seasons.append({
                        "num": int(season_number),
                        "title": season_title.strip(),
                        "image": f"/posters/{season_num_str}/poster.png",
                        "description": season_descriptions.get(season_title.strip(), ""),
                    })
            except Exception as e:
                logger.warning("Failed to parse season NFO %s: %s", season_nfo, e)
        
        for nfo_file in sorted(season_dir.glob("One Pace - S*E* - *.nfo")):
            if nfo_file.stem in skip_files:
                continue
            match = filename_pattern.match(nfo_file.stem)
            if match:
                episodes.append({
                    "filename": nfo_file.stem,
                    "season": int(match.group(1)),
                    "episode": int(match.group(2)),
                    "title": match.group(3),
                })

    return episodes, seasons


def _build_episode_mapping(media_location: Path | None) -> tuple[list[dict], list[dict]]:
    """
    Build a complete mapping of all One Pace episodes with metadata from NFO files
    and torrent information from Google Sheets.

    This function:
    1. Parses arc_overview.json to map season numbers to arc names
    2. Loads each arc's JSON file to get torrent links and CRC32 checksums
    3. Parses NFO files to get episode metadata (title, season, episode number)
    4. Joins the data to create a unified episode mapping

    Args:
        media_location: Base path where media files are/will be stored

    Returns:
        Tuple of (episodes, seasons) where episodes is a list of dicts and
        seasons is a list of dicts with season info (num, title, image, description).
    """

    # Step 1: Load and parse arc overview
    with open(SHEETS_DIR / "arc_overview.json") as f:
        arc_overview = json.load(f)

    season_map = _build_season_to_arc_map(arc_overview)

    # Step 2: Load arc episode data
    arc_episode_map = _load_arc_episodes(SHEETS_DIR, season_map)

    # Step 3: Parse NFO files
    nfo_episodes, seasons = _parse_nfo_files(METADATA_CONTENT_DIR)

    # Step 4: Build mappings
    results = []
    logger.debug("Processing %d NFO episodes", len(nfo_episodes))

    for episode_id, nfo in enumerate(nfo_episodes, start=1):
        season_num = nfo["season"]
        ep_num = nfo["episode"]

        # Get arc info for this season
        arc_info = season_map.get(season_num)
        if arc_info is None:
            logger.warning("No arc mapping for season %d", season_num)
            continue

        # Look up sheet data
        sheet_key = (arc_info["arc_name"], ep_num)
        sheet_row = arc_episode_map.get(sheet_key)

        # Extract torrent info from sheet row
        torrent_link = None
        crc32 = None
        torrent_link_extended = None
        crc32_extended = None

        if sheet_row:
            mkv_crc32 = sheet_row.get("MKV CRC32")
            if isinstance(mkv_crc32, dict):
                torrent_link = mkv_crc32.get("link")
                crc32 = mkv_crc32.get("text")

            mkv_crc32_ext = sheet_row.get("MKV CRC32 (Extended)")
            if isinstance(mkv_crc32_ext, dict):
                torrent_link_extended = mkv_crc32_ext.get("link")
                crc32_extended = mkv_crc32_ext.get("text")

        # Extract and normalise duration from sheet row ("hh:mm:ss" → "mm:ss" when hh is "00")
        duration = None
        if sheet_row:
            length_raw = sheet_row.get("Length")
            if length_raw and isinstance(length_raw, str):
                duration = length_raw[3:] if length_raw.startswith("00:") else length_raw

        # Build absolute file location path when the media library location is configured.
        file_location = ""
        if media_location is not None:
            file_location = str(
                media_location.resolve() / f"Season {season_num}" / f"{nfo['filename']}.mkv"
            )

        results.append({
            "id": episode_id,
            "ep_name": nfo["filename"],
            "title": nfo["title"],
            "season": season_num,
            "ep_number": ep_num,
            "duration": duration,
            "file_location_media": file_location,
            "torrent_link": torrent_link,
            "crc32": crc32,
            "torrent_link_extended": torrent_link_extended,
            "crc32_extended": crc32_extended,
        })

    return results, seasons


def _save_metadata_mapping(mapping: list[dict], media_location: Path):
    """Save the episode metadata mapping to a JSON file in the app data directory."""
    output_path = Path("data/constructed_metadata.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(mapping, f, indent=2)
    logger.info("Saved constructed metadata mapping to %s", output_path)

def refresh_and_build_mapping(
    media_location: Path | None,
    force_refresh: bool = False,
    save_mapping: bool = False,
):
    """Refresh data and build metadata mapping, populating the in-memory caches."""
    global _episode_cache, _season_cache
    _refresh_data(force=force_refresh)
    _episode_cache, _season_cache = _build_episode_mapping(media_location)
    if save_mapping:
        _save_metadata_mapping(_episode_cache, media_location)
    return _episode_cache


def refresh_build_and_sync_media(
    media_location: Path | None,
    force_refresh: bool = False,
    save_mapping: bool = False,
) -> dict[str, Any]:
    """Refresh metadata sources, rebuild caches, and sync managed media metadata."""
    refresh_and_build_mapping(
        media_location=media_location,
        force_refresh=force_refresh,
        save_mapping=save_mapping,
    )
    if media_location is None:
        logger.info("Skipping media metadata sync because media_data_location is not configured")
        return {
        "copied_files": 0,
        "removed_files": 0,
        "removed_directories": 0,
        "skipped_files": 0,
        "active_seasons": [],
        "enabled_backdrops": [],
    }

    return sync_media_metadata(media_location, episodes=_episode_cache or [])
