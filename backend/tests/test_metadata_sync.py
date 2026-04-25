import asyncio
from pathlib import Path

import api
import metadata


def _write_file(path: Path, content: str = "x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _episode_stem(season: int, episode_number: int) -> str:
    return f"One Pace - S{season:02d}E{episode_number:02d} - Episode {season}-{episode_number}"


def _build_episode(media_root: Path, season: int, episode_number: int, present: bool) -> dict:
    video_path = media_root / f"Season {season}" / f"{_episode_stem(season, episode_number)}.mkv"
    if present:
        _write_file(video_path, "video")

    return {
        "season": season,
        "ep_number": episode_number,
        "ep_name": _episode_stem(season, episode_number),
        "file_location_media": str(video_path),
    }


def _create_sources(metadata_root: Path, assets_root: Path, season_totals: dict[int, int]):
    for filename in metadata.ROOT_METADATA_FILES:
        _write_file(metadata_root / filename, filename)

    for filename in ("backdrop.jpg", "backdrop-2.jpg", "backdrop-3.jpg", "backdrop-4.jpg"):
        _write_file(metadata_root / filename, filename)

    for filename in ("backdrop-5.jpg", "backdrop-6.jpg", "backdrop-7.jpg", "backdrop-8.jpg"):
        _write_file(assets_root / filename, filename)

    for season, total_episodes in season_totals.items():
        season_dir = metadata_root / f"Season {season}"
        _write_file(season_dir / "poster.png", f"poster-{season}")
        _write_file(season_dir / "season.nfo", f"season-{season}")
        for episode_number in range(1, total_episodes + 1):
            _write_file(
                season_dir / f"{_episode_stem(season, episode_number)}.nfo",
                f"nfo-{season}-{episode_number}",
            )


def _patch_sources(monkeypatch, metadata_root: Path, assets_root: Path):
    monkeypatch.setattr(metadata, "METADATA_CONTENT_DIR", metadata_root)
    monkeypatch.setattr(metadata, "ASSETS_DIR", assets_root)


def test_sync_media_metadata_copies_relevant_files_and_removes_stale_managed_files(monkeypatch, tmp_path: Path):
    metadata_root = tmp_path / "metadata-root"
    assets_root = tmp_path / "assets-root"
    media_root = tmp_path / "media-root"
    _create_sources(metadata_root, assets_root, {13: 1, 14: 2, 15: 1})
    _patch_sources(monkeypatch, metadata_root, assets_root)

    episodes = [
        _build_episode(media_root, 13, 1, present=False),
        _build_episode(media_root, 14, 1, present=True),
        _build_episode(media_root, 14, 2, present=False),
        _build_episode(media_root, 15, 1, present=True),
    ]

    _write_file(media_root / "backdrop-2.jpg", "stale")
    _write_file(media_root / "Season 13" / "poster.png", "stale")
    _write_file(media_root / "Season 13" / "season.nfo", "stale")
    _write_file(media_root / "Season 14" / f"{_episode_stem(14, 2)}.nfo", "stale")

    summary = metadata.sync_media_metadata(media_root, episodes)

    assert summary["active_seasons"] == [14, 15]
    assert summary["enabled_backdrops"] == ["backdrop-3.jpg", "backdrop-5.jpg", "backdrop-6.jpg"]
    assert summary["removed_directories"] == 1

    assert (media_root / "logo.png").exists()
    assert (media_root / "poster.png").exists()
    assert (media_root / "poster-2.png").exists()
    assert (media_root / "tvshow.nfo").exists()
    assert (media_root / "backdrop-3.jpg").exists()
    assert (media_root / "backdrop-5.jpg").exists()
    assert (media_root / "backdrop-6.jpg").exists()
    assert not (media_root / "backdrop-2.jpg").exists()

    assert (media_root / "Season 14" / "poster.png").exists()
    assert (media_root / "Season 14" / "season.nfo").exists()
    assert (media_root / "Season 14" / f"{_episode_stem(14, 1)}.nfo").exists()
    assert not (media_root / "Season 14" / f"{_episode_stem(14, 2)}.nfo").exists()

    assert (media_root / "Season 15" / "poster.png").exists()
    assert (media_root / "Season 15" / "season.nfo").exists()
    assert (media_root / "Season 15" / f"{_episode_stem(15, 1)}.nfo").exists()
    assert not (media_root / "Season 13").exists()


def test_sync_media_metadata_preserves_unknown_files_when_directory_cannot_be_removed(monkeypatch, tmp_path: Path):
    metadata_root = tmp_path / "metadata-root"
    assets_root = tmp_path / "assets-root"
    media_root = tmp_path / "media-root"
    _create_sources(metadata_root, assets_root, {14: 1})
    _patch_sources(monkeypatch, metadata_root, assets_root)

    episodes = [_build_episode(media_root, 14, 1, present=False)]
    _write_file(media_root / "Season 14" / "poster.png", "stale")
    _write_file(media_root / "Season 14" / "season.nfo", "stale")
    _write_file(media_root / "Season 14" / "custom.txt", "keep me")

    summary = metadata.sync_media_metadata(media_root, episodes)

    assert summary["removed_directories"] == 0
    assert (media_root / "Season 14").exists()
    assert (media_root / "Season 14" / "custom.txt").exists()
    assert not (media_root / "Season 14" / "poster.png").exists()
    assert not (media_root / "Season 14" / "season.nfo").exists()


def test_sync_media_metadata_removes_skipped_extended_nfo_from_inactive_season(monkeypatch, tmp_path: Path):
    metadata_root = tmp_path / "metadata-root"
    assets_root = tmp_path / "assets-root"
    media_root = tmp_path / "media-root"
    _create_sources(metadata_root, assets_root, {6: 2})
    _write_file(metadata_root / "Season 6" / "One Pace - S06E05 - Live (Extended).nfo", "extended")
    _patch_sources(monkeypatch, metadata_root, assets_root)

    episodes = [
        _build_episode(media_root, 6, 1, present=False),
        _build_episode(media_root, 6, 2, present=False),
    ]
    _write_file(media_root / "Season 6" / "One Pace - S06E05 - Live (Extended).nfo", "stale")

    summary = metadata.sync_media_metadata(media_root, episodes)

    assert summary["removed_files"] == 1
    assert summary["removed_directories"] == 1
    assert not (media_root / "Season 6").exists()


def test_sync_media_metadata_uses_halfway_rules_for_half_season_backdrops(monkeypatch, tmp_path: Path):
    metadata_root = tmp_path / "metadata-root"
    assets_root = tmp_path / "assets-root"
    media_root = tmp_path / "media-root"
    _create_sources(metadata_root, assets_root, {16: 25, 19: 25})
    _patch_sources(monkeypatch, metadata_root, assets_root)

    episodes = [
        *[_build_episode(media_root, 16, episode_number, present=episode_number <= 13) for episode_number in range(1, 26)],
        *[_build_episode(media_root, 19, episode_number, present=episode_number <= 12) for episode_number in range(1, 26)],
    ]

    summary = metadata.sync_media_metadata(media_root, episodes)

    assert "backdrop-7.jpg" in summary["enabled_backdrops"]
    assert "backdrop-8.jpg" not in summary["enabled_backdrops"]


def test_sync_media_metadata_uses_latest_season_final_episode_exception(monkeypatch, tmp_path: Path):
    metadata_root = tmp_path / "metadata-root"
    assets_root = tmp_path / "assets-root"
    media_root = tmp_path / "media-root"
    _create_sources(metadata_root, assets_root, {36: 20})
    _patch_sources(monkeypatch, metadata_root, assets_root)

    episodes = [
        _build_episode(media_root, 36, episode_number, present=episode_number == 20)
        for episode_number in range(1, 21)
    ]

    summary = metadata.sync_media_metadata(media_root, episodes)

    assert "backdrop.jpg" in summary["enabled_backdrops"]
    assert (media_root / "backdrop.jpg").exists()


def test_metadata_sync_route_returns_summary(monkeypatch):
    async def fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(
        api.db,
        "get_settings",
        lambda: {"media_data_location": {"value": "/tmp/one-pace-media"}},
    )
    monkeypatch.setattr(api.asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(
        api,
        "refresh_build_and_sync_media",
        lambda media_location, force_refresh, save_mapping: {
            "copied_files": 3,
            "removed_files": 1,
            "removed_directories": 2,
            "skipped_files": 4,
            "active_seasons": [14, 15],
            "enabled_backdrops": ["backdrop-3.jpg"],
        },
    )

    response = asyncio.run(api.sync_metadata_route())

    assert response.model_dump() == {
        "copied_files": 3,
        "removed_files": 1,
        "removed_directories": 2,
        "skipped_files": 4,
        "active_seasons": [14, 15],
        "enabled_backdrops": ["backdrop-3.jpg"],
    }
