"""Data source functions for downloading raw data and storing it in the data directory."""

import json
import re
from io import BytesIO
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from git import Repo
from openpyxl import load_workbook

from logging_config import get_logger

logger = get_logger(__name__)

GITHUB_REPO_URL = "https://github.com/tissla/one-pace-jellyfin"
GOOGLE_SHEET_ID = "1HQRMJgu_zArp-sLnvFMDzOyjdsht87eFLECxMK858lA"

METADATA_DIR = Path("data/eps-metadata")
SHEETS_DIR = Path("data/sheets")


def _get_session_with_retries() -> requests.Session:
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


def fetch_episode_metadata():
    """Clone or pull the One Pace Jellyfin metadata repository."""
    if (METADATA_DIR / ".git").exists():
        repo = Repo(METADATA_DIR)
        logger.info("Pulling latest episode metadata")
        repo.remotes.origin.pull()
        logger.debug("Git pull completed for %s", METADATA_DIR)
    else:
        logger.info("Cloning One Pace Jellyfin metadata repository")
        Repo.clone_from(GITHUB_REPO_URL, METADATA_DIR)
        logger.debug("Git clone completed to %s", METADATA_DIR)


def _fetch_google_sheet_xlsx(
    sheet_id: str, save_xlsx: bool = False
) -> dict[str, list[dict]]:
    """Fetch all sheets from a Google Sheet as XLSX to preserve hyperlinks.

    Args:
        sheet_id: The Google Sheet ID to fetch
        save_xlsx: If True, save a copy of the downloaded XLSX file for debugging
    """
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    logger.debug("Fetching Google Sheet: %s", sheet_id)

    session = _get_session_with_retries()
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
        SHEETS_DIR.mkdir(parents=True, exist_ok=True)
        with open(SHEETS_DIR / "onepace_sheets.xlsx", "wb") as f:
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


def fetch_onepace_sheet():
    """Download the One Pace Google Sheet and save each tab as JSON."""
    all_sheets = _fetch_google_sheet_xlsx(GOOGLE_SHEET_ID)

    SHEETS_DIR.mkdir(parents=True, exist_ok=True)

    for sheet_name, rows in all_sheets.items():
        safe_name = sheet_name.replace("/", "-").replace(" ", "_").lower()
        output_path = SHEETS_DIR / f"{safe_name}.json"

        with open(output_path, "w") as f:
            json.dump(rows, f, indent=2, default=str)

        logger.info("Saved %d rows to %s", len(rows), output_path)
