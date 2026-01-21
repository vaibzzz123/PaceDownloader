import requests
from requests.exceptions import RequestException

from db import get_settings

from pynyaasi.nyaasi import NyaaSiClient

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
            return nyaa_id, "id"
    elif "?q=" in torrent_link:
        info_hash = torrent_link.split("?q=")[-1].rstrip("/")
        if len(info_hash) == 40 and all(c in "0123456789abcdef" for c in info_hash.lower()):
            return info_hash, "info_hash"

    return None


def resolve_info_hash_to_id(info_hash: str) -> int | None:
    """
    Convert an info hash to a nyaa.si resource ID via redirect.

    Nyaa.si redirects info hash queries to the actual resource page.
    """
    try:
        url = f"{NYAA_BASE_URL}/?q={info_hash}"
        resp = requests.get(url, allow_redirects=False, timeout=10)
        if resp.status_code == 302:
            location = resp.headers.get("Location", "")
            if "/view/" in location:
                return int(location.split("/view/")[-1])
    except (RequestException, ValueError):
        pass
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
        return None
    prefer_extended = settings["prefer_extended"]["value"]

    torrent_link = None
    if prefer_extended:
        torrent_link = episode.get("torrent_link_extended")
    if not torrent_link:
        torrent_link = episode.get("torrent_link")

    if not torrent_link:
        return None

    parsed = extract_nyaa_id(torrent_link)
    if not parsed:
        return None

    value, id_type = parsed

    try:
        if id_type == "id":
            return nyaa_client.get_resource(int(value))
        elif id_type == "info_hash":
            nyaa_id = resolve_info_hash_to_id(value)
            if nyaa_id:
                return nyaa_client.get_resource(nyaa_id)
    except Exception:
        pass

    return None


def get_magnet_link(nyaa_resource) -> str | None:
    """Extract magnet URL from a nyaa resource."""
    if nyaa_resource:
        return nyaa_resource.magnet_url
    return None
