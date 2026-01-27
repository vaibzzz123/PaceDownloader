import requests
from requests.exceptions import RequestException

from db import get_settings
from logging_config import get_logger
from pynyaasi.nyaasi import NyaaSiClient

logger = get_logger(__name__)

nyaa_client = NyaaSiClient()

NYAA_BASE_URL = "https://nyaa.si"


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
