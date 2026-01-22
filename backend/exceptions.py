"""Custom exceptions for the download manager."""


class DownloadManagerError(Exception):
    """Base exception for download manager errors."""

    pass


class QBittorrentConnectionError(DownloadManagerError):
    """Failed to connect to qBittorrent."""

    pass


class QBittorrentOperationError(DownloadManagerError):
    """qBittorrent operation failed."""

    pass


class TorrentNotFoundError(DownloadManagerError):
    """Torrent not found in qBittorrent."""

    pass


class FileNotFoundInTorrentError(DownloadManagerError):
    """Expected file not found in torrent."""

    pass


class EpisodeAlreadyDownloadingError(DownloadManagerError):
    """Episode is already being downloaded."""

    pass


class EpisodeNotFoundError(DownloadManagerError):
    """Episode not found in metadata."""

    pass


class MetadataNotFoundError(DownloadManagerError):
    """Episode metadata not found."""

    pass


class PathMappingError(DownloadManagerError):
    """Path mapping configuration error."""

    pass
