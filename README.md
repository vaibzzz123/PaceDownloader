# Pace Downloader

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
- **Docker** with the Docker Compose plugin for the containerized setup
- **Python 3.14+** for local backend development
- **Node.js 24+** for local frontend development
- **pnpm 10+** for local frontend dependencies (Corepack recommended)
- A running **Jellyfin** instance with a configured media library

## Setup

### Option A: Docker Quickstart

The Docker setup builds one app image that runs both the SvelteKit frontend and the FastAPI backend. Only the frontend port is published to the host; browser calls to `/api/...` and `/posters/...` are proxied internally to FastAPI.

```bash
cp compose.example.yml compose.yml
# Edit compose.yml for your media/download mounts and any environment overrides.
docker compose up --build
```

Then open:

```text
http://localhost:3000
```

By default, Compose binds the app to `127.0.0.1`, so it is only reachable from
the machine running Docker. Set `PACE_PORT` if you want a different host port:

```bash
PACE_PORT=3030 docker compose up --build
```

Do not expose Pace Downloader directly to the internet. It can control
qBittorrent, write to your configured media directories, and show local
configuration details. For remote access, put it behind a trusted VPN, reverse
proxy, or authentication layer. If you intentionally need it to listen on other
network interfaces, set `PACE_HOST` in your local environment or `compose.yml`.
The settings and setup endpoints intentionally handle local system information,
including qBittorrent connection details and media/download path configuration,
so treat the app as private infrastructure.

The container stores runtime data in the `pace-data` named volume at `/var/lib/pace-downloader`, including:

- `backend.sqlite3`
- `data/`
- `logs/`

The public container health endpoint is:

```text
http://localhost:3000/health
```

Port `8000` is intentionally not published by the Compose file.

For Docker, pass configuration through your shell, a repo-root `.env` file next to `compose.yml`, or the local `compose.yml` itself. Do not commit credentials or local media paths.

#### Docker Media And Download Mounts

The app needs to see the Jellyfin-ready output path and, when qBittorrent downloads outside the app container, the downloaded files. Add bind mounts to `compose.yml` that match the paths you save in settings or pass through environment variables.

Common container paths:

```yaml
volumes:
  - pace-data:/var/lib/pace-downloader
  - /path/on/host/media:/media
  - /path/on/host/downloads:/downloads
```

Then configure:

```env
MEDIA_DATA_LOCATION=/media
QBT_PATH_LOCAL=/downloads
QBT_PATH_REMOTE=/downloads
```

`QBT_PATH_REMOTE` is the path prefix qBittorrent reports for downloaded files. `QBT_PATH_LOCAL` is the matching path prefix visible to Pace Downloader inside its container. Set both values together, or leave both empty if qBittorrent returns paths the app can already read.

For example, if qBittorrent reports `/data/torrents/episode.mkv` but the Pace Downloader container can read the same file as `/downloads/episode.mkv`, use:

```env
QBT_PATH_REMOTE=/data/torrents
QBT_PATH_LOCAL=/downloads
```

#### qBittorrent From Docker

If qBittorrent runs directly on the Linux Docker host, use the Compose-provided host gateway name. The provided `compose.example.yml` includes the needed `extra_hosts` entry; keep it in your local `compose.yml` when using this address.

```env
QBT_HOSTNAME=http://host.docker.internal:8080
```

If qBittorrent runs on another machine, use its LAN IP address or DNS name:

```env
QBT_HOSTNAME=http://192.168.1.50:8080
```

If qBittorrent runs in another Docker stack, connect both stacks to a shared Docker network or use any hostname reachable from the Pace Downloader container. For a shared external network, attach the service in `compose.yml`:

```yaml
services:
  pace-downloader:
    networks:
      - media

networks:
  media:
    external: true
```

Then use the qBittorrent service or container DNS name:

```env
QBT_HOSTNAME=http://qbittorrent:8080
```

After saving initial setup through the UI, restart the container so startup-only services are recreated with the saved settings:

```bash
docker compose restart pace-downloader
```

### Option B: Local Development

#### 1. Backend

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create a .env file in the backend directory (for development, see below):
touch .env

# Run the development server
fastapi dev main.py
# Backend is now available at http://localhost:8000
```

#### 2. Frontend

```bash
cd frontend

# Enable pnpm through Corepack if needed
corepack enable pnpm

# Install dependencies
pnpm install

