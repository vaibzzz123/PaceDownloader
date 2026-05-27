import asyncio
import os
import shutil
from pathlib import Path

from qbittorrent import QbittorrentClient
from qbittorrentapi import TorrentState
from metadata import get_episodes, sync_media_metadata
from release_resolver import resolve_episode_release
from logging_config import get_logger
from events import downloads_broadcaster
import app_settings
import db

logger = get_logger(__name__)


def _crc32_matches(expected: str | None, actual: str) -> bool:
    if expected is None:
        return False
    return expected.strip().lower() == actual.strip().lower()


class DownloadManager:
    def __init__(
        self,
        qbt_client: QbittorrentClient | None = None,
    ):
        self.qbt_client = qbt_client

    def reset_all(self):
        """Remove all tracked torrents from qBittorrent (with files) and clear the DB."""
        torrent_downloads = db.get_all_torrent_downloads()
        for torrent in torrent_downloads:
            try:
                self.qbt_client.stop_torrent(torrent["infohash"])
                logger.info("Removed torrent %s from qBittorrent", torrent["infohash"])
            except Exception as e:
                logger.warning("Failed to remove torrent %s from qBittorrent: %s", torrent["infohash"], e)
        db.clear_all_downloads()
        logger.info("Reset complete: all downloads cleared")


    def _sync_media_metadata_after_disk_change(self):
        media_location_value = app_settings.get_setting_value("media_data_location")
        if not media_location_value:
            logger.debug("Skipping media metadata sync after disk change because media_data_location is not configured")
            return

        try:
            summary = sync_media_metadata(Path(media_location_value), episodes=get_episodes())
            logger.info(
                "Media metadata synced after disk change: copied=%d skipped=%d removed=%d removed_dirs=%d",
                summary["copied_files"],
                summary["skipped_files"],
                summary["removed_files"],
                summary["removed_directories"],
            )
        except Exception as e:
            logger.warning("Failed to sync media metadata after disk change: %s", e)


    def download_episode(self, episode_id: int, prefer_extended: bool = True):
        episode_metadata = next(ep for ep in get_episodes() if ep["id"] == episode_id)

        logger.info("Starting download for episode ID: %d", episode_id)
        resolved_release = resolve_episode_release(episode_metadata, prefer_extended=prefer_extended)
        infohash = resolved_release.info_hash
        crc32 = resolved_release.crc32
        is_extended = _crc32_matches(episode_metadata.get("crc32_extended"), crc32)

        torrent_download = db.get_torrent_download(infohash)
        if torrent_download:
            self._add_episode_to_existing_torrent(infohash, crc32)
        else:
            self._create_torrent_for_episode(resolved_release.magnet_uri, infohash, crc32)

        episode_file = self.qbt_client.get_file_by_crc32(infohash, crc32)
        file_path_torrent = None
        if episode_file:
            torrent_info = self.qbt_client.get_torrent_info(infohash)
            full_path = os.path.join(torrent_info.save_path, episode_file.name)
            file_path_torrent = self._translate_file_path(full_path)
        db.create_episode_download(
            ep_id=episode_id,
            torrent_infohash=infohash,
            crc32=crc32,
            prefer_extended=is_extended,
            file_path_torrent=file_path_torrent,
            file_path_disk=episode_metadata["file_location_media"],
            status="downloading",
        )
        logger.info("Download started for episode ID %d with info hash %s", episode_id, infohash)

    def _add_episode_to_existing_torrent(self, infohash: str, crc32: str):
        episode_file = self.qbt_client.get_file_by_crc32(infohash, crc32)
        if not episode_file:
            raise ValueError(f"Could not find file with CRC32 {crc32} in torrent {infohash}")
        self.qbt_client.change_file_priority(infohash, episode_file, self.qbt_client.FilePriority.NORMAL)
        self.qbt_client.start_torrent(infohash)
        db.update_torrent_download_status(infohash, "downloading")

    def _create_torrent_for_episode(self, magnet_link: str, infohash: str, crc32: str):
        torrent_info = self.qbt_client.create_torrent(magnet_link)
        self.qbt_client.pause_torrent(torrent_info.hash)
        self.qbt_client.change_file_priority(torrent_info.hash, None, self.qbt_client.FilePriority.DONT_DOWNLOAD)
        episode_file = self.qbt_client.get_file_by_crc32(torrent_info.hash, crc32)
        if not episode_file:
            raise ValueError(f"Could not find file with CRC32 {crc32} in torrent {infohash}")
        self.qbt_client.change_file_priority(torrent_info.hash, episode_file, self.qbt_client.FilePriority.NORMAL)
        self.qbt_client.start_torrent(torrent_info.hash)
        db.create_torrent_download(infohash, name=torrent_info.name, status="downloading")

    def pause_episode(self, episode_id: int):
        episode_download = db.get_episode_download_by_ep_id(episode_id)
        if not episode_download:
            raise ValueError(f"No download found for episode ID {episode_id}")
        infohash = episode_download["torrent_infohash"]
        self.qbt_client.pause_torrent(infohash)
        for ep in db.get_episode_downloads_by_torrent(infohash):
            if ep["status"] == "downloading":
                db.update_episode_download_status(ep["id"], "paused")
        db.update_torrent_download_status(infohash, "paused")
        logger.info("Paused download for episode ID %d", episode_id)

    def resume_episode(self, episode_id: int):
        episode_download = db.get_episode_download_by_ep_id(episode_id)
        if not episode_download:
            raise ValueError(f"No download found for episode ID {episode_id}")
        infohash = episode_download["torrent_infohash"]
        self.qbt_client.start_torrent(infohash)
        for ep in db.get_episode_downloads_by_torrent(infohash):
            if ep["status"] == "paused":
                db.update_episode_download_status(ep["id"], "downloading")
        db.update_torrent_download_status(infohash, "downloading")
        logger.info("Resumed download for episode ID %d", episode_id)

    def remove_episode(self, episode_id: int) -> tuple[str, str] | None:
        """Remove an episode download.

        Returns (infohash, new_torrent_status) if the torrent's status changed as a
        side-effect of the removal, so the caller can broadcast the change.
        Returns None if the torrent was deleted entirely or its status was unaffected.
        """
        episode_download = db.get_episode_download_by_ep_id(episode_id)
        if not episode_download:
            raise ValueError(f"No download found for episode ID {episode_id}")

        infohash = episode_download["torrent_infohash"]
        crc32 = episode_download["crc32"]

        if infohash is not None:
            # Set file priority to don't download in qBittorrent
            episode_file = self.qbt_client.get_file_by_crc32(infohash, crc32)
            if episode_file:
                self.qbt_client.change_file_priority(infohash, episode_file, self.qbt_client.FilePriority.DONT_DOWNLOAD)

        # Delete the file at the disk (hardlink/copy) location
        file_path_disk = episode_download["file_path_disk"]
        if file_path_disk and os.path.exists(file_path_disk):
            os.remove(file_path_disk)
            logger.info("Removed disk file for episode %d: %s", episode_id, file_path_disk)

        # Remove the episode download DB record
        db.delete_episode_download(episode_download["id"])
        self._sync_media_metadata_after_disk_change()

        if infohash is None:
            logger.info("Removed imported episode download for episode ID %d", episode_id)
            return None

        # Update the torrent's status based on what's left
        remaining = db.get_episode_downloads_by_torrent(infohash)
        if not remaining:
            self.qbt_client.stop_torrent(infohash)
            db.delete_torrent_download(infohash)
            logger.info("Removed torrent %s from qBittorrent (no remaining episodes)", infohash)
            return (infohash, "removed")
        elif all(ep["status"] in ("hardlink", "copy") for ep in remaining):
            db.update_torrent_download_status(infohash, "completed")
            logger.info("Torrent %s marked completed after episode %d removed", infohash, episode_id)
            return (infohash, "completed")

        logger.info("Removed episode download for episode ID %d", episode_id)
        return None

    def pause_torrent(self, infohash: str):
        torrent = db.get_torrent_download(infohash)
        if not torrent:
            raise ValueError(f"No torrent found with infohash {infohash}")
        self.qbt_client.pause_torrent(infohash)
        for ep in db.get_episode_downloads_by_torrent(infohash):
            if ep["status"] == "downloading":
                db.update_episode_download_status(ep["id"], "paused")
        db.update_torrent_download_status(infohash, "paused")
        logger.info("Paused torrent %s", infohash)

    def resume_torrent(self, infohash: str):
        torrent = db.get_torrent_download(infohash)
        if not torrent:
            raise ValueError(f"No torrent found with infohash {infohash}")
        self.qbt_client.start_torrent(infohash)
        for ep in db.get_episode_downloads_by_torrent(infohash):
            if ep["status"] == "paused":
                db.update_episode_download_status(ep["id"], "downloading")
        db.update_torrent_download_status(infohash, "downloading")
        logger.info("Resumed torrent %s", infohash)

    def remove_torrent(self, infohash: str):
        torrent = db.get_torrent_download(infohash)
        if not torrent:
            raise ValueError(f"No torrent found with infohash {infohash}")
        self.qbt_client.stop_torrent(infohash)
        for ep in db.get_episode_downloads_by_torrent(infohash):
            file_path_disk = ep["file_path_disk"]
            if file_path_disk and os.path.exists(file_path_disk):
                os.remove(file_path_disk)
                logger.info("Removed disk file for episode %s: %s", ep["ep_id"], file_path_disk)
        db.delete_episode_downloads_by_torrent(infohash)
        db.delete_torrent_download(infohash)
        self._sync_media_metadata_after_disk_change()
        logger.info("Removed torrent %s", infohash)

    def get_episode_info(self, episode_id: int) -> dict | None:
        episode_download = db.get_episode_download_by_ep_id(episode_id)
        if not episode_download:
            return None

        info = dict(episode_download)

        if episode_download["status"] in ("hardlink", "copy", "imported"):
            info["download_progress"] = 1.0
        else:
            infohash = episode_download["torrent_infohash"]
            crc32 = episode_download["crc32"]
            try:
                episode_file = self.qbt_client.get_file_by_crc32(infohash, crc32)
                info["download_progress"] = episode_file.progress if episode_file else 0.0
            except Exception as e:
                logger.warning("Could not fetch progress for episode %d: %s", episode_id, e)
                info["download_progress"] = 0.0

        return info

    def list_episode_downloads(self) -> list[dict]:
        return db.get_all_episode_downloads()

    def list_torrent_downloads(self) -> list[dict]:
        return db.get_all_torrent_downloads()

    def list_episode_downloads_with_progress(self) -> list[dict]:
        """Return all episode downloads enriched with per-episode qBittorrent progress and torrent name."""
        episode_downloads = db.get_all_episode_downloads()
        if not episode_downloads:
            return []

        by_infohash: dict[str, list[dict]] = {}
        for dl in episode_downloads:
            by_infohash.setdefault(dl["torrent_infohash"], []).append(dl)

        progress_map: dict[int, float] = {}
        torrent_name_map: dict[str | None, str] = {}
        for infohash, eps in by_infohash.items():
            if infohash is None:
                # Imported episodes have no torrent; file is already on disk
                torrent_name_map[None] = ""
                for ep in eps:
                    progress_map[int(ep["ep_id"])] = 100.0
                continue
            torrent_record = db.get_torrent_download(infohash)
            torrent_name_map[infohash] = torrent_record["name"] if torrent_record and torrent_record["name"] else infohash
            try:
                files = self.qbt_client.get_torrent_files(infohash)
                for ep in eps:
                    ep_id = int(ep["ep_id"])
                    if ep["status"] in ("hardlink", "copy", "imported"):
                        progress_map[ep_id] = 100.0
                    else:
                        matching = next((f for f in files if ep["crc32"].lower() in f.name.lower()), None)
                        progress_map[ep_id] = round(matching.progress * 100, 1) if matching else 0.0
            except Exception as e:
                logger.warning("Could not fetch files for torrent %s: %s", infohash, e)
                for ep in eps:
                    ep_id = int(ep["ep_id"])
                    progress_map[ep_id] = 100.0 if ep["status"] in ("hardlink", "copy", "imported") else 0.0

        return [
            {
                **dl,
                "ep_id": int(dl["ep_id"]),
                "progress": progress_map.get(int(dl["ep_id"]), 0.0),
                "torrent_name": torrent_name_map.get(dl["torrent_infohash"], dl["torrent_infohash"] or ""),
            }
            for dl in episode_downloads
        ]

    def list_torrent_downloads_with_progress(self) -> list[dict]:
        """Return all torrent downloads with progress from qBittorrent."""
        torrent_downloads = db.get_all_torrent_downloads()
        if not torrent_downloads:
            return []

        infohashes = [t["infohash"] for t in torrent_downloads]
        try:
            torrent_infos = self.qbt_client.get_torrents_info(infohashes)
        except Exception as e:
            logger.warning("Could not fetch torrent info from qBittorrent: %s", e)
            torrent_infos = {}

        return [
            {
                "infohash": t["infohash"],
                "name": t["name"] if t["name"] else t["infohash"],
                "status": t["status"],
                "progress": round(torrent_infos[t["infohash"]].progress * 100, 1) if t["infohash"] in torrent_infos else 0.0,
                "ep_ids": [int(ep["ep_id"]) for ep in db.get_episode_downloads_by_torrent(t["infohash"])],
            }
            for t in torrent_downloads
        ]

    def poll_downloads(self) -> list[dict]:
        """Poll qBittorrent for download progress and return a list of SSE events."""
        events: list[dict] = []

        downloading = db.get_episode_downloads_by_status("downloading")
        if not downloading:
            return events

        # Group by torrent to batch qBittorrent API calls
        by_torrent: dict[str, list[dict]] = {}
        for ep in downloading:
            by_torrent.setdefault(ep["torrent_infohash"], []).append(ep)

        # Single call to get save_path for all torrents at once
        torrent_infos = self.qbt_client.get_torrents_info(list(by_torrent.keys()))

        # Collect per-torrent progress events
        for infohash, torrent_info in torrent_infos.items():
            events.append({
                "type": "download_progress",
                "subject": "torrent",
                "infohash": infohash,
                "progress": round(torrent_info.progress * 100, 1),
            })

        # One files call per unique torrent instead of one per episode
        for infohash, episodes in by_torrent.items():
            try:
                files = self.qbt_client.get_torrent_files(infohash)
            except Exception as e:
                logger.error("Failed to get files for torrent %s: %s", infohash, e)
                continue

            for ep in episodes:
                ep_id = ep["ep_id"]
                crc32 = ep["crc32"]

                matching_file = next(
                    (f for f in files if crc32.lower() in f.name.lower()), None
                )
                if not matching_file:
                    continue

                events.append({
                    "type": "download_progress",
                    "subject": "episode",
                    "ep_id": int(ep_id),
                    "progress": round(matching_file.progress * 100, 1),
                })

                try:
                    if not ep["file_path_torrent"]:
                        torrent_info = torrent_infos.get(infohash)
                        if torrent_info:
                            full_path = os.path.join(torrent_info.save_path, matching_file.name)
                            translated = self._translate_file_path(full_path)
                            db.update_episode_download_paths(ep["id"], file_path_torrent=translated)
                            logger.info("Resolved file path for episode %s: %s", ep_id, translated)

                    if matching_file.progress >= 1.0:
                        logger.info("Episode %s download complete, placing file", ep_id)
                        final_status = self._add_episode_to_data_location(int(ep_id))
                        events.append({
                            "type": "episode_status_changed",
                            "ep_id": int(ep_id),
                            "status": final_status,
                        })
                        torrent = db.get_torrent_download(infohash)
                        if torrent and torrent["status"] == "completed":
                            events.append({
                                "type": "episode_status_changed",
                                "infohash": infohash,
                                "status": "completed",
                            })
                except Exception as e:
                    logger.error("Error processing episode %s: %s", ep_id, e)

        return events

    async def start_polling(self):
        settings = app_settings.get_settings()
        interval = settings["qbt_polling_rate"]["value"] if settings else 10
        logger.info("Starting download polling with interval %ds", interval)
        asyncio.create_task(self._poll_loop(interval))

    async def _poll_loop(self, interval: int):
        while True:
            try:
                events = await asyncio.to_thread(self.poll_downloads)
                for event in events:
                    downloads_broadcaster.publish(event)
            except Exception as e:
                logger.error("Error during poll cycle: %s", e)
            await asyncio.sleep(interval)

    def scan_existing_episodes(self) -> dict:
        """Scan for pre-existing episode files and create DB records.

        Iterates episode metadata and checks whether each expected file exists on disk,
        then searches qBittorrent for an associated completed torrent by CRC32 substring
        match. No Nyaa API calls needed. Torrent file lists are fetched lazily and cached
        per hash to avoid redundant API calls.

        Returns a dict with keys: found, already_tracked, errors — each a list of
        episode info dicts (ep_id, title, season) with status for found and error for errors.
        """
        found: list[dict] = []
        already_tracked: list[dict] = []
        errors: list[dict] = []

        settings = app_settings.get_settings()
        if not settings:
            logger.warning("Scan: no settings found, aborting")
            return {"found": found, "already_tracked": already_tracked, "errors": errors}

        prefer_extended = bool(settings["prefer_extended"]["value"])
        all_episodes = get_episodes()

        # Fetch all qbt torrents once; files are fetched lazily per torrent and cached
        all_torrents = []
        torrent_files_cache: dict[str, list] = {}
        try:
            all_torrents = self.qbt_client.get_all_torrents()
        except Exception as e:
            logger.warning("Scan: could not reach qBittorrent, all found episodes will be 'imported': %s", e)

        def get_files(infohash: str) -> list:
            if infohash not in torrent_files_cache:
                try:
                    torrent_files_cache[infohash] = self.qbt_client.get_torrent_files(infohash)
                except Exception as exc:
                    logger.warning("Scan: could not fetch files for torrent %s: %s", infohash, exc)
                    torrent_files_cache[infohash] = []
            return torrent_files_cache[infohash]

        for ep in all_episodes:
            file_path = ep.get("file_location_media")
            if not file_path or not os.path.exists(file_path):
                continue

            ep_info = {"ep_id": ep["id"], "title": ep.get("title", ""), "season": ep.get("season", 0)}

            existing = db.get_episode_download_by_ep_id(ep["id"])
            if existing:
                already_tracked.append({**ep_info, "status": existing["status"]})
                continue

            try:
                if prefer_extended and ep.get("crc32_extended"):
                    crc32 = ep["crc32_extended"]
                    is_extended = True
                else:
                    crc32 = ep.get("crc32") or ""
                    is_extended = False

                # Search qbt for a torrent containing this CRC32 file, fully downloaded
                matched_torrent = None
                matched_file = None
                if crc32:
                    for torrent in all_torrents:
                        for f in get_files(torrent.hash):
                            if f.name and crc32.lower() in f.name.lower() and f.progress >= 1.0:
                                matched_torrent = torrent
                                matched_file = f
                                break
                        if matched_torrent:
                            break

                if matched_torrent and matched_file:
                    file_path_torrent = self._translate_file_path(
                        os.path.join(matched_torrent.save_path, matched_file.name)
                    )
                    # Detect hardlink vs copy via inode comparison
                    status = "copy"
                    if os.path.exists(file_path_torrent):
                        try:
                            st_t = os.stat(file_path_torrent)
                            st_d = os.stat(file_path)
                            if st_t.st_ino == st_d.st_ino and st_t.st_dev == st_d.st_dev:
                                status = "hardlink"
                        except OSError:
                            pass

                    torrent_infohash = matched_torrent.hash
                    if not db.get_torrent_download(torrent_infohash):
                        db.create_torrent_download(torrent_infohash, name=matched_torrent.name, status="completed")
                    db.create_episode_download(
                        ep_id=ep["id"],
                        crc32=crc32,
                        torrent_infohash=torrent_infohash,
                        prefer_extended=is_extended,
                        file_path_torrent=file_path_torrent,
                        file_path_disk=file_path,
                        status=status,
                    )
                    logger.info("Scan: episode %d linked to torrent %s (%s)", ep["id"], torrent_infohash, status)
                    found.append({**ep_info, "status": status})
                else:
                    db.create_episode_download(
                        ep_id=ep["id"],
                        crc32=crc32,
                        torrent_infohash=None,
                        prefer_extended=is_extended,
                        file_path_disk=file_path,
                        status="imported",
                    )
                    logger.info("Scan: episode %d imported (no associated torrent found)", ep["id"])
                    found.append({**ep_info, "status": "imported"})

            except Exception as e:
                logger.error("Scan: error processing episode %d: %s", ep["id"], e)
                errors.append({**ep_info, "error": str(e)})

        # Phase 2: recover in-progress torrents whose files aren't at file_location_media yet
        if all_torrents:
            episodes_by_crc32: dict[str, dict] = {}
            for ep in all_episodes:
                if ep.get("crc32"):
                    episodes_by_crc32[ep["crc32"].lower()] = ep
                if ep.get("crc32_extended"):
                    episodes_by_crc32[ep["crc32_extended"].lower()] = ep

            handled_ep_ids = {item["ep_id"] for item in found + already_tracked + errors}

            def qbt_state_to_status(raw_state: str) -> str:
                try:
                    state = TorrentState(raw_state)
                except ValueError:
                    return "downloading"
                if state.is_stopped:
                    return "paused"
                if state.is_checking or state in (TorrentState.QUEUED_DOWNLOAD, TorrentState.QUEUED_UPLOAD):
                    return "pending"
                return "downloading"

            for torrent in all_torrents:
                for f in get_files(torrent.hash):
                    if not f.name or f.progress >= 1.0:
                        continue

                    matched_ep = None
                    matched_crc32_lower = None
                    for crc32_lower, ep in episodes_by_crc32.items():
                        if crc32_lower in f.name.lower():
                            matched_ep = ep
                            matched_crc32_lower = crc32_lower
                            break

                    if not matched_ep:
                        continue

                    ep_id = matched_ep["id"]
                    if ep_id in handled_ep_ids:
                        continue

                    ep_info = {"ep_id": ep_id, "title": matched_ep.get("title", ""), "season": matched_ep.get("season", 0)}

                    existing = db.get_episode_download_by_ep_id(ep_id)
                    if existing:
                        already_tracked.append({**ep_info, "status": existing["status"]})
                        handled_ep_ids.add(ep_id)
                        continue

                    try:
                        is_extended = bool(
                            matched_ep.get("crc32_extended") and
                            matched_ep["crc32_extended"].lower() == matched_crc32_lower
                        )
                        actual_crc32 = matched_ep.get("crc32_extended" if is_extended else "crc32") or ""
                        status = qbt_state_to_status(torrent.state)

                        if not db.get_torrent_download(torrent.hash):
                            db.create_torrent_download(torrent.hash, name=torrent.name, status=status)

                        file_path_torrent = self._translate_file_path(
                            os.path.join(torrent.save_path, f.name)
                        )
                        db.create_episode_download(
                            ep_id=ep_id,
                            crc32=actual_crc32,
                            torrent_infohash=torrent.hash,
                            prefer_extended=is_extended,
                            file_path_torrent=file_path_torrent,
                            file_path_disk=matched_ep.get("file_location_media"),
                            status=status,
                        )
                        found.append({**ep_info, "status": status})
                        handled_ep_ids.add(ep_id)
                        logger.info(
                            "Scan: episode %d recovered from in-progress torrent %s (%s)",
                            ep_id, torrent.hash, status,
                        )
                    except Exception as e:
                        errors.append({**ep_info, "error": str(e)})
                        handled_ep_ids.add(ep_id)
                        logger.error("Scan: error processing in-progress episode %d: %s", ep_id, e)

        logger.info(
            "Scan complete: found=%d, already_tracked=%d, errors=%d",
            len(found), len(already_tracked), len(errors),
        )
        return {"found": found, "already_tracked": already_tracked, "errors": errors}

    def _add_episode_to_data_location(self, episode_id: int) -> str:
        """Place the downloaded file at the media location. Returns the final status string."""
        episode_download = db.get_episode_download_by_ep_id(episode_id)
        if not episode_download:
            raise ValueError(f"No download found for episode ID {episode_id}")

        src = episode_download["file_path_torrent"]
        dest = episode_download["file_path_disk"]
        if not src or not dest:
            raise ValueError(f"Missing file paths for episode ID {episode_id}")

        os.makedirs(os.path.dirname(dest), exist_ok=True)

        try:
            os.link(src, dest)
            logger.info("Hardlinked episode %d: %s -> %s", episode_id, src, dest)
            status = "hardlink"
        except OSError as e:
            logger.warning("Hardlink failed for episode %d (%s), falling back to copy", episode_id, e)
            shutil.copy2(src, dest)
            logger.info("Copied episode %d: %s -> %s", episode_id, src, dest)
            status = "copy"

        db.update_episode_download_status(episode_download["id"], status)
        self._sync_media_metadata_after_disk_change()

        infohash = episode_download["torrent_infohash"]
        remaining = db.get_episode_downloads_by_torrent(infohash)
        if all(ep["status"] in ("hardlink", "copy") for ep in remaining):
            db.update_torrent_download_status(infohash, "completed")
            logger.info("All episodes for torrent %s completed", infohash)

        return status

    def _translate_file_path(self, file_path: str) -> str:
        settings = app_settings.get_settings()
        if not settings:
            return file_path

        local_path = settings["qbt_path_local"]["value"] or ""
        remote_path = settings["qbt_path_remote"]["value"] or ""
        if not local_path or not remote_path:
            return file_path

        if file_path.startswith(remote_path):
            translated = file_path.replace(remote_path, local_path, 1)
            logger.debug("Translated path: %s -> %s", file_path, translated)
            return translated

        return file_path
