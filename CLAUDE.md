# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Pace-DL - A full-stack web app with a FastAPI backend and SvelteKit frontend that automates downloading One Pace episodes (fan-edited One Piece anime) via qBittorrent and places them in the correct media structure for Jellyfin media server.

## MCP Settings:

Always use Context7 MCP when I need library/API documentation, code generation, setup or configuration steps without me having to explicitly ask, Unless the conversation is about Svelte, at which point use the Svelte MCP server below.

You have access to the Chrome DevTools MCP for web related tasks as well.

You are able to use the Svelte MCP server, where you have access to comprehensive Svelte 5 and SvelteKit documentation. Here's how to use the available tools effectively:

### Available Svelte MCP Tools:

#### 1. list-sections

Use this FIRST to discover all available documentation sections. Returns a structured list with titles, use_cases, and paths.
When asked about Svelte or SvelteKit topics, ALWAYS use this tool at the start of the chat to find relevant sections.

#### 2. get-documentation

Retrieves full documentation content for specific sections. Accepts single or multiple sections.
After calling the list-sections tool, you MUST analyze the returned documentation sections (especially the use_cases field) and then use the get-documentation tool to fetch ALL documentation sections that are relevant for the user's task.

#### 3. svelte-autofixer

Analyzes Svelte code and returns issues and suggestions.
You MUST use this tool whenever writing Svelte code before sending it to the user. Keep calling it until no issues or suggestions are returned.

#### 4. playground-link

Generates a Svelte Playground link with the provided code.
After completing the code, ask the user if they want a playground link. Only call this tool after user confirmation and NEVER if code was written to files in their project.

## Common Commands

### Backend

All commands run from the `backend/` directory:

```bash
# Install dependencies (use venv at backend/venv/)
cd backend && pip install -r requirements.txt

# Run the backend (serves on http://localhost:8000)
cd backend && fastapi dev main.py

# Run all tests
cd backend && pytest

# Run a single test file
cd backend && pytest tests/test_qbittorrent.py -v

# Run tests with coverage
cd backend && pytest --cov
```

### Frontend

All commands run from the `frontend/` directory:

```bash
# Install dependencies
cd frontend && npm install

# Run the dev server (serves on http://localhost:5173)
cd frontend && npm run dev

# Generate TypeScript types from backend OpenAPI spec (backend must be running)
cd frontend && npm run generate-types

# Build for production
cd frontend && npm run build
```

## Tech Stack

### Frontend
- **SvelteKit 2** with **Svelte 5** (uses modern runes: `$state`, `$derived`, `$effect`, and snippets)
- **Skeleton UI v4** (`@skeletonlabs/skeleton` + `@skeletonlabs/skeleton-svelte`) - all shadcn components were removed
- **Tailwind CSS 4** with Vite plugin
- **Fuse.js** for fuzzy search in tables
- **Lucide Svelte** for icons
- **openapi-typescript** for auto-generating TypeScript types from backend OpenAPI spec
- **TypeScript** with strict mode

### Backend
- **FastAPI** with **Uvicorn** ASGI server
- **Pydantic v2** for data validation and API models
- **SQLite** via `sqlite3` module
- **qbittorrent-api** for qBittorrent interaction
- **pynyaasi** for Nyaa.si torrent search
- **openpyxl** for Excel/Google Sheets parsing
- **GitPython** for cloning/updating metadata repo

## Architecture

### Frontend Structure

```
frontend/src/
├── lib/
│   ├── components/
│   │   ├── ColorTable/         - Reusable table with fuzzy search, row highlighting, status-based row colors
│   │   ├── DownloadProgress/   - Progress bar with status-based styling and animations
│   │   ├── LeftSideMenu/       - Side drawer navigation (Skeleton Drawer)
│   │   ├── SeasonCard/         - Card displaying season poster, title, and description
│   │   ├── SeasonGrid/         - CSS grid layout for season cards
│   │   ├── SeasonInfo/         - Season detail header (poster + info)
│   │   └── SpoilerText/        - Text component that hides content in spoiler mode
│   ├── state/
│   │   └── index.svelte.ts     - Global app state (dark mode, spoiler mode) persisted to localStorage
│   └── types/
│       └── api.d.ts            - Auto-generated TypeScript types from OpenAPI spec
├── routes/
│   ├── +layout.svelte          - Root layout with sidebar, dark/spoiler mode toggles
│   ├── +page.svelte            - Home page: season grid
│   ├── +page.server.ts         - Server load: fetches all seasons from API
│   ├── downloads/
│   │   └── +page.svelte        - Downloads page with episode/torrent tabs and search
│   └── season/[id]/
│       ├── +page.svelte        - Season detail: episode list with download actions
│       └── +page.server.ts     - Server load: fetches season-specific data from API
├── app.css                     - Tailwind + Skeleton + custom imports
└── PaceDownloaderPurple.css    - Custom Skeleton theme
```

