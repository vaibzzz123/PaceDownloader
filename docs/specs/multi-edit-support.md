# Multi-Edit Support Beginning With Onigashima Pace

## Purpose

Add first-class support for multiple fan **Edits** without spreading source-specific spreadsheet, display-metadata, or download-provider behavior through the application. The first additional Edit is Onigashima Pace. The implementation must preserve existing One Pace downloads and make later built-in Edits such as Shaved Egghead or dubbed Pace projects additions at established seams rather than new cross-application branches.

Use the language and invariants in `CONTEXT.md`. ADR 0002 records the architecture choice.

## Product Result

- The season index groups enabled Edit Seasons under release-ordered headings such as “One Pace Seasons” and “Onigashima Pace Seasons.”
- One Pace remains enabled during migration. Every newly shipped Edit is disabled until explicitly enabled in Settings and the backend restarts.
- Each Edit is a separate Jellyfin TV show below one shared Media Data Location.
- Onigashima Pace obtains its authoritative catalog and public Google Drive links from its spreadsheet without Google credentials.
- Every episode action and status uses a canonical Episode Key rather than a globally assigned integer.
- Torrent and direct-download episodes share the same lifecycle, progress contract, API operations, and regular downloads table.
- The existing torrent table and explicit whole-torrent controls remain for aggregate qBittorrent operations.

## Non-Goals

- User-defined Edits, arbitrary spreadsheet mappings, or executable plugins.
- Google API credentials or application-owned Google credentials.
- User-configurable display-metadata repository URLs or per-Edit media roots.
- Pinning display-metadata content to application releases or retaining an update history beyond the last working local snapshot.
- Fractional episode numbers downstream of an Edit Spreadsheet Adapter.
- Treating display-metadata repositories as authoritative catalogs.
- Transcoding or changing downloaded media containers.

## Onigashima Display Metadata Source

The built-in Onigashima Pace Edit definition uses:

- repository: `https://github.com/vaibzzz123/PaceDownloader-Extra-Metadata`
- expected content subdirectory: `onigashima-pace`

The repository currently contains `tvshow.nfo`, two numbered season directories, season NFOs, and episode NFOs. Image assets such as show posters, season thumbnails, logos, and backdrops are intentionally absent for now. Their absence does not block the spreadsheet-derived catalog, Google Drive downloads, or NFO synchronization; the UI uses fallback/placeholder imagery and synchronization skips unavailable image files.

Images can be added later under the same `onigashima-pace` hierarchy without a Pace Downloader release. The next successful metadata refresh fetches the latest default-branch content, validates it, exposes the images through Edit-qualified poster URLs, and copies applicable Managed Metadata Files during synchronization.

## Built-In Edit Registry

Add one registry owned by the backend catalog module. Each immutable Edit definition contains:

- stable lowercase ASCII `edit_id`
- display name
- release-defined sort rank
- stable Jellyfin show-directory name
- whether it is enabled for a fresh/legacy installation
- spreadsheet source configuration and Edit Spreadsheet Adapter
- Edit Display Metadata Source repository URL and expected content subdirectory
- any Edit-specific release source needed by its torrent download definitions

Initial definitions:

| Edit ID | Display name | Order | Existing installs | Show directory |
|---|---|---:|---|---|
| `one-pace` | One Pace | 10 | enabled | `One Pace` |
| `onigashima-pace` | Onigashima Pace | 20 | disabled until opt-in | `Onigashima Pace` |

The Onigashima definition binds `https://github.com/vaibzzz123/PaceDownloader-Extra-Metadata` to the fixed `onigashima-pace` content subdirectory.

Reject duplicate IDs, duplicate sort ranks, duplicate show directories, unsafe paths, and invalid slug IDs at process startup. Consumers receive enabled definitions in registry order; they do not sort by display name or persist user order.

