"""Data source functions for fetching episode metadata and Google Sheets data."""

import json
import re
import shutil
import time
from io import BytesIO
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from git import Repo
from openpyxl import load_workbook

from logging_config import get_logger

logger = get_logger(__name__)


def get_session_with_retries() -> requests.Session:
    """Create a requests session with retry logic."""
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def refresh_episode_metadata(force: bool = False, max_age_hours: int = 24):
    """Clone or pull the One Pace Jellyfin metadata repository."""
    repo_path = Path("data/eps-metadata")

    if (repo_path / ".git").exists():
        repo = Repo(repo_path)

        if not force:
            fetch_head = repo_path / ".git" / "FETCH_HEAD"
            if fetch_head.exists():
                fetch_age_hours = (time.time() - fetch_head.stat().st_mtime) / 3600
                if fetch_age_hours < max_age_hours:
                    logger.info(
                        "Episode metadata is %.1f hours old (max: %d), skipping refresh. Use force=True to override.",
                        fetch_age_hours,
                        max_age_hours,
                    )
                    return

        logger.info("Pulling latest episode metadata")
        repo.remotes.origin.pull()
        logger.debug("Git pull completed for %s", repo_path)
    else:
        logger.info("Cloning One Pace Jellyfin metadata repository")
        Repo.clone_from("https://github.com/tissla/one-pace-jellyfin", repo_path)
        logger.debug("Git clone completed to %s", repo_path)


def fetch_google_sheet_xlsx(
    sheet_id: str, save_xlsx: bool = False
) -> dict[str, list[dict]]:
    """Fetch all sheets from a Google Sheet as XLSX to preserve hyperlinks.

    Args:
        sheet_id: The Google Sheet ID to fetch
        save_xlsx: If True, save a copy of the downloaded XLSX file for debugging
    """
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    logger.debug("Fetching Google Sheet: %s", sheet_id)

    session = get_session_with_retries()
    response = session.get(url, timeout=300, stream=True)
    response.raise_for_status()
    logger.debug("Google Sheets response status: %d", response.status_code)

    # Download in chunks to handle large files better
    chunks = []
    for chunk in response.iter_content(chunk_size=8192):
        chunks.append(chunk)
    xlsx_bytes = b"".join(chunks)

    # Optionally save a copy for debugging
    if save_xlsx:
        sheets_dir = Path("data/sheets")
        sheets_dir.mkdir(parents=True, exist_ok=True)
        with open(sheets_dir / "onepace_sheets.xlsx", "wb") as f:
            f.write(xlsx_bytes)

    workbook = load_workbook(BytesIO(xlsx_bytes))
    all_sheets = {}

    for sheet_name in workbook.sheetnames:
        sheet = workbook[sheet_name]
        rows = list(sheet.iter_rows())

        if not rows:
            all_sheets[sheet_name] = []
            continue

        # Get headers from first row
        headers = [cell.value for cell in rows[0]]

        data = []
        for row in rows[1:]:
            row_dict = {}
            has_data = False
            for header, cell in zip(headers, row):
                if header is None:
                    continue
                # Check if cell has a hyperlink object
                if cell.hyperlink:
                    row_dict[header] = {
                        "text": cell.value,
                        "link": cell.hyperlink.target,
                    }
                    has_data = True
                # Check if cell value is a =HYPERLINK() formula string
                elif isinstance(cell.value, str) and cell.value.startswith(
                    "=HYPERLINK"
                ):
                    # Pattern to parse =HYPERLINK("url","text") or =HYPERLINK("url", "text") formulas
                    HYPERLINK_PATTERN = re.compile(
                        r'=HYPERLINK\("([^"]+)",\s*"([^"]+)"\)'
                    )
                    match = HYPERLINK_PATTERN.match(cell.value)
                    if match:
                        row_dict[header] = {
                            "text": match.group(2),
                            "link": match.group(1),
                        }
                        has_data = True
                    else:
                        row_dict[header] = cell.value
                        has_data = True
                else:
                    row_dict[header] = cell.value
                    if cell.value is not None:
                        has_data = True
            # Skip rows where all values are null
            if has_data:
                data.append(row_dict)

        all_sheets[sheet_name] = data

    return all_sheets


def initialize_media(media_data_location: Path):
    """Copy episode metadata files from the cloned repo to the media data location."""
    source_dir = Path("data/eps-metadata/One Pace")

    if not source_dir.exists():
        logger.debug("Source directory not found, refreshing episode metadata")
        refresh_episode_metadata()

    if not media_data_location.exists():
        logger.debug("Creating media data location at %s", media_data_location)
        media_data_location.mkdir(parents=True, exist_ok=True)

    shutil.copytree(source_dir, media_data_location, dirs_exist_ok=True)

    logger.info("Copied metadata from '%s' to '%s'", source_dir, media_data_location)


def refresh_onepace_sheet(force: bool = False, max_age_hours: int = 24):
    """Download all sheets from the One Pace Google Sheet."""
    output_dir = Path("data/sheets")

    if not force and output_dir.exists():
        json_files = list(output_dir.glob("*.json"))
        if json_files:
            newest_file = max(json_files, key=lambda f: f.stat().st_mtime)
            file_age_hours = (time.time() - newest_file.stat().st_mtime) / 3600

            if file_age_hours < max_age_hours:
                logger.info(
                    "Sheets data is %.1f hours old (max: %d), skipping refresh",
                    file_age_hours,
                    max_age_hours,
                )
                return

    sheet_id = "1HQRMJgu_zArp-sLnvFMDzOyjdsht87eFLECxMK858lA"

    all_sheets = fetch_google_sheet_xlsx(sheet_id)

    output_dir.mkdir(parents=True, exist_ok=True)

    for sheet_name, rows in all_sheets.items():
        safe_name = sheet_name.replace("/", "-").replace(" ", "_").lower()
        output_path = output_dir / f"{safe_name}.json"

        with open(output_path, "w") as f:
            json.dump(rows, f, indent=2, default=str)

        logger.info("Downloaded %d rows to %s", len(rows), output_path)
