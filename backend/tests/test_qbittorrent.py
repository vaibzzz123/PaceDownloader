from unittest.mock import MagicMock, patch

from qbittorrent import QbittorrentClient

@patch("qbittorrent.get_settings")
def test_qbittorrent_client_initialization(mock_get_settings):
    mock_get_settings.return_value = {
        "qbt_hostname": {"value": "http://localhost:8080"},
        "qbt_username": {"value": "admin"},
        "qbt_password": {"value": "adminadmin"},
        "qbt_path_local": {"value": ""},
        "qbt_path_remote": {"value": ""},
        "qbt_category": {"value": ""},
        "qbt_download_location": {"value": ""},
    }

    with patch("qbittorrent.qbittorrentapi.Client") as mock_client_class:
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance

        qb_client = QbittorrentClient()

        mock_client_class.assert_called_once_with(
            host="http://localhost:8080",
            username="admin",
            password="adminadmin",
        )
        mock_client_instance.auth_log_in.assert_called_once()