Store enabled Edit IDs as a Restart-Applied Setting. Unknown stored IDs must be reported and ignored rather than instantiated. Saving a selection updates Restart Required. The restarted process applies the selection as one coherent catalog/worker configuration. When an Edit becomes disabled, pause its queued and downloading episodes, stop refreshing it, and hide it from catalog navigation. Preserve its tracked rows, installed media, partial data, and Managed Metadata Files. Re-enabling does not automatically resume paused work.

## Normalized Edit Catalog

Create typed, immutable catalog models rather than continuing to pass unvalidated dictionaries. The external catalog interface returns one Edit snapshot containing:

- Edit identity and display name
- ordered Edit Seasons with positive integer season numbers
- ordered episodes with canonical Episode Keys and positive Normalized Episode Numbers
- source-derived display fallback values needed when optional metadata is absent
- one method-discriminated download definition per downloadable episode
- available Download Variants in deterministic order

The conceptual download union is:

```text
TorrentDownload
  method = torrent
  variants: TorrentVariant[]

GoogleDriveDownload
  method = google_drive
  variants: GoogleDriveVariant[]
```

A torrent variant owns the normalized fields required by the existing release resolver, including its CRC32 and source release hints. A Google Drive variant owns a normalized public file/share identifier plus expected filename or container information needed to validate and place the response. Provider-specific spreadsheet column names and raw hyperlinks never leave the corresponding Edit Spreadsheet Adapter.

Every episode supplies canonical `standard` and optional `extended` variant IDs. The global `prefer_extended` setting selects `extended` for bulk actions when available and otherwise selects `standard`; an individual download request can name either available variant explicitly.

Constructed Metadata joins a Normalized Edit Catalog with optional display metadata by Episode Key. It cannot add a season or episode that the spreadsheet adapter did not emit. Missing titles, descriptions, NFOs, or images use explicit fallback values and produce a visible per-Edit warning without blocking browsing or downloads.

## Edit Spreadsheet Adapters And Caches

Place raw spreadsheet acquisition and parsing behind one interface that produces a validated Normalized Edit Catalog snapshot. Implement two adapters immediately; do not preserve a generic header-driven parser as the public seam.

### One Pace Adapter

Move current One Pace overview/per-arc rules, Arc Status Suffix removal, source field normalization, and torrent retrieval data into a One Pace adapter. Preserve the existing per-tab all-or-nothing cache behavior inside this adapter. Convert the current release-resolution inputs into typed torrent variants without changing the resolver’s verified-CRC behavior.

This is the compatibility adapter: prove the normalized output matches current One Pace seasons, episode ordering, standard/extended availability, titles, and resolved releases before adding Onigashima behavior.

### Onigashima Pace Adapter

Use the main spreadsheet ID `1HoYogAchoU5DWxVJzUy3eZcHMZk_hUmzUVnQm9KxeFI`. Fetch XLSX, not header-only CSV, because hyperlinks and the unlabeled extended-cut column must survive ingestion.

The adapter owns these current source rules:

- standard public Google Drive hyperlinks come from column A
- extended-cut public Google Drive hyperlinks come from the unlabeled column I
- Onigashima and End of Wano groupings become integer Edit Seasons according to the sheet’s source grouping
- End of Wano `03.5` is included, normalized to episode 4, and later source labels shift to maintain a contiguous positive integer sequence
- extended cuts currently exist for Onigashima 09, 25, 28, 33, 40, and 42
- source media may be MP4; no `.mkv` assumption escapes the adapter/download definition

The spreadsheet is mutable. At implementation start, fetch it again and update the adapter fixture/count expectations from that observed snapshot rather than hardcoding the handoff’s 48 Onigashima episodes, four End of Wano episodes, optional `03.5`, and six extended cuts without verification.

### Snapshot Promotion

Use independent cache roots such as `data/edit-sheets/<edit-id>/`. Refresh, parse, normalize, and validate into a staging snapshot. Promote only after the entire Edit succeeds. One Edit’s failure retains that Edit’s last complete snapshot while other Edits can promote newer snapshots. If an enabled Edit has never produced a valid snapshot, mark only that Edit unavailable and report the error through catalog status/health data.

