# Setup Wizard Remaining Roadmap

## Purpose

Finish **Initial Setup** for Pace Downloader in a way that is practical for a human maintainer to implement and verify incrementally.

This file used to be organized for agents working in parallel slices. The current goal is different: keep the work readable, dependency-ordered, and easy to drive manually.

## Product Goal

A fresh install should have a clear first-run path:

1. Backend starts even when setup is incomplete.
2. Visiting the app sends the user to `/setup`.
3. The setup wizard validates media, qBittorrent, and optional path mapping.
4. The wizard saves settings.
5. The user sees a restart-required completion state.
6. After restarting the backend/container, normal app routes load.

## Current State

The setup wizard shell exists:

- `frontend/src/routes/setup/+page.svelte`
- `frontend/src/lib/components/SetupWizard/SetupWizard.svelte`

The backend exposes setup status and validation endpoints:

- `GET /setup/status`
- `POST /setup/validate/media`
- `POST /setup/validate/qbittorrent`
- `POST /setup/validate/path-mapping`

The restart-required endpoint still needs to be added:

- `GET /restart-required`

Singleton app-state storage now exists in `backend/db.py` for lifecycle flags:

- `restart_required`
- `initial_setup_complete`

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

Generated frontend API types already appear to include the setup endpoints. Regenerate `frontend/src/lib/types/api.d.ts` after adding `GET /restart-required`, or after any other backend route/model contract change.

## Non-Goals

- Do not add username/password app auth.
- Do not redesign the whole settings page.
- Do not add in-process qBittorrent/download-manager reinitialization for v1.
- Do not add remote path probing through qBittorrent unless explicitly asked later.
- Do not hand-edit `frontend/src/lib/types/api.d.ts`; regenerate it from OpenAPI.

## Frontend API Pattern

Do not add `frontend/src/lib/api/setup.ts` for now.

The frontend currently keeps API calls close to the route using them:

- Initial page data is fetched in route-local `+page.server.ts` files.
- Client-side actions use small local helpers inside the relevant route `+page.svelte`.
- Reusable components receive typed callback props for validation/save work instead of importing backend URLs or calling API endpoints directly.
- API response shapes are typed with `components['schemas'][...]` from `$lib/types/api`.
- Requests use `PUBLIC_BACKEND_URL`.

For setup, follow that pattern:

- Add `frontend/src/routes/setup/+page.server.ts`.
- Fetch `/settings`, `/setup/status`, and `/restart-required` there.
- Pass `data.settings`, `data.setupStatus`, and `data.restartRequired` into `SetupWizard`.
- Use `setupStatus.required` plus `restartRequired` to distinguish Initial Setup waiting for restart from later settings-page restart-required changes.
- Keep setup validation and save helpers local to `frontend/src/routes/setup/+page.svelte`, and pass typed callbacks into `SetupWizard.svelte`.

## API Contract

### `GET /setup/status`

Returns whether Initial Setup still blocks normal app routes, whether the required setup configuration has been saved, and which setup steps are incomplete.

Important: `complete` means Initial Setup is fully applied and no longer blocks normal app routes. Required configuration being saved is necessary, but not sufficient. For v1, the wizard save should set `restart_required = true` and leave `initial_setup_complete = false`; a backend/container restart marks Initial Setup complete.

Use separate concepts:

- `configuration_complete`: derived from saved settings and step validation. This becomes `true` as soon as the wizard has successfully saved required settings.
- `complete`: derived from `configuration_complete` and `app_state.initial_setup_complete`. This becomes `true` only after the backend has restarted and applied saved setup.
- `required`: `true` when Initial Setup still blocks normal app routes. This remains true after the wizard save until restart finishes.

Expected shape:

