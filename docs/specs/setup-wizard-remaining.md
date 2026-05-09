# Setup Wizard Remaining Implementation Spec

## Purpose

Finish **Initial Setup** for Pace Downloader without bundling every remaining change into one large patch.

This spec is written for agents/subagents working independently on slices. Each slice should be small, testable, and should avoid changing unrelated behavior.

## Current State

The setup wizard UI shell exists in the frontend.

The backend now exposes setup status and validation endpoints:

- `GET /setup/status`
- `POST /setup/validate/media`
- `POST /setup/validate/qbittorrent`
- `POST /setup/validate/path-mapping`

The backend setup validation logic lives in:

- `backend/setup_validation.py`
- `backend/models.py`
- `backend/api.py`
- `backend/tests/test_setup_validation.py`

Backend validation currently covers:

- required setup fields
- media path existence/directory/writability
- qBittorrent login/connectivity
- optional path mapping consistency
- local qBittorrent path existence when mapping is configured

Auth is intentionally out of scope for v1.

## Non-Goals

- Do not add username/password app auth.
- Do not redesign the whole settings page.
- Do not change download logic unless working on the backend boot/runtime-error slice.
- Do not add remote path probing through qBittorrent unless explicitly asked later.
- Do not hand-edit `frontend/src/lib/types/api.d.ts`; regenerate it from OpenAPI.

## API Contract

### `GET /setup/status`

Returns whether setup configuration fields are populated and which steps are incomplete.

Important: `complete` means the required configuration is saved. For v1, **Initial Setup** is not fully complete until the backend/container has restarted and applied that saved configuration.

Expected shape:

```json
{
  "required": true,
  "complete": false,
  "missing_fields": ["media_data_location", "qbt_hostname"],
  "steps": [
    {
      "id": "media",
      "complete": false,
      "required": true,
      "missing_fields": ["media_data_location"],
      "errors": []
    }
  ]
}
```

Known step IDs:

- `media`
- `qbt`
- `paths`
- `preferences`

Frontend owns display labels and step order.

### `POST /setup/validate/media`

Request:

```json
{
  "media_data_location": "/media/One Pace"
}
```

`media_data_location` means the **Media Data Location**: the path visible to Pace Downloader where organized episode files will be placed. It is not necessarily the path Jellyfin uses inside its own container.

Response:

```json
{
  "ok": true,
  "message": "Media data location is valid",
  "details": {
    "path": "/media/One Pace",
    "exists": true,
    "is_dir": true,
    "writable": true
  }
}
```

### `POST /setup/validate/qbittorrent`

Request:

```json
{
  "qbt_hostname": "http://qbittorrent:8080",
  "qbt_username": "admin",
  "qbt_password": "adminadmin"
}
```

Response:

```json
{
  "ok": true,
  "message": "qBittorrent connection is valid",
  "details": {
    "version": "v5.0.0"
  }
}
```

### `POST /setup/validate/path-mapping`

Request:

```json
{
  "qbt_path_local": "/mnt/downloads",
  "qbt_path_remote": "/downloads"
}
```

Path mapping is optional. It is required only when qBittorrent reports torrent file paths from a different filesystem perspective than Pace Downloader can access.

Example:

- qBittorrent reports `/downloads/torrent_folder_1/torrent_file_1.mkv`
- Pace Downloader can access the same file at `/data/torrents/downloads/torrent_folder_1/torrent_file_1.mkv`
- `qbt_path_remote=/downloads`
- `qbt_path_local=/data/torrents/downloads`

If there is no mismatch, both fields should be left empty and Pace Downloader will treat qBittorrent-reported paths as directly usable.

Response:

```json
{
  "ok": true,
  "message": "qBittorrent path mapping is valid",
  "details": {
    "mapping_required": true,
    "local_path": "/mnt/downloads",
    "remote_path": "/downloads",
    "local_exists": true,
    "local_is_dir": true
  }
}
```

Remote path is trusted. Runtime placement/linking errors should be surfaced separately.

## Slice 1: Regenerate API Types

### Goal

Expose new setup endpoints to frontend TypeScript.

### Ownership

Frontend generated API types only.

### Files

- `frontend/src/lib/types/api.d.ts`

### Steps

1. Start backend locally.
2. Run from `frontend/`:

   ```bash
   pnpm generate-types
   ```

3. Review generated diff.

### Acceptance Criteria

- Generated types include setup status and validation endpoints.
- No manual edits to generated file.
- Frontend build still passes after later slices.

### Notes

`pnpm generate-types` expects backend at `http://localhost:8000`.