Keep raw XLSX/CSV inputs needed for parser retry. Never combine tabs or rows from different source generations within one Edit snapshot.

## Edit Display Metadata Sources

Replace the single hardcoded metadata repository with one cache per built-in Edit, for example `data/edit-metadata/<edit-id>/`. Each Edit definition supplies its official repository URL and expected fixed content subdirectory.

For each enabled Edit:

1. Fetch the latest default-branch content into a staging location.
2. Validate that the expected content subdirectory exists, paths remain within the checkout, and the minimum show/season metadata structure is parseable.
3. Promote staging as the active snapshot only after validation.
4. Retain one previous working snapshot solely for rollback.
5. If the latest content fails, keep serving the active snapshot and surface a warning; do not pin or expose repository revisions as product state.

Refactor metadata construction so spreadsheet catalogs enumerate episodes and metadata repositories are lookup/enrichment inputs only. Refactor `metadata.file_synchronizer` to operate per Edit show directory and source root. One Edit’s missing display files must not trigger deletion in another Edit’s show directory.

Serve poster assets under an Edit-qualified path, such as `/posters/<edit-id>/...`, so identical `Season N` names cannot collide.

### Integration Timing

The display-metadata repository enters the runtime workflow after an Edit is enabled and the backend restarts:

1. The spreadsheet adapter refreshes and builds the authoritative Normalized Edit Catalog.
2. The display-metadata refresher clones or updates the Edit's repository snapshot.
3. Metadata construction reads `onigashima-pace` and joins NFO/display fields only onto Episode Keys emitted by the spreadsheet adapter.
4. The web UI uses the enriched Constructed Metadata and Edit-qualified poster URLs. Missing images resolve to the normal fallback/placeholder presentation.
5. After an episode is installed or a metadata sync is requested, Media Metadata Synchronization copies available show, season, episode, and image files into `<Media Data Location>/Onigashima Pace/...`.

The repository is therefore first wired into the common per-Edit refresh/enrichment infrastructure in Phase 2 and first used for Onigashima Pace in Phase 4. Adding posters or season thumbnails later requires only an upstream repository update; the normal refresh and synchronization path consumes them.

## Canonical Identity And HTTP Contract

The canonical Episode Key format is:

```text
<edit-id>:s<season-number>:e<normalized-episode-number>
```

Examples:

```text
one-pace:s1:e1
onigashima-pace:s1:e9
```

Validate the full string at every external boundary. Reject leading zero ambiguity, zero/negative numbers, uppercase/unsafe Edit IDs, unknown Edits, and keys whose encoded season/episode disagree with catalog data. Internal SQLite surrogate IDs may support joins but never appear as episode identity.

Replace globally addressed season and episode routes with Edit-qualified routes. The target shape is:

```text
GET    /edits
GET    /edits/{edit_id}/seasons
GET    /edits/{edit_id}/seasons/{season_number}
GET    /edits/{edit_id}/seasons/{season_number}/episodes
POST   /episodes/{episode_key}/download
POST   /episodes/{episode_key}/pause
POST   /episodes/{episode_key}/resume
DELETE /episodes/{episode_key}
POST   /edits/{edit_id}/seasons/{season_number}/download
POST   /edits/{edit_id}/seasons/{season_number}/pause
POST   /edits/{edit_id}/seasons/{season_number}/resume
DELETE /edits/{edit_id}/seasons/{season_number}
```

The download request accepts an optional explicit `variant_id`; omission applies the global preference. Repeating a request for the same desired variant is idempotent. Requesting a different variant atomically changes the desired variant, cancels/deselects the old transfer, discards only incompatible partial data, and queues the replacement while preserving installed media.

Remove old integer episode and globally numbered season routes in the same cutover. Update every backend caller, frontend route, SSE handler, and generated OpenAPI type; do not add compatibility aliases.

Episode payloads and SSE events include:

- `episode_key`
- `edit_id`, season number, and normalized episode number as convenient non-identity fields
- method and requested/installed variant IDs
- provider-neutral Episode Download State
- `downloaded_bytes`
- nullable `total_bytes`
- error detail when state is `error`

