from dataclasses import dataclass

import db
import download_manager
from download_manager import DownloadManager
from release_resolver import ResolvedRelease


@dataclass
class FakeFile:
    name: str
    index: int = 0
    progress: float = 0.0


@dataclass
class FakeTorrentInfo:
    hash: str
    name: str
    save_path: str


@dataclass
class FakeNyaaResource:
    info_hash: str
    magnet_url: str
    directory_tree: None = None


class FakeQbittorrentClient:
    class FilePriority:
        DONT_DOWNLOAD = 0
        NORMAL = 1

    def __init__(self, infohash: str):
        self.infohash = infohash
        self.file = FakeFile("Fixture Release [DEADBEEF].mkv")
        self.torrent_info = FakeTorrentInfo(
            hash=infohash,
            name="Verified Release",
            save_path="/downloads",
        )
        self.created_magnets: list[str] = []
        self.file_lookup_requests: list[tuple[str, str]] = []
        self.priority_changes: list[tuple[str, object, object]] = []
        self.started_torrents: list[str] = []
        self.paused_torrents: list[str] = []

    def create_torrent(self, magnet_link: str) -> FakeTorrentInfo:
        self.created_magnets.append(magnet_link)
        return self.torrent_info

    def pause_torrent(self, infohash: str):
        self.paused_torrents.append(infohash)

    def change_file_priority(self, infohash: str, files: object, priority: object):
        self.priority_changes.append((infohash, files, priority))

    def get_file_by_crc32(self, infohash: str, target_crc32: str) -> FakeFile | None:
        self.file_lookup_requests.append((infohash, target_crc32))
        if target_crc32.lower() in self.file.name.lower():
            return self.file
        return None

    def start_torrent(self, infohash: str):
        self.started_torrents.append(infohash)

    def get_torrent_info(self, infohash: str) -> FakeTorrentInfo:
        return self.torrent_info


def test_download_episode_uses_release_resolver_crc32_and_magnet(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.sqlite3"))
    db.initialize_db()

    episode = {
        "id": 101,
        "ep_name": "One Pace - S01E01 - Fixture Episode",
        "title": "Fixture Episode",
        "season": 1,
        "ep_number": 1,
        "sheet_episode_name": "Fixture Arc 01",
        "release_date": "2026-04-22",
        "crc32": "DEADBEEF",
        "crc32_extended": "FACEFEED",
        "file_location_media": "/media/Season 1/Fixture Release [DEADBEEF].mkv",
    }
    monkeypatch.setattr(download_manager, "get_episodes", lambda: [episode])

    infohash = "a" * 40
    resolved_release = ResolvedRelease(
        release={},
        nyaa_resource=FakeNyaaResource(info_hash=infohash, magnet_url="magnet:verified"),
        nyaa_id=123,
        crc32="DEADBEEF",
        info_hash=infohash,
        magnet_uri="magnet:verified",
    )
    resolver_calls = []

    def fake_resolve_episode_release(received_episode, *, prefer_extended):
        resolver_calls.append((received_episode, prefer_extended))
        return resolved_release

    monkeypatch.setattr(download_manager, "resolve_episode_release", fake_resolve_episode_release)

    qbt_client = FakeQbittorrentClient(infohash)
    manager = DownloadManager(qbt_client)

    manager.download_episode(101, prefer_extended=True)

    assert resolver_calls == [(episode, True)]
    assert qbt_client.created_magnets == ["magnet:verified"]
    assert qbt_client.started_torrents == [infohash]

    torrent_download = db.get_torrent_download(infohash)
    assert torrent_download is not None
    assert torrent_download["name"] == "Verified Release"
    assert torrent_download["status"] == "downloading"

    episode_download = db.get_episode_download_by_ep_id(101)
    assert episode_download is not None
    assert episode_download["crc32"] == "DEADBEEF"
    assert episode_download["prefer_extended"] == 0
    assert episode_download["torrent_infohash"] == infohash
    assert episode_download["file_path_torrent"] == "/downloads/Fixture Release [DEADBEEF].mkv"
    assert episode_download["file_path_disk"] == "/media/Season 1/Fixture Release [DEADBEEF].mkv"
    assert episode_download["status"] == "downloading"


def test_add_episode_to_data_location_syncs_media_metadata(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.sqlite3"))
    db.initialize_db()

    media_root = tmp_path / "media"
    src = tmp_path / "downloads" / "Fixture Release [DEADBEEF].mkv"
    dest = media_root / "Season 1" / "Fixture Release [DEADBEEF].mkv"
    src.parent.mkdir(parents=True)
    src.write_text("video")

    infohash = "b" * 40
    db.create_torrent_download(infohash, name="Verified Release", status="downloading")
    download_id = db.create_episode_download(
        ep_id="101",
        crc32="DEADBEEF",
        torrent_infohash=infohash,
        file_path_torrent=str(src),
        file_path_disk=str(dest),
        status="downloading",
    )

    episodes = [
        {
            "id": 101,
            "season": 1,
            "ep_number": 1,
            "ep_name": "One Pace - S01E01 - Fixture Episode",
            "file_location_media": str(dest),
        }
    ]
    sync_calls = []

    monkeypatch.setattr(download_manager.app_settings, "get_setting_value", lambda field: str(media_root))
    monkeypatch.setattr(download_manager, "get_episodes", lambda: episodes)
    monkeypatch.setattr(
        download_manager,
        "sync_media_metadata",
        lambda media_location, episodes: sync_calls.append((media_location, episodes))
        or {
            "copied_files": 1,
            "skipped_files": 0,
            "removed_files": 0,
            "removed_directories": 0,
        },
    )

    manager = DownloadManager(qbt_client=None)

    assert manager._add_episode_to_data_location(101) == "hardlink"
    assert dest.exists()
    assert db.get_episode_download(download_id)["status"] == "hardlink"
    assert sync_calls == [(media_root, episodes)]


def test_metadata_sync_failure_does_not_fail_episode_placement(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.sqlite3"))
    db.initialize_db()

    media_root = tmp_path / "media"
    src = tmp_path / "downloads" / "Fixture Release [DEADBEEF].mkv"
    dest = media_root / "Season 1" / "Fixture Release [DEADBEEF].mkv"
    src.parent.mkdir(parents=True)
    src.write_text("video")

    infohash = "c" * 40
    db.create_torrent_download(infohash, name="Verified Release", status="downloading")
    db.create_episode_download(
        ep_id="101",
        crc32="DEADBEEF",
        torrent_infohash=infohash,
        file_path_torrent=str(src),
        file_path_disk=str(dest),
        status="downloading",
    )

    monkeypatch.setattr(download_manager.app_settings, "get_setting_value", lambda field: str(media_root))
    monkeypatch.setattr(download_manager, "get_episodes", lambda: [])
    monkeypatch.setattr(
        download_manager,
        "sync_media_metadata",
        lambda media_location, episodes: (_ for _ in ()).throw(RuntimeError("metadata unavailable")),
    )

    manager = DownloadManager(qbt_client=None)

    assert manager._add_episode_to_data_location(101) == "hardlink"
    assert dest.exists()
    assert db.get_episode_download_by_ep_id(101)["status"] == "hardlink"
