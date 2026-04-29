import json
from pathlib import Path

import metadata


def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def _write_file(path: Path, content: str = "x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_build_episode_mapping_normalizes_sheet_episode_fields(monkeypatch, tmp_path: Path):
    sheets_root = tmp_path / "sheets"
    metadata_root = tmp_path / "metadata" / "One Pace"

    _write_json(
        sheets_root / "arc_overview.json",
        [
            {
                "No.": 1,
                "Arcs": "Test Arc",
            },
        ],
    )
    _write_json(
        sheets_root / "test_arc.json",
        [
            {
                " One Pace Episode": "Test Arc 01",
                "Release Date": "2026.04.22",
                "Length": "00:24:53",
                "MKV CRC32": "DEADBEEF",
                "MKV CRC32 (Extended)": "FACEFEED",
            },
            {
                " One Pace Episode": "Test Arc 02",
                "Release Date": "2026-04-23 00:00:00",
                "Length": "01:02:03",
                "MKV CRC32": {
                    "text": "ABCD1234",
                    "link": "https://nyaa.si/view/0",
                },
                "MKV CRC32 (Extended)": None,
            },
        ],
    )

    _write_file(
        metadata_root / "Season 1" / "season.nfo",
        "<season><title>1. Test Arc</title></season>",
    )
    _write_file(metadata_root / "Season 1" / "One Pace - S01E01 - First Episode.nfo")
    _write_file(metadata_root / "Season 1" / "One Pace - S01E02 - Second Episode.nfo")

    monkeypatch.setattr(metadata, "SHEETS_DIR", sheets_root)
    monkeypatch.setattr(metadata, "METADATA_CONTENT_DIR", metadata_root)

    episodes, seasons = metadata._build_episode_mapping(media_location=None)

    assert seasons == [
        {
            "num": 1,
            "title": "Test Arc",
            "image": "/posters/Season 1/poster.png",
            "description": "",
        },
    ]

    assert episodes[0] == {
        "id": 1,
        "ep_name": "One Pace - S01E01 - First Episode",
        "title": "First Episode",
        "season": 1,
        "ep_number": 1,
        "duration": "24:53",
        "file_location_media": "",
        "sheet_episode_name": "Test Arc 01",
        "release_date": "2026-04-22",
        "torrent_link": None,
        "crc32": "DEADBEEF",
        "torrent_link_extended": None,
        "crc32_extended": "FACEFEED",
    }
    assert episodes[1] == {
        "id": 2,
        "ep_name": "One Pace - S01E02 - Second Episode",
        "title": "Second Episode",
        "season": 1,
        "ep_number": 2,
        "duration": "01:02:03",
        "file_location_media": "",
        "sheet_episode_name": "Test Arc 02",
        "release_date": "2026-04-23",
        "torrent_link": "https://nyaa.si/view/0",
        "crc32": "ABCD1234",
        "torrent_link_extended": None,
        "crc32_extended": None,
    }
