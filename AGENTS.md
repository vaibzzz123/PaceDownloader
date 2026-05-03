# AGENTS.md

This file guides coding agents working in this repository.

## Project Snapshot

- `Pace-DL` is a full-stack app for browsing and downloading One Pace episodes through qBittorrent and organizing them for Jellyfin.
- The backend is `FastAPI` + `SQLite`.
- The frontend is `SvelteKit 2` + `Svelte 5` runes + `Skeleton UI`.
- Frontend tooling also includes `Tailwind CSS 4`, `Lucide Svelte`, `Fuse.js`, strict `TypeScript`, and `openapi-typescript`.
- Backend libraries worth knowing about include `Pydantic v2`, `qbittorrent-api`, `pynyaasi`, `openpyxl`, and `GitPython`.
- The project is still in active development, so prefer focused changes over broad refactors unless the user explicitly asks for one.

## First Pass

- Start by reading [README.md](README.md) and the files closest to the requested change.
- Check the working tree before editing and do not overwrite unrelated user changes.
- Treat `.env` files, qBittorrent credentials, and local media paths as sensitive.
- Do not treat runtime artifacts like `backend/backend.sqlite3` or downloaded metadata under `backend/data/` as source files to hand-edit.

## MCP And Documentation Workflow

- Use `ctx7` when the user asks about a library, framework, SDK, API, CLI tool, or cloud service, or when you need current setup/configuration guidance.
- Exception: for `Svelte` or `SvelteKit` topics, prefer the Svelte MCP server instead of `ctx7`.
- Use Chrome DevTools MCP for browser-side work when it helps: reproducing UI bugs, checking console/network failures, validating rendered pages, or smoke-testing frontend changes.
- Resolve the library first:

```bash
npx ctx7@latest library "<official library name>" "<user question>"
```

- Then fetch docs with the chosen `/org/project` ID:

```bash
npx ctx7@latest docs <libraryId> "<user question>"
```

- Use the full user question as the query so the returned docs are specific.
- If `ctx7` fails with a quota/login error, tell the user to run `npx ctx7@latest login` or set `CONTEXT7_API_KEY`; do not silently fall back to stale memory for library-specific answers.

### Svelte MCP Workflow

- For `Svelte` and `SvelteKit` questions, start with `list_sections`.
- After reviewing the returned sections and `use_cases`, fetch all relevant sections with `get_documentation`.
- Use `svelte_autofixer` whenever you write or significantly edit Svelte code before handing it off.
- If `svelte_autofixer` returns issues or suggestions, fix them and run it again until the result is clean.
- Only use `playground_link` after asking the user if they want a playground link.
- Never use `playground_link` for code that has already been written into this repository's files.

## Repo Layout

- `backend/`
  FastAPI app, SQLite helpers, metadata ingestion, qBittorrent integration, SSE events, and tests.
- `frontend/`
  SvelteKit app with route-level server loads, reusable components, and generated API typings.
- `frontend/src/lib/types/api.d.ts`
  Generated from the backend OpenAPI spec. Do not hand-edit this file.
- `CLAUDE.md`
  Useful repository notes and command references; keep `AGENTS.md` and `CLAUDE.md` aligned when updating shared workflow guidance.

## Backend Notes

- Run backend commands from `backend/`.
- `main.py` performs important startup work immediately: loads env vars, initializes the database, configures logging, refreshes metadata, constructs the qBittorrent client and `DownloadManager`, then starts polling and a startup scan.
- Settings live in SQLite but may be overridden by environment variables. If you add or rename a setting, update all of these together:
  - `backend/db.py`
  - backend models / API request-response types
  - settings routes
  - `frontend/src/routes/settings/+page.svelte`
  - README or other setup docs if behavior changes
- Download state is spread across the DB layer, `download_manager.py`, API routes, and SSE events. Keep those parts consistent when changing statuses or lifecycle behavior.
- qBittorrent path mapping matters for Docker/NFS setups. Be careful when changing anything related to `qbt_path_local`, `qbt_path_remote`, file linking, or disk paths.
- Prefer mocking qBittorrent, filesystem, and remote metadata sources in tests rather than hitting live services.

## Frontend Notes

- Run frontend commands from `frontend/` using `pnpm`.
- Follow the existing Svelte 5 style: use runes like `$state`, `$derived`, and `$effect` instead of introducing older store-heavy patterns unless the surrounding code already uses them.
- For Svelte/SvelteKit documentation or API questions, use the Svelte MCP workflow above instead of generic library lookup.
- Data is commonly fetched in `+page.server.ts` files, then copied into local mutable state so SSE updates can patch rows in place without full reloads.
- The season and downloads pages depend on SSE status payloads from the backend. If backend event names or status strings change, update the frontend maps at the same time.
- Keep using the existing UI stack and patterns:
  - Skeleton UI components/utilities
  - Lucide Svelte icons
  - Tailwind CSS 4 utilities and existing theme files
  - Fuse.js-backed search behavior in reusable tables
  - table-based reusable components like `ColorTable`
  - `PUBLIC_BACKEND_URL` for backend requests
- Quote shell paths that include route params such as `frontend/src/routes/season/[id]/+page.svelte` when using `zsh`, or the shell will treat brackets as globs.

## API And Types

- Backend changes to routes, response models, or request payloads usually require regenerating frontend types:

```bash
cd frontend
pnpm generate-types
```

- `generate-types` expects the backend to be running at `http://localhost:8000`.
- After regenerating types, review affected pages and components for shape changes instead of assuming type generation is the only required update.

## Common Commands

Backend:

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
fastapi dev main.py
pytest
pytest tests/test_qbittorrent.py -v
```

Frontend:

```bash
cd frontend
pnpm install
pnpm dev
pnpm build
pnpm generate-types
```

## Validation

- For backend-only changes, run the smallest relevant `pytest` scope first, then broader tests if needed.
- For frontend-only changes, run `pnpm build`.
- For user-facing frontend changes, use Chrome DevTools MCP for a quick sanity check when feasible.
- For API contract changes, regenerate `frontend/src/lib/types/api.d.ts` and then run the frontend build.
- If validation is skipped because local services, env vars, or networked dependencies are unavailable, say so explicitly in the final handoff.

## High-Risk Areas

- `backend/download_manager.py`
  Coordinates status transitions, qBittorrent actions, linking/copying, and DB updates.
- `backend/metadata.py`
  Joins multiple external metadata sources and can affect season/episode identity across the app.
- `backend/db.py`
  Contains lightweight migrations; schema changes should remain backward-compatible with existing local DBs.
- `frontend/src/routes/downloads/+page.svelte`
  Mixes server-loaded data, optimistic UI, SSE updates, and tab/query-param behavior.
- `frontend/src/routes/settings/+page.svelte`
  Mirrors backend settings shape closely, including env-override handling.

## Change Style

- Prefer small, coherent changes that preserve current architecture.
- Keep backend and frontend terminology aligned, especially around statuses and setting names.
- When a change affects both the backend contract and the UI, update both in the same pass.
- Add brief comments only where the code would otherwise be hard to follow.
