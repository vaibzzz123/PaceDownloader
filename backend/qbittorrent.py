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
