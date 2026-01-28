# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

One Pace Jellyfin Web UI - A web app with a Python backend that automates downloading One Pace episodes (fan-edited One Piece anime) via qBittorrent and places them in the correct media structure for Jellyfin media server.

## Common Commands

All commands run from the `backend/` directory:

```bash
# Install dependencies (use venv at backend/venv/)
cd backend && pip install -r requirements.txt

# Run the backend
cd backend && python main.py

# Run all tests
cd backend && pytest

# Run a single test file
cd backend && pytest tests/test_qbittorrent.py -v

# Run tests with coverage
cd backend && pytest --cov
```

## Architecture

### Data Flow

1. **Metadata Collection**: Episode metadata comes from two sources:
   - NFO files from `tissla/one-pace-jellyfin` GitHub repo (cloned to `data/eps-metadata/`)
   - Google Sheets XLSX export containing CRC32 checksums and Nyaa torrent links (saved to `data/sheets/`)

2. **Episode Mapping**: `metadata.py:build_episode_mapping()` joins NFO file data with Google Sheets data to create a unified episode list with torrent info

3. **Download Process**:
   - `DownloadManager` receives episode download requests
   - Fetches torrent info from Nyaa.si via `nyaa_utils.py`
   - Creates/manages torrents through `QbittorrentClient`
   - Uses CRC32 in filename to identify correct file within multi-file torrents
   - Polls for download completion and hardlinks/copies files to media location

### Key Modules

- **db.py**: SQLite database with three tables: `settings` (singleton), `torrent_download`, `episode_download`. Settings support environment variable overrides.

- **download_manager.py**: Orchestrates downloads with background polling thread. Episode states: `pending` → `downloading` → `hardlink`/`copy`

- **qbittorrent.py**: Wrapper around `qbittorrent-api`. Handles torrent creation, file priority management (to download specific files), and metadata waiting.

- **metadata.py**: Maps integer season numbers (from NFO) to arc names (from Sheets), handles naming mismatches between sources

- **data_sources.py**: Fetches data with caching (default 24h). Google Sheets exported as XLSX to preserve hyperlinks containing torrent URLs.

### Configuration

Settings stored in SQLite but overridable via environment variables (uppercase field names):
- `QBT_HOSTNAME`, `QBT_USERNAME`, `QBT_PASSWORD` - qBittorrent connection
- `QBT_PATH_MAPPING` - Path translation between qBittorrent and local filesystem (format: `local_path:remote_path`)
- `MEDIA_DATA_LOCATION` - Where to place downloaded episodes
- `PREFER_EXTENDED` - Prefer extended episode versions when available
- `QBT_POLLING_RATE` - Download status polling interval in seconds
