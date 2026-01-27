from nyaa_utils import get_nyaa_resource_for_episode
from qbittorrent import QbittorrentClient
from logging_config import get_logger
import db

logger = get_logger(__name__)


class DownloadManager:
    def __init__(
        self,
        qbt_client: QbittorrentClient | None = None,
        metadata_mapping: list[dict] | None = None,
    ):
        self.qbt_client = qbt_client
        self.metadata_mapping = metadata_mapping

    def download_episode(self, episode_id: int, prefer_extended: bool = True):
        episode_metadata = list(
            filter(lambda x: x["id"] == episode_id, self.metadata_mapping)
        )[0]

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
        db.create_episode_download(
            ep_id=episode_id,
            torrent_infohash=infohash,
            crc32=crc32,
            prefer_extended=prefer_extended,
            # TODO: Get actual file path from qBittorrent client, and add path translation
            file_path_torrent=episode_file.name if episode_file else None,
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
        # Logic to remove episode download using qBittorrent client
        pass

    def get_episode_status(self, episode_id: int):
        # Logic to check download status of an episode
        pass

    def list_active_downloads(self):
        # Logic to list all active downloads
        pass

    def _add_episode_to_data_location(self, episode_id: int):
        # Internal method to handle file placement after download
        pass
