from dataclasses import dataclass

import pytest

from release_resolver import ReleaseResolutionError, release_contains_crc32, resolve_episode_release


@dataclass
class FakeFile:
    name: str
    is_folder: bool = False

    def __iter__(self):
        return iter(())


class FakeDirectory:
    is_folder = True

    def __init__(self, *children):
        self.children = children

    def __iter__(self):
        return iter(self.children)


@dataclass
class FakeResource:
    info_hash: str
    magnet_url: str
    directory_tree: FakeDirectory | FakeFile | None


class FakeNyaaClient:
    def __init__(self, resources):
        self.resources = resources
        self.requested_ids = []

    def get_resource(self, nyaa_id: int):
        self.requested_ids.append(nyaa_id)
        return self.resources[nyaa_id]


def _episode(**overrides):
    episode = {
        "ep_name": "One Pace - S01E01 - Fixture Episode",
        "sheet_episode_name": "Fixture Arc 01",
        "release_date": "2026-04-22",
        "crc32": "DEADBEEF",
        "crc32_extended": None,
    }
    episode.update(overrides)
    return episode


def _release(title, nyaa_id, publication_date="2026-04-22", info_hash=None, magnet_uri=None):
    return {
        "title": title,
        "normalized_title": "",
        "publication_date": publication_date,
        "categories": [],
        "nyaa_url": None,
        "nyaa_id": nyaa_id,
        "torrent_url": None,
        "magnet_uri": magnet_uri or f"magnet:?xt=urn:btih:{abs(nyaa_id)}",
        "info_hash": info_hash or f"{abs(nyaa_id):040d}",
        "torrent_file_name": f"{title}.torrent",
    }


def _resource(crc32, info_hash="0" * 40, magnet_url="magnet:?xt=urn:btih:fixture"):
    return FakeResource(
        info_hash=info_hash,
        magnet_url=magnet_url,
        directory_tree=FakeDirectory(FakeFile(f"Fixture Release [{crc32}].mkv")),
    )


def test_resolver_uses_individual_release_before_batch_release():
    episode = _episode()
    releases = [
        _release("Fixture Arc", -20),
        _release("Fixture Arc 01", -10),
    ]
    nyaa_client = FakeNyaaClient({
        -10: _resource("DEADBEEF", info_hash="a" * 40, magnet_url="magnet:individual"),
        -20: _resource("DEADBEEF", info_hash="b" * 40, magnet_url="magnet:batch"),
    })

    resolved = resolve_episode_release(episode, releases, nyaa_client=nyaa_client)

    assert resolved.nyaa_id == -10
    assert resolved.info_hash == "a" * 40
    assert resolved.magnet_uri == "magnet:individual"
    assert nyaa_client.requested_ids == [-10]


def test_resolver_prefers_plus_or_minus_one_day_date_match_but_requires_crc32():
    episode = _episode()
    releases = [
        _release("Fixture Arc 01", -30, publication_date="2026-04-21"),
        _release("Fixture Arc 01", -31, publication_date="2026-04-17"),
    ]
    nyaa_client = FakeNyaaClient({
        -30: _resource("BAADF00D", info_hash="c" * 40, magnet_url="magnet:wrong-crc"),
        -31: _resource("DEADBEEF", info_hash="d" * 40, magnet_url="magnet:right-crc"),
    })

    resolved = resolve_episode_release(episode, releases, nyaa_client=nyaa_client)

    assert resolved.nyaa_id == -31
    assert resolved.crc32 == "DEADBEEF"
    assert nyaa_client.requested_ids == [-30, -31]


def test_resolver_falls_back_to_batch_release_after_removing_episode_number():
    episode = _episode(sheet_episode_name="Fixture Arc 03", release_date="2026-05-05", crc32="FACEFEED")
    releases = [
        _release("Other Arc 03", -40, publication_date="2026-05-05"),
        _release("Fixture Arc", -41, publication_date="2026-04-01"),
    ]
    nyaa_client = FakeNyaaClient({
        -40: _resource("FACEFEED", info_hash="e" * 40, magnet_url="magnet:other"),
        -41: FakeResource(
            info_hash="f" * 40,
            magnet_url="magnet:batch",
            directory_tree=FakeDirectory(
                FakeFile("Fixture Arc 01 [11111111].mkv"),
                FakeFile("Fixture Arc 03 [FACEFEED].mkv"),
            ),
        ),
    })

    resolved = resolve_episode_release(episode, releases, nyaa_client=nyaa_client)

    assert resolved.nyaa_id == -41
    assert resolved.magnet_uri == "magnet:batch"
    assert nyaa_client.requested_ids == [-41]


def test_resolver_matches_single_episode_arc_when_sheet_name_has_no_episode_number():
    episode = _episode(
        ep_name="Fixture Show - S07E01 - Side Story",
        ep_number=1,
        sheet_episode_name="Side Story",
        release_date="2026-02-21",
        crc32="1177A2B6",
    )
    releases = [
        _release("Side Story 01", -70, publication_date="2023-10-06"),
        _release("Side Story 01", -71, publication_date="2026-02-21"),
    ]
    nyaa_client = FakeNyaaClient({
        -70: _resource("E75794DB", info_hash="7" * 40, magnet_url="magnet:old"),
        -71: _resource("1177A2B6", info_hash="8" * 40, magnet_url="magnet:current"),
    })

    resolved = resolve_episode_release(episode, releases, nyaa_client=nyaa_client)

    assert resolved.nyaa_id == -71
    assert resolved.magnet_uri == "magnet:current"
    assert nyaa_client.requested_ids == [-71]


