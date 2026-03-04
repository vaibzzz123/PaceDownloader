import time
import re
from enum import Enum

import qbittorrentapi
from qbittorrentapi import TorrentDictionary
from db import get_settings
from logging_config import get_logger

logger = get_logger(__name__)


class QbittorrentClient:
    def __init__(self):
        settings = get_settings()
        if not settings:
            logger.error("Qbittorrent settings not found in database")
            raise ValueError("Qbittorrent settings are required")

        self._hostname = settings["qbt_hostname"]["value"]
        self._username = settings["qbt_username"]["value"]
        self._password = settings["qbt_password"]["value"]
        self._category = settings["qbt_category"]["value"] or ""
        self._download_location = settings["qbt_download_location"]["value"] or ""
        self._client: qbittorrentapi.Client | None = None

        self._initialize_connection()

    def _initialize_connection(self):
        if self._client is None:
            logger.debug(
                "Initializing qBittorrent client connection to %s", self._hostname
            )
            self._client = qbittorrentapi.Client(
                host=self._hostname,
                username=self._username,
                password=self._password,
                REQUESTS_ARGS={"timeout": 10},
            )
            try:
                self._client.auth_log_in()
                logger.info(
                    "Successfully connected to qBittorrent at %s", self._hostname
                )
            except qbittorrentapi.LoginFailed as e:
                logger.error("Failed to log in to qBittorrent: %s", e)
                raise

    class FilePriority(Enum):
        DONT_DOWNLOAD = 0
        NORMAL = 1
        HIGH = 6
        MAX = 7

    def create_torrent(
        self, torrent_magnet_link: str, metadata_timeout: int = 60
    ) -> TorrentDictionary:
        """Add a torrent to qBittorrent using its magnet link, waiting until metadata is fetched."""

        logger.debug("Adding torrent %s to qBittorrent", torrent_magnet_link)
        try:
            info_hash = self.extract_info_hash(torrent_magnet_link)
            resp = self._client.torrents_add(
                urls=torrent_magnet_link,
                category=self._category if self._category else None,
                save_path=self._download_location if self._download_location else None,
            )
            if resp == "Fails.":
                # Torrent already exists in qBittorrent (duplicate add) — proceed to use it
                logger.info("Torrent %s already in qBittorrent, reusing", info_hash)
            elif resp != "Ok.":
                raise Exception(f"Failed to add torrent: {resp}")
            else:
                logger.info("Added torrent for magnet link: %s", torrent_magnet_link)
            logger.info(
                "Waiting for metadata to be fetched for torrent with hash: %s",
                info_hash,
            )

        except Exception as e:
            logger.error(
                "Failed to add torrent with magnet link %s: %s", torrent_magnet_link, e
            )
            raise

        try:
            """Wait for metadata to be ready for a torrent."""
            start_time = time.time()
            while time.time() - start_time < metadata_timeout:
                torrents = self._client.torrents_info(torrent_hashes=info_hash)
                if torrents:
                    torrent = torrents[0]
                    if torrent.name and torrent.name != info_hash:
                        files = self._client.torrents_files(torrent_hash=info_hash)
                        if files:
                            logger.info(
                                "Metadata fetched for torrent: %s", torrent.name
                            )
                            return torrent
                time.sleep(1)
            raise TimeoutError(
                f"Timed out waiting for torrent metadata after {metadata_timeout} seconds"
            )
        except Exception as e:
            logger.error(
                "Failed to retrieve torrent info for hash %s: %s", info_hash, e
            )
            raise

    def extract_info_hash(self, torrent_magnet_link: str) -> str:
        """Extract info hash from a magnet link."""
        hash_match = re.search(
            r"btih:([a-fA-F0-9]{40}|[a-zA-Z2-7]{32})", torrent_magnet_link
        )
        if not hash_match:
            raise ValueError("Could not extract info hash from magnet link")
        return hash_match.group(1).lower()

    def get_torrent_info(self, info_hash: str):
        """Retrieve torrent info by its info hash."""
        try:
            torrents = self._client.torrents_info(torrent_hashes=info_hash)
            if torrents:
                logger.info("Metadata fetched for torrent: %s", info_hash)
                return torrents[0]
        except Exception as e:
            logger.error(
                "Failed to retrieve torrent info for hash %s: %s", info_hash, e
            )
            raise

    def get_torrents_info(self, info_hashes: list[str]) -> dict:
        """Retrieve torrent info for multiple hashes in a single API call. Returns dict keyed by hash."""
        try:
            torrents = self._client.torrents_info(torrent_hashes=info_hashes)
            return {t.hash: t for t in torrents}
        except Exception as e:
            logger.error("Failed to retrieve torrent info for hashes %s: %s", info_hashes, e)
            raise

    def get_torrent_files(self, info_hash: str) -> list:
        """Get all files for a torrent."""
        try:
            return self._client.torrents_files(torrent_hash=info_hash)
        except Exception as e:
            logger.error("Failed to get files for torrent %s: %s", info_hash, e)
            raise

    def start_torrent(self, info_hash: str):
        """Start a torrent by its info hash."""
        try:
            self._client.torrents_resume(torrent_hashes=info_hash)
            logger.info("Started torrent with hash: %s", info_hash)
        except Exception as e:
            logger.error("Failed to start torrent with hash %s: %s", info_hash, e)
            raise

    def pause_torrent(self, info_hash: str):
        """Pause a torrent by its info hash."""
        try:
            self._client.torrents_pause(torrent_hashes=info_hash)
            logger.info("Paused torrent with hash: %s", info_hash)
        except Exception as e:
            logger.error("Failed to pause torrent with hash %s: %s", info_hash, e)
            raise

    def stop_torrent(self, info_hash: str):
        """Stop (remove) a torrent by its info hash."""
        try:
            self._client.torrents_delete(torrent_hashes=info_hash, delete_files=True)
            logger.info("Stopped torrent with hash: %s", info_hash)
        except Exception as e:
            logger.error("Failed to stop torrent with hash %s: %s", info_hash, e)
            raise
    
    def get_file_by_crc32(self, info_hash: str, target_crc32: str):
        """Get a file within a torrent by its CRC32 checksum."""
        try:
            files = self._client.torrents_files(torrent_hash=info_hash)
            for file in files:
                if file.name and target_crc32.lower() in file.name.lower():
                    logger.info(
                        "Found file with CRC32 %s in torrent %s: %s",
                        target_crc32,
                        info_hash,
                        file.name,
                    )
                    return file
            logger.warning(
                "No file with CRC32 %s found in torrent %s", target_crc32, info_hash
            )
            return None
        except Exception as e:
            logger.error(
                "Failed to get files for torrent with hash %s: %s", info_hash, e
            )
            raise

    def change_file_priority(self, info_hash: str, files: list[dict] | dict | None, priority: FilePriority):
        """Change the priority of specific files in a torrent."""
        try:
            if files is None:
                # If no specific file IDs are provided, change priority for all files
                files = self._client.torrents_files(torrent_hash=info_hash)
            elif isinstance(files, dict):
                files = [files]
            
            file_indices = list(map(lambda f: f.index, files))
            self._client.torrents_file_priority(
                torrent_hash=info_hash,
                file_ids=file_indices,
                priority=priority.value
            )
            for f in files:
                logger.debug(
                    "Set priority %d for file %s in torrent %s",
                    priority.value,
                    f.name,
                    info_hash,
                )
        except Exception as e:
            logger.error("Failed to change file priorities for hash %s: %s", info_hash, e)
            raise