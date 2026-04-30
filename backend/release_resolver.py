"""Resolve episode metadata to a verified One Pace release torrent."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal, Protocol, TypedDict, cast

from data_sources import RELEASES_JSON_PATH
from logging_config import get_logger
from nyaa_utils import resolve_info_hash_to_id
from pynyaasi.nyaasi import NyaaSiClient

logger = get_logger(__name__)

DATE_MATCH_WINDOW_DAYS = 1
NO_DATE_DISTANCE = 999_999
CrcField = Literal["crc32", "crc32_extended"]
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


class NyaaDirectoryTreeNode(Protocol):
    """File or folder node from pynyaasi's torrent directory tree."""

    name: str
    is_folder: bool

    def __iter__(self) -> Iterator[NyaaDirectoryTreeNode]:
        ...


class NyaaFlatFileItem(Protocol):
    """Flat file item shape used by tests or alternate Nyaa resource clients."""

    name: str


class NyaaResource(Protocol):
    """Subset of pynyaasi's ResourceItem used for verification."""

    info_hash: str | None
    magnet_url: str | None
    directory_tree: NyaaDirectoryTreeNode | None


class NyaaResourceClient(Protocol):
    """Client interface needed to fetch a Nyaa resource by ID."""

    def get_resource(self, nyaa_id: int) -> NyaaResource:
        ...


class ReleaseResolutionError(ValueError):
    """Raised when no release can be verified for an episode."""


@dataclass(frozen=True)
class ResolvedRelease:
    """A release whose Nyaa file listing contains the requested episode CRC32."""

    release: OnePaceRelease
    nyaa_resource: NyaaResource
    nyaa_id: int
    crc32: str
    info_hash: str
    magnet_uri: str


def load_onepace_releases(path: Path = RELEASES_JSON_PATH) -> list[OnePaceRelease]:
    """Load parsed One Pace release feed records from disk."""
    if not path.exists():
        raise ReleaseResolutionError(f"One Pace release feed cache not found: {path}")

    with open(path) as f:
        releases = json.load(f)

    if not isinstance(releases, list) or not all(isinstance(release, dict) for release in releases):
        raise ReleaseResolutionError(f"One Pace release feed cache is invalid: {path}")

    return cast(list[OnePaceRelease], releases)


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
) -> ResolvedRelease:
    """Find a release for an episode and verify it contains the requested CRC32."""
    release_records = releases if releases is not None else load_onepace_releases()
    client = nyaa_client or NyaaSiClient()
    resource_cache: dict[int, NyaaResource] = {}

    for crc_field, crc32 in _episode_crc_options(episode, prefer_extended):
        candidates = [
            # Only does a soft check based on the parsed RSS data titles, etc.
            *_find_ranked_individual_release_candidates(episode, release_records, crc_field),
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

    raise ReleaseResolutionError(
        f"Could not find a One Pace release containing CRC32 for {episode.get('ep_name') or episode.get('sheet_episode_name')}"
    )


def release_contains_crc32(resource: NyaaResource, crc32: str | None) -> bool:
    """Return True when a Nyaa resource file tree contains the target CRC32."""
    normalized_crc32 = _normalize_crc32(crc32)
    if not normalized_crc32:
        return False

    return any(
        normalized_crc32.lower() in file_name.lower()
        for file_name in _iter_nyaa_resource_file_names(resource)
    )


def _episode_crc_options(episode: EpisodeReleaseMetadata, prefer_extended: bool) -> list[tuple[CrcField, str]]:
    standard_crc32 = _normalize_crc32(episode.get("crc32"))
    extended_crc32 = _normalize_crc32(episode.get("crc32_extended"))

    options: list[tuple[CrcField, str | None]]
    if prefer_extended:
        options = [("crc32_extended", extended_crc32), ("crc32", standard_crc32)]
    else:
        options = [("crc32", standard_crc32), ("crc32_extended", extended_crc32)]

    valid_options: list[tuple[CrcField, str]] = []
    for field, crc32 in options:
        if crc32 is not None:
            valid_options.append((field, crc32))

    return valid_options


def _find_ranked_individual_release_candidates(
    episode: EpisodeReleaseMetadata,
    releases: Sequence[OnePaceRelease],
    crc_field: CrcField,
) -> list[OnePaceRelease]:
    episode_titles = _episode_individual_title_candidates(episode)
    wants_extended = crc_field == "crc32_extended"
    matches: list[OnePaceRelease] = []
    for release in releases:
        for episode_title in episode_titles:
            if _is_individual_title_match(release, episode_title, wants_extended=wants_extended):
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
) -> ResolvedRelease | None:
    nyaa_id = _release_nyaa_id(release, resolve_info_hash_to_id_func)
    if nyaa_id is None:
        logger.debug("Skipping release without resolvable Nyaa ID: %s", release.get("title"))
        return None

    try:
        # Minimizing requests to nyaa api for every resolve
        resource = resource_cache.get(nyaa_id)
        if resource is None:
            resource = nyaa_client.get_resource(nyaa_id)
            resource_cache[nyaa_id] = resource
    except Exception as e:
        logger.warning("Could not fetch Nyaa resource %s for release %s: %s", nyaa_id, release.get("title"), e)
        return None

    if not release_contains_crc32(resource, crc32):
        logger.debug("Nyaa resource %s did not contain CRC32 %s", nyaa_id, crc32)
        return None

    info_hash = (resource.info_hash or release.get("info_hash") or "").lower()
    magnet_uri = resource.magnet_url or release.get("magnet_uri") or ""
    if not info_hash or not magnet_uri:
        logger.warning("Verified release %s is missing info hash or magnet URI", release.get("title"))
        return None

    return ResolvedRelease(
        release=cast(OnePaceRelease, dict(release)),
        nyaa_resource=resource,
        nyaa_id=nyaa_id,
        crc32=crc32,
        info_hash=info_hash,
        magnet_uri=magnet_uri,
    )


