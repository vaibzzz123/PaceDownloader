import requests

from pynyaasi.nyaasi import NyaaSiClient

nyaa_client = NyaaSiClient()


def extract_nyaa_id(torrent_link):
    """Extract NyaaSi ID from a torrent link."""
    if torrent_link:
        try:
            # two types of links, one with id at end, one with query param
            if "nyaa.si/view/" in torrent_link:
                return torrent_link.split("nyaa.si/view/")[-1], "id"
            else:
                return torrent_link.rstrip("/").split("?q=")[-1], "query"
        except ValueError:
            print(f"Invalid torrent link format: {torrent_link}")
    return None


def resolve_info_hash_to_id(info_hash: str) -> int | None:
    """Convert an info hash to a nyaa.si resource ID via redirect."""
    url = f"https://nyaa.si/?q={info_hash}"
    resp = requests.get(url, allow_redirects=False)
    if resp.status_code == 302:
        location = resp.headers.get("Location", "")
        if "/view/" in location:
            return int(location.split("/view/")[-1])
    return None


def get_nyaa_resource_for_episode(episode, prefer_extended: bool = False):
    """Get nyaa resource for a given episode using NyaaSiClient."""
    torrent_link = (
        episode.get("torrent_link_extended", "")
        if prefer_extended
        else episode.get("torrent_link", "")
    )
    nyaa_id, id_type = extract_nyaa_id(torrent_link)
    nyaa_resource = None
    if id_type == "id":
        nyaa_resource = nyaa_client.get_resource(int(nyaa_id))
    elif id_type == "query":
        nyaa_id_resolved = resolve_info_hash_to_id(nyaa_id)
        if nyaa_id_resolved:
            nyaa_resource = nyaa_client.get_resource(nyaa_id_resolved)
    else:
        print("Could not determine NyaaSi ID type.")
    if nyaa_resource:
        return nyaa_resource
    return None

def get_magnet_link(nyaa_resource) -> str:
    if nyaa_resource:
        return nyaa_resource.magnet_url
    return None