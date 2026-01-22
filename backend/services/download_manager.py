"""Download orchestration service - coordinates qBittorrent, database, and file operations."""

import time
from dataclasses import dataclass

from logging_config import get_logger
from repositories.episode_download_repo import EpisodeDownloadRepository
from repositories.torrent_download_repo import TorrentDownloadRepository
from services.file_manager import FileManager
from services.path_mapper import PathMapper
from services.qbittorrent_client import QBittorrentClient, TorrentFile

logger = get_logger(__name__)


@dataclass
class DownloadRequest:
    """Request to download an episode."""

    ep_id: int
    magnet_link: str
    crc32: str
    prefer_extended: bool
    destination_path: str  # Where the final file should go (media directory)


@dataclass
class DownloadResult:
    """Result of a download operation."""

    success: bool
    message: str
    episode_download_id: int | None = None
    torrent_hash: str | None = None


class DownloadManager:
    """
    Orchestrates episode downloads.

    Handles the workflows:
    1. Download new episode (new or existing torrent)
    2. Add episode to existing torrent
    3. Remove episode (cleanup files, update torrent)
    4. Handle download completion
    5. Pause/resume torrents
    """

    def __init__(
        self,
        qbt_client: QBittorrentClient,
        path_mapper: PathMapper,
        file_manager: FileManager,
        episode_repo: EpisodeDownloadRepository,
        torrent_repo: TorrentDownloadRepository,
    ):
        """
        Initialize download manager.

        Args:
            qbt_client: qBittorrent API client
            path_mapper: Path mapping service
            file_manager: File operations service
            episode_repo: Episode download repository
            torrent_repo: Torrent download repository
        """
        self._qbt = qbt_client
        self._path_mapper = path_mapper
        self._file_manager = file_manager
        self._episode_repo = episode_repo
        self._torrent_repo = torrent_repo

    def download_episode(self, request: DownloadRequest) -> DownloadResult:
        """
        Start or resume download of an episode.

        Workflow:
        1. Check if episode already being downloaded
        2. Check if torrent with same magnet exists
        3. If new torrent: add to qBittorrent, create records
        4. If existing torrent: update records, select additional file
        5. Find file by CRC32 and select for download
        6. Resume torrent
        """
        # Check if already downloading
        existing = self._episode_repo.get_by_ep_id(request.ep_id)
        if existing:
            return DownloadResult(
                success=False,
                message=f"Episode {request.ep_id} is already being downloaded",
                episode_download_id=existing.id,
            )

        # Check for existing torrent with same magnet
        existing_torrent = self._torrent_repo.get_by_magnet(request.magnet_link)

        if existing_torrent:
            # Torrent exists - add episode to it
            return self._add_episode_to_existing_torrent(
                request, existing_torrent.qbt_torrent_id
            )
        else:
            # New torrent needed
            return self._download_with_new_torrent(request)

    def _download_with_new_torrent(self, request: DownloadRequest) -> DownloadResult:
        """Add new torrent and start episode download."""
        # Add torrent to qBittorrent (paused)
        torrent_hash = self._qbt.add_torrent(request.magnet_link, paused=True)

        if not torrent_hash:
            return DownloadResult(
                success=False,
                message="Failed to add torrent to qBittorrent",
            )

        # Wait for metadata to load (up to 30 seconds)
        logger.info("Waiting for torrent metadata to load...")
        for _ in range(30):
            torrent_info = self._qbt.get_torrent(torrent_hash)
            if torrent_info and torrent_info.state not in ("metaDL", "stalledDL"):
                break
            time.sleep(1)

        # Get torrent files and find matching file
        files = self._qbt.get_torrent_files(torrent_hash)
        if not files:
            logger.error("Torrent has no files, metadata may still be loading")
            return DownloadResult(
                success=False,
                message="Torrent has no files (metadata may still be loading)",
            )

        # Skip all files first
        self._qbt.skip_all_files(torrent_hash)

        # Find file by CRC32
        matching_file = self._qbt.find_file_by_crc32(torrent_hash, request.crc32)
        if not matching_file:
            return DownloadResult(
                success=False,
                message=f"No file found with CRC32 {request.crc32} in torrent",
            )

        # Select the matching file
        self._qbt.set_file_priority(torrent_hash, [matching_file.index], priority=1)

        # Get torrent info for paths
        torrent_info = self._qbt.get_torrent(torrent_hash)

        # Create torrent download record
        self._torrent_repo.create(
            qbt_torrent_id=torrent_hash,
            torrent_magnet_link=request.magnet_link,
            download_path=torrent_info.save_path if torrent_info else None,
            total_files=len(files),
            selected_files=1,
            status="downloading",
        )

        # Calculate file paths
        # qbt_file_path is the path as qBittorrent sees it
        if torrent_info and torrent_info.content_path:
            qbt_file_path = f"{torrent_info.content_path}/{matching_file.name}"
        else:
            qbt_file_path = matching_file.name

        # Convert to app view path
        app_file_path = self._path_mapper.qbt_to_app(qbt_file_path)

        # Create episode download record
        episode_download_id = self._episode_repo.create(
            ep_id=request.ep_id,
            torrent_magnet_link=request.magnet_link,
            qbt_torrent_id=torrent_hash,
            prefer_extended=request.prefer_extended,
            file_path_torrent=app_file_path,
            file_path_disk=request.destination_path,
            status="downloading",
        )

        # Create junction record
        self._torrent_repo.add_episode(torrent_hash, request.ep_id)

        # Resume torrent
        self._qbt.resume_torrent(torrent_hash)

        # Update torrent status
        self._torrent_repo.update(torrent_hash, status="downloading")

        return DownloadResult(
            success=True,
            message="Download started",
            episode_download_id=episode_download_id,
            torrent_hash=torrent_hash,
        )

    def _add_episode_to_existing_torrent(
        self,
        request: DownloadRequest,
        torrent_hash: str,
    ) -> DownloadResult:
        """Add episode to an existing torrent."""
        # Find file by CRC32
        matching_file = self._qbt.find_file_by_crc32(torrent_hash, request.crc32)
        if not matching_file:
            return DownloadResult(
                success=False,
                message=f"No file found with CRC32 {request.crc32} in torrent",
            )

        # Select the file for download
        self._qbt.set_file_priority(torrent_hash, [matching_file.index], priority=1)

        # Get torrent info for paths
        torrent_info = self._qbt.get_torrent(torrent_hash)

        # Calculate file paths
        if torrent_info and torrent_info.content_path:
            qbt_file_path = f"{torrent_info.content_path}/{matching_file.name}"
        else:
            qbt_file_path = matching_file.name

        app_file_path = self._path_mapper.qbt_to_app(qbt_file_path)

        # Create episode record
        episode_download_id = self._episode_repo.create(
            ep_id=request.ep_id,
            torrent_magnet_link=request.magnet_link,
            qbt_torrent_id=torrent_hash,
            prefer_extended=request.prefer_extended,
            file_path_torrent=app_file_path,
            file_path_disk=request.destination_path,
            status="downloading",
        )

        # Update junction table
        self._torrent_repo.add_episode(torrent_hash, request.ep_id)

        # Update torrent selected file count
        self._torrent_repo.increment_selected_files(torrent_hash)

        # Ensure torrent is running
        self._qbt.resume_torrent(torrent_hash)

        return DownloadResult(
            success=True,
            message="Episode added to existing torrent",
            episode_download_id=episode_download_id,
            torrent_hash=torrent_hash,
        )

    def handle_download_complete(self, ep_id: int) -> DownloadResult:
        """
        Handle completion of an episode download.

        Creates hardlink (or copy) to destination.
        """
        episode = self._episode_repo.get_by_ep_id(ep_id)
        if not episode:
            return DownloadResult(
                success=False,
                message=f"Episode download {ep_id} not found",
            )

        if not episode.file_path_torrent:
            return DownloadResult(
                success=False,
                message="Source file path not set",
            )

        if not episode.file_path_disk:
            return DownloadResult(
                success=False,
                message="Destination file path not set",
            )

        # Create destination file (hardlink preferred, copy fallback)
        success, file_type, error = self._file_manager.create_destination_file(
            source_path=episode.file_path_torrent,
            dest_path=episode.file_path_disk,
            prefer_hardlink=True,
        )

        if success:
            self._episode_repo.update(
                ep_id=ep_id,
                status="completed",
                file_type=file_type,
            )
            logger.info(
                "Episode %d download completed, created %s at %s",
                ep_id,
                file_type,
                episode.file_path_disk,
            )
            return DownloadResult(
                success=True,
                message=f"Download completed, created {file_type}",
            )
        else:
            self._episode_repo.update(ep_id=ep_id, status="error")
            return DownloadResult(
                success=False,
                message=error or "Unknown error creating destination file",
            )

    def remove_episode(
        self,
        ep_id: int,
        delete_torrent_if_empty: bool = False,
    ) -> DownloadResult:
        """
        Remove an episode download.

        Workflow:
        1. Delete hardlink/copy at destination
        2. Deselect file in qBittorrent
        3. Remove episode from torrent tracking
        4. Delete episode record
        5. Optionally delete entire torrent if no episodes remain
        """
        episode = self._episode_repo.get_by_ep_id(ep_id)
        if not episode:
            return DownloadResult(
                success=False,
                message=f"Episode download {ep_id} not found",
            )

        torrent_hash = episode.qbt_torrent_id

        # Delete destination file if exists
        if episode.file_path_disk:
            success, error = self._file_manager.delete_file(episode.file_path_disk)
            if not success:
                logger.warning("Failed to delete destination file: %s", error)

        # Find and deselect file in qBittorrent
        if episode.file_path_torrent:
            files = self._qbt.get_torrent_files(torrent_hash)
            for f in files:
                # Check if this is the file for this episode
                if f.name in episode.file_path_torrent:
                    self._qbt.set_file_priority(torrent_hash, [f.index], priority=0)
                    logger.debug("Deselected file %s in torrent", f.name)
                    break

        # Remove from junction table
        self._torrent_repo.remove_episode(torrent_hash, ep_id)

        # Decrement selected files count
        self._torrent_repo.decrement_selected_files(torrent_hash)

        # Delete episode record
        self._episode_repo.delete(ep_id)

        # Check if torrent has remaining episodes
        remaining_episodes = self._torrent_repo.get_episode_ids(torrent_hash)

        if not remaining_episodes:
            if delete_torrent_if_empty:
                self._qbt.delete_torrent(torrent_hash, delete_files=True)
                self._torrent_repo.delete(torrent_hash)
                return DownloadResult(
                    success=True,
                    message="Episode removed and empty torrent deleted",
                )
            else:
                return DownloadResult(
                    success=True,
                    message="Episode removed. Torrent has no more tracked episodes.",
                )

        return DownloadResult(
            success=True,
            message="Episode removed",
        )

    def pause_episode(self, ep_id: int) -> DownloadResult:
        """
        Pause an episode download.

        Note: This pauses the entire torrent, affecting all episodes
        sharing the same torrent.
        """
        episode = self._episode_repo.get_by_ep_id(ep_id)
        if not episode:
            return DownloadResult(
                success=False,
                message=f"Episode download {ep_id} not found",
            )

        success = self._qbt.pause_torrent(episode.qbt_torrent_id)
        if success:
            # Update all episodes for this torrent to paused status
            episodes = self._episode_repo.get_by_qbt_torrent_id(episode.qbt_torrent_id)
            for ep in episodes:
                if ep.status == "downloading":
                    self._episode_repo.update(ep.ep_id, status="paused")

            self._torrent_repo.update(episode.qbt_torrent_id, status="paused")

            return DownloadResult(
                success=True,
                message="Torrent paused (affects all episodes in this torrent)",
            )
        else:
            return DownloadResult(
                success=False,
                message="Failed to pause torrent",
            )

    def resume_episode(self, ep_id: int) -> DownloadResult:
        """
        Resume an episode download.

        Note: This resumes the entire torrent, affecting all episodes
        sharing the same torrent.
        """
        episode = self._episode_repo.get_by_ep_id(ep_id)
        if not episode:
            return DownloadResult(
                success=False,
                message=f"Episode download {ep_id} not found",
            )

        success = self._qbt.resume_torrent(episode.qbt_torrent_id)
        if success:
            # Update all episodes for this torrent to downloading status
            episodes = self._episode_repo.get_by_qbt_torrent_id(episode.qbt_torrent_id)
            for ep in episodes:
                if ep.status == "paused":
                    self._episode_repo.update(ep.ep_id, status="downloading")

            self._torrent_repo.update(episode.qbt_torrent_id, status="downloading")

            return DownloadResult(
                success=True,
                message="Torrent resumed (affects all episodes in this torrent)",
            )
        else:
            return DownloadResult(
                success=False,
                message="Failed to resume torrent",
            )

    def check_episode_progress(self, ep_id: int) -> tuple[float, bool]:
        """
        Check the download progress of an episode.

        Returns:
            Tuple of (progress 0.0-1.0, is_complete)
        """
        episode = self._episode_repo.get_by_ep_id(ep_id)
        if not episode:
            return 0.0, False

        # Get the file for this episode
        files = self._qbt.get_torrent_files(episode.qbt_torrent_id)
        for f in files:
            if episode.file_path_torrent and f.name in episode.file_path_torrent:
                return f.progress, f.progress >= 1.0

        return 0.0, False

    def get_episode_status(self, ep_id: int) -> dict | None:
        """
        Get detailed status of an episode download.

        Returns dict with status, progress, file paths, etc.
        """
        episode = self._episode_repo.get_by_ep_id(ep_id)
        if not episode:
            return None

        progress, is_complete = self.check_episode_progress(ep_id)

        return {
            "ep_id": episode.ep_id,
            "status": episode.status,
            "progress": progress,
            "is_complete": is_complete,
            "prefer_extended": episode.prefer_extended,
            "file_path_torrent": episode.file_path_torrent,
            "file_path_disk": episode.file_path_disk,
            "file_type": episode.file_type,
            "torrent_hash": episode.qbt_torrent_id,
        }
