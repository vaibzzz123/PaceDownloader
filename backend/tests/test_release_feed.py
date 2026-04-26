import json
from pathlib import Path

import data_sources
import metadata


RSS_SAMPLE = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns="https://www.rssboard.org/rss-specification" xmlns:torrent="http://xmlns.ezrss.it/0.1/">
  <channel>
    <item>
      <guid isPermaLink="false">urn:btih:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa</guid>
      <title>Test Arc 01</title>
      <pubDate>Wed, 22 Apr 2026 00:00:00 GMT</pubDate>
      <category domain="https://onepace.net/releases">variant/regular</category>
      <link>https://nyaa.si/view/0</link>
      <enclosure type="application/x-bittorrent" url="https://nyaa.si/download/0.torrent" length="46340"/>
      <torrent:infoHash>AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA</torrent:infoHash>
      <torrent:magnetURI>magnet:?xt=urn:btih:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa</torrent:magnetURI>
      <torrent:fileName>[Fixture Group][001-002] Test Arc 01 [1080p][DEADBEEF].mkv.torrent</torrent:fileName>
    </item>
    <item>
      <guid isPermaLink="false">urn:btih:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb</guid>
      <title>Fixture Batch</title>
      <pubDate>Mon, 01 Jul 2013 00:00:00 GMT</pubDate>
      <category domain="https://onepace.net/releases">variant/regular</category>
      <category domain="https://onepace.net/releases">outdated</category>
      <link>https://nyaa.si/view/https://nyaa.si/?f=0&amp;c=0_0&amp;q=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb</link>
      <enclosure type="application/x-bittorrent" url="https://nyaa.si/download/https://nyaa.si/?f=0&amp;c=0_0&amp;q=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.torrent" length="39799"/>
      <torrent:infoHash>bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb</torrent:infoHash>
      <torrent:magnetURI>magnet:?xt=urn:btih:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb</torrent:magnetURI>
      <torrent:fileName>[Fixture Group][010-020] Fixture Batch [720p].torrent</torrent:fileName>
    </item>
  </channel>
</rss>
"""


def test_parse_onepace_releases_rss_extracts_release_records():
    releases = data_sources.parse_onepace_releases_rss(RSS_SAMPLE)

    assert releases == [
        {
            "title": "Test Arc 01",
            "normalized_title": "test arc 01",
            "publication_date": "2026-04-22",
            "categories": ["variant/regular"],
            "nyaa_url": "https://nyaa.si/view/0",
            "nyaa_id": 0,
            "torrent_url": "https://nyaa.si/download/0.torrent",
            "magnet_uri": "magnet:?xt=urn:btih:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "info_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "torrent_file_name": "[Fixture Group][001-002] Test Arc 01 [1080p][DEADBEEF].mkv.torrent",
        },
        {
            "title": "Fixture Batch",
            "normalized_title": "fixture batch",
            "publication_date": "2013-07-01",
            "categories": ["variant/regular", "outdated"],
            "nyaa_url": "https://nyaa.si/view/https://nyaa.si/?f=0&c=0_0&q=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "nyaa_id": None,
            "torrent_url": "https://nyaa.si/download/https://nyaa.si/?f=0&c=0_0&q=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.torrent",
            "magnet_uri": "magnet:?xt=urn:btih:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "info_hash": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "torrent_file_name": "[Fixture Group][010-020] Fixture Batch [720p].torrent",
        },
    ]


def test_fetch_onepace_releases_writes_parsed_json(monkeypatch, tmp_path: Path):
    class FakeResponse:
        text = RSS_SAMPLE

        def raise_for_status(self):
            return None

    class FakeSession:
        def get(self, url: str, timeout: int):
            assert url == data_sources.ONEPACE_RELEASES_RSS_URL
            assert timeout == 60
            return FakeResponse()

    output_path = tmp_path / "onepace_releases.json"
    monkeypatch.setattr(data_sources, "_get_session_with_retries", lambda: FakeSession())
    monkeypatch.setattr(data_sources, "RELEASES_DIR", tmp_path)
    monkeypatch.setattr(data_sources, "RELEASES_JSON_PATH", output_path)

    data_sources.fetch_onepace_releases()

    releases = json.loads(output_path.read_text())
    assert len(releases) == 2
    assert releases[0]["title"] == "Test Arc 01"
    assert releases[0]["nyaa_id"] == 0


def test_refresh_data_fetches_releases_when_stale(monkeypatch):
    calls = []

    monkeypatch.setattr(metadata, "_is_metadata_fresh", lambda max_age_hours: True)
    monkeypatch.setattr(metadata, "_is_sheets_fresh", lambda max_age_hours: True)
    monkeypatch.setattr(metadata, "_is_releases_fresh", lambda max_age_hours: False)
    monkeypatch.setattr(metadata, "fetch_episode_metadata", lambda: calls.append("metadata"))
    monkeypatch.setattr(metadata, "fetch_onepace_sheet", lambda: calls.append("sheets"))
    monkeypatch.setattr(metadata, "fetch_onepace_releases", lambda: calls.append("releases"))

    metadata._refresh_data()

    assert calls == ["releases"]