Percentage is derived only when total bytes are known. State transitions and finalization events publish immediately. Byte progress publishes at the existing configured polling cadence, never faster than five seconds.

Keep `/torrent` and whole-torrent action routes for the existing aggregate torrent table. Torrent-table actions intentionally affect every tracked episode in that torrent; episode-table actions affect only the selected Episode Key.

## Provider-Neutral Download Module

Replace the qBittorrent-centric `DownloadManager` interface with a download coordinator whose callers know only Episode Keys, variants, lifecycle state, progress, and episode/season operations. Keep method behavior behind two real internal adapters:

- torrent transfer adapter, reusing `QbittorrentClient` and the verified release resolver
- public Google Drive transfer adapter

The coordinator owns persistence, allowed transitions, request idempotency, variant supersession, finalization, deletion policy, startup reconciliation, and events. Adapters own provider operations and raw provider diagnostics. Do not leak Google cookies/URLs or qBittorrent states into the common lifecycle.

Allowed lifecycle states:

```text
queued -> downloading -> finalizing -> installed
queued/downloading -> paused
paused -> queued
queued/downloading/finalizing -> error
error -> queued (explicit Retry)
```

Deletion removes the tracking row rather than introducing a `deleted` state. Copy, hardlink, and atomic move are finalization mechanisms, not lifecycle states.

On startup:

- reconcile and recover queued, downloading, and finalizing work
- keep paused work paused
- keep error work in error until explicit Retry
- reconcile installed paths and any duplicate left by an interrupted extension-changing replacement

A two-worker global pool runs direct downloads; remaining requests stay queued. Own and shut down these workers with the application lifecycle rather than creating detached per-request threads.

### Pause And Shared Torrents

Pausing one torrent-backed Episode Key sets only its selected file to do-not-download while sibling episode files continue. Pause the whole torrent only when no managed episode in it remains active. Resuming restores the selected file priority and starts the torrent if necessary.

The existing torrent table retains explicit whole-torrent pause/resume/delete controls. Those are visibly group operations and update all affected episode states immediately.

### Ownership-Aware Delete

Persist whether Pace Downloader created a torrent job or attached to a pre-existing qBittorrent job.

Deleting an Episode Key always:

- stops/deselects its transfer
- removes its installed show file
- removes its direct-download partial data
- removes its tracking state
- runs Media Metadata Synchronization for the affected Edit

When no tracked episodes reference a torrent, remove its job and payload only if Pace Downloader created it. Never remove a pre-existing user-owned torrent or its payload. Shared jobs stay until their last tracked reference is gone.

### Errors And Retry

Classify transfer failures as retryable or terminal. Retry transient network/server/rate-limit failures with bounded exponential backoff. Enter `error` after the retry budget is exhausted, or immediately for invalid source identifiers, confirmation/quota HTML masquerading as media, unsafe filenames, mismatched Range responses that cannot be restarted safely, and failed media validation.

Keep a valid compatible partial file on retryable failure. Explicit Retry resumes the same requested variant. A failed replacement never deletes or overwrites the installed old variant.

## Public Google Drive Adapter

Use unauthenticated HTTPS and a per-transfer/session cookie jar. Support public share/file identifiers, redirect chains, Drive confirmation pages, and confirmed download URLs without embedding credentials.

For each transfer:

1. Derive a hidden `.part` path on the same filesystem as the final Edit show path. Store enough sidecar/persistent identity to prove the part belongs to the Episode Key, variant, and source file.
2. If a compatible part exists, send a Range request from its current size.
3. Append only after receiving a valid `206` whose `Content-Range` begins at the requested offset. If the server ignores Range with a valid `200`, truncate and restart. Never append a full response to a part.
4. Follow confirmation redirects/cookies with bounded attempts.
5. Reject HTML/quota/error documents regardless of HTTP success status. Validate content disposition/type, nonzero size, expected container extension, and recognizable MP4/Matroska container signature before promotion.
6. Update downloaded bytes while streaming. Set total bytes only from trustworthy `Content-Length`/`Content-Range` semantics.
7. Flush and close the staged file, enter `finalizing`, and install it in the destination directory.

