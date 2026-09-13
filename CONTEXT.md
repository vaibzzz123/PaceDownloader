# Pace Downloader

Pace Downloader is a companion app for browsing, downloading, and organizing episodes from supported anime fan **Edits** for Jellyfin.

## Language

**Edit**:
An independently maintained fan edit catalog, such as One Pace, Onigashima Pace, or Shaved Egghead. An Edit is a top-level catalog in Pace Downloader and is organized as its own TV show in Jellyfin.
_Avoid_: provider, release group, season collection

**Edit Season**:
A numbered group of episodes belonging to exactly one **Edit**. Its identity is the combination of the Edit and its season number; season numbers are not globally unique across Edits.
_Avoid_: global season, fractional season

**Edit Display Metadata Source**:
An upstream, version-controlled repository that supplies Jellyfin display metadata such as NFO data and images for one or more **Edits**. It enriches the catalog but does not define which Edit Seasons or episodes exist or how they are downloaded.
_Avoid_: catalog source, download source, metadata cache

**Episode Key**:
The stable identity of an episode, derived from its **Edit**, **Edit Season** number, and normalized integer episode number.
_Avoid_: database row ID, globally enumerated episode ID

**Normalized Episode Number**:
The positive integer assigned by an **Edit Spreadsheet Adapter** to an episode after converting the source spreadsheet's labels into a contiguous sequence. It is used consistently for the Episode Key, ordering, API data, filenames, and Jellyfin metadata.
_Avoid_: raw spreadsheet label, fractional episode number, Jellyfin-only number

**Download Variant**:
An alternative cut available for one **Episode Key**, such as a standard cut or extended cut. Download Variants do not create additional logical episodes and do not choose their own download mechanism.
_Avoid_: separate episode, episode version, download source

**Episode Download Method**:
The download mechanism assigned to an **Episode Key**, such as torrent or Google Drive. Every Download Variant of that episode uses the same Episode Download Method.
_Avoid_: Edit download method, variant download method

**Initial Setup**:
The required configuration flow and backend restart completed before Pace Downloader can use media storage and qBittorrent.
_Avoid_: first-run setup, setup wizard, setup flow

**Restart Required**:
The temporary state after saved settings need a backend restart before the running process has applied them. This can happen after Initial Setup is saved, or after a later Restart-Applied Setting changes.
_Avoid_: setup complete, ready

**Restart-Applied Setting**:
A setting change that requires a backend restart before Pace Downloader's runtime services use the new value.
_Avoid_: core setting, important setting

**Effective Setting**:
The setting value Pace Downloader should use after applying environment variable overrides on top of the stored SQLite value.
_Avoid_: db setting, saved value

**Media Data Location**:
The path visible to Pace Downloader where organized episode files for supported **Edits** are placed.
_Avoid_: Jellyfin library path, Jellyfin media path

**Constructed Metadata**:
The Edit, season, and episode information Pace Downloader builds by joining authoritative **Episode Sheet Source Data** with optional **Edit Display Metadata Sources** for browsing, downloads, and media placement.
_Avoid_: metadata cache, metadata mapping

**Episode Sheet Source Data**:
The downloaded exports and parsed rows Pace Downloader stores from an Edit's authoritative episode spreadsheet before building **Constructed Metadata**. The spreadsheet determines which Edit Seasons and episodes exist and supplies their download-source references.
_Avoid_: display metadata, sheet tab data, metadata cache

**Edit Spreadsheet Adapter**:
The source-specific translator that reads one Edit's Episode Sheet Source Data and emits the **Normalized Edit Catalog**. Spreadsheet column names, tab layouts, and source-specific cleanup rules remain inside this adapter.
_Avoid_: metadata constructor, generic sheet parser

**Normalized Edit Catalog**:
The source-independent schema emitted by every **Edit Spreadsheet Adapter**. It describes Edit Seasons, episodes with Normalized Episode Numbers, Episode Keys, Episode Download Methods, available Download Variants, ordering, and the provider-specific identifiers needed to retrieve each variant.
_Avoid_: raw sheet rows, Jellyfin display metadata

**Arc Status Suffix**:
A status marker such as `(TBR)` or `(WIP)` appended to an arc name in the One Pace Episode Guide.
_Avoid_: moniker, tag, title suffix

**Managed Metadata Files**:
The Jellyfin-readable image and NFO files Pace Downloader owns for supported **Edits** under the **Media Data Location**.
_Avoid_: source metadata, constructed metadata

**Media Metadata Synchronization**:
The process that makes **Managed Metadata Files** under the **Media Data Location** match the supported Edit episodes currently present on disk.
_Avoid_: metadata construction, metadata refresh

**qBittorrent Remote Path**:
The download path prefix reported by qBittorrent from qBittorrent's filesystem perspective.
_Avoid_: app download path

