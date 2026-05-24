# Docker Containerization

## Purpose

Make Pace Downloader runnable as a Dockerized app while exposing only the SvelteKit frontend to the host network.

The first Docker target is a **single app image** that runs both:

- the SvelteKit Node server
- the FastAPI backend

FastAPI must stay private inside the container. Browser-visible requests should go through the SvelteKit frontend.

## Product Goal

A user should be able to run:

```bash
docker compose up --build
```

Then open:

```text
http://localhost:3000
```

The public container surface should be:

- `/` and normal app routes from SvelteKit
- `/api/...` proxied by SvelteKit to FastAPI
- `/posters/...` proxied by SvelteKit to FastAPI poster static files
- `/health` as the public container health endpoint

Port `8000` should not be published to the host.

## Non-Goals

- Do not include qBittorrent in the default Compose stack.
- Do not require Nginx for the first Docker version.
- Do not switch from SQLite to another database.
- Do not hand-edit `frontend/src/lib/types/api.d.ts`.
- Do not require local development to run through Docker.

## Runtime Model

Inside the container:

- FastAPI listens on `127.0.0.1:8000`.
- SvelteKit listens on `0.0.0.0:3000`.
- The host maps only `PACE_PORT` to container port `3000`.
- SvelteKit calls FastAPI through `BACKEND_INTERNAL_URL`.

Default internal backend URL rules:

- Docker image default: `BACKEND_INTERNAL_URL=http://127.0.0.1:8000`
- Frontend code fallback: `http://localhost:8000` when the variable is missing

This keeps local development simple:

```bash
cd backend
fastapi dev main.py

cd frontend
pnpm dev
```

In local development, browser calls still go to same-origin frontend paths such as `/api/settings`; SvelteKit proxies those to `http://localhost:8000`.

## Persistent Data

Use a named Docker volume for app runtime data:

```text
pace-data:/var/lib/pace-downloader
```

The backend process should run with `/var/lib/pace-downloader` as its working directory so existing relative paths persist there:

- `backend.sqlite3`
- `data/`
- `logs/`

Media and download paths should be explicit bind mounts chosen by the user.

Example container paths:

- `/media` for the Jellyfin-ready output location
- `/downloads` for qBittorrent-visible downloads when needed for path mapping

## Public And Internal URLs

The app should stop requiring browser code to know the backend origin.

Browser-facing frontend code should use:

```text
/api/settings
/api/events/downloads
/api/episode/{id}/download
/posters/...
```

Server-only SvelteKit code may call FastAPI directly through the internal URL:

```text
BACKEND_INTERNAL_URL/settings
BACKEND_INTERNAL_URL/app-state
```

The old browser-public backend URL environment variable should not be used for normal app API calls.

## SvelteKit Proxy Routes

Add a catch-all API proxy:

```text
frontend/src/routes/api/[...path]/+server.ts
```

It should:

- read `BACKEND_INTERNAL_URL` from `$env/dynamic/private`
- fall back to `http://localhost:8000`
- preserve the request path and query string
- forward request method, headers, and body
- return the backend response status, headers, and body stream
- support `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`, and `HEAD`

Add a poster proxy:

```text
frontend/src/routes/posters/[...path]/+server.ts
```

It should forward to FastAPI `/posters/...` and preserve content headers so images render normally.

Add a public frontend health endpoint:

```text
frontend/src/routes/health/+server.ts
```

It should return `200` when SvelteKit can reach FastAPI and a non-`200` response when the internal backend is unavailable. Use `/health`, not `/healthz`.

`frontend/src/hooks.server.ts` must not redirect or block `/api`, `/posters`, or `/health`.

## Docker Files

Add:

- `Dockerfile`
- `.dockerignore`
- `compose.yaml`
- `docker/start.py`

The Docker image should build the frontend with `pnpm build`, install backend Python dependencies from `backend/requirements.txt`, and run both services in the final image.

`docker/start.py` should:

- create the persistent data directories if missing
- start FastAPI with `uvicorn main:app --app-dir /app/backend --host 127.0.0.1 --port 8000`
- start SvelteKit with `node build`
- set `HOST=0.0.0.0` and `PORT=3000` for SvelteKit
- forward `SIGTERM` and `SIGINT` to both children
- exit non-zero if either child exits unexpectedly

The final image should set:

