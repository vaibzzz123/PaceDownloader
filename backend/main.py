import json
import re
import shutil
import zlib
import sys
from io import BytesIO
from pathlib import Path
import os

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from git import Repo
from openpyxl import load_workbook
from dotenv import load_dotenv

load_dotenv()

global media_data_location


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

# Pattern to parse =HYPERLINK("url","text") or =HYPERLINK("url", "text") formulas
HYPERLINK_PATTERN = re.compile(r'=HYPERLINK\("([^"]+)",\s*"([^"]+)"\)')

def calculate_crc32(filepath: str) -> str:
    crc = 0
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            crc = zlib.crc32(chunk, crc)
    return format(crc & 0xFFFFFFFF, "08x")

def refresh_episode_metadata():
    repo_path = Path("data/eps-metadata")
    if (repo_path / ".git").exists():
        repo = Repo(repo_path)
        repo.remotes.origin.pull()
    else:
        Repo.clone_from("https://github.com/tissla/one-pace-jellyfin", repo_path)

def fetch_google_sheet_xlsx(sheet_id: str) -> dict[str, list[dict]]:
    """Fetch all sheets from a Google Sheet as XLSX to preserve hyperlinks."""
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"

    session = get_session_with_retries()
    response = session.get(url, timeout=300, stream=True)
    response.raise_for_status()

    # Download in chunks to handle large files better
    chunks = []
    for chunk in response.iter_content(chunk_size=8192):
        chunks.append(chunk)
    xlsx_data = BytesIO(b"".join(chunks))

    workbook = load_workbook(xlsx_data)
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
                    row_dict[header] = {"text": cell.value, "link": cell.hyperlink.target}
                    has_data = True
                # Check if cell value is a =HYPERLINK() formula string
                elif isinstance(cell.value, str) and cell.value.startswith("=HYPERLINK"):
                    match = HYPERLINK_PATTERN.match(cell.value)
                    if match:
                        row_dict[header] = {"text": match.group(2), "link": match.group(1)}
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
        refresh_episode_metadata()

    media_data_location.mkdir(parents=True, exist_ok=True)

    shutil.copytree(source_dir, media_data_location, dirs_exist_ok=True)

    print(f"Copied metadata from '{source_dir}' to '{media_data_location}'")


def refresh_onepace_sheet():
    """Download all sheets from the One Pace Google Sheet."""
    sheet_id = "1HQRMJgu_zArp-sLnvFMDzOyjdsht87eFLECxMK858lA"

    all_sheets = fetch_google_sheet_xlsx(sheet_id)

    output_dir = Path("data/sheets")
    output_dir.mkdir(parents=True, exist_ok=True)

    for sheet_name, rows in all_sheets.items():
        # Sanitize filename
        safe_name = sheet_name.replace("/", "-").replace(" ", "_").lower()
        output_path = output_dir / f"{safe_name}.json"

        with open(output_path, "w") as f:
            json.dump(rows, f, indent=2, default=str)

        print(f"Downloaded {len(rows)} rows to {output_path}")

    return all_sheets

if __name__ == "__main__":
    # if len(sys.argv) != 2:
    #     print(f"Usage: {sys.argv[0]} <filepath>")
    #     sys.exit(1)

    # filepath = sys.argv[1]
    # checksum = calculate_crc32(filepath)
    # print(f"CRC32: {checksum}")
    media_data_location = Path(os.getenv("MEDIA_DATA_LOCATION", "data/media"))
    initialize_media(media_data_location)
    # refresh_episode_metadata()
    # refresh_onepace_sheet()