**qBittorrent Local Path**:
The same qBittorrent downloads path prefix as visible to Pace Downloader.
_Avoid_: qBittorrent download path

**qBittorrent Path Mapping**:
The optional translation from **qBittorrent Remote Path** to **qBittorrent Local Path** when qBittorrent and Pace Downloader see the same downloads at different paths.
_Avoid_: media mapping, Jellyfin mapping

## Relationships

- An **Edit** contains one or more **Edit Seasons**.
- An **Edit Season** belongs to exactly one **Edit**.
- Pace Downloader groups **Edit Seasons** by Edit in the web UI, such as “One Pace Seasons” and “Onigashima Pace Seasons.”
- Each **Edit** is organized as a separate Jellyfin TV show under the **Media Data Location**.
- Two **Edit Seasons** may have the same season number when they belong to different Edits.
- An **Episode Key** combines a stable Edit identifier, Edit Season number, and **Normalized Episode Number**.
- **Episode Keys** are derived from source identity rather than assigned by database insertion order.
- Edit Season numbers and **Normalized Episode Numbers** are integers everywhere in Pace Downloader.
- An **Edit Spreadsheet Adapter** renumbers fractional or otherwise irregular source labels into a contiguous integer episode sequence.
- The raw spreadsheet label does not become a second identity or a Jellyfin-only episode number.
- One **Episode Key** may offer multiple **Download Variants**.
- At most one **Download Variant** for an Episode Key is installed at a time.
- Installing a different **Download Variant** replaces the currently installed media while preserving the **Episode Key** and its Jellyfin episode identity.
- An **Episode Key** has one **Episode Download Method**.
- Every **Download Variant** under an Episode Key follows that episode's **Episode Download Method**.
- Different episodes within the same **Edit** may use different **Episode Download Methods**.
- **Edit Display Metadata Sources** are maintained upstream from Pace Downloader and optionally enrich **Constructed Metadata** with Jellyfin display metadata.
- **Initial Setup** configures the media storage location and qBittorrent connection used by Pace Downloader.
- **Restart Required** occurs before **Initial Setup** is complete when setup was saved but not restarted.
- **Restart Required** can also occur after **Initial Setup** when a changed **Restart-Applied Setting** has not been applied by a backend restart.
- A changed **Restart-Applied Setting** creates **Restart Required**.
- **Effective Setting** values decide whether **Initial Setup** has enough configuration; environment variables count.
- **Media Data Location** is owned from Pace Downloader's filesystem perspective; Jellyfin may mount the same data at a different path.
- **Episode Sheet Source Data** is the source of truth for the available Edit Seasons, episodes, and their download-source references.
- Each supported spreadsheet format has an **Edit Spreadsheet Adapter**.
- Every **Edit Spreadsheet Adapter** emits the same **Normalized Edit Catalog** schema.
- Spreadsheet-specific column names, tab layouts, and normalization rules do not escape the **Edit Spreadsheet Adapter**.
- Download management, APIs, the web UI, and metadata construction consume the **Normalized Edit Catalog**, not raw spreadsheet rows.
- For the One Pace **Edit**, **Episode Sheet Source Data** includes the overview and per-arc episode rows from the One Pace Episode Guide spreadsheet.
- **Episode Sheet Source Data** keeps raw CSV and XLSX exports available for parser retries without refetching from Google.
- **Episode Sheet Source Data** stores raw CSV exports per tab under a source-specific cache directory.
- **Episode Sheet Source Data** derives per-arc tab names from overview arc names without **Arc Status Suffixes**.
- **Episode Sheet Source Data** refreshes preserve the previous complete cache when any required tab fails to refresh.
- **Episode Sheet Source Data** normalizes only fields needed to build **Constructed Metadata**.
- **Episode Sheet Source Data** supplies the authoritative catalog used to build **Constructed Metadata**.
- **Constructed Metadata** is built before Pace Downloader can reliably browse episodes, resolve downloads, or perform **Media Metadata Synchronization**.
- **Media Metadata Synchronization** writes and removes only **Managed Metadata Files** under the **Media Data Location**.
- **qBittorrent Path Mapping** is required only when qBittorrent reports paths that Pace Downloader cannot use directly.
- **qBittorrent Path Mapping** translates paths from **qBittorrent Remote Path** to **qBittorrent Local Path**.

## Example dialogue

