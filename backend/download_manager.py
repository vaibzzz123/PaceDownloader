import asyncio
import os
import shutil

from nyaa_utils import get_nyaa_resource_for_episode
from qbittorrent import QbittorrentClient
from metadata import get_episodes
from logging_config import get_logger
import db

logger = get_logger(__name__)


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


    def download_episode(self, episode_id: int, prefer_extended: bool = True):
        episode_metadata = next(ep for ep in get_episodes() if ep["id"] == episode_id)

        logger.info("Starting download for episode ID: %d", episode_id)
        nyaa_resource = get_nyaa_resource_for_episode(episode_metadata)
        if not nyaa_resource or not nyaa_resource.info_hash:
            raise ValueError(f"Could not find nyaa resource for episode ID {episode_id}")

        infohash = nyaa_resource.info_hash
        if prefer_extended:
            crc32 = episode_metadata.get("crc32_extended") or episode_metadata["crc32"]
        else:
            crc32 = episode_metadata["crc32"]

        torrent_download = db.get_torrent_download(infohash)
        if torrent_download:
            self._add_episode_to_existing_torrent(infohash, crc32)
        else:
            self._create_torrent_for_episode(nyaa_resource.magnet_url, infohash, crc32)

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
            prefer_extended=prefer_extended,
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

    def _create_torrent_for_episode(self, magnet_link: str, infohash: str, crc32: str):
        torrent_info = self.qbt_client.create_torrent(magnet_link)
        self.qbt_client.pause_torrent(torrent_info.hash)
        self.qbt_client.change_file_priority(torrent_info.hash, None, self.qbt_client.FilePriority.DONT_DOWNLOAD)
        episode_file = self.qbt_client.get_file_by_crc32(torrent_info.hash, crc32)
        if not episode_file:
            raise ValueError(f"Could not find file with CRC32 {crc32} in torrent {infohash}")
        self.qbt_client.change_file_priority(torrent_info.hash, episode_file, self.qbt_client.FilePriority.NORMAL)
        self.qbt_client.start_torrent(torrent_info.hash)
        db.create_torrent_download(infohash)

    def pause_episode(self, episode_id: int):
        episode_download = db.get_episode_download_by_ep_id(episode_id)
        if not episode_download:
            raise ValueError(f"No download found for episode ID {episode_id}")
        self.qbt_client.pause_torrent(episode_download["torrent_infohash"])
        db.update_episode_download_status(episode_download["id"], "paused")
        logger.info("Paused download for episode ID %d", episode_id)

    def resume_episode(self, episode_id: int):
        episode_download = db.get_episode_download_by_ep_id(episode_id)
        if not episode_download:
            raise ValueError(f"No download found for episode ID {episode_id}")
        self.qbt_client.start_torrent(episode_download["torrent_infohash"])
        db.update_episode_download_status(episode_download["id"], "downloading")
        logger.info("Resumed download for episode ID %d", episode_id)

    def remove_episode(self, episode_id: int):
        episode_download = db.get_episode_download_by_ep_id(episode_id)
        if not episode_download:
            raise ValueError(f"No download found for episode ID {episode_id}")

        infohash = episode_download["torrent_infohash"]
        crc32 = episode_download["crc32"]

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

        # If no other episodes use this torrent, remove it entirely from qBittorrent
        remaining = db.get_episode_downloads_by_torrent(infohash)
        if not remaining:
            self.qbt_client.stop_torrent(infohash)
            db.delete_torrent_download(infohash)
            logger.info("Removed torrent %s from qBittorrent (no remaining episodes)", infohash)

        logger.info("Removed episode download for episode ID %d", episode_id)

    def pause_torrent(self, infohash: str):
        torrent = db.get_torrent_download(infohash)
        if not torrent:
            raise ValueError(f"No torrent found with infohash {infohash}")
        self.qbt_client.pause_torrent(infohash)
        for ep in db.get_episode_downloads_by_torrent(infohash):
            if ep["status"] == "downloading":
                db.update_episode_download_status(ep["id"], "paused")
        logger.info("Paused torrent %s", infohash)

    def resume_torrent(self, infohash: str):
        torrent = db.get_torrent_download(infohash)
        if not torrent:
            raise ValueError(f"No torrent found with infohash {infohash}")
        self.qbt_client.start_torrent(infohash)
        for ep in db.get_episode_downloads_by_torrent(infohash):
            if ep["status"] == "paused":
                db.update_episode_download_status(ep["id"], "downloading")
        logger.info("Resumed torrent %s", infohash)

    def remove_torrent(self, infohash: str):
        torrent = db.get_torrent_download(infohash)
        if not torrent:
            raise ValueError(f"No torrent found with infohash {infohash}")
        self.qbt_client.stop_torrent(infohash)
        db.delete_episode_downloads_by_torrent(infohash)
        db.delete_torrent_download(infohash)
        logger.info("Removed torrent %s", infohash)

    def get_episode_info(self, episode_id: int) -> dict | None:
        episode_download = db.get_episode_download_by_ep_id(episode_id)
        if not episode_download:
            return None

        info = dict(episode_download)

        if episode_download["status"] in ("hardlink", "copy"):
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

    def poll_downloads(self):
        downloading = db.get_episode_downloads_by_status("downloading")
        if not downloading:
            return

        # Group by torrent to batch qBittorrent API calls
        by_torrent: dict[str, list[dict]] = {}
        for ep in downloading:
            by_torrent.setdefault(ep["torrent_infohash"], []).append(ep)

        # Single call to get save_path for all torrents at once
        torrent_infos = self.qbt_client.get_torrents_info(list(by_torrent.keys()))

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
                        self._add_episode_to_data_location(int(ep_id))
                except Exception as e:
                    logger.error("Error processing episode %s: %s", ep_id, e)

    async def start_polling(self):
        settings = db.get_settings()
        interval = settings["qbt_polling_rate"]["value"] if settings else 10
        logger.info("Starting download polling with interval %ds", interval)
        asyncio.create_task(self._poll_loop(interval))

    async def _poll_loop(self, interval: int):
        while True:
            try:
                await asyncio.to_thread(self.poll_downloads)
            except Exception as e:
                logger.error("Error during poll cycle: %s", e)
            await asyncio.sleep(interval)

    def _add_episode_to_data_location(self, episode_id: int):
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
            db.update_episode_download_status(episode_download["id"], "hardlink")
        except OSError as e:
            logger.warning("Hardlink failed for episode %d (%s), falling back to copy", episode_id, e)
            shutil.copy2(src, dest)
            logger.info("Copied episode %d: %s -> %s", episode_id, src, dest)
            db.update_episode_download_status(episode_download["id"], "copy")

    def _translate_file_path(self, file_path: str) -> str:
        settings = db.get_settings()
        if not settings or not settings["qbt_path_mapping"]["value"]:
            return file_path

        mapping = settings["qbt_path_mapping"]["value"]
        # Format: "local_path:remote_path" e.g. "/home/user/downloads/:/downloads/"
        parts = mapping.split(":")
        if len(parts) != 2:
            logger.warning("Invalid qbt_path_mapping format: %s", mapping)
            return file_path

        local_path, remote_path = parts
        if file_path.startswith(remote_path):
            translated = file_path.replace(remote_path, local_path, 1)
            logger.debug("Translated path: %s -> %s", file_path, translated)
            return translated

        return file_path