```json
{
  "required": true,
  "complete": false,
  "configuration_complete": false,
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

### `GET /restart-required`

Returns whether the current backend process needs a restart before saved settings are applied.

Expected response is a plain JSON boolean:

```json
true
```

Storage and lifecycle:

- Store `restart_required` and `initial_setup_complete` in the database as singleton runtime/app state, not as Python process variables and not as settings exposed through `/settings`.
- During backend startup after DB initialization, derive whether the saved configuration is complete.
- If saved configuration is complete, set `initial_setup_complete = true` and clear `restart_required`. A fresh process has now had the chance to apply saved settings.
- If saved configuration is incomplete, set `initial_setup_complete = false`.
- Set `restart_required = true` from `PUT /settings` when Initial Setup changes from unconfigured to configured, but keep `initial_setup_complete = false` until restart.
- Set `restart_required = true` from `PUT /settings` when any restart-applied effective setting changes after Initial Setup is already complete.
- Do not clear `initial_setup_complete` for later settings-page changes that require restart; the app is still usable with the old applied settings.
- Do not set `restart_required` when only `prefer_extended` changes.
- If qBittorrent is unreachable after restart, treat that as a connectivity/configuration problem, not as a still-pending restart.

Restart-applied settings:

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

## Implementation Order

### Milestone 1: Backend Boots Without Setup

This is the first dependency. The wizard cannot deliver a good first-run experience if the backend fails before the user can configure it.

Files to inspect/change:

- `backend/main.py`
- `backend/qbittorrent.py`
- `backend/dependencies.py`
- `backend/download_manager.py`
- `backend/api.py`
- backend tests

Desired behavior:

- Backend starts with empty `media_data_location`.
- Backend starts with empty `qbt_hostname`.
- Backend starts when qBittorrent is unreachable.
- `/settings`, `/setup/status`, and `/setup/validate/*` still work.
- Routes that require the download manager return a clear setup/configuration error.
- No download polling loop starts without a configured qBittorrent client.
- For v1, saved setup requires a manual backend/container restart.

Suggested approach:

1. Initialize DB and logging as today.
2. Build setup status at boot.
3. If setup is incomplete, skip qBittorrent client construction.
4. If setup is incomplete, skip download-manager construction, polling, and startup scan.
5. Keep setup/settings routes available.
6. Do not add live lifecycle reinitialization yet.

Acceptance criteria:

- Backend can start with a fresh or empty settings DB.
- Setup endpoints work before qBittorrent is configured.
- Download routes return a useful error shape instead of crashing.
- Existing configured startup behavior still works.

Validation:

- Add or update backend tests for incomplete setup startup.
- Add or update API tests for setup endpoint availability.
- Add or update API tests for qBittorrent/download-manager-required route errors.

### Milestone 2: Setup Route Server Load

Follow the current SvelteKit pattern instead of introducing a shared setup API client.

Files:

- `frontend/src/routes/setup/+page.server.ts`
- `frontend/src/routes/setup/+page.svelte`
- `frontend/src/lib/components/SetupWizard/SetupWizard.svelte`

Steps:

1. Add `frontend/src/routes/setup/+page.server.ts`.
2. Fetch `GET /settings`.
3. Fetch `GET /setup/status`.
4. Once `GET /restart-required` exists, also fetch it in the same server load.
5. Type the settings and setup-status responses using `$lib/types/api`.
6. Return `{ settings, setupStatus, restartRequired }`.
7. Pass `data.settings`, `data.setupStatus`, and `data.restartRequired` from `+page.svelte` into `SetupWizard`.

The setup page needs `GET /setup/status` because `restartRequired === true` has two meanings. If `setupStatus.required === true`, the user must stay in setup and see the restart-required completion state. If `setupStatus.required === false`, restart is only a settings-page/app-wide notice and must not force setup.

Acceptance criteria:

- Setup page has current settings available as initial form values.
- Setup page can distinguish Initial Setup waiting for restart from later restart-required settings changes.
- Setup page has the backend restart-required flag available once that endpoint exists.
- Failed server-load requests produce useful SvelteKit errors.

Validation:

- Run frontend build after wiring.

### Milestone 3: Wizard Form State And Validation

Replace the placeholder wizard content with real fields and per-step validation.

Files:

- `frontend/src/lib/components/SetupWizard/SetupWizard.svelte`
- `frontend/src/routes/setup/+page.svelte`

Form state:

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

Validation behavior:

- Media step calls `POST /setup/validate/media`.
- qBittorrent step calls `POST /setup/validate/qbittorrent`.
- Paths step calls `POST /setup/validate/path-mapping`.
- Empty path mapping is accepted.
- One-sided path mapping is rejected.
- Validation responses with `ok: false` should display their message and should not advance.
- HTTP/network failures should show a useful error.

UI notes:

- Use the existing Skeleton/Svelte patterns from the settings page.
- Keep labels friendly rather than exposing raw setting keys.
- qBittorrent password uses `type="password"` and `autocomplete="new-password"`.
- Preferences are visible but not required unless backend settings validation rejects final save.
- Review step masks the password.
- Light and dark modes should remain usable.

Suggested labels:

- `media_data_location`: "Media data location" - "Path visible to Pace Downloader where organized One Pace files will be placed."
- `qbt_hostname`: "qBittorrent Web UI URL" - "URL Pace Downloader uses to reach qBittorrent."
- `qbt_username`: "qBittorrent username"
- `qbt_password`: "qBittorrent password"
- `qbt_path_remote`: "Remote path reported by qBittorrent" - "Path prefix qBittorrent reports for downloaded files, such as `/downloads`."
- `qbt_path_local`: "Path visible to Pace Downloader" - "Matching path prefix Pace Downloader can read, such as `/data/torrents/downloads`."
- `qbt_category`: "qBittorrent category"
- `qbt_download_location`: "qBittorrent download location"
- `qbt_polling_rate`: "Polling rate"
- `log_level`: "Log level"

Acceptance criteria:

- Wizard contains no dummy placeholder field text.
- User cannot advance past media/qBittorrent/path steps when validation fails.
- Validation messages appear near relevant fields.
- Password is never displayed in review.
- Advanced/default settings are visible but clearly optional.

Validation:

- Run frontend build.
- Manually check `/setup` in browser.

### Milestone 4: Save Settings And Restart Required UX

Persist setup through the existing settings endpoint.

Files:

- `frontend/src/lib/components/SetupWizard/SetupWizard.svelte`
- backend settings models/routes only if the save contract must change

Steps:

1. On final review, submit the full payload to `PUT /settings`.
2. Ensure `qbt_polling_rate` is at least `5`.
3. Preserve current defaults for optional fields.
4. Show backend `422` errors inline.
5. After successful save, show a restart-required state.
6. Tell Docker Compose users to restart the backend/app container.
7. Do not automatically navigate into the app before restart.

Acceptance criteria:

- Settings are saved to backend.
- Password is sent only on validation/save and never rendered back.
- Restart-required state clearly says v1 applies setup after backend/container restart.
- Initial Setup is presented as incomplete until restart finishes.

Validation:

- Run frontend build.
- Manual smoke test with backend.

### Milestone 5: App Route Guard

Guard app routes after the backend can boot incomplete, the setup page can save settings, and the backend exposes restart-required state.

Files to consider:

- `backend/db.py`
- `backend/app_settings.py`
- `backend/api.py`
- `backend/main.py`
- `backend/tests/test_settings_api.py`
- `frontend/src/hooks.server.ts`
- `frontend/src/routes/(app)/+layout.svelte`
- `frontend/src/routes/setup/+page.server.ts`
- `frontend/src/routes/setup/+page.svelte`
- `frontend/src/lib/components/SetupWizard/SetupWizard.svelte`

Backend restart-required behavior:

1. Add singleton runtime/app-state storage for `restart_required` and `initial_setup_complete`.
2. Add DB/app-settings helpers to read and set both flags.
3. Add `GET /restart-required`, returning a plain JSON boolean.
4. During backend startup after DB initialization, compute whether required setup configuration is saved.
5. If required setup configuration is saved, set `initial_setup_complete = true` and clear `restart_required`.
6. If required setup configuration is incomplete, set `initial_setup_complete = false`.
7. In `PUT /settings`, compare effective settings before and after save.
8. When required setup configuration changes from incomplete to complete, set `restart_required = true` and keep `initial_setup_complete = false`.
9. When Initial Setup is already complete, set `restart_required = true` for changes to restart-applied effective settings.
10. Do not set the flag when only `prefer_extended` changes.
11. Preserve masked password behavior so submitting `********` does not create a false positive change.

Setup status behavior:

- Derive `configuration_complete` from saved settings and step validation.
- Derive `complete` from `configuration_complete && initial_setup_complete`.
- Derive `required` from `!complete`.
- Initial wizard save should produce `configuration_complete === true`, `complete === false`, and `restart_required === true`.
- Later settings-page restart-required changes should preserve `complete === true`.

Frontend route behavior:

- `/setup` is always accessible.
- Settings remains accessible while restart is required.
- Route guard checks `GET /setup/status` to decide Initial Setup redirects.
- If `setupStatus.required === true`, redirect non-setup routes to `/setup`.
- If `setupStatus.required === false`, app routes proceed even when `restartRequired === true`.
- `restartRequired === true` with `setupStatus.required === true` means saved initial setup is waiting for restart; `/setup` shows the restart-required final page.
- `restartRequired === true` with `setupStatus.required === false` means a settings-page change requires restart; allow normal app use and show restart messaging in settings/app chrome.
- Backend unreachable should show a useful error state, not an infinite redirect.
- Avoid redirect loops for `/setup` and `/settings`.

Setup page behavior:

- Server load fetches `GET /settings`, `GET /setup/status`, and `GET /restart-required`.
- `SetupWizard` receives `setupStatus` and `restartRequired`.
- If `restartRequired === true` and `setupStatus.required === true`, open directly to the final restart-required page.
- If `restartRequired === true` and `setupStatus.required === false`, do not force the final setup page; that state belongs to the settings/app restart notice.
- Disable further final saves while showing the restart-required page.
- After save success, keep showing the local restart-required state immediately; future reloads should get it from `GET /restart-required`.

Acceptance criteria:

- `GET /restart-required` returns `false` by default.
- Fresh app-state defaults to `initial_setup_complete = false`.
- Completing initial setup sets `restart_required = true`.
- Completing initial setup does not set `initial_setup_complete = true` until backend restart.
- Backend startup with complete saved configuration sets `initial_setup_complete = true` and clears `restart_required`.
- Backend startup with incomplete saved configuration leaves or sets `initial_setup_complete = false`.
- Changing a restart-applied setting sets `restart_required = true`.
- Changing only `prefer_extended` does not set `restart_required = true`.
- Settings-page changes that require restart do not set `initial_setup_complete = false`.
- Visiting an app route with incomplete setup redirects to `/setup`.
- Visiting `/setup` does not redirect-loop.
- Visiting settings while restart is required does not redirect-loop.
- Saved setup plus backend restart allows normal app navigation.
- Saved setup without backend restart shows the setup restart-required state.
- Restart-required settings changes after Initial Setup do not force app routes back to `/setup`.

Validation:

- Add or update backend tests for the restart-required endpoint and settings-save flag behavior.
- Add or update backend tests for `initial_setup_complete` startup behavior.
- Add or update backend tests for setup status `configuration_complete`, `complete`, and `required` combinations.
- Start the backend and regenerate frontend OpenAPI types:
  ```bash
  cd frontend
  pnpm generate-types
  ```
- Review `frontend/src/lib/types/api.d.ts` after generation.
- Run frontend build.
- Manual checks:
  - incomplete setup -> app route redirects
  - `/setup` direct load works
  - `/settings` direct load works while restart is required
  - saved setup before restart -> restart-required state
  - saved setup after restart -> app route loads

### Milestone 6: Settings Restart Required UX

Show **Restart Required** on the Settings page when the backend restart-required flag is true.

Files:

- `frontend/src/routes/(app)/settings/+page.server.ts`
- `frontend/src/routes/(app)/settings/+page.svelte`

Backend remains the source of truth. Do not rely on frontend-only snapshot comparison for restart-required state.

Steps:

1. Fetch `GET /settings` and `GET /restart-required` in the settings page server load.
2. Show a persistent **Restart Required** message when `restartRequired === true`.
3. On save success, call `GET /restart-required` again.
4. Show **Restart Required** if the refetched value is true; otherwise show the normal "Settings saved." message.
5. Tell Docker Compose users to restart the backend/app container.
6. Do not block saving non-restart settings.

Restart-applied settings are owned by the backend flag logic:

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

Acceptance criteria:

- Loading settings while `GET /restart-required` returns true shows a persistent **Restart Required** message.
- Changing qBittorrent connection fields shows **Restart Required** after save because the backend flag becomes true.
- Changing media data location shows **Restart Required** after save because the backend flag becomes true.
- Changing only `prefer_extended` shows normal "Settings saved."
- Password masking does not produce false positives when the value is the unchanged masked placeholder.
- Environment-overridden settings remain disabled as today.

Validation:

- Run frontend build.
- Manual check initial settings load with restart-required true.
- Manual check restart vs non-restart settings.

### Milestone 7: Runtime Placement Error Surfacing

Make runtime path mapping or media placement failures visible instead of only logging them.

Files to consider:

- `backend/download_manager.py`
- `backend/db.py`
- `backend/api.py`
- `frontend/src/routes/(app)/downloads/+page.svelte`
- SSE status handling

Desired behavior when `_add_episode_to_data_location()` fails:

- Mark episode download as `error`.
- Store or expose a useful error message if the current schema supports it.
- Broadcast an SSE status update.
- Keep the poller alive.

Acceptance criteria:

- Bad qBittorrent path mapping produces visible error status.
- Poller does not crash.
- Error is not swallowed as only a log line.
- Existing happy path still hardlinks/copies as before.

Validation:

- Add or update unit tests for failed placement marking episode `error`.
- Add or update unit tests for poller event on placement failure.
- Manually check downloads UI if the existing UI supports `Error` status.

## Final Integration Checklist

Use a fresh DB or reset settings, then verify:

1. Backend starts.
2. Frontend starts.
3. Visiting an app route redirects to `/setup`.
4. Wizard loads current/default settings.
5. Media validation works.
6. qBittorrent validation works.
7. Empty path mapping validates.
8. One-sided path mapping fails.
9. Settings save succeeds.
10. Setup save sets `restart_required = true`.
11. Setup save leaves `initial_setup_complete = false`.
12. `GET /setup/status` reports `configuration_complete = true`, `complete = false`, and `required = true` before restart.
13. `GET /restart-required` returns `true` before restart.
14. Restart-required completion screen appears.
15. Backend/container restart sets `initial_setup_complete = true`, clears `restart_required`, and applies settings.
16. `GET /setup/status` reports `complete = true` and `required = false` after restart.
17. `GET /restart-required` returns `false` after restart.
18. Settings page shows the restart-required message while the flag is true.
19. Frontend OpenAPI types include `GET /restart-required` and any setup-status shape changes.
20. Changing a restart-applied setting from Settings sets `restart_required = true`.
21. Changing a restart-applied setting from Settings does not set `initial_setup_complete = false`.
22. Changing only `prefer_extended` does not set `restart_required = true`.
23. App routes keep loading during later settings-page restart-required state.
24. App routes load after initial setup restart.
25. Download-manager routes behave normally after restart.
26. No auth fields appear.
27. No secrets are displayed in logs or UI.
28. Dark/light UI both remain acceptable.

## Working Notes

- Keep changes small and coherent.
- Prefer existing route-local fetch patterns over new shared client abstractions.
- Keep backend and frontend terminology aligned.
- Regenerate OpenAPI types only after backend contract changes; for this plan, regenerate after adding `GET /restart-required` and after changing the setup-status response shape.
- Do not hand-edit generated API types.
- Do not mix runtime placement-error handling into the wizard milestones unless needed for a specific bug.