For same-path replacement, use atomic replace. When the container extension changes, rename the validated staged file to its new final path first, transactionally persist the installed variant/path, then remove the old path. This permits a brief duplicate but never a gap without valid installed media. Startup reconciliation removes a duplicate left around the commit boundary.

Pause closes the active response cooperatively and keeps a valid part. Resume restarts from the part when Range is supported; otherwise it safely restarts at byte zero. Pause/resume/finalization state changes do not wait for the polling tick.

## SQLite Migration

Use a new schema version and explicit migration functions in `backend/db.py`; do not continue adding provider columns to the current table ad hoc.

The provider-neutral episode download record needs at least:

- canonical `episode_key` with a unique constraint
- method
- desired variant ID
- installed variant ID and installed path, nullable until installed
- lifecycle state
- downloaded and nullable total bytes
- error code/message
- timestamps needed for queue/retry ordering

Keep torrent jobs in a provider-specific table with infohash, aggregate status/details, and Pace Downloader ownership. Reference them from torrent transfer state without making infohash the episode identity. Store only the minimum direct-download recovery fields that are not derivable from the catalog and canonical staging path.

### Legacy Download Rows

Before replacing the old integer-keyed tables:

1. Load the last valid legacy One Pace constructed-metadata cache.
2. Map every tracked `ep_id` uniquely to season and episode, then to `one-pace:sN:eN`.
3. Map `hardlink`, `copy`, `completed`, and `imported` outcomes to `installed`, preserving the finalization mechanism separately where known.
4. Preserve downloading, paused, pending, and error intent in their provider-neutral equivalents.
5. Mark existing torrent jobs as app-owned only when current persisted evidence proves Pace Downloader created them; uncertainty must default to user-owned.
6. Rewrite installed media paths for the new nested show directory.
7. Build and validate replacement tables inside one SQLite transaction, then swap them in.

If any tracked row is missing from the legacy cache, maps ambiguously, has an invalid state, or would violate uniqueness, abort and leave the old schema/data intact. Report the exact row and remediation; never partially migrate or reset tracking.

## Automatic Media Layout Migration

The selected migration treats the current effective Media Data Location as the new shared parent. Therefore existing managed One Pace content moves from:

```text
<media>/Season N/...
```

to:

```text
<media>/One Pace/Season N/...
```

This rule intentionally also produces `<old>/One Pace/...` when the old configured directory itself was named `One Pace`; it does not guess that the parent directory should replace the configured value.

Because filesystem moves cannot join the SQLite transaction, make the migration journaled and idempotent:

1. Record a media-layout migration version and planned source/destination entries.
2. Create `<media>/One Pace` on the same filesystem.
3. Move only known managed show-level metadata, backdrops, `Season N` directories, and tracked installed episode paths.
4. Refuse a destination conflict unless source and destination are provably the same file; do not overwrite user files.
5. Persist each completed move so restart resumes safely.
6. Rewrite validated database paths and mark the layout version complete only after every move and schema migration succeed.
7. Run per-Edit Media Metadata Synchronization after completion.

Do not move unrelated files from Media Data Location. If a cross-filesystem condition, permissions failure, or conflict prevents a safe move, stop normal startup with an actionable migration error while preserving the journal for retry.

Document that Jellyfin’s TV library should scan the shared parent from Jellyfin’s own filesystem perspective. After migration, trigger/rescan Jellyfin outside Pace Downloader as currently required; Pace Downloader does not need Jellyfin credentials.

## Initial Setup And Runtime Dependencies

Media Data Location is always required. qBittorrent settings and connectivity are required only when the effective enabled catalogs contain torrent episodes.

Update the shared setup-completeness helper, setup wizard, Settings page, and health response together:

- a direct-download-only enabled catalog can complete Initial Setup without qBittorrent
- enabling an Edit that needs torrents makes qBittorrent fields required after restart
- qBittorrent remains required for the default One Pace-enabled migration
- path-mapping validation appears only when qBittorrent is required/configured
- health reports catalog/display-source failures per Edit and download-provider readiness independently

Do not instantiate qBittorrent or run its poller when no effective enabled catalog needs it. Always create the provider-neutral coordinator so direct-download-only installations have the same episode interface.

## Frontend Cutover

### Navigation And Seasons

Return enabled Edits and their status from the root server load. Render one section per available Edit in release-defined order. Show an unavailable Edit warning without hiding healthy Edit sections.

Replace the global season route with an Edit-qualified SvelteKit route such as:

```text
frontend/src/routes/(app)/edit/[editId]/season/[seasonNumber]/
```

Use Edit ID plus season number in links, load functions, keyed lists, optimistic state, and bulk actions. Remove the old `season/[id]` route in the same cutover.

### Settings

Add built-in Edit checkboxes in release-defined order. One Pace is selected for existing/fresh migrated installations; Onigashima Pace starts unselected. Saving changes sets Restart Required. Explain that disabling pauses active work but preserves files and that newly enabled Edits appear after restart.

The Onigashima option ships disabled by default but is otherwise available once its catalog and direct-download adapter are implemented. Missing optional image assets in its configured display-metadata repository do not disable the Edit.

### Downloads

Keep all methods in the regular episode downloads table. Add Edit, method, requested/installed variant, provider-neutral state, transferred bytes, nullable total, and error display. Use a determinate percentage bar only when total is known; otherwise show an indeterminate bar plus formatted transferred bytes.

Keep the existing torrent table and whole-torrent controls. Torrent-backed episodes therefore appear in the episode table and their aggregate torrent also appears in the torrent table. Direct downloads have no synthetic aggregate job row.

Update optimistic actions and SSE matching to canonical Episode Keys. A per-episode pause affects only that row; a torrent-table group operation updates every episode event received for that infohash.

Regenerate `frontend/src/lib/types/api.d.ts` from the final OpenAPI schema; never hand-edit it.

## Implementation Phases

### Phase 1: Establish The Catalog Seam With One Pace

- Add typed canonical identity, Edit registry, catalog models, and adapter interface.
- Move current One Pace spreadsheet rules behind the One Pace adapter.
- Make Constructed Metadata consume Normalized Edit Catalog output while retaining current single-Edit behavior.
- Change display metadata from episode enumeration to optional keyed enrichment.
- Prove current One Pace episode order, variants, release resolution, and fallback behavior through the new interface.

Exit condition: One Pace runs from its normalized adapter with no caller reading raw sheet rows or using NFO filenames as episode existence.

### Phase 2: Qualify Identity, Storage, And Media Layout

- Add schema/media migration versions and journaled automatic One Pace nesting.
- Strictly migrate legacy download rows to canonical Episode Keys.
- Make file placement and Media Metadata Synchronization Edit-qualified.
- Add per-Edit spreadsheet and display-metadata snapshot roots.
- Add Edit-qualified backend routes, poster paths, SSE identities, and frontend season routes; remove integer/global routes.

Exit condition: existing One Pace data survives migration, and duplicate season numbers from two synthetic fixture Edits cannot collide in DB, API, events, posters, or disk paths.

### Phase 3: Provider-Neutral Download Lifecycle

- Introduce the coordinator, lifecycle transitions, progress shape, ownership tracking, startup reconciliation, and provider adapter interface.
- Move qBittorrent behavior behind the torrent adapter.
- Implement per-episode shared-torrent pause plus retained explicit whole-torrent controls.
- Cut the Downloads page and SSE handling to the new episode contract while retaining the torrent table.

Exit condition: all current One Pace torrent actions use canonical keys and the common lifecycle, including restart, retry, delete, and shared-torrent cases.

### Phase 4: Onigashima Catalog And Direct Downloads

