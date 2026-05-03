"""Resolve episode metadata to a verified One Pace release torrent."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, cast

from crc_utils import file_names_contain_crc32, normalize_crc32
from data_sources import RELEASES_JSON_PATH
from date_utils import parse_iso_date
from logging_config import get_logger
from nyaa_utils import (
    NyaaResource,
    NyaaResourceClient,
    NyaaSearchItem,
    date_string_from_nyaa_time,
    iter_nyaa_resource_file_names,
    iter_nyaa_search_items_by_crc32,
    resolve_info_hash_to_id,
)
from pynyaasi.nyaasi import NyaaSiClient

logger = get_logger(__name__)

DATE_MATCH_WINDOW_DAYS = 1
NO_DATE_DISTANCE = 999_999
CRC32_OVERRIDES_JSON_PATH = Path(__file__).parent / "release_crc32_overrides.json"
NyaaIdResolver = Callable[[str], int | None]


class EpisodeReleaseMetadata(TypedDict, total=False):
    """Episode fields used to match sheet metadata against release feed records."""

    id: int
    ep_name: str
    title: str
    season: int
    ep_number: int
    sheet_episode_name: str | None
    release_title: str | None
    release_date: str | None
    crc32: str | None
    crc32_extended: str | None


class OnePaceRelease(TypedDict, total=False):
    """Parsed release-feed record from data/releases/onepace_releases.json."""

    title: str
    normalized_title: str
    publication_date: str | None
    categories: list[str]
    nyaa_url: str | None
    nyaa_id: int | str | None
    torrent_url: str | None
    magnet_uri: str | None
    info_hash: str | None
    torrent_file_name: str | None


class ReleaseResolutionError(ValueError):
    """Raised when no release can be verified for an episode."""


@dataclass(frozen=True)
class ResolvedRelease:
    """A release whose Nyaa listing or feed file name contains the requested CRC32."""

    release: OnePaceRelease
    nyaa_resource: NyaaResource | None
    nyaa_id: int | None
    crc32: str
    info_hash: str
    magnet_uri: str
    crc32_override_note: str | None = None


class EpisodeCrc32Override(TypedDict, total=False):
    """CRC correction used only after the spreadsheet CRCs fail verification."""

    season: int
    ep_number: int
    release_date: str
    crc32: str | None
    crc32_extended: str | None
    note: str | None


def load_onepace_releases(path: Path = RELEASES_JSON_PATH) -> list[OnePaceRelease]:
    """Load parsed One Pace release feed records from disk."""
    if not path.exists():
        raise ReleaseResolutionError(f"One Pace release feed cache not found: {path}")

    with open(path) as f:
        releases = json.load(f)

    if not isinstance(releases, list) or not all(isinstance(release, dict) for release in releases):
        raise ReleaseResolutionError(f"One Pace release feed cache is invalid: {path}")

    return cast(list[OnePaceRelease], releases)


def load_crc32_overrides(path: Path = CRC32_OVERRIDES_JSON_PATH) -> list[EpisodeCrc32Override]:
    """Load metadata-only CRC overrides used after normal CRC verification fails."""
    if not path.exists():
        return []

    with open(path) as f:
        payload = json.load(f)

    overrides = payload.get("episode_crc32_overrides") if isinstance(payload, dict) else None
    if not isinstance(overrides, list) or not all(isinstance(override, dict) for override in overrides):
        raise ReleaseResolutionError(f"CRC32 override file is invalid: {path}")

    return cast(list[EpisodeCrc32Override], overrides)


def normalize_release_lookup_text(value: str | None) -> str:
    """Normalize release and episode names for title matching."""
    if not value:
        return ""
    normalized = re.sub(r"\s+", " ", value).strip().lower()
    return re.sub(r"[^a-z0-9]+", " ", normalized).strip()


def resolve_episode_release(
    episode: EpisodeReleaseMetadata,
    releases: Sequence[OnePaceRelease] | None = None,
    *, # this means everything after this is a keyword argument, needs to be explicit ex) resolve_episode_release(episode, releases, prefer_extended=False)
    prefer_extended: bool = True,
    nyaa_client: NyaaResourceClient | None = None,
    resolve_info_hash_to_id_func: NyaaIdResolver = resolve_info_hash_to_id,
    crc32_overrides: Sequence[EpisodeCrc32Override] | None = None,
) -> ResolvedRelease:
    """Find a release for an episode and verify it contains the requested CRC32."""
    release_records = releases if releases is not None else load_onepace_releases()
    override_records = crc32_overrides if crc32_overrides is not None else load_crc32_overrides()
    client = nyaa_client or NyaaSiClient()
    resource_cache: dict[int, NyaaResource] = {}
    search_cache: dict[str, list[NyaaSearchItem]] = {}

    for is_extended, crc32 in _episode_crc_options(episode, prefer_extended):
        candidates = [
            # Only does a soft check based on the parsed RSS data titles, etc.
            *_find_ranked_individual_release_candidates(
                episode,
                release_records,
                is_extended=is_extended,
            ),
            *_find_ranked_batch_release_candidates(episode, release_records),
        ]

        for release in candidates:
            # Stronger check verifying with nyaa.si API
            resolved = _verify_release_candidate(
                release=release,
                crc32=crc32,
                nyaa_client=client,
                resource_cache=resource_cache,
                resolve_info_hash_to_id_func=resolve_info_hash_to_id_func,
            )
            if resolved is not None:
                return resolved

    for is_extended, crc32, override in _episode_override_crc_options(episode, override_records, prefer_extended):
        candidates = [
            *_find_ranked_individual_release_candidates(
                episode,
                release_records,
                is_extended=is_extended,
            ),
            *_find_ranked_batch_release_candidates(episode, release_records),
        ]

        for release in candidates:
            if not _release_date_matches_expected_date(
                release=release,
                expected_date=override.get("release_date"),
            ):
                continue

            resolved = _verify_release_candidate(
                release=release,
                crc32=crc32,
                nyaa_client=client,
                resource_cache=resource_cache,
                resolve_info_hash_to_id_func=resolve_info_hash_to_id_func,
                crc32_override_note=override.get("note"),
            )
            if resolved is not None:
                return resolved

            resolved = _verify_release_feed_file_name_candidate(
                release=release,
                crc32=crc32,
                crc32_override_note=override.get("note"),
            )
            if resolved is not None:
                return resolved

    for is_extended, crc32, override in _episode_override_crc_options(episode, override_records, prefer_extended):
        resolved = _resolve_from_nyaa_search(
            episode=episode,
            crc32=crc32,
            is_extended=is_extended,
            expected_date=override.get("release_date"),
            nyaa_client=client,
            resource_cache=resource_cache,
            search_cache=search_cache,
            crc32_override_note=override.get("note"),
        )
        if resolved is not None:
            return resolved

    for is_extended, crc32 in _episode_crc_options(episode, prefer_extended):
        resolved = _resolve_from_nyaa_search(
            episode=episode,
            crc32=crc32,
            is_extended=is_extended,
            expected_date=episode.get("release_date"),
            nyaa_client=client,
            resource_cache=resource_cache,
            search_cache=search_cache,
        )
        if resolved is not None:
            return resolved

    raise ReleaseResolutionError(
        f"Could not find a One Pace release containing CRC32 for {episode.get('ep_name') or episode.get('sheet_episode_name')}"
    )


# TODO: This feels so weird, fix this function up later
def _episode_crc_options(episode: EpisodeReleaseMetadata, prefer_extended: bool) -> list[tuple[bool, str]]:
    standard_crc32 = normalize_crc32(episode.get("crc32"))
    extended_crc32 = normalize_crc32(episode.get("crc32_extended"))

    options: list[tuple[bool, str | None]]
    if prefer_extended:
        options = [(True, extended_crc32), (False, standard_crc32)]
    else:
        options = [(False, standard_crc32), (True, extended_crc32)]

    valid_options: list[tuple[bool, str]] = []
    for is_extended, crc32 in options:
        if crc32 is not None:
            valid_options.append((is_extended, crc32))

    return valid_options


def _episode_override_crc_options(
    episode: EpisodeReleaseMetadata,
    overrides: Sequence[EpisodeCrc32Override],
    prefer_extended: bool,
) -> list[tuple[bool, str, EpisodeCrc32Override]]:
    matching_overrides = [
        override
        for override in overrides
        if _override_matches_episode(override, episode)
    ]

    options: list[tuple[bool, str, EpisodeCrc32Override]] = []
    for override in matching_overrides:
        standard_crc32 = normalize_crc32(override.get("crc32"))
        extended_crc32 = normalize_crc32(override.get("crc32_extended"))

        if prefer_extended:
            ordered_crc_values = [(True, extended_crc32), (False, standard_crc32)]
        else:
            ordered_crc_values = [(False, standard_crc32), (True, extended_crc32)]

        for is_extended, crc32 in ordered_crc_values:
            if crc32 is not None:
                options.append((is_extended, crc32, override))

    return options


def _override_matches_episode(
    override: EpisodeCrc32Override,
    episode: EpisodeReleaseMetadata,
) -> bool:
    return (
        override.get("season") == episode.get("season")
        and override.get("ep_number") == episode.get("ep_number")
    )


def _release_date_matches_expected_date(
    *,
    release: OnePaceRelease,
    expected_date: object,
) -> bool:
    distance = _release_date_distance_days(release=release, expected_date=expected_date)
    if distance is None:
        return False
    return abs(distance) <= DATE_MATCH_WINDOW_DAYS


def _find_ranked_individual_release_candidates(
    episode: EpisodeReleaseMetadata,
    releases: Sequence[OnePaceRelease],
    *,
    is_extended: bool,
) -> list[OnePaceRelease]:
    episode_titles = _episode_individual_title_candidates(episode)
    matches: list[OnePaceRelease] = []
    for release in releases:
        for episode_title in episode_titles:
            if _is_individual_title_match(release, episode_title, is_extended=is_extended):
                matches.append(release)
                break

    return sorted(matches, key=lambda release: _release_candidate_date_rank(episode, release))


def _find_ranked_batch_release_candidates(
    episode: EpisodeReleaseMetadata,
    releases: Sequence[OnePaceRelease],
) -> list[OnePaceRelease]:
    batch_titles = _episode_batch_title_candidates(episode)
    individual_titles = _episode_individual_title_candidates(episode)
    matches: list[OnePaceRelease] = []
    for release in releases:
        for batch_title in batch_titles:
            if _is_batch_title_match(release, batch_title, individual_titles):
                matches.append(release)
                break

    return sorted(matches, key=lambda release: _release_candidate_date_rank(episode, release))


def _verify_release_candidate(
    *,
    release: OnePaceRelease,
    crc32: str,
    nyaa_client: NyaaResourceClient,
    resource_cache: dict[int, NyaaResource],
    resolve_info_hash_to_id_func: NyaaIdResolver,
    crc32_override_note: str | None = None,
) -> ResolvedRelease | None:
    nyaa_id = _release_nyaa_id(release, resolve_info_hash_to_id_func)
    if nyaa_id is None:
        logger.debug("Skipping release without resolvable Nyaa ID: %s", release.get("title"))
        return None

    resource = _get_cached_nyaa_resource(
        nyaa_id=nyaa_id,
        release=release,
        nyaa_client=nyaa_client,
        resource_cache=resource_cache,
        fetch_context="Nyaa resource",
    )
    if resource is None:
        return None

    if not file_names_contain_crc32(iter_nyaa_resource_file_names(resource), crc32):
        logger.debug("Nyaa resource %s did not contain CRC32 %s", nyaa_id, crc32)
        return None

    return _resolved_release_from_verified_resource(
        release=release,
        resource=resource,
        nyaa_id=nyaa_id,
        crc32=crc32,
        missing_data_context=f"release {release.get('title')}",
        crc32_override_note=crc32_override_note,
    )


def _verify_release_feed_file_name_candidate(
    *,
    release: OnePaceRelease,
    crc32: str,
    crc32_override_note: str | None,
) -> ResolvedRelease | None:
    if _release_explicit_nyaa_id(release) is not None:
        return None

    torrent_file_name = release.get("torrent_file_name") or ""
    if not file_names_contain_crc32([torrent_file_name], crc32):
        return None

    info_hash = (release.get("info_hash") or "").lower()
    magnet_uri = release.get("magnet_uri") or ""
    if not info_hash or not magnet_uri:
        return None

    return ResolvedRelease(
        release=cast(OnePaceRelease, dict(release)),
        nyaa_resource=None,
        nyaa_id=None,
        crc32=crc32,
        info_hash=info_hash,
        magnet_uri=magnet_uri,
        crc32_override_note=crc32_override_note,
    )


def _resolve_from_nyaa_search(
    *,
    episode: EpisodeReleaseMetadata,
    crc32: str,
    is_extended: bool,
    expected_date: object,
    nyaa_client: NyaaResourceClient,
    resource_cache: dict[int, NyaaResource],
    search_cache: dict[str, list[NyaaSearchItem]],
    crc32_override_note: str | None = None,
) -> ResolvedRelease | None:
    for search_item in iter_nyaa_search_items_by_crc32(
        nyaa_client=nyaa_client,
        crc32=crc32,
        search_cache=search_cache,
    ):
        release = _release_from_nyaa_search_item(search_item)
        if not _release_date_matches_expected_date(release=release, expected_date=expected_date):
            continue

        search_title = release.get("title")
        if not _text_matches_episode_title(search_title, episode=episode, is_extended=is_extended):
            continue

        resolved = _verify_nyaa_search_candidate(
            release=release,
            episode=episode,
            crc32=crc32,
            is_extended=is_extended,
            nyaa_client=nyaa_client,
            resource_cache=resource_cache,
            crc32_override_note=crc32_override_note,
        )
        if resolved is not None:
            return resolved

    return None


def _verify_nyaa_search_candidate(
    *,
    release: OnePaceRelease,
    episode: EpisodeReleaseMetadata,
    crc32: str,
    is_extended: bool,
    nyaa_client: NyaaResourceClient,
    resource_cache: dict[int, NyaaResource],
    crc32_override_note: str | None = None,
) -> ResolvedRelease | None:
    nyaa_id = _release_explicit_nyaa_id(release)
    if nyaa_id is None:
        return None

    resource = _get_cached_nyaa_resource(
        nyaa_id=nyaa_id,
        release=release,
        nyaa_client=nyaa_client,
        resource_cache=resource_cache,
        fetch_context="Nyaa search result",
    )
    if resource is None:
        return None

    file_names = list(iter_nyaa_resource_file_names(resource))
    if not file_names_contain_crc32(file_names, crc32):
        logger.debug("Nyaa search result %s did not contain CRC32 %s", nyaa_id, crc32)
        return None

    if not _file_names_match_episode(file_names, episode=episode, is_extended=is_extended):
        logger.debug("Nyaa search result %s did not match episode title", nyaa_id)
        return None

    return _resolved_release_from_verified_resource(
        release=release,
        resource=resource,
        nyaa_id=nyaa_id,
        crc32=crc32,
        missing_data_context=f"Nyaa search result {nyaa_id}",
        crc32_override_note=crc32_override_note,
    )


def _get_cached_nyaa_resource(
    *,
    nyaa_id: int,
    release: OnePaceRelease,
    nyaa_client: NyaaResourceClient,
    resource_cache: dict[int, NyaaResource],
    fetch_context: str,
) -> NyaaResource | None:
    try:
        resource = resource_cache.get(nyaa_id)
        if resource is None:
            resource = nyaa_client.get_resource(nyaa_id)
            resource_cache[nyaa_id] = resource
        return resource
    except Exception as e:
        logger.warning("Could not fetch %s %s for release %s: %s", fetch_context, nyaa_id, release.get("title"), e)
        return None


def _resolved_release_from_verified_resource(
    *,
    release: OnePaceRelease,
    resource: NyaaResource,
    nyaa_id: int,
    crc32: str,
    missing_data_context: str,
    crc32_override_note: str | None,
) -> ResolvedRelease | None:
    info_hash = (resource.info_hash or release.get("info_hash") or "").lower()
    magnet_uri = resource.magnet_url or release.get("magnet_uri") or ""
    if not info_hash or not magnet_uri:
        logger.warning("Verified %s is missing info hash or magnet URI", missing_data_context)
        return None

    return ResolvedRelease(
        release=cast(OnePaceRelease, dict(release)),
        nyaa_resource=resource,
        nyaa_id=nyaa_id,
        crc32=crc32,
        info_hash=info_hash,
        magnet_uri=magnet_uri,
        crc32_override_note=crc32_override_note,
    )


def _release_from_nyaa_search_item(search_item: NyaaSearchItem) -> OnePaceRelease:
    title = getattr(search_item, "title", "")
    return {
        "title": title,
        "normalized_title": normalize_release_lookup_text(title),
        "publication_date": date_string_from_nyaa_time(getattr(search_item, "time", None)),
        "categories": [],
        "nyaa_url": None,
        "nyaa_id": getattr(search_item, "id", None),
        "torrent_url": getattr(search_item, "torrent_download_url", None),
        "magnet_uri": getattr(search_item, "magnet_url", None),
        "info_hash": None,
        "torrent_file_name": title,
    }


def _release_nyaa_id(
    release: OnePaceRelease,
    resolve_info_hash_to_id_func: NyaaIdResolver,
) -> int | None:
    explicit_nyaa_id = _release_explicit_nyaa_id(release)
    if explicit_nyaa_id is not None:
        return explicit_nyaa_id

    info_hash = release.get("info_hash")
    if isinstance(info_hash, str) and info_hash:
        return resolve_info_hash_to_id_func(info_hash)

    return None


def _release_explicit_nyaa_id(release: OnePaceRelease) -> int | None:
    nyaa_id = release.get("nyaa_id")
    if isinstance(nyaa_id, int):
        return nyaa_id
    if isinstance(nyaa_id, str) and nyaa_id.isdigit():
        return int(nyaa_id)
    return None


def _is_individual_title_match(
    release: OnePaceRelease,
    episode_title: str,
    *,
    is_extended: bool,
) -> bool:
    release_title = _release_normalized_title(release)
    if not release_title or not episode_title:
        return False
    if release_title == episode_title:
        return True
    return is_extended and release_title in {f"{episode_title} extended", f"{episode_title} extended cut"}


def _is_batch_title_match(
    release: OnePaceRelease,
    batch_title: str,
    individual_titles: Sequence[str],
) -> bool:
    release_title = _release_normalized_title(release)
    if not release_title or not batch_title:
        return False
    if release_title in individual_titles:
        return False
    if release_title == batch_title:
        return True
    if release_title == f"{batch_title} batch":
        return True
    return release_title.startswith(f"{batch_title} ") and not _looks_like_numbered_release(release_title)


def _file_names_match_episode(
    file_names: Iterable[str],
    *,
    episode: EpisodeReleaseMetadata,
    is_extended: bool,
) -> bool:
    for file_name in file_names:
        if _text_matches_episode_title(file_name, episode=episode, is_extended=is_extended):
            return True
    return False


def _text_matches_episode_title(
    value: str | None,
    *,
    episode: EpisodeReleaseMetadata,
    is_extended: bool,
) -> bool:
    normalized_value = normalize_release_lookup_text(value)
    if not normalized_value:
        return False

    for episode_title in _episode_individual_title_candidates(episode):
        if _normalized_text_contains_episode_title(
            normalized_value,
            episode_title=episode_title,
            is_extended=is_extended,
        ):
            return True
    return False


def _normalized_text_contains_episode_title(
    normalized_value: str,
    *,
    episode_title: str,
    is_extended: bool,
) -> bool:
    if is_extended:
        return (
            _normalized_text_contains_phrase(normalized_value, f"{episode_title} extended")
            or _normalized_text_contains_phrase(normalized_value, f"{episode_title} extended cut")
        )

    if _normalized_text_contains_phrase(normalized_value, f"{episode_title} extended"):
        return False
    if _normalized_text_contains_phrase(normalized_value, f"{episode_title} extended cut"):
        return False
    return _normalized_text_contains_phrase(normalized_value, episode_title)


def _normalized_text_contains_phrase(normalized_value: str, phrase: str) -> bool:
    return f" {phrase} " in f" {normalized_value} "


def _release_candidate_date_rank(episode: EpisodeReleaseMetadata, release: OnePaceRelease) -> tuple[int, int]:
    distance = _release_date_distance_days(release=release, expected_date=episode.get("release_date"))
    if distance is None:
        return (2, NO_DATE_DISTANCE)
    abs_distance = abs(distance)
    if abs_distance <= DATE_MATCH_WINDOW_DAYS:
        return (0, abs_distance)
    return (1, abs_distance)


def _release_date_distance_days(
    *,
    release: OnePaceRelease,
    expected_date: object,
) -> int | None:
    parsed_expected_date = parse_iso_date(expected_date)
    release_date = parse_iso_date(release.get("publication_date"))
    if parsed_expected_date is None or release_date is None:
        return None
    return (release_date - parsed_expected_date).days


def _episode_individual_title_candidates(episode: EpisodeReleaseMetadata) -> list[str]:
    titles: list[str] = []
    for title in _episode_title_values(episode):
        normalized_title = normalize_release_lookup_text(title)
        _append_unique_title(titles, normalized_title)
        if normalized_title and not _looks_like_numbered_release(normalized_title):
            episode_number = _episode_number_suffix(episode)
            if episode_number is not None:
                _append_unique_title(titles, f"{normalized_title} {episode_number}")

    return titles


def _episode_title_values(episode: EpisodeReleaseMetadata) -> list[str]:
    values: list[str] = []
    for value in (
        episode.get("sheet_episode_name"),
        episode.get("release_title"),
        episode.get("title"),
        _title_from_episode_file_name(episode.get("ep_name")),
        episode.get("ep_name"),
    ):
        if isinstance(value, str) and value.strip():
            values.append(value)
    return values


# Gets title by removing everything before the final '-' and using that as a title candidate
def _title_from_episode_file_name(ep_name: str | None) -> str | None:
    if not isinstance(ep_name, str) or not ep_name.strip():
        return None
    return ep_name.rsplit(" - ", 1)[-1].strip()


def _append_unique_title(titles: list[str], title: str) -> None:
    if title and title not in titles:
        titles.append(title)


def _episode_number_suffix(episode: EpisodeReleaseMetadata) -> str | None:
    ep_number = episode.get("ep_number")
    if not isinstance(ep_number, int):
        return None
    return f"{ep_number:02d}"


def _episode_batch_title_candidates(episode: EpisodeReleaseMetadata) -> list[str]:
    titles: list[str] = []
    for title in _episode_individual_title_candidates(episode):
        _append_unique_title(titles, _remove_trailing_episode_number(title))
    return titles


def _remove_trailing_episode_number(title: str) -> str:
    words = title.split()
    while words and words[-1] in {"extended", "cut"}:
        words.pop()
    if words and words[-1].isdigit():
        words.pop()
    return " ".join(words)


def _release_normalized_title(release: OnePaceRelease) -> str:
    return normalize_release_lookup_text(release.get("normalized_title") or release.get("title"))


def _looks_like_numbered_release(title: str) -> bool:
    words = title.split()
    while words and words[-1] in {"extended", "cut"}:
        words.pop()
    return bool(words and words[-1].isdigit())