**Key frontend patterns:**
- Server-side data fetching via `+page.server.ts` files calling the FastAPI backend
- ColorTable uses Svelte 5 snippets for flexible cell/header rendering while staying abstract
- URL query params used for tab navigation and row highlighting (no page re-renders)
- Global state uses Svelte 5 runes with a blocking script for early localStorage injection

### Backend Structure

```
backend/
├── main.py                   - FastAPI app setup, static file mounts, metadata init
├── api.py                    - API route definitions
├── models.py                 - Pydantic response models (e.g. SeasonResponse)
├── db.py                     - SQLite database with settings, torrent, and episode tables
├── metadata.py               - Episode metadata parsing, NFO + Sheets joining
├── download_manager.py       - Download orchestration with background polling
├── qbittorrent.py            - qBittorrent client wrapper
├── data_sources.py           - External data fetching (Git clone, Sheets download)
├── nyaa_utils.py             - Nyaa.si torrent lookup
├── logging_config.py         - Centralized logging configuration
├── season_descriptions.json  - Season/arc description text
└── tests/
    └── test_qbittorrent.py
```

### API Endpoints

```
GET  /                    - Health check
GET  /season              - List all seasons (returns SeasonResponse[])
GET  /season/{season_num} - Get specific season with episode details
GET  /posters/*           - Static file serving for season poster images
```

The backend generates an OpenAPI spec at `/openapi.json` which the frontend uses to auto-generate TypeScript types.

### Data Flow

1. **Metadata Collection**: Episode metadata comes from two sources:
   - NFO files from `tissla/one-pace-jellyfin` GitHub repo (cloned to `data/eps-metadata/`)
   - Google Sheets XLSX export containing CRC32 checksums and Nyaa torrent links (saved to `data/sheets/`)

2. **Episode Mapping**: `metadata.py:build_episode_mapping()` joins NFO file data with Google Sheets data to create a unified episode list with torrent info. `metadata.py:refresh_and_build_mapping()` is the single entry point used by both startup and API refresh.

3. **API Layer**: FastAPI serves season/episode data to the SvelteKit frontend. Poster images are served as static files (not base64-encoded). Pydantic models in `models.py` define the response shapes and generate the OpenAPI spec.

4. **Download Process**:
   - `DownloadManager` receives episode download requests
   - Fetches torrent info from Nyaa.si via `nyaa_utils.py`
   - Creates/manages torrents through `QbittorrentClient`
   - Uses CRC32 in filename to identify correct file within multi-file torrents
   - Polls for download completion and hardlinks/copies files to media location

### Key Backend Modules

- **main.py**: FastAPI app creation, mounts static files for poster images at `/posters`, includes API router, initializes metadata on startup.

- **api.py**: FastAPI route definitions with type-annotated endpoints for proper OpenAPI spec generation.

- **models.py**: Pydantic `BaseModel` classes (e.g. `SeasonResponse` with `num`, `title`, `description`, `image` fields) used as FastAPI response models.

- **db.py**: SQLite database with three tables: `settings` (singleton), `torrent_download`, `episode_download`. Settings support environment variable overrides.

- **download_manager.py**: Orchestrates downloads with background polling thread. Episode states: `pending` → `downloading` → `paused` → `hardlink`/`copy`/`error`

- **qbittorrent.py**: Wrapper around `qbittorrent-api`. Handles torrent creation, file priority management (to download specific files), metadata waiting, and path translation for Docker/NFS setups.

- **metadata.py**: Maps integer season numbers (from NFO) to arc names (from Sheets), handles naming mismatches between sources. Has a global metadata handler instance rather than static instances.

- **data_sources.py**: Responsible only for downloading and storing raw data (Git clone, Sheets XLSX). 24-hour caching by default.

- **logging_config.py**: Centralized logging setup, configurable via `LOG_LEVEL` env var.

### Configuration

Settings stored in SQLite but overridable via environment variables (uppercase field names):
- `QBT_HOSTNAME`, `QBT_USERNAME`, `QBT_PASSWORD` - qBittorrent connection
- `QBT_PATH_MAPPING` - Path translation between qBittorrent and local filesystem (format: `local_path:remote_path`)
- `MEDIA_DATA_LOCATION` - Where to place downloaded episodes
- `PREFER_EXTENDED` - Prefer extended episode versions when available
- `QBT_POLLING_RATE` - Download status polling interval in seconds
- `LOG_LEVEL` - Logging verbosity
