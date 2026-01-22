"""Path mapping service for translating between app and qBittorrent filesystems."""

from pathlib import Path

from logging_config import get_logger

logger = get_logger(__name__)


class PathMapper:
    """
    Translates paths between application filesystem and qBittorrent filesystem.

    This is needed for containerized deployments where qBittorrent sees files
    at different paths than this application.

    Example mapping: "/home/user/downloads:/downloads"
    - App sees: /home/user/downloads/torrent/file.mkv
    - qBittorrent sees: /downloads/torrent/file.mkv
    """

    def __init__(self, path_mapping: str | None = None):
        """
        Initialize path mapper.

        Args:
            path_mapping: Colon-separated mapping "app_path:qbt_path"
                         If None or empty, no translation occurs (same filesystem view)
        """
        self._app_prefix: Path | None = None
        self._qbt_prefix: Path | None = None

        if path_mapping:
            parts = path_mapping.split(":", 1)
            if len(parts) == 2 and parts[0] and parts[1]:
                self._app_prefix = Path(parts[0])
                self._qbt_prefix = Path(parts[1])
                logger.debug(
                    "Path mapping configured: app=%s, qbt=%s",
                    self._app_prefix,
                    self._qbt_prefix,
                )
            else:
                logger.warning(
                    "Invalid path mapping format: %s. Expected 'app_path:qbt_path'",
                    path_mapping,
                )

    @property
    def is_configured(self) -> bool:
        """Check if path mapping is configured."""
        return self._app_prefix is not None and self._qbt_prefix is not None

    def app_to_qbt(self, app_path: str) -> str:
        """
        Convert application path to qBittorrent path.

        Args:
            app_path: Path as seen by this application

        Returns:
            Path as seen by qBittorrent
        """
        if not self.is_configured:
            return app_path

        try:
            app_path_obj = Path(app_path)
            relative = app_path_obj.relative_to(self._app_prefix)
            qbt_path = self._qbt_prefix / relative
            return str(qbt_path)
        except ValueError:
            logger.warning(
                "Path %s is not under app prefix %s, returning unchanged",
                app_path,
                self._app_prefix,
            )
            return app_path

    def qbt_to_app(self, qbt_path: str) -> str:
        """
        Convert qBittorrent path to application path.

        Args:
            qbt_path: Path as seen by qBittorrent

        Returns:
            Path as seen by this application
        """
        if not self.is_configured:
            return qbt_path

        try:
            qbt_path_obj = Path(qbt_path)
            relative = qbt_path_obj.relative_to(self._qbt_prefix)
            app_path = self._app_prefix / relative
            return str(app_path)
        except ValueError:
            logger.warning(
                "Path %s is not under qbt prefix %s, returning unchanged",
                qbt_path,
                self._qbt_prefix,
            )
            return qbt_path
