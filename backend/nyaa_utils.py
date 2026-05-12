from collections.abc import Iterable, Iterator
from typing import Protocol, cast

import requests
from requests.exceptions import RequestException

from date_utils import parse_iso_date
from app_settings import get_settings
from logging_config import get_logger
from pynyaasi.nyaasi import NyaaSiClient

logger = get_logger(__name__)

nyaa_client = NyaaSiClient()

NYAA_BASE_URL = "https://nyaa.si"
NYAA_SEARCH_RESULT_LIMIT = 10


class NyaaDirectoryTreeNode(Protocol):
    """File or folder node from pynyaasi's torrent directory tree."""

    name: str
    is_folder: bool

    def __iter__(self) -> Iterator["NyaaDirectoryTreeNode"]:
        ...


class NyaaFlatFileItem(Protocol):
    """Flat file item shape used by tests or alternate Nyaa resource clients."""

    name: str


class NyaaResource(Protocol):
    """Subset of pynyaasi's ResourceItem used for torrent verification."""

    info_hash: str | None
    magnet_url: str | None
    directory_tree: NyaaDirectoryTreeNode | None


class NyaaSearchItem(Protocol):
    """Subset of pynyaasi's ListItem used for CRC32 fallback searches."""

    id: int
    title: str
    time: str


class NyaaResourceClient(Protocol):
    """Client interface needed to search and fetch Nyaa resources."""

    def get_resource(self, nyaa_id: int) -> NyaaResource:
        ...

    def iter_items(self, query: str = "") -> Iterable[NyaaSearchItem]:
        ...


def extract_nyaa_id(torrent_link: str) -> tuple[str, str] | None:
    """
    Extract NyaaSi ID or info hash from a torrent link.

    Returns a tuple of (id_or_hash, type) where type is either "id" or "info_hash",
    or None if the link is invalid.
    """
    if not torrent_link:
        return None

    if "/view/" in torrent_link:
        nyaa_id = torrent_link.split("/view/")[-1].rstrip("/")
        if nyaa_id.isdigit():
            logger.debug("Extracted Nyaa ID %s from link", nyaa_id)
            return nyaa_id, "id"
    elif "?q=" in torrent_link:
        info_hash = torrent_link.split("?q=")[-1].rstrip("/")
        if len(info_hash) == 40 and all(c in "0123456789abcdef" for c in info_hash.lower()):
            logger.debug("Extracted info hash %s from link", info_hash)
            return info_hash, "info_hash"

    logger.debug("Could not extract Nyaa ID from link: %s", torrent_link)
    return None


def resolve_info_hash_to_id(info_hash: str) -> int | None:
    """
    Convert an info hash to a nyaa.si resource ID via redirect.

    Nyaa.si redirects info hash queries to the actual resource page.
    """
    try:
        url = f"{NYAA_BASE_URL}/?q={info_hash}"
        logger.debug("Resolving info hash via redirect: %s", info_hash)
        resp = requests.get(url, allow_redirects=False, timeout=10)
        if resp.status_code == 302:
            location = resp.headers.get("Location", "")
            if "/view/" in location:
                nyaa_id = int(location.split("/view/")[-1])
                logger.debug("Resolved info hash to Nyaa ID %d", nyaa_id)
                return nyaa_id
        logger.debug("No redirect found for info hash (status: %d)", resp.status_code)
    except (RequestException, ValueError) as e:
        logger.error("Failed to resolve info hash %s: %s", info_hash, e)
    return None


def iter_nyaa_resource_file_names(resource: NyaaResource) -> Iterable[str]:
    """Yield file names from pynyaasi's directory-tree or flat-file resource shapes."""
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


def iter_nyaa_search_items_by_crc32(
    *,
    nyaa_client: NyaaResourceClient,
    crc32: str,
    search_cache: dict[str, list[NyaaSearchItem]],
) -> Iterable[NyaaSearchItem]:
    """Search Nyaa by CRC32 with a small per-resolution cache and result cap."""
    yield from iter_nyaa_search_items(
        nyaa_client=nyaa_client,
        query=crc32,
        search_cache=search_cache,
        search_context=f"CRC32 {crc32}",
    )


def iter_nyaa_search_items(
    *,
    nyaa_client: NyaaResourceClient,
    query: str,
    search_cache: dict[str, list[NyaaSearchItem]],
    search_context: str,
) -> Iterable[NyaaSearchItem]:
    """Search Nyaa with a small per-resolution cache and result cap."""
    cached_items = search_cache.get(query)
    if cached_items is not None:
        yield from cached_items
        return

    search_items: list[NyaaSearchItem] = []
    try:
        for index, search_item in enumerate(nyaa_client.iter_items(query=query)):
            if index >= NYAA_SEARCH_RESULT_LIMIT:
                break
            search_items.append(search_item)
    except Exception as e:
        logger.warning("Could not search Nyaa for %s: %s", search_context, e)
        return

    search_cache[query] = search_items
    yield from search_items


def date_string_from_nyaa_time(value: object) -> str | None:
    """Extract the ISO date portion from a Nyaa list-item timestamp."""
    if not isinstance(value, str) or len(value) < 10:
        return None
    date_text = value[:10]
    if parse_iso_date(date_text) is None:
        return None
    return date_text


def _iter_nyaa_directory_tree_file_names(node: NyaaDirectoryTreeNode) -> Iterable[str]:
    if not node.is_folder:
        yield node.name
        return

    for child in node:
        yield from _iter_nyaa_directory_tree_file_names(child)


def get_nyaa_resource_for_episode(episode: dict):
    """
    Get nyaa resource for a given episode using NyaaSiClient.

    Args:
        episode: Episode dict containing torrent_link and optionally torrent_link_extended

    Returns:
        ResourceItem from pynyaasi or None if not found
    """
    settings = get_settings()
    if not settings:
        logger.warning("No settings found, cannot fetch Nyaa resource")
        return None
    prefer_extended = settings["prefer_extended"]["value"]

    torrent_link = None
    if prefer_extended:
        torrent_link = episode.get("torrent_link_extended")
        if torrent_link:
            logger.debug("Using extended torrent link")
    if not torrent_link:
        torrent_link = episode.get("torrent_link")
        if torrent_link and prefer_extended:
            logger.debug("Extended link not available, falling back to standard link")

    if not torrent_link:
        logger.debug("No torrent link found for episode: %s", episode.get("ep_name"))
        return None

    parsed = extract_nyaa_id(torrent_link)
    if not parsed:
        return None

    value, id_type = parsed

    try:
        if id_type == "id":
            logger.debug("Fetching Nyaa resource by ID: %s", value)
            return nyaa_client.get_resource(int(value))
        elif id_type == "info_hash":
            nyaa_id = resolve_info_hash_to_id(value)
            if nyaa_id:
                logger.debug("Fetching Nyaa resource by resolved ID: %d", nyaa_id)
                return nyaa_client.get_resource(nyaa_id)
    except Exception as e:
        logger.error("Failed to fetch Nyaa resource for %s: %s", episode.get("ep_name"), e)

    return None
