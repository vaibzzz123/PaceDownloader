"""Episode metadata parsing and mapping logic for One Pace."""

import json
import re
import shutil
import time
from pathlib import Path
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
DEFAULT_MAX_AGE_HOURS = 24

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
    media_location: Path | None = None,
):
    """Refresh episode metadata and sheets data if stale.

    Args:
        force: Force refresh regardless of age.
        max_age_hours: Maximum age in hours before data is considered stale.
        media_location: If provided, sync metadata files to this directory
            whenever episode metadata is refreshed.
    """
    if force or not _is_metadata_fresh(max_age_hours):
        fetch_episode_metadata()
        if media_location:
            _initialize_media(media_location)
    else:
        logger.info("Episode metadata is fresh, skipping refresh")

    if force or not _is_sheets_fresh(max_age_hours):
        fetch_onepace_sheet()
    else:
        logger.info("Sheets data is fresh, skipping refresh")


def _initialize_media(media_data_location: Path):
    """Copy episode metadata files from the cloned repo to the media data location."""
    if not METADATA_CONTENT_DIR.exists():
        logger.debug("Source directory not found, fetching episode metadata")
        fetch_episode_metadata()

    media_data_location.mkdir(parents=True, exist_ok=True)

    copied = skipped = 0
    for src_file in METADATA_CONTENT_DIR.rglob("*"):
        if src_file.is_dir():
            continue
        dst_file = media_data_location / src_file.relative_to(METADATA_CONTENT_DIR)
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        # Skip unchanged files — avoids re-copying hundreds of files over NFS on every metadata refresh
        if dst_file.exists():
            src_stat = src_file.stat()
            dst_stat = dst_file.stat()
            if src_stat.st_size == dst_stat.st_size and abs(src_stat.st_mtime - dst_stat.st_mtime) < 1:
                skipped += 1
                continue
        shutil.copy2(src_file, dst_file)  # copy2 preserves mtime so the above check works next time
        copied += 1

    logger.info("Metadata sync: copied %d, skipped %d unchanged files to '%s'", copied, skipped, media_data_location)


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


def _build_episode_mapping(media_location: Path) -> tuple[list[dict], list[dict]]:
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

        # Build absolute file location path
        file_location = str(media_location.resolve() / f"Season {season_num}" / f"{nfo['filename']}.mkv")

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

def refresh_and_build_mapping(media_location: Path, force_refresh: bool = False, save_mapping: bool = False):
    """Refresh data and build metadata mapping, populating the in-memory caches."""
    global _episode_cache, _season_cache
    _refresh_data(media_location=media_location, force=force_refresh)
    _episode_cache, _season_cache = _build_episode_mapping(media_location)
    if save_mapping:
        _save_metadata_mapping(_episode_cache, media_location)
    return _episode_cache
