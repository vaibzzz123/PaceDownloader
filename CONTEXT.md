# Pace Downloader

Pace Downloader is a companion app for downloading One Pace episodes through qBittorrent and organizing them for Jellyfin.

## Language

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
The path visible to Pace Downloader where organized One Pace episode files are placed.
_Avoid_: Jellyfin library path, Jellyfin media path

**Constructed Metadata**:
The episode and season information Pace Downloader builds from One Pace source metadata for browsing, downloads, and media placement.
_Avoid_: metadata cache, metadata mapping

**Managed Metadata Files**:
The Jellyfin-readable image and NFO files Pace Downloader owns under the **Media Data Location**.
_Avoid_: source metadata, constructed metadata

**Media Metadata Synchronization**:
The process that makes **Managed Metadata Files** under the **Media Data Location** match the One Pace episodes currently present on disk.
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

- **Initial Setup** configures the media storage location and qBittorrent connection used by Pace Downloader.
- **Restart Required** occurs before **Initial Setup** is complete when setup was saved but not restarted.
- **Restart Required** can also occur after **Initial Setup** when a changed **Restart-Applied Setting** has not been applied by a backend restart.
- A changed **Restart-Applied Setting** creates **Restart Required**.
- **Effective Setting** values decide whether **Initial Setup** has enough configuration; environment variables count.
- **Media Data Location** is owned from Pace Downloader's filesystem perspective; Jellyfin may mount the same data at a different path.
- **Constructed Metadata** is built before Pace Downloader can reliably browse episodes, resolve downloads, or perform **Media Metadata Synchronization**.
- **Media Metadata Synchronization** writes and removes only **Managed Metadata Files** under the **Media Data Location**.
- **qBittorrent Path Mapping** is required only when qBittorrent reports paths that Pace Downloader cannot use directly.
- **qBittorrent Path Mapping** translates paths from **qBittorrent Remote Path** to **qBittorrent Local Path**.

## Example dialogue

> **Dev:** "Should **Initial Setup** create app user credentials?"
> **Domain expert:** "No — app authentication is out of scope for v1."
> **Dev:** "Is **Initial Setup** complete right after saving settings?"
> **Domain expert:** "No — the backend must restart before the app is functional."
> **Dev:** "Does changing qBittorrent hostname from Settings apply immediately?"
> **Domain expert:** "No — qBittorrent connection settings are **Restart-Applied Settings**."
> **Dev:** "Should the user enter Jellyfin's library path for **Media Data Location**?"
> **Domain expert:** "No — Pace Downloader needs the path it can write to."
> **Dev:** "Is **Media Metadata Synchronization** the same thing as building **Constructed Metadata**?"
> **Domain expert:** "No — **Constructed Metadata** is the app's episode and season view; **Media Metadata Synchronization** changes Jellyfin-readable files on disk."
> **Dev:** "When does **qBittorrent Path Mapping** matter?"
> **Domain expert:** "Only when qBittorrent reports `/downloads/file.mkv` but Pace Downloader must read that file at `/data/torrents/downloads/file.mkv`."

## Flagged ambiguities

- "setup wizard" refers to the frontend UI component; **Initial Setup** refers to the domain flow.
- "core important stuff" was resolved to **Restart-Applied Setting**.
- "media location" was resolved to **Media Data Location**, the path visible to Pace Downloader, not Jellyfin.
- "metadata" can mean **Constructed Metadata**, **Managed Metadata Files**, or **Media Metadata Synchronization**; prefer the precise term when discussing responsibilities.
- "path mapping" was resolved to **qBittorrent Path Mapping**, translating qBittorrent-reported paths into Pace Downloader-visible paths.
