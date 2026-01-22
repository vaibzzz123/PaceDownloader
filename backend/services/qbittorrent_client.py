"""qBittorrent API client wrapper with connection management."""

import base64
import re
from dataclasses import dataclass

import qbittorrentapi

from logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class TorrentInfo:
    """Simplified torrent information."""

    hash: str
    name: str
    state: str
    progress: float
    save_path: str
    content_path: str
    total_size: int
    downloaded: int


@dataclass
class TorrentFile:
    """Information about a file within a torrent."""

    index: int
    name: str
    size: int
    progress: float
    priority: int  # 0=skip, 1=normal, 6=high, 7=max


class QBittorrentClient:
    """
    Wrapper around qbittorrent-api with automatic connection management.

    Provides a simplified interface for common operations needed for
    managing episode downloads.
    """

    def __init__(
        self,
        hostname: str,
        username: str,
        password: str,
        category: str | None = None,
        download_location: str | None = None,
    ):
        """
        Initialize qBittorrent client.

        Args:
            hostname: qBittorrent Web UI host (e.g., "http://localhost:8080")
            username: qBittorrent username
            password: qBittorrent password
            category: Optional category to assign to new torrents
            download_location: Optional download location for new torrents
        """
        self._hostname = hostname
        self._username = username
        self._password = password
        self._category = category
        self._download_location = download_location
        self._client: qbittorrentapi.Client | None = None

    def _ensure_connected(self) -> None:
        """Ensure client is connected, creating connection if needed."""
        if self._client is None:
            self._client = qbittorrentapi.Client(
                host=self._hostname,
                username=self._username,
                password=self._password,
            )
            logger.debug("Created qBittorrent client connection to %s", self._hostname)

    def test_connection(self) -> tuple[bool, str]:
        """
        Test connection to qBittorrent.

        Returns:
            Tuple of (success, message)
        """
        try:
            self._ensure_connected()
            version = self._client.app_version()
            api_version = self._client.app_web_api_version()
            message = f"Connected to qBittorrent {version} (API {api_version})"
            logger.info(message)
            return True, message
        except qbittorrentapi.LoginFailed as e:
            message = f"Login failed: {e}"
            logger.error(message)
            return False, message
        except Exception as e:
            message = f"Connection failed: {e}"
            logger.error(message)
            return False, message

    def add_torrent(
        self,
        magnet_link: str,
        paused: bool = True,
    ) -> str | None:
        """
        Add a torrent by magnet link.

        Args:
            magnet_link: The magnet link to add
            paused: Start paused (default True, for file selection before download)

        Returns:
            Torrent hash (lowercase) if successful, None otherwise
        """
        self._ensure_connected()

        # Extract info hash from magnet for return value
        info_hash = self._extract_hash_from_magnet(magnet_link)
        if not info_hash:
            logger.error("Could not extract info hash from magnet link")
            return None

        options = {
            "is_paused": paused,
            "use_auto_torrent_management": False,
        }

        if self._category:
            options["category"] = self._category
        if self._download_location:
            options["savepath"] = self._download_location

        try:
            result = self._client.torrents_add(urls=magnet_link, **options)
            if result == "Ok.":
                logger.info("Added torrent with hash %s (paused=%s)", info_hash, paused)
                return info_hash.lower()
            else:
                logger.error("Failed to add torrent: %s", result)
                return None
        except Exception as e:
            logger.error("Failed to add torrent: %s", e)
            return None

    def get_torrent(self, torrent_hash: str) -> TorrentInfo | None:
        """
        Get torrent information by hash.

        Args:
            torrent_hash: The torrent hash

        Returns:
            TorrentInfo if found, None otherwise
        """
        self._ensure_connected()

        try:
            torrents = self._client.torrents_info(torrent_hashes=torrent_hash)
            if torrents:
                t = torrents[0]
                return TorrentInfo(
                    hash=t.hash,
                    name=t.name,
                    state=t.state,
                    progress=t.progress,
                    save_path=t.save_path,
                    content_path=t.content_path,
                    total_size=t.total_size,
                    downloaded=t.downloaded,
                )
            return None
        except Exception as e:
            logger.error("Failed to get torrent %s: %s", torrent_hash, e)
            return None

    def get_torrent_files(self, torrent_hash: str) -> list[TorrentFile]:
        """
        Get list of files in a torrent.

        Args:
            torrent_hash: The torrent hash

        Returns:
            List of TorrentFile objects
        """
        self._ensure_connected()

        try:
            files = self._client.torrents_files(torrent_hash=torrent_hash)
            return [
                TorrentFile(
                    index=f.index,
                    name=f.name,
                    size=f.size,
                    progress=f.progress,
                    priority=f.priority,
                )
                for f in files
            ]
        except Exception as e:
            logger.error("Failed to get files for torrent %s: %s", torrent_hash, e)
            return []

    def set_file_priority(
        self,
        torrent_hash: str,
        file_indices: list[int],
        priority: int = 1,
    ) -> bool:
        """
        Set download priority for specific files.

        Args:
            torrent_hash: Torrent hash
            file_indices: List of file indices to modify
            priority: 0=skip, 1=normal, 6=high, 7=max

        Returns:
            True if successful
        """
        self._ensure_connected()

        try:
            self._client.torrents_file_priority(
                torrent_hash=torrent_hash,
                file_ids=file_indices,
                priority=priority,
            )
            logger.debug(
                "Set priority %d for files %s in torrent %s",
                priority,
                file_indices,
                torrent_hash,
            )
            return True
        except Exception as e:
            logger.error(
                "Failed to set file priority for torrent %s: %s",
                torrent_hash,
                e,
            )
            return False

    def skip_all_files(self, torrent_hash: str) -> bool:
        """
        Set all files in torrent to skip (priority 0).

        Args:
            torrent_hash: Torrent hash

        Returns:
            True if successful
        """
        files = self.get_torrent_files(torrent_hash)
        if not files:
            return False

        all_indices = [f.index for f in files]
        return self.set_file_priority(torrent_hash, all_indices, priority=0)

    def resume_torrent(self, torrent_hash: str) -> bool:
        """
        Resume a paused torrent.

        Args:
            torrent_hash: Torrent hash

        Returns:
            True if successful
        """
        self._ensure_connected()

        try:
            self._client.torrents_resume(torrent_hashes=torrent_hash)
            logger.info("Resumed torrent %s", torrent_hash)
            return True
        except Exception as e:
            logger.error("Failed to resume torrent %s: %s", torrent_hash, e)
            return False

    def pause_torrent(self, torrent_hash: str) -> bool:
        """
        Pause a torrent.

        Args:
            torrent_hash: Torrent hash

        Returns:
            True if successful
        """
        self._ensure_connected()

        try:
            self._client.torrents_pause(torrent_hashes=torrent_hash)
            logger.info("Paused torrent %s", torrent_hash)
            return True
        except Exception as e:
            logger.error("Failed to pause torrent %s: %s", torrent_hash, e)
            return False

    def delete_torrent(self, torrent_hash: str, delete_files: bool = False) -> bool:
        """
        Delete a torrent, optionally with files.

        Args:
            torrent_hash: Torrent hash
            delete_files: If True, also delete downloaded files

        Returns:
            True if successful
        """
        self._ensure_connected()

        try:
            self._client.torrents_delete(
                torrent_hashes=torrent_hash,
                delete_files=delete_files,
            )
            logger.info(
                "Deleted torrent %s (delete_files=%s)",
                torrent_hash,
                delete_files,
            )
            return True
        except Exception as e:
            logger.error("Failed to delete torrent %s: %s", torrent_hash, e)
            return False

    def find_file_by_crc32(
        self,
        torrent_hash: str,
        crc32: str,
    ) -> TorrentFile | None:
        """
        Find a file in a torrent by CRC32 hash in filename.

        One Pace files contain CRC32 in brackets: [E5F09F49]

        Args:
            torrent_hash: Torrent hash
            crc32: 8-character CRC32 hex string

        Returns:
            TorrentFile if found, None otherwise
        """
        files = self.get_torrent_files(torrent_hash)
        crc32_upper = crc32.upper()
        crc32_pattern = f"[{crc32_upper}]"

        for f in files:
            if crc32_pattern in f.name.upper():
                logger.debug("Found file with CRC32 %s: %s", crc32, f.name)
                return f

        logger.debug("No file found with CRC32 %s in torrent %s", crc32, torrent_hash)
        return None

    def _extract_hash_from_magnet(self, magnet_link: str) -> str | None:
        """
        Extract info hash from magnet link.

        Args:
            magnet_link: Magnet link

        Returns:
            40-character hex info hash, or None if not found
        """
        # Try hex-encoded hash (40 characters)
        match = re.search(r"urn:btih:([a-fA-F0-9]{40})", magnet_link)
        if match:
            return match.group(1)

        # Try base32 encoded hash (32 characters)
        match = re.search(r"urn:btih:([A-Za-z2-7]{32})", magnet_link)
        if match:
            try:
                decoded = base64.b32decode(match.group(1).upper())
                return decoded.hex()
            except Exception:
                logger.warning("Failed to decode base32 info hash")
                pass

        logger.warning("Could not extract info hash from magnet link")
        return None