## Slice 2: Frontend Setup API Helpers

### Goal

Create a small typed client layer for setup status, validation, and final save.

### Ownership

Frontend setup API utilities.

### Candidate Files

- `frontend/src/lib/api/setup.ts`
- existing API utility files, if any
- `frontend/src/lib/types/api.d.ts`

### Steps

1. Inspect current frontend fetch patterns.
2. Add helpers for:
   - fetch setup status
   - validate media
   - validate qBittorrent
   - validate path mapping
   - save settings through existing `PUT /settings`
3. Use `PUBLIC_BACKEND_URL`.
4. Keep helper responses close to generated OpenAPI types.

### Acceptance Criteria

- Helpers do not duplicate endpoint strings throughout components.
- Failed HTTP requests throw useful errors.
- Validation responses with `ok: false` do not throw by default; UI should display their message.

### Tests

- Typecheck/build in frontend.

## Slice 3: Wizard Form State And Validation Wiring

### Goal

Wire current `SetupWizard.svelte` UI to backend validation endpoints without redirect guard yet.

### Ownership

Setup wizard component and setup route only.

### Candidate Files

- `frontend/src/lib/components/SetupWizard/SetupWizard.svelte`
- `frontend/src/routes/setup/+page.svelte`
- setup API helper from Slice 2

### Steps

1. Add form state for:
   - `media_data_location`
   - `qbt_hostname`
   - `qbt_username`
   - `qbt_password`
   - `qbt_path_local`
   - `qbt_path_remote`
   - `prefer_extended`
   - `qbt_category`
   - `qbt_download_location`
   - `qbt_polling_rate`
   - `log_level`
2. Replace all dummy `"<Step> form fields go here"` placeholders with real fields.
3. Follow existing settings page field patterns where appropriate:
   - Skeleton `label`, `input`, `select`, and `checkbox` classes
   - same setting names as `frontend/src/routes/(app)/settings/+page.svelte`
   - qBittorrent password input uses `type="password"` and `autocomplete="new-password"`
   - user-facing labels use friendly domain language instead of raw setting keys
   - fields with Docker/path ambiguity include short descriptions below the label
4. Media step calls `POST /setup/validate/media`.
5. qBittorrent step calls `POST /setup/validate/qbittorrent`.
6. Paths step calls `POST /setup/validate/path-mapping`.
7. Preferences step should show optional defaults for `prefer_extended`, `qbt_category`, `qbt_download_location`, `qbt_polling_rate`, and `log_level`.
8. Optional preference fields should not block Initial Setup unless backend settings validation rejects the final save.
9. Make it clear through field grouping and defaults that these values can be left unchanged.
10. Review step shows summarized values, with password masked.

### Acceptance Criteria

- User cannot advance past media/qBittorrent/path steps when validation returns `ok: false`.
- Validation message appears near relevant fields.
- The wizard contains no dummy placeholder field text.
- Form controls match existing Skeleton/settings page patterns unless a setup-specific layout is clearer.
- User-facing field labels are friendly and descriptive; raw setting names stay in code.
- qBittorrent password is never displayed in review.
- Advanced/default settings are visible during Initial Setup but are not explicitly required.
- Empty path mapping is accepted.
- One-sided path mapping is rejected.
- UI remains usable in light and dark mode.

### Tests

- Frontend build.
- Manual browser check on `/setup`.
- Optional component tests if existing test infra supports them.

## Slice 4: Save Settings And Completion UX

### Goal

Persist completed setup through existing settings save endpoint.

### Ownership

Setup wizard save behavior.

### Candidate Files

- `frontend/src/lib/components/SetupWizard/SetupWizard.svelte`
- setup API helper
- settings types

### Steps

1. On final step, submit full settings payload to `PUT /settings`.
2. Ensure `qbt_polling_rate` is at least `5`.
3. Preserve current defaults for optional fields.
4. After successful save, show a restart-required state.
5. Tell Docker Compose users to restart the backend/app container.
6. Do not automatically navigate into the app before restart.

### Acceptance Criteria

- Settings are saved to backend.
- Backend `422` errors are shown inline.
- Password is sent only on save/validation, never rendered back.
- Restart-required state uses existing app/Skeleton visual language.
- Restart-required state clearly says v1 applies setup after container restart.
- The screen should explain that **Initial Setup** is not complete until restart finishes.

### Tests

- Frontend build.
- Manual smoke test with backend.
- Backend settings tests if save contract changes.

## Slice 5: Redirect Guard

### Goal

Automatically send users to `/setup` when setup is incomplete.

### Ownership

SvelteKit route layout/load guard.

### Candidate Files

- `frontend/src/routes/+layout.svelte`
- `frontend/src/routes/+layout.ts` or `+layout.server.ts`
- `frontend/src/routes/(app)/+layout.ts` or route group layout
- `frontend/src/routes/setup/+page.svelte`

### Design

Prefer guarding only the app route group, not every route globally.

Suggested behavior:

- `/setup` always accessible.
- app routes check `GET /setup/status`.
- if `required === true`, redirect to `/setup`.
- if setup config is complete and backend has restarted, app routes proceed.
- if setup config is complete but download manager/runtime is unavailable, show restart-required state instead of treating the app as ready.

### Acceptance Criteria

- Visiting app route with incomplete setup redirects to `/setup`.
- Visiting `/setup` does not redirect-loop.
- Saved setup plus backend restart allows normal app navigation.
- Saved setup without backend restart shows restart-required state.
- Restart-required state appears both on `/setup` after save and on guarded app routes if the user tries to enter before restarting.
- Backend unreachable should show useful error state, not infinite redirect.

### Tests

- Frontend build.
- Manual checks:
  - incomplete setup -> app route redirects
  - saved setup plus backend restart -> app route loads
  - `/setup` direct load works

## Slice 6: Settings Restart Required UX

### Goal

Show **Restart Required** on the Settings page when a saved **Restart-Applied Setting** changes.

### Ownership

Settings page save behavior and user messaging.

### Candidate Files

- `frontend/src/routes/(app)/settings/+page.svelte`
- settings API helper if one exists later
- optional shared restart-required component

### Restart-Applied Settings

Changing any of these should show **Restart Required** after a successful save:

- `media_data_location`
- `qbt_hostname`
- `qbt_username`
- `qbt_password`
- `qbt_path_local`
- `qbt_path_remote`
- `qbt_category`
- `qbt_download_location`
- `qbt_polling_rate`
- `log_level`

`prefer_extended` does not require restart because download requests already read the current setting when they start.

### Settings Page Labels

The Settings page already uses friendly labels. Do not redesign or rename the Settings page labels as part of this slice unless needed for the restart-required message.

For consistency, the Initial Setup wizard should use friendly labels and descriptions instead of raw setting names. Suggested labels:

- `media_data_location`: "Media data location" — "Path visible to Pace Downloader where organized One Pace files will be placed."
- `qbt_hostname`: "qBittorrent Web UI URL" — "URL Pace Downloader uses to reach qBittorrent."
- `qbt_username`: "qBittorrent username"
- `qbt_password`: "qBittorrent password"
- `qbt_path_remote`: "Remote path reported by qBittorrent" — "Path prefix qBittorrent reports for downloaded files, such as `/downloads`."
- `qbt_path_local`: "Path visible to Pace Downloader" — "Matching path prefix Pace Downloader can read, such as `/data/torrents/downloads`."
- `qbt_category`: "qBittorrent category"
- `qbt_download_location`: "qBittorrent download location"
- `qbt_polling_rate`: "Polling rate"
- `log_level`: "Log level"

### Steps

1. Keep a snapshot of loaded setting values before edits.
2. On save success, compare submitted values with the loaded snapshot.
3. If any **Restart-Applied Setting** changed, show **Restart Required** instead of only "Settings saved."
4. The message should tell Docker Compose users to restart the backend/app container.
5. Do not block saving non-restart settings.

### Acceptance Criteria

- Changing qBittorrent connection fields shows **Restart Required** after save.
- Changing media data location shows **Restart Required** after save.
- Changing only `prefer_extended` shows normal "Settings saved."
- Password masking does not produce false positives when the value is the unchanged masked placeholder.
- Environment-overridden settings remain disabled as today.

### Tests

- Frontend build.
- Manual check:
  - qBittorrent hostname changed -> restart message
  - prefer extended changed only -> saved message
  - env-overridden field disabled

## Slice 7: Backend Boot Tolerance

### Goal

Allow backend to start when setup is incomplete.

### Ownership

Backend startup path and qBittorrent initialization.

### Candidate Files

- `backend/main.py`
- `backend/qbittorrent.py`
- `backend/dependencies.py`
- `backend/download_manager.py`
- `backend/api.py`
- backend tests

### Current Problem

`main.py` currently performs startup work that assumes settings/qBittorrent are already valid. That conflicts with **Initial Setup**.

### Desired Behavior

Backend should start even when:

- `media_data_location` is empty
- `qbt_hostname` is empty
- qBittorrent is unavailable

