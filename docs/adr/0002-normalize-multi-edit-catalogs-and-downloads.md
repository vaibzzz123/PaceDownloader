# Normalize multi-Edit catalogs and downloads

Pace Downloader will support built-in **Edits** through release-defined **Edit Spreadsheet Adapters** that emit one **Normalized Edit Catalog** contract. The catalog will use canonical Episode Keys and method-discriminated download definitions, while download management will expose one provider-neutral episode lifecycle across torrents and direct downloads. This seam prevents spreadsheet layouts, Google Drive behavior, qBittorrent state, and display-metadata repository structure from spreading through the database, HTTP routes, SSE events, and frontend.

## Considered Options

- Continue extending the current One Pace-shaped metadata dictionaries and qBittorrent-centric manager. This avoids an initial migration but makes every new Edit and download method add branches throughout the application.
- Make arbitrary spreadsheets or executable plugins user-configurable. This permits additions without a release but requires a parsing language or untrusted executable adapters before the supported source formats are understood.
- Ship reviewed Edit definitions and adapters, normalize their output, and place provider-specific behavior behind download adapters. This makes two real seams: spreadsheet adapters normalize independently maintained catalogs, and download adapters implement a shared episode lifecycle.

## Consequences

- Edit identity, ordering, spreadsheet behavior, display-metadata repository URL, expected repository subdirectory, and Jellyfin show directory are built into releases. Newly added Edits are disabled until the user explicitly opts in; Edit enablement is restart-applied.
- Each Edit has its own display-metadata repository. Pace Downloader follows its latest upstream content, validates its fixed release-defined layout, and retains the last working local snapshot when an update breaks. These repositories enrich display data only; spreadsheets remain authoritative for seasons, episodes, and download references.
- Onigashima Pace uses `https://github.com/vaibzzz123/PaceDownloader-Extra-Metadata` with the fixed `onigashima-pace` content subdirectory. Missing optional image assets do not make its authoritative spreadsheet catalog unavailable.
- Episode Keys are encoded as `<edit-id>:s<season-number>:e<normalized-episode-number>` throughout persistence, HTTP, and events. Globally assigned episode integers are removed from the public interface.
- An episode download definition is a discriminated union whose method owns typed Download Variants and retrieval identifiers. Mixed torrent and direct-download variants under one Episode Key are structurally invalid.
- Episode downloads use `queued`, `downloading`, `paused`, `finalizing`, `installed`, and `error` regardless of provider. Progress is downloaded bytes plus a nullable total; finalization mechanism and raw provider details are separate data.
- Media uses one shared **Media Data Location** with a stable show directory per Edit. Existing One Pace data and integer-keyed download rows require an automatic, strict, recoverable migration.