def _release_nyaa_id(
    release: OnePaceRelease,
    resolve_info_hash_to_id_func: NyaaIdResolver,
) -> int | None:
    nyaa_id = release.get("nyaa_id")
    if isinstance(nyaa_id, int):
        return nyaa_id
    if isinstance(nyaa_id, str) and nyaa_id.isdigit():
        return int(nyaa_id)

    info_hash = release.get("info_hash")
    if isinstance(info_hash, str) and info_hash:
        return resolve_info_hash_to_id_func(info_hash)

    return None


def _is_individual_title_match(
    release: OnePaceRelease,
    episode_title: str,
    *,
    wants_extended: bool,
) -> bool:
    release_title = _release_normalized_title(release)
    if not release_title or not episode_title:
        return False
    if release_title == episode_title:
        return True
    return wants_extended and release_title in {f"{episode_title} extended", f"{episode_title} extended cut"}


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


def _release_candidate_date_rank(episode: EpisodeReleaseMetadata, release: OnePaceRelease) -> tuple[int, int]:
    distance = _release_date_distance_days(episode, release)
    if distance is None:
        return (2, NO_DATE_DISTANCE)
    abs_distance = abs(distance)
    if abs_distance <= DATE_MATCH_WINDOW_DAYS:
        return (0, abs_distance)
    return (1, abs_distance)


def _release_date_distance_days(episode: EpisodeReleaseMetadata, release: OnePaceRelease) -> int | None:
    episode_date = _parse_iso_date(episode.get("release_date"))
    release_date = _parse_iso_date(release.get("publication_date"))
    if episode_date is None or release_date is None:
        return None
    return (release_date - episode_date).days


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


def _parse_iso_date(value: object) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def _normalize_crc32(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    crc32 = value.strip().upper()
    return crc32 or None


def _iter_nyaa_resource_file_names(resource: NyaaResource) -> Iterable[str]:
    directory_tree = resource.directory_tree
    if directory_tree is not None:
        yield from _iter_nyaa_directory_tree_file_names(directory_tree)
        return

    files = cast(Iterable[NyaaFlatFileItem | str] | None, getattr(resource, "files", None))
    if files is not None:
        for file_item in files:
            name = file_item if isinstance(file_item, str) else getattr(file_item, "name", None)
            if isinstance(name, str):
                yield name


def _iter_nyaa_directory_tree_file_names(node: NyaaDirectoryTreeNode) -> Iterable[str]:
    if not node.is_folder:
        yield node.name
        return

    for child in node:
        yield from _iter_nyaa_directory_tree_file_names(child)
