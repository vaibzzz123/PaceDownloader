import time
import re

import qbittorrentapi
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
        self._path_mapping = settings["qbt_path_mapping"]["value"] or ""
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
            )
            try:
                self._client.auth_log_in()
                logger.info(
                    "Successfully connected to qBittorrent at %s", self._hostname
                )
            except qbittorrentapi.LoginFailed as e:
                logger.error("Failed to log in to qBittorrent: %s", e)
                raise
    
    def create_torrent(self, torrent_magnet_link: str):
        """
        Add a torrent and wait for metadata to be fetched, then pause it.

        Args:
            torrent_magnet_link: The magnet link to add
            timeout: Maximum seconds to wait for metadata (default 60)

        Returns:
            The torrent info once metadata is fetched
        """

        if self._client is None:
            self._initialize_connection()

        # Extract info hash from magnet link to identify the torrent
        hash_match = re.search(r'btih:([a-fA-F0-9]{40}|[a-zA-Z2-7]{32})', torrent_magnet_link)
        if not hash_match:
            raise ValueError("Could not extract info hash from magnet link")

        info_hash = hash_match.group(1).lower()

        logger.debug("Adding torrent %s to qBittorrent", torrent_magnet_link)
        try:
            resp = self._client.torrents_add(
                urls=torrent_magnet_link,
                category=self._category if self._category else None,
                save_path=self._download_location if self._download_location else None,
            )
            if(resp != "Ok."):
                raise Exception(f"Failed to add torrent: {resp}")
            logger.info("Added torrent for magnet link: %s", torrent_magnet_link)

            return info_hash

        except Exception as e:
            logger.error("Failed to add torrent with magnet link %s: %s", torrent_magnet_link, e)
            raise

    def get_torrent_info(self, info_hash: str, timeout: int = 60):
        """Retrieve torrent info by its info hash."""
        if self._client is None:
            self._initialize_connection()

        try:
            # Poll until metadata is fetched
            start_time = time.time()
            while time.time() - start_time < timeout:
                torrents = self._client.torrents_info(torrent_hashes=info_hash)
                if torrents:
                    torrent = torrents[0]
                    # Metadata is fetched when the torrent has a name (not just the hash)
                    # and has files available
                    if torrent.name and torrent.name != info_hash:
                        files = self._client.torrents_files(torrent_hash=info_hash)
                        if files:
                            logger.info("Metadata fetched for torrent: %s", torrent.name)
                            return torrent
                time.sleep(1)

            raise TimeoutError(f"Timed out waiting for torrent metadata after {timeout} seconds")

        except Exception as e:
            logger.error("Failed to retrieve torrent info for hash %s: %s", info_hash, e)
            raise
    
    def pause_torrent(self, info_hash: str):
        """Pause a torrent by its info hash."""
        if self._client is None:
            self._initialize_connection()

        try:
            self._client.torrents_pause(torrent_hashes=info_hash)
            logger.info("Paused torrent with hash: %s", info_hash)
        except Exception as e:
            logger.error("Failed to pause torrent with hash %s: %s", info_hash, e)
            raise
    
    def stop_torrent(self, info_hash: str):
        """Stop (remove) a torrent by its info hash."""
        if self._client is None:
            self._initialize_connection()

        try:
            self._client.torrents_delete(torrent_hashes=info_hash, delete_files=True)
            logger.info("Stopped torrent with hash: %s", info_hash)
        except Exception as e:
            logger.error("Failed to stop torrent with hash %s: %s", info_hash, e)
            raise