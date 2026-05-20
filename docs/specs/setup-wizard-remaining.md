# Initial Setup And Restart State

## Purpose

Finish **Initial Setup** with one small lifecycle model that is easy to reason about:

- **Initial Setup Complete** says whether the backend has restarted with enough effective configuration for normal app routes.
- **Restart Required** says whether saved settings differ from the settings currently applied by the running backend process.

The setup wizard validates and saves settings. It does not directly set lifecycle flags. The backend owns those flags.

## Product Goal

A fresh install should behave like this:

1. The backend starts even when required settings are missing.
2. App routes redirect to `/setup` while **Initial Setup Complete** is false.
3. The setup wizard validates media, qBittorrent, and optional path mapping.
4. The wizard saves settings through `PUT /settings`.
5. If the saved effective configuration is complete, the user sees a restart-required setup completion screen.
6. After backend/container restart, normal app routes load.
7. Later changes to Restart-Applied Settings show a restart warning but do not block normal app use.

## Non-Goals

- Do not add app username/password authentication.
- Do not add in-process qBittorrent/download-manager reinitialization for v1.
- Do not probe qBittorrent remote paths from the backend.
- Do not hand-edit `frontend/src/lib/types/api.d.ts`; regenerate it from OpenAPI.
- Do not expose lifecycle flags as user-editable settings.

## Lifecycle State

The backend stores lifecycle state in the singleton `app_state` row:

- `initial_setup_complete`
- `restart_required`

The four meaningful states are:

| `initial_setup_complete` | `restart_required` | Meaning | Frontend behavior |
|---|---:|---|---|
| `false` | `false` | Initial Setup still needs required values | Redirect app routes to `/setup`; show wizard |
| `false` | `true` | Initial Setup was saved, but the backend has not restarted with it | Redirect app routes to `/setup`; show restart-required completion |
| `true` | `false` | Current backend process has applied saved setup | Normal app |
| `true` | `true` | A later Restart-Applied Setting changed | Normal app; show Settings restart warning |

No frontend input should set either flag directly.

## Effective Settings

Use effective settings whenever deciding whether setup is complete or whether runtime behavior can start. Effective settings are the values returned by `db.get_settings()`:

- environment value when an env var is present
- SQLite value otherwise
- `env_override: true` when the value came from env

Environment variables count as valid configuration. For example, if `MEDIA_DATA_LOCATION` and `QBT_HOSTNAME` are set, Initial Setup can be complete even when those fields are empty in SQLite.

Required Initial Setup configuration:

- `media_data_location` has a non-empty effective value.
- `qbt_hostname` has a non-empty effective value.
- `qbt_path_local` and `qbt_path_remote` are either both empty or both non-empty.

Connectivity validation is not part of lifecycle completeness. If qBittorrent is unreachable after restart, that is an operational/configuration problem, not pending Initial Setup.

## Settings Save Rules

`PUT /settings` must preserve the difference between stored settings and effective settings.

On save:

1. Read effective settings before save.
2. Read stored SQLite settings before save where needed.
3. Preserve the stored password when the submitted password is the masked placeholder.
4. Preserve stored SQLite values for env-overridden fields instead of writing env values back into SQLite.
5. Save the resulting stored settings.
6. Read effective settings after save.
7. Update lifecycle flags from backend-owned rules.

Flag rules:

- If Initial Setup is incomplete before save and effective configuration is complete after save, set `restart_required = true` and keep `initial_setup_complete = false`.
- If Initial Setup is incomplete after save, keep `initial_setup_complete = false` and `restart_required = false`.
- If Initial Setup is complete and a Restart-Applied Setting changed effectively, set `restart_required = true`.
- Do not clear `initial_setup_complete` for later settings-page changes.
- Do not set `restart_required` when only `prefer_extended` changed.

Restart-Applied Settings:

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

`prefer_extended` is not Restart-Applied because download requests read it when they start.

## Startup Rules

During backend startup, after DB initialization and dotenv loading:

1. Read effective settings.
2. If required Initial Setup configuration is complete:
   - set `initial_setup_complete = true`
   - set `restart_required = false`
   - initialize metadata sync, qBittorrent client, download manager, polling, and startup scan
3. If required Initial Setup configuration is incomplete:
   - set `initial_setup_complete = false`
   - set `restart_required = false`
   - skip qBittorrent client, download manager, polling, and startup scan

The same shared helper should decide Initial Setup configuration completeness for startup, settings-save flag logic, and tests.

## API Contract

### `GET /app-state`

Returns the two lifecycle flags.

```json
{
  "initial_setup_complete": false,
  "restart_required": true
}
```

This endpoint is the frontend source of truth for route guards and restart messaging.

### `GET /settings`

Returns effective settings, including `env_override`, with the qBittorrent password masked for UI display.

### `PUT /settings`

Saves stored settings and updates lifecycle flags using the rules above.

The frontend should keep using this endpoint for both the setup wizard and the Settings page.

### `POST /setup/validate/media`

Validates `media_data_location`.

Request:

```json
{
  "media_data_location": "/media/One Pace"
}
```

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

Validates qBittorrent Web UI login/connectivity.

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

Validates optional qBittorrent path mapping. Empty mapping is valid. One-sided mapping is invalid.

Request:

```json
{
  "qbt_path_local": "/mnt/downloads",
  "qbt_path_remote": "/downloads"
}
```

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

Remote path is trusted. Runtime placement/linking errors should be surfaced by download status handling.

## Frontend Behavior

Keep API calls route-local. Do not add a shared setup API client yet.

### Route Guard

`frontend/src/hooks.server.ts` should fetch `GET /app-state`.

- If `initial_setup_complete === false`, redirect non-setup routes to `/setup`.
- If `initial_setup_complete === true`, allow app routes even when `restart_required === true`.
- Backend unreachable should produce a useful SvelteKit error instead of a redirect loop.

### Setup Page

`frontend/src/routes/setup/+page.server.ts` should fetch:

- `GET /settings`
- `GET /app-state`

The setup page should:

- show the wizard when `initial_setup_complete === false && restart_required === false`
- show the restart-required completion state when `initial_setup_complete === false && restart_required === true`
- avoid offering another final save while waiting for restart
- optionally redirect away from `/setup` when `initial_setup_complete === true`

### Settings Page

`frontend/src/routes/(app)/settings/+page.server.ts` should fetch:

- `GET /settings`
- `GET /app-state`

The Settings page should:

- show a persistent Restart Required warning when `initial_setup_complete === true && restart_required === true`
- refetch `GET /app-state` after save
- show normal "Settings saved" feedback when no restart is required
- keep env-overridden fields disabled as today

### Setup Wizard

The wizard should keep using per-step validation:

- Media step calls `POST /setup/validate/media`.
- qBittorrent step calls `POST /setup/validate/qbittorrent`.
- Paths step calls `POST /setup/validate/path-mapping`.
- Final review calls `PUT /settings`.

Validation responses with `ok: false` should display their message and should not advance. Passwords should never be displayed in review or logs.

## Implementation Plan

### 1. Backend State Contract

Files:

- `backend/models.py`
- `backend/api.py`
- `backend/db.py`
- `backend/app_settings.py`
- `backend/setup_validation.py`
- `backend/main.py`

Work:

- Add `AppStateResponse`.
- Add `GET /app-state`.
- Keep `app_state` storage in SQLite.
- Add one shared helper for Initial Setup configuration completeness.
- Use that helper in startup and settings-save logic.
- Remove or stop relying on detailed setup-status lifecycle fields.

### 2. Effective Settings Save

Files:

- `backend/api.py`
- `backend/app_settings.py`
- `backend/db.py`
- backend tests

Work:

- Preserve masked password behavior.
- Preserve stored DB values for env-overridden fields.
- Compare effective Restart-Applied Settings before and after save.
- Set lifecycle flags according to the rules in this document.
- Treat invalid `QBT_POLLING_RATE` env values as absent/fallback, not as an effective string value.

### 3. Frontend Wiring

Files:

- `frontend/src/hooks.server.ts`
- `frontend/src/routes/setup/+page.server.ts`
- `frontend/src/routes/setup/+page.svelte`
- `frontend/src/lib/components/SetupWizard/SetupWizard.svelte`
- `frontend/src/routes/(app)/settings/+page.server.ts`
- `frontend/src/routes/(app)/settings/+page.svelte`

Work:

- Fetch `GET /app-state` where route decisions or restart messaging need it.
- Replace setup-status route guard logic with app-state logic.
- Show setup restart-required state from app-state.
- Show settings restart warning from app-state.

### 4. API Types And Validation

After backend contract changes:

```bash
cd frontend
pnpm generate-types
pnpm build
```

Backend validation:

```bash
cd backend
pytest tests/test_setup_validation.py tests/test_settings_api.py tests/test_db.py
```

Run broader tests if the lifecycle changes touch download-manager startup behavior.

## Test Checklist

Backend tests should cover:

- `GET /app-state` default response.
- Startup with incomplete effective settings sets `initial_setup_complete = false` and `restart_required = false`.
- Startup with complete effective settings sets `initial_setup_complete = true` and `restart_required = false`.
- Env vars count toward required Initial Setup configuration.
- One-sided qBittorrent path mapping makes Initial Setup configuration incomplete.
- Completing Initial Setup through `PUT /settings` sets `restart_required = true` and leaves `initial_setup_complete = false`.
- Changing a Restart-Applied Setting after Initial Setup sets `restart_required = true`.
- Changing only `prefer_extended` does not set `restart_required = true`.
- Env-overridden fields are not written back into SQLite during save.
- Masked qBittorrent password does not create a false positive settings change.

Manual checks:

- Fresh DB redirects app routes to `/setup`.
- Saving valid setup shows the restart-required setup completion state.
- Restarting the backend after saving setup allows normal app navigation.
- Later restart-required Settings changes do not redirect app routes to `/setup`.
- Settings page shows Restart Required only when app-state says it should.
- No secrets are displayed in UI or logs.
