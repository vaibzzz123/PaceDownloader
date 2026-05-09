# Pace Downloader

Pace Downloader is a companion app for downloading One Pace episodes through qBittorrent and organizing them for Jellyfin.

## Language

**Initial Setup**:
The required configuration flow and backend restart completed before Pace Downloader can use media storage and qBittorrent.
_Avoid_: first-run setup, setup wizard, setup flow

**Restart Required**:
The temporary state after setup settings are saved but before the backend has restarted and applied them.
_Avoid_: setup complete, ready

**Restart-Applied Setting**:
A setting change that requires a backend restart before Pace Downloader's runtime services use the new value.
_Avoid_: core setting, important setting

**Media Data Location**:
The path visible to Pace Downloader where organized One Pace episode files are placed.
_Avoid_: Jellyfin library path, Jellyfin media path

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
- **Restart Required** occurs before **Initial Setup** is complete.
- A changed **Restart-Applied Setting** creates **Restart Required**.
- **Media Data Location** is owned from Pace Downloader's filesystem perspective; Jellyfin may mount the same data at a different path.
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
> **Dev:** "When does **qBittorrent Path Mapping** matter?"
> **Domain expert:** "Only when qBittorrent reports `/downloads/file.mkv` but Pace Downloader must read that file at `/data/torrents/downloads/file.mkv`."

## Flagged ambiguities

- "setup wizard" refers to the frontend UI component; **Initial Setup** refers to the domain flow.
- "core important stuff" was resolved to **Restart-Applied Setting**.
- "media location" was resolved to **Media Data Location**, the path visible to Pace Downloader, not Jellyfin.
- "path mapping" was resolved to **qBittorrent Path Mapping**, translating qBittorrent-reported paths into Pace Downloader-visible paths.