Routes that require qBittorrent/download manager should return a clear setup/config error until configured.

### Suggested Approach

1. Initialize DB and logging as today.
2. Build setup status at boot.
3. If setup incomplete:
   - skip metadata sync that requires media path
   - skip qBittorrent client construction
   - skip download manager polling/startup scan
4. Keep `/health`, `/settings`, `/setup/status`, and `/setup/validate/*` working.
5. After settings are saved, require a manual container/backend restart for v1.
6. Do not add in-process qBittorrent/download-manager reinitialization in this feature slice.

For v1, the setup wizard should save config and then tell the user to restart the container. Live lifecycle management is deferred to a future feature because it needs careful handling for polling tasks, startup scans, and active requests.

### Acceptance Criteria

- Backend starts with empty settings DB.
- Setup endpoints work before qBittorrent is configured.
- Download routes return clear error when download manager is unavailable.
- No polling loop starts without a configured qBittorrent client.

### Tests

- Backend test for startup/init path with incomplete settings.
- API test for setup endpoint availability when setup incomplete.
- API test for qBittorrent-required route error shape.

## Slice 8: Runtime Placement Error Surfacing

### Goal

When path mapping or media placement fails at runtime, expose a clear error instead of silently retrying every poll.

### Ownership

Backend download manager status/error handling and frontend display if needed.

### Candidate Files

- `backend/download_manager.py`
- `backend/db.py`
- `backend/api.py`
- `frontend/src/routes/(app)/downloads/+page.svelte`
- SSE status handling

### Current Behavior

Placement errors in `poll_downloads()` are caught and logged, but episode status is not marked `error`.

### Desired Behavior

When `_add_episode_to_data_location()` fails:

- mark episode download as `error`
- optionally store error message
- broadcast SSE status update
- keep poller alive

### Acceptance Criteria

- Bad qBittorrent path mapping produces visible error status.
- Poller does not crash.
- Error is not swallowed as only a log line.
- Existing happy path still hardlinks/copies as before.

### Tests

- Unit test for failed placement marks episode `error`.
- Unit test for poller event on placement failure.
- Frontend manual check if UI already supports `Error` status.

## Slice 9: Final Integration Pass

### Goal

Verify **Initial Setup** end to end.

### Steps

1. Reset or use fresh DB.
2. Start backend.
3. Start frontend.
4. Visit app route.
5. Confirm redirect to `/setup`.
6. Fill wizard with valid media path and qBittorrent config.
7. Validate each step.
8. Save settings.
9. Confirm restart-required completion screen appears.
10. Restart backend/container manually.
11. Confirm app route loads.
12. Confirm health/download routes behave.

### Acceptance Criteria

- First-run user has clear path from empty config to app usage.
- No auth fields appear.
- No redirect loops.
- No secrets in logs or UI.
- Dark/light UI both acceptable.

## Agent Coordination Rules

- Keep each slice in one PR/commit when possible.
- Do not mix backend boot refactor with frontend form wiring.
- Do not regenerate OpenAPI types unless backend is running and API contract changed.
- Do not hand-edit generated OpenAPI types.
- Do not revert unrelated worktree changes.
- If a slice touches both backend and frontend, update tests/build for both.
- Prefer existing app UI patterns over new styling systems.

## Suggested Parallelization

Safe parallel work:

- Slice 1 and Slice 2 can be done together if backend is running.
- Slice 3 and Slice 4 should usually be sequential.
- Slice 6 can run in parallel with setup wizard work if write scopes stay settings-page-only.
- Slice 7 can run in parallel with frontend work if write scopes stay backend-only.
- Slice 8 can run after Slice 7 or independently if scoped carefully.

Avoid parallel work:

- Multiple agents editing `SetupWizard.svelte`.
- Multiple agents editing `backend/download_manager.py`.
- API contract changes while another agent regenerates frontend types.

## Open Questions

- Should setup status require qBittorrent credentials, or only hostname plus successful validation during wizard?
- Should validation responses ever use non-200 status codes, or keep `ok: false` for all user-correctable setup failures?
- Should runtime placement errors store full exception text in DB, or only a generic user-safe message?

## Definition Of Done

Feature is done when:

- Backend starts on first run with incomplete config.
- `/setup` validates and saves required settings.
- App routes redirect to setup only when required.
- Restart-required state gives clear manual restart instructions.
- Normal app usage works after manual backend/container restart.
- Invalid media/qBittorrent/path inputs produce useful messages.
- Runtime placement failures surface as visible errors.
- Backend tests pass.
- Frontend build passes.
