import api


class FakeDownloadManager:
    def list_episode_downloads_with_progress(self):
        return [
            {
                "ep_id": 101,
                "prefer_extended": False,
                "status": "downloading",
                "progress": 25.0,
                "torrent_infohash": "fixture-hash",
                "torrent_name": "Fixture Torrent",
                "created_at": "2026-07-24 12:00:00",
            }
        ]

    def list_torrent_downloads_with_progress(self):
        return [
            {
                "infohash": "fixture-hash",
                "name": "Fixture Torrent",
                "status": "downloading",
                "progress": 25.0,
                "ep_ids": [101],
                "created_at": "2026-07-24 12:00:00",
            }
        ]


def test_download_list_routes_expose_created_at(monkeypatch):
    monkeypatch.setattr(
        api.metadata.metadata_constructor,
        "get_episodes",
        lambda: [{"id": 101, "season": 1, "title": "Fixture Episode"}],
    )
    manager = FakeDownloadManager()

    episodes = api.list_episode_downloads_route(manager)
    torrents = api.list_torrent_downloads_route(manager)

    assert episodes[0].created_at == "2026-07-24 12:00:00"
    assert torrents[0].created_at == "2026-07-24 12:00:00"
