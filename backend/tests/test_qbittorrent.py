from unittest.mock import MagicMock, patch

import pytest
import qbittorrentapi
from qbittorrentapi.torrents import TorrentsAddedMetadata

from qbittorrent import QbittorrentClient


def _mock_settings():
    return {
        "qbt_hostname": {"value": "http://qbittorrent.test:18080"},
        "qbt_username": {"value": "admin"},
        "qbt_password": {"value": "adminadmin"},
        "qbt_path_local": {"value": ""},
        "qbt_path_remote": {"value": ""},
        "qbt_category": {"value": ""},
        "qbt_download_location": {"value": ""},
    }


@patch("qbittorrent.get_settings")
def test_qbittorrent_client_initialization(mock_get_settings):
    mock_get_settings.return_value = _mock_settings()

    with patch("qbittorrent.qbittorrentapi.Client") as mock_client_class:
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance

        qb_client = QbittorrentClient()

        mock_client_class.assert_called_once_with(
            host="http://qbittorrent.test:18080",
            username="admin",
            password="adminadmin",
            REQUESTS_ARGS={"timeout": 10},
        )
        mock_client_instance.auth_log_in.assert_called_once()


@patch("qbittorrent.get_settings")
def test_create_torrent_accepts_torrents_added_metadata_response(mock_get_settings):
    mock_get_settings.return_value = _mock_settings()
    infohash = "a" * 40
    torrent = MagicMock(hash=infohash, name="Fixture Torrent")

    with patch("qbittorrent.qbittorrentapi.Client") as mock_client_class:
        mock_client_instance = MagicMock()
        mock_client_instance.torrents_add.return_value = TorrentsAddedMetadata({
            "added_torrent_ids": [infohash],
            "failure_count": 0,
            "pending_count": 0,
            "success_count": 1,
        })
        mock_client_instance.torrents_info.return_value = [torrent]
        mock_client_instance.torrents_files.return_value = [MagicMock(name="episode.mkv")]
        mock_client_class.return_value = mock_client_instance

        qb_client = QbittorrentClient()

        assert qb_client.create_torrent(f"magnet:?xt=urn:btih:{infohash}") == torrent


@patch("qbittorrent.get_settings")
def test_create_torrent_reuses_existing_torrent_on_conflict(mock_get_settings):
    mock_get_settings.return_value = _mock_settings()
    infohash = "b" * 40
    torrent = MagicMock(hash=infohash, name="Existing Torrent")

    with patch("qbittorrent.qbittorrentapi.Client") as mock_client_class:
        mock_client_instance = MagicMock()
        mock_client_instance.torrents_add.side_effect = qbittorrentapi.Conflict409Error("Conflict")
        mock_client_instance.torrents_info.return_value = [torrent]
        mock_client_instance.torrents_files.return_value = [MagicMock(name="episode.mkv")]
        mock_client_class.return_value = mock_client_instance

        qb_client = QbittorrentClient()

        assert qb_client.create_torrent(f"magnet:?xt=urn:btih:{infohash}") == torrent


@patch("qbittorrent.get_settings")
def test_create_torrent_rejects_failed_torrents_added_metadata_response(mock_get_settings):
    mock_get_settings.return_value = _mock_settings()
    infohash = "c" * 40

    with patch("qbittorrent.qbittorrentapi.Client") as mock_client_class:
        mock_client_instance = MagicMock()
        mock_client_instance.torrents_add.return_value = TorrentsAddedMetadata({
            "added_torrent_ids": [],
            "failure_count": 1,
            "pending_count": 0,
            "success_count": 0,
        })
        mock_client_class.return_value = mock_client_instance

        qb_client = QbittorrentClient()

        with pytest.raises(Exception, match="Failed to add torrent"):
            qb_client.create_torrent(f"magnet:?xt=urn:btih:{infohash}")
