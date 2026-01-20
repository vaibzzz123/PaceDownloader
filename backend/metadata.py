"""Episode metadata parsing and mapping logic for One Pace."""

import json
import re
from pathlib import Path

from data_sources import refresh_episode_metadata, refresh_onepace_sheet


def build_season_to_arc_map(arc_overview: list[dict]) -> dict[int, dict]:
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


def parse_episode_number(ep_value: str) -> int:
    """
    Extract episode number from "Arc Name ##" format.

    Args:
        ep_value: Episode identifier like "Romance Dawn 01" or "Egghead 08"

    Returns:
        Episode number as integer, or 1 for single-episode arcs without number
    """
    ep_value = ep_value.strip()

    # Try to match trailing digits (handles "01", "08", "00", etc.)
    match = re.search(r'(\d+)$', ep_value)
    if match:
        return int(match.group(1))

    # Single-episode arc (no number suffix)
    return 1


def find_arc_json_file(sheets_dir: Path, json_filename: str) -> Path | None:
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


def load_arc_episodes(sheets_dir: Path, season_map: dict[int, dict]) -> dict[tuple[str, int], dict]:
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
        json_path = find_arc_json_file(sheets_dir, arc_info["json_filename"])

        if json_path is None:
            print(f"Warning: Missing JSON file for {arc_info['arc_name']}: {arc_info['json_filename']}")
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

            ep_num = parse_episode_number(ep_col_value)
            arc_episode_map[(arc_info["arc_name"], ep_num)] = row

    return arc_episode_map


def parse_nfo_files(metadata_dir: Path) -> list[dict]:
    """
    Parse all episode NFO files and extract metadata from filenames.

    Filename format: "One Pace - S##E## - Title.nfo"

    Args:
        metadata_dir: Path to the "One Pace" metadata directory

    Returns:
        List of dicts with keys: filename, season, episode, title
    """
    episodes = []
    filename_pattern = re.compile(r"One Pace - S(\d+)E(\d+) - (.+)")

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

    return episodes


def build_episode_mapping(media_location: Path) -> list[dict]:
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
        List of dictionaries, each containing:
        - ep_name: str - Episode name (NFO filename without extension)
        - season: int - Season number
        - ep_number: int - Episode number within season
        - file_location_media: str - Absolute path to media file
        - torrent_link: str | None - Nyaa torrent link
        - crc32: str | None - CRC32 checksum of the MKV file
        - torrent_link_extended: str | None - Extended version torrent link
        - crc32_extended: str | None - Extended version CRC32 checksum
    """
    metadata_dir = Path("data/eps-metadata/One Pace")
    sheets_dir = Path("data/sheets")

    # Ensure data is available
    if not metadata_dir.exists():
        refresh_episode_metadata()
    if not sheets_dir.exists():
        refresh_onepace_sheet()

    # Step 1: Load and parse arc overview
    with open(sheets_dir / "arc_overview.json") as f:
        arc_overview = json.load(f)

    season_map = build_season_to_arc_map(arc_overview)

    # Step 2: Load arc episode data
    arc_episode_map = load_arc_episodes(sheets_dir, season_map)

    # Step 3: Parse NFO files
    nfo_episodes = parse_nfo_files(metadata_dir)

    # Step 4: Build mappings
    results = []

    for nfo in nfo_episodes:
        season_num = nfo["season"]
        ep_num = nfo["episode"]

        # Get arc info for this season
        arc_info = season_map.get(season_num)
        if arc_info is None:
            print(f"Warning: No arc mapping for season {season_num}")
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

        # Build absolute file location path
        file_location = str(media_location.resolve() / f"Season {season_num}" / f"{nfo['filename']}.mkv")

        results.append({
            "ep_name": nfo["filename"],
            "season": season_num,
            "ep_number": ep_num,
            "file_location_media": file_location,
            "torrent_link": torrent_link,
            "crc32": crc32,
            "torrent_link_extended": torrent_link_extended,
            "crc32_extended": crc32_extended,
        })

    return results


def save_metadata_mapping(mapping: list[dict], media_location: Path):
    """Save the episode metadata mapping to a JSON file in the media location."""
    output_path = media_location / "episode_metadata.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(mapping, f, indent=2)
    print(f"Saved episode metadata mapping to {output_path}")