- Re-fetch the mutable Onigashima spreadsheet and save deterministic XLSX fixtures.
- Implement its adapter, grouping, `03.5` normalization, standard links, unlabeled extended links, and MP4-aware target data.
- Implement the two-worker public Google Drive adapter, confirmation/cookie handling, Range resume, truthful byte progress, validation, and safe replacement.
- Add Onigashima to Settings as disabled by default and update grouped season/download UI.
- Connect `https://github.com/vaibzzz123/PaceDownloader-Extra-Metadata` using its fixed `onigashima-pace` content subdirectory and verify NFO enrichment plus missing-image fallbacks.

Exit condition: enabling Onigashima then restarting exposes its grouped seasons; a public Drive episode can download, pause, resume, survive restart, finalize into its show directory, switch variants without losing installed media, and delete cleanly without Google credentials.

### Phase 5: Setup, Documentation, And Release Migration

- Make qBittorrent requirements conditional on effective enabled catalogs.
- Update setup/status/health UI and backend rules.
- Update README container mounts and Jellyfin TV-library layout, migration behavior, Edit enablement, direct-download behavior, and indeterminate progress.
- Regenerate OpenAPI types and remove obsolete integer identity, hardcoded One Pace path, global metadata-source, and qBittorrent-only status code.

Exit condition: fresh, upgraded One Pace-only, One Pace plus Onigashima, and direct-download-only configurations have documented, coherent setup and restart behavior.

## Verification Strategy

### Contract And Adapter Tests

- Canonical Episode Key round-trip and rejection of noncanonical keys.
- Duplicate Edit registry identity/order/path rejection.
- One Pace adapter parity using existing source fixtures.
- Onigashima XLSX fixture verifies both hyperlink columns, integer normalization around `03.5`, observed episode counts, extended variants, and MP4 data.
- Method-discriminated validation rejects mixed torrent/Google Drive variants.
- Per-Edit snapshot promotion preserves last valid data and isolates failures.
- Display enrichment cannot add catalog episodes and degrades with explicit fallbacks.
- Onigashima display metadata loads from the configured `onigashima-pace` subdirectory, and absent optional images do not reject the snapshot or catalog.

### Migration Tests

Use copied temporary SQLite/media fixtures representing the current schema:

- all known legacy states and variant flags map correctly
- unmappable/duplicate rows abort without changing old tables
- interrupted filesystem migration resumes from its journal
- destination conflicts stop without overwriting either file
- installed paths and hardlinks/copies remain valid after nesting
- a directory already named `One Pace` follows the selected automatic nesting rule

### Download Lifecycle Tests

Exercise the coordinator interface, not adapter internals:

- allowed transitions and rejection of stale worker completions
- repeated same-variant request is idempotent
- changing variants cancels old work and preserves installed media
- active work recovers on restart while paused/error states do not auto-resume
- per-episode pause does not pause a sibling in the same torrent
- whole-torrent controls update all members
- app-owned unreferenced torrents are removed; pre-existing torrents survive
- disabling an Edit pauses work without deleting state/media

Use a local fake HTTP server for direct-download behavior:

- redirect plus confirmation cookie
- known and unknown totals
- valid Range resume
- server ignoring Range and safe restart
- mismatched Content-Range rejection
- HTML/quota response with HTTP 200 rejection
- dropped connection with bounded retries
- pause/resume and process restart from a part
- same-extension atomic replacement
- extension-changing commit-new/delete-old recovery

### End-To-End Proof

- Run the legacy migration against disposable DB/media copies and inspect resulting Episode Keys and paths.
- Start the backend with qBittorrent faked and both Edit fixtures loaded; generate OpenAPI types.
- Run the frontend build.
- In the browser, enable Onigashima, observe Restart Required, restart, verify grouped season navigation, start a fake/public-safe direct download, observe determinate and indeterminate SSE progress, pause/resume, switch variant, and delete.
- Verify the regular downloads table contains both methods and the torrent table still controls aggregate torrent jobs.
- Run the smallest backend test modules for each phase, then the backend suite once after integration.