```dockerfile
ENV BACKEND_INTERNAL_URL=http://127.0.0.1:8000
```

## Compose Defaults

Default service:

```yaml
services:
  pace-downloader:
    build: .
    ports:
      - "${PACE_PORT:-3000}:3000"
    volumes:
      - pace-data:/var/lib/pace-downloader
```

Include Linux host qBittorrent support:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

This is only needed when qBittorrent runs directly on the Docker host and the app uses:

```text
QBT_HOSTNAME=http://host.docker.internal:8080
```

If qBittorrent runs on another machine or another container network, use that address instead.

Document common environment values:

```env
MEDIA_DATA_LOCATION=/media
QBT_HOSTNAME=http://host.docker.internal:8080
QBT_PATH_LOCAL=/downloads
QBT_PATH_REMOTE=/downloads
PREFER_EXTENDED=true
LOG_LEVEL=INFO
```

## Implementation Slices

### Slice 1: Backend URL Helper And Proxy Foundation

- Add a small frontend server-only helper for resolving `BACKEND_INTERNAL_URL` with fallback to `http://localhost:8000`.
- Add `/api/[...path]` proxy route.
- Add `/posters/[...path]` proxy route.
- Add `/health` route.
- Update `hooks.server.ts` to skip route guarding for `/api`, `/posters`, and `/health`.

Validation:

```bash
cd frontend
pnpm build
```

### Slice 2: Move Browser Calls To Same-Origin Paths

- Replace browser-side API fetches in `.svelte` files with `/api/...`.
- Replace browser-side `EventSource` URLs with `/api/events/downloads`.
- Ensure image URLs rendered to the DOM use `/posters/...`.
- Keep server loads working, either by using the server-only internal backend helper or by using same-origin proxy paths where appropriate.

Validation:

```bash
cd frontend
pnpm build
```

Manual checks:

- Setup wizard loads through the frontend.
- Settings save calls `/api/settings`.
- Download actions call `/api/episode/...`.
- SSE connects to `/api/events/downloads`.
- Season posters load from `/posters/...`.

### Slice 3: Container Runtime

- Add `Dockerfile`.
- Add `.dockerignore`.
- Add `docker/start.py`.
- Make the backend runtime work from `/var/lib/pace-downloader`.
- Ensure `data/eps-metadata/One Pace` exists before FastAPI mounts `/posters`.

Validation:

```bash
docker build -t pace-downloader .
```

### Slice 4: Compose And Persistent Storage

- Add `compose.yaml`.
- Publish only port `3000`.
- Add `pace-data` named volume.
- Add example media/download bind mounts as commented guidance.
- Add `extra_hosts` for host qBittorrent support.

Validation:

```bash
docker compose up --build
```

Manual checks:

- `http://localhost:3000` loads.
- `http://localhost:3000/health` returns a useful status.
- `http://localhost:8000` is not reachable unless the user separately runs a local backend.
- Restarting the service preserves SQLite setup state.

### Slice 5: Documentation

- Update `README.md` with Docker quickstart.
- Document qBittorrent connection examples:
  - qBittorrent on the Docker host via `host.docker.internal`
  - qBittorrent on another machine via LAN IP/DNS
  - qBittorrent in another Docker stack via an attached network or reachable hostname
- Document media and download bind mount expectations.
- Replace old `QBT_PATH_MAPPING` wording with `QBT_PATH_LOCAL` and `QBT_PATH_REMOTE`.

Validation:

```bash
rg "QBT_PATH_MAPPING|healthz" README.md AGENTS.md CLAUDE.md docs frontend
rg "PUBLIC_.*BACKEND" README.md AGENTS.md CLAUDE.md docs frontend
```

## End-To-End Acceptance Checklist

- Frontend is reachable at `http://localhost:${PACE_PORT:-3000}`.
- Backend port `8000` is not published by Compose.
- `/api/...` forwards JSON and mutation requests to FastAPI.
- `/api/events/downloads` streams SSE without buffering symptoms.
- `/posters/...` returns poster images.
- `/health` reflects frontend-to-backend reachability.
- Fresh Docker volume redirects app routes to `/setup`.
- Saving initial setup shows the restart-required state.
- `docker compose restart pace-downloader` applies saved setup.
- App state survives container recreation because `pace-data` persists.
- Local non-Docker development still works without setting `BACKEND_INTERNAL_URL`.
