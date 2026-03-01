# Pace-DL

A full-stack web app that automates downloading [One Pace](https://onepace.net) episodes (fan-edited One Piece anime) via qBittorrent and organizes them into the correct media structure for a [Jellyfin](https://jellyfin.org) media server.

## What It Does

One Pace releases episodes as torrents on Nyaa.si. This app provides a web UI to browse all arcs and episodes, then downloads selected episodes through qBittorrent and places the files where Jellyfin expects them — with proper naming so metadata scraping works correctly.

**Key features:**
- Browse all One Pace arcs and episodes with posters and descriptions
- Download individual episodes or entire arcs
- Track download progress with status per episode
- Spoiler mode to hide episode titles, season images, and season descriptions
- Dark mode
- Configurable qBittorrent integration (supports Docker path mapping)
- Prefers extended episode versions when available

> **Work in progress** — this project is not yet ready for general use. Core download functionality and setup flow are still being built. See [TODO.txt](TODO.txt) for what's planned.

## Prerequisites

- **qBittorrent** with Web UI enabled (accessible from the machine running this app)
- **Python 3.14+** for the backend
- **Node.js 24+** for the frontend
- A running **Jellyfin** instance with a configured media library

## Setup

### 1. Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create a .env file in the root directory of the backend (for development, see below):
touch backend/.env

# Run the development server
fastapi dev main.py
# Backend is now available at http://localhost:8000
```

### 2. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Create a .env file in the root directory of the frontend (for development, see below):
touch frontend/.env

# Run the dev server
npm run dev
# Frontend is now available at http://localhost:5173
```

### 3. Configuration

On first run, configure the app via environment variables or the settings UI (in progress). Place the environment variables in a `.env` file in the root directory of the backend:

| Variable | Description | Default |
|---|---|---|
| `QBT_HOSTNAME` | qBittorrent Web UI URL (e.g. `http://localhost:8080`) | |
| `QBT_USERNAME` | qBittorrent username | |
| `QBT_PASSWORD` | qBittorrent password | |
| `MEDIA_DATA_LOCATION` | Path where downloaded episodes will be placed for Jellyfin | |
| `QBT_PATH_MAPPING` | Path translation for Docker/NFS setups (`local_path:remote_path`) | |
| `QBT_CATEGORY` | qBittorrent category to assign to torrents | |
| `QBT_DOWNLOAD_LOCATION` | Custom download directory in qBittorrent | |
| `PREFER_EXTENDED` | Prefer extended episode versions (`true`/`false`) | `true` |
| `QBT_POLLING_RATE` | Download status polling interval in seconds | `10` |
| `LOG_LEVEL` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |

Settings can also be stored in the SQLite database (`backend/backend.sqlite3`). Environment variables take precedence over database values.

Also create a `.env` file in the root directory of the frontend (for development):

```
BACKEND_URL=http://localhost:8000
```

**Path mapping example** (qBittorrent in Docker):
```
QBT_PATH_MAPPING=/mnt/media:/downloads
```
This translates `/downloads/file.mkv` (qBittorrent's view) to `/mnt/media/file.mkv` (local filesystem view/view from this app's container once implemented).

## Architecture

```
┌─────────────────┐         ┌─────────────────┐
│  SvelteKit UI   │ ──────► │ FastAPI Backend │
│  :5173          │         │ :8000           │
└─────────────────┘         └────────┬────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
             ┌──────────┐   ┌──────────────┐  ┌──────────┐
             │ SQLite   │   │  qBittorrent │  │ Nyaa.si  │
             │ (state)  │   │  (torrents)  │  │ (search) │
             └──────────┘   └──────────────┘  └──────────┘
```

### Data Flow

1. **Metadata**: On startup, the backend clones [`tissla/one-pace-jellyfin`](https://github.com/tissla/one-pace-jellyfin) for NFO metadata and downloads a Google Sheets export of the official [One Pace Episode Guide](https://docs.google.com/spreadsheets/d/1HQRMJgu_zArp-sLnvFMDzOyjdsht87eFLECxMK858lA/edit?gid=0#gid=0). These are joined to create a unified episode list and internal metadata for the application.

2. **Browsing**: The SvelteKit frontend fetches season/episode data from the FastAPI backend and displays it with posters, titles, and descriptions.

3. **Downloading**: When you request an episode download, the backend looks up the torrent on Nyaa.si, adds it to qBittorrent (setting file priorities so only the requested episode downloads), and polls for completion. Once done, the file is hardlinked (or copied) to the Jellyfin media location.

### Backend Structure

```
backend/
├── main.py              - App entry point, startup tasks
├── api.py               - REST API routes
├── models.py            - Pydantic response models
├── db.py                - SQLite helpers (settings, downloads)
├── metadata.py          - Episode metadata parsing and joining
├── download_manager.py  - Download orchestration + polling
├── qbittorrent.py       - qBittorrent client wrapper
├── data_sources.py      - Git clone + Sheets download
├── nyaa_utils.py        - Nyaa.si torrent lookup
└── logging_config.py    - Logging setup
```

### Frontend Structure

```
frontend/src/
├── lib/
│   ├── components/      - Reusable UI components
│   ├── state/           - Global app state (dark/spoiler mode)
│   └── types/           - Auto-generated API types
└── routes/
    ├── +page.svelte     - Home: season grid
    ├── downloads/       - Download tracking page
    └── season/[id]/     - Season detail + episode list
```

### API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `GET` | `/season` | List all seasons |
| `GET` | `/season/{num}` | Get season details |
| `GET` | `/season/{num}/episodes` | Get episodes with download status |
| `GET` | `/events` | SSE stream for download progress |
| `GET` | `/posters/*` | Season poster images |

The backend exposes an OpenAPI spec at `/openapi.json`. Run `npm run generate-types` in the frontend to regenerate TypeScript types from it.

## Development

### Backend tests

```bash
cd backend
pytest                              # run all tests
pytest tests/test_qbittorrent.py -v # run a specific file
pytest --cov                        # with coverage
```

### Regenerate frontend types

With the backend running:

```bash
cd frontend && npm run generate-types
```

### Production build

```bash
cd frontend && npm run build
```

## Tech Stack

**Frontend:** SvelteKit 2, Svelte 5 (runes), Skeleton UI v4, Tailwind CSS 4, TypeScript

**Backend:** FastAPI, Pydantic v2, SQLite, qbittorrent-api, pynyaasi, openpyxl, GitPython

## License

MIT — see [LICENSE](LICENSE)