# Run the dev server
pnpm dev
# Frontend is now available at http://localhost:5173
```

### Configuration

On first run, configure the app via environment variables or the settings UI (in progress). For local backend development, place environment variables in `backend/.env`:

| Variable | Description | Default |
|---|---|---|
| `QBT_HOSTNAME` | qBittorrent Web UI URL (e.g. `http://localhost:8080`) | |
| `QBT_USERNAME` | qBittorrent username | |
| `QBT_PASSWORD` | qBittorrent password | |
| `MEDIA_DATA_LOCATION` | Path where downloaded episodes will be placed for Jellyfin | |
| `QBT_PATH_LOCAL` | Path prefix visible to Pace Downloader for downloaded files | |
| `QBT_PATH_REMOTE` | Path prefix reported by qBittorrent for downloaded files | |
| `QBT_CATEGORY` | qBittorrent category to assign to torrents | |
| `QBT_DOWNLOAD_LOCATION` | Custom download directory in qBittorrent | |
| `PREFER_EXTENDED` | Prefer extended episode versions (`true`/`false`) | `true` |
| `QBT_POLLING_RATE` | Download status polling interval in seconds | `10` |
| `LOG_LEVEL` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |

Settings can also be stored in the SQLite database (`backend/backend.sqlite3`). Environment variables take precedence over database values.
API responses mask the qBittorrent password, but settings and setup validation
responses can still reveal local hostnames, usernames, and filesystem layout.
Keep the app on a trusted local network or behind access control.

The frontend does not need a `.env` file for the normal local setup. Browser requests use same-origin paths such as `/api/settings` and `/posters/...`, and SvelteKit proxies them to the FastAPI backend. By default, the frontend server calls the backend at `http://localhost:8000`.

If your local backend runs somewhere else, create `frontend/.env` and set:

```
BACKEND_INTERNAL_URL=http://localhost:8000
```

**Path mapping example** (qBittorrent reports a different path than Pace Downloader can read):

```
QBT_PATH_REMOTE=/downloads
QBT_PATH_LOCAL=/mnt/media
```

This translates `/downloads/file.mkv` from qBittorrent into `/mnt/media/file.mkv` for the backend.

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

1. **Metadata**: On startup, the backend clones [`tissla/one-pace-jellyfin`](https://github.com/tissla/one-pace-jellyfin) for NFO metadata, downloads a Google Sheets export of the official [One Pace Episode Guide](https://docs.google.com/spreadsheets/d/1HQRMJgu_zArp-sLnvFMDzOyjdsht87eFLECxMK858lA/edit?gid=0#gid=0), and fetches the One Pace releases RSS feed. The NFO files and spreadsheet rows are joined into the app's episode list, while parsed release records are cached under `backend/data/releases/` for torrent resolution.

2. **Browsing**: The SvelteKit frontend fetches season/episode data from the FastAPI backend and displays it with posters, titles, and descriptions.

3. **Downloading**: When you request an episode download, the backend uses the spreadsheet episode name, release date, and CRC32 to find a matching individual or batch release from the cached One Pace release feed. Candidate releases are verified against Nyaa.si file listings by CRC32 before their magnet links are added to qBittorrent. If the release feed is missing or stale, the resolver can fall back to a runtime Nyaa search by CRC32, but it still verifies the file listing, episode title, and release date before accepting a result. If a spreadsheet CRC or release date is known to be stale, `backend/release_crc32_overrides.json` can provide a metadata-only correction keyed by season and episode number; these overrides are only used after normal CRC verification fails. qBittorrent file priorities are set so only the requested episode downloads, and once done, the file is hardlinked (or copied) to the Jellyfin media location.

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
├── data_sources.py      - Git clone + Sheets/release feed downloads
├── release_resolver.py  - Release feed torrent matching + CRC verification
├── nyaa_utils.py        - Nyaa.si helper utilities
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

The backend exposes an OpenAPI spec at `/openapi.json`. Run `pnpm generate-types` in the frontend to regenerate TypeScript types from it.

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
cd frontend && pnpm generate-types
```

### Production build

```bash
cd frontend && pnpm build
```

## Tech Stack

**Frontend:** SvelteKit 2, Svelte 5 (runes), Skeleton UI v4, Tailwind CSS 4, TypeScript

**Backend:** FastAPI, Pydantic v2, SQLite, qbittorrent-api, pynyaasi, openpyxl, GitPython

## License

MIT — see [LICENSE](LICENSE)