> **Dev:** "Is Onigashima Pace another One Pace season?"
> **Domain expert:** "No — it is a separate **Edit** with its own **Edit Seasons** and its own Jellyfin TV show."
> **Dev:** "Can One Pace and Onigashima Pace both contain Season 1?"
> **Domain expert:** "Yes — an **Edit Season** is identified within its Edit, not by a globally unique season number."
> **Dev:** "Does the upstream repository decide which Onigashima Pace episodes are available?"
> **Domain expert:** "No — **Episode Sheet Source Data** is authoritative; the **Edit Display Metadata Source** only enriches those episodes for Jellyfin."
> **Dev:** "Should the metadata constructor contain special cases for Onigashima Pace spreadsheet columns?"
> **Domain expert:** "No — an **Edit Spreadsheet Adapter** translates them into the **Normalized Edit Catalog** consumed by the rest of the app."
> **Dev:** "Should the database assign the next integer when it discovers an episode?"
> **Domain expert:** "No — derive its **Episode Key** from the Edit, Edit Season number, and **Normalized Episode Number**."
> **Dev:** "How should End of Wano 03.5 be represented?"
> **Domain expert:** "The adapter assigns it **Normalized Episode Number** 4 and shifts the spreadsheet's episode 4 to number 5; integers are used everywhere downstream."
> **Dev:** "Is an extended cut a second Jellyfin episode?"
> **Domain expert:** "No — it is another **Download Variant** for the same **Episode Key**, and installing it replaces the currently installed variant."
> **Dev:** "Can the standard cut use Google Drive while the extended cut uses a torrent?"
> **Domain expert:** "No — both variants follow the **Episode Download Method** assigned to their Episode Key."
> **Dev:** "Should **Initial Setup** create app user credentials?"
> **Domain expert:** "No — app authentication is out of scope for v1."
> **Dev:** "Is **Initial Setup** complete right after saving settings?"
> **Domain expert:** "No — the backend must restart before the app is functional."
> **Dev:** "Does changing qBittorrent hostname from Settings apply immediately?"
> **Domain expert:** "No — qBittorrent connection settings are **Restart-Applied Settings**."
> **Dev:** "Should the user enter Jellyfin's library path for **Media Data Location**?"
> **Domain expert:** "No — Pace Downloader needs the path it can write to."
> **Dev:** "Is **Episode Sheet Source Data** just the Arc Overview tab?"
> **Domain expert:** "No — it means the ingested One Pace Episode Guide spreadsheet rows, including Arc Overview and the per-arc episode tabs."
> **Dev:** "Should `(TBR)` be part of the tab name when loading **Episode Sheet Source Data**?"
> **Domain expert:** "No — `(TBR)` and `(WIP)` are **Arc Status Suffixes**, not part of the per-arc tab name."
> **Dev:** "If one tab fails during an **Episode Sheet Source Data** refresh, should we keep the tabs that succeeded?"
> **Domain expert:** "No — keep the previous complete cache rather than mixing old and new tabs."
> **Dev:** "If Arc Overview adds a new arc, should parsing update the JSON cache before the new tab CSV is present?"
> **Domain expert:** "No — all required raw tab exports must be present before parsed rows are promoted."
> **Dev:** "Should the CSV import infer numbers and dates for every Episode Guide column?"
> **Domain expert:** "No — normalize only the fields needed to build **Constructed Metadata**."
> **Dev:** "Is **Media Metadata Synchronization** the same thing as building **Constructed Metadata**?"
> **Domain expert:** "No — **Constructed Metadata** is the app's episode and season view; **Media Metadata Synchronization** changes Jellyfin-readable files on disk."
> **Dev:** "When does **qBittorrent Path Mapping** matter?"
> **Domain expert:** "Only when qBittorrent reports `/downloads/file.mkv` but Pace Downloader must read that file at `/data/torrents/downloads/file.mkv`."

## Flagged ambiguities

- "season" alone does not identify an **Edit Season** across the whole catalog; include the Edit when the context is not already clear.
- "show" refers to the Jellyfin representation of an **Edit**; use **Edit** for the Pace Downloader domain concept.
- "metadata repository" was resolved to **Edit Display Metadata Source** because the upstream repository contains Jellyfin display metadata, not the authoritative episode catalog.
- "extended episode" refers to a **Download Variant**, not a second episode.
- "download method" belongs to an **Episode Key**, not to its Edit or individual Download Variants.
- Fractional spreadsheet labels such as `03.5` are normalized to integer **Normalized Episode Numbers** and are not preserved as runtime identifiers.
- "setup wizard" refers to the frontend UI component; **Initial Setup** refers to the domain flow.
- "core important stuff" was resolved to **Restart-Applied Setting**.
- "media location" was resolved to **Media Data Location**, the path visible to Pace Downloader, not Jellyfin.
- "metadata" can mean **Constructed Metadata**, **Managed Metadata Files**, or **Media Metadata Synchronization**; prefer the precise term when discussing responsibilities.
- "episode sheet" refers to the complete authoritative spreadsheet source for an Edit, not only one Google Sheets tab.
- "normalized schema" was resolved to the **Normalized Edit Catalog** emitted by every Edit Spreadsheet Adapter.
- "extra moniker" was resolved to **Arc Status Suffix** for `(TBR)` and `(WIP)` markers on Episode Guide arc names.
- "path mapping" was resolved to **qBittorrent Path Mapping**, translating qBittorrent-reported paths into Pace Downloader-visible paths.