def test_resolver_uses_nfo_title_when_sheet_name_is_shorter_than_release_title():
    episode = _episode(
        ep_name="Fixture Show - S25E01 - A Longer Special Episode Name",
        ep_number=1,
        title="A Longer Special Episode Name",
        sheet_episode_name="Special Episode",
        release_date="2024-03-29",
        crc32="2BC41092",
    )
    releases = [
        _release("A Longer Special Episode Name 01", -80, publication_date="2024-03-29"),
    ]
    nyaa_client = FakeNyaaClient({
        -80: _resource("2BC41092", info_hash="9" * 40, magnet_url="magnet:straw-hats"),
    })

    resolved = resolve_episode_release(episode, releases, nyaa_client=nyaa_client)

    assert resolved.nyaa_id == -80
    assert resolved.magnet_uri == "magnet:straw-hats"
    assert nyaa_client.requested_ids == [-80]


def test_resolver_prefers_extended_crc32_when_requested():
    episode = _episode(crc32="11111111", crc32_extended="22222222")
    releases = [
        _release("Fixture Arc 01", -50),
        _release("Fixture Arc 01 Extended Cut", -51),
    ]
    nyaa_client = FakeNyaaClient({
        -50: _resource("11111111", info_hash="1" * 40, magnet_url="magnet:standard"),
        -51: _resource("22222222", info_hash="2" * 40, magnet_url="magnet:extended"),
    })

    resolved = resolve_episode_release(episode, releases, prefer_extended=True, nyaa_client=nyaa_client)

    assert resolved.nyaa_id == -51
    assert resolved.crc32 == "22222222"
    assert resolved.magnet_uri == "magnet:extended"


def test_resolver_uses_crc_override_after_sheet_crc_fails_when_release_date_matches():
    episode = _episode(
        season=3,
        ep_number=2,
        sheet_episode_name="Fixture Arc 02",
        crc32="11111111",
    )
    releases = [
        _release("Fixture Arc 02", -90),
    ]
    nyaa_client = FakeNyaaClient({
        -90: _resource("ABCDEF12", info_hash="a" * 40, magnet_url="magnet:override"),
    })
    overrides = [
        {
            "season": 3,
            "ep_number": 2,
            "release_date": "2026-04-22",
            "crc32": "ABCDEF12",
            "note": "Fixture correction",
        },
    ]

    resolved = resolve_episode_release(
        episode,
        releases,
        nyaa_client=nyaa_client,
        crc32_overrides=overrides,
    )

    assert resolved.nyaa_id == -90
    assert resolved.crc32 == "ABCDEF12"
    assert resolved.magnet_uri == "magnet:override"
    assert resolved.crc32_override_note == "Fixture correction"
    assert nyaa_client.requested_ids == [-90]


def test_resolver_skips_crc_override_when_release_date_does_not_match():
    episode = _episode(
        season=3,
        ep_number=2,
        sheet_episode_name="Fixture Arc 02",
        crc32="11111111",
    )
    releases = [
        _release("Fixture Arc 02", -91, publication_date="2026-04-20"),
    ]
    nyaa_client = FakeNyaaClient({
        -91: _resource("ABCDEF12"),
    })
    overrides = [
        {
            "season": 3,
            "ep_number": 2,
            "release_date": "2026-04-22",
            "crc32": "ABCDEF12",
            "note": "Fixture correction",
        },
    ]

    with pytest.raises(ReleaseResolutionError):
        resolve_episode_release(
            episode,
            releases,
            nyaa_client=nyaa_client,
            crc32_overrides=overrides,
        )


def test_resolver_can_verify_crc_override_from_release_feed_file_name_without_nyaa_id():
    episode = _episode(
        season=4,
        ep_number=1,
        sheet_episode_name="Fixture Special 01",
        crc32="11111111",
    )
    releases = [
        {
            "title": "Fixture Special 01",
            "normalized_title": "",
            "publication_date": "2026-04-22",
            "categories": [],
            "nyaa_url": None,
            "nyaa_id": None,
            "torrent_url": None,
            "magnet_uri": "magnet:feed-only",
            "info_hash": "b" * 40,
            "torrent_file_name": "Fixture Special 01 [ABCDEF12].mkv.torrent",
        },
    ]
    nyaa_client = FakeNyaaClient({})
    overrides = [
        {
            "season": 4,
            "ep_number": 1,
            "release_date": "2026-04-22",
            "crc32": "ABCDEF12",
            "note": "Fixture feed correction",
        },
    ]

    resolved = resolve_episode_release(
        episode,
        releases,
        nyaa_client=nyaa_client,
        resolve_info_hash_to_id_func=lambda _info_hash: None,
        crc32_overrides=overrides,
    )

    assert resolved.nyaa_id is None
    assert resolved.nyaa_resource is None
    assert resolved.crc32 == "ABCDEF12"
    assert resolved.info_hash == "b" * 40
    assert resolved.magnet_uri == "magnet:feed-only"
    assert resolved.crc32_override_note == "Fixture feed correction"
    assert nyaa_client.requested_ids == []


def test_resolver_raises_when_no_candidate_contains_crc32():
    episode = _episode(crc32="DEADBEEF")
    releases = [_release("Fixture Arc 01", -60)]
    nyaa_client = FakeNyaaClient({
        -60: _resource("BAADF00D"),
    })

    with pytest.raises(ReleaseResolutionError):
        resolve_episode_release(episode, releases, nyaa_client=nyaa_client)


def test_release_contains_crc32_checks_nested_file_tree():
    resource = FakeResource(
        info_hash="0" * 40,
        magnet_url="magnet:fixture",
        directory_tree=FakeDirectory(
            FakeDirectory(FakeFile("Fixture Arc 01 [ABCDEF12].mkv")),
        ),
    )

    assert release_contains_crc32(resource, "abcdef12")
    assert not release_contains_crc32(resource, "DEADBEEF")
