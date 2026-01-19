import zlib
import sys
from pathlib import Path

from git import Repo

def calculate_crc32(filepath: str) -> str:
    crc = 0
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            crc = zlib.crc32(chunk, crc)
    return format(crc & 0xFFFFFFFF, "08x")

def refresh_episode_metadata():
    repo_path = Path("data/eps-metadata")
    if (repo_path / ".git").exists():
        repo = Repo(repo_path)
        repo.remotes.origin.pull()
    else:
        Repo.clone_from("https://github.com/tissla/one-pace-jellyfin", repo_path)


if __name__ == "__main__":
    # if len(sys.argv) != 2:
    #     print(f"Usage: {sys.argv[0]} <filepath>")
    #     sys.exit(1)

    # filepath = sys.argv[1]
    # checksum = calculate_crc32(filepath)
    # print(f"CRC32: {checksum}")
    refresh_episode_metadata()