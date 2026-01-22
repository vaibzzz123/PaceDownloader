"""Episode download repository for database access."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from db import con, cur
from logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class EpisodeDownload:
    """Represents an episode download record."""

    id: int
    ep_id: int
    torrent_magnet_link: str
    qbt_torrent_id: str
    prefer_extended: bool
    file_path_torrent: str | None
    file_path_disk: str | None
    file_type: str | None
    status: str
    created_at: str
    updated_at: str


class EpisodeDownloadRepository:
    """Repository for episode download database operations."""

    def _row_to_episode_download(self, row: tuple, columns: list[str]) -> EpisodeDownload:
        """Convert a database row to an EpisodeDownload object."""
        data = dict(zip(columns, row))
        return EpisodeDownload(
            id=data["id"],
            ep_id=data["ep_id"],
            torrent_magnet_link=data["torrent_magnet_link"],
            qbt_torrent_id=data["qbt_torrent_id"],
            prefer_extended=bool(data["prefer_extended"]),
            file_path_torrent=data["file_path_torrent"],
            file_path_disk=data["file_path_disk"],
            file_type=data["file_type"],
            status=data["status"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )

    def create(
        self,
        ep_id: int,
        torrent_magnet_link: str,
        qbt_torrent_id: str,
        prefer_extended: bool = False,
        file_path_torrent: str | None = None,
        file_path_disk: str | None = None,
        status: str = "pending",
    ) -> int:
        """
        Create a new episode download record.

        Returns the ID of the created record.
        """
        cur.execute(
            """
            INSERT INTO episode_download (
                ep_id, torrent_magnet_link, qbt_torrent_id, prefer_extended,
                file_path_torrent, file_path_disk, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ep_id,
                torrent_magnet_link,
                qbt_torrent_id,
                int(prefer_extended),
                file_path_torrent,
                file_path_disk,
                status,
            ),
        )
        con.commit()
        record_id = cur.lastrowid
        logger.info("Created episode download record for ep_id=%d, id=%d", ep_id, record_id)
        return record_id

    def get_by_ep_id(self, ep_id: int) -> EpisodeDownload | None:
        """Get an episode download by episode ID."""
        cur.execute("SELECT * FROM episode_download WHERE ep_id = ?", (ep_id,))
        row = cur.fetchone()
        if not row:
            return None
        columns = [desc[0] for desc in cur.description]
        return self._row_to_episode_download(row, columns)

    def get_by_id(self, record_id: int) -> EpisodeDownload | None:
        """Get an episode download by its ID."""
        cur.execute("SELECT * FROM episode_download WHERE id = ?", (record_id,))
        row = cur.fetchone()
        if not row:
            return None
        columns = [desc[0] for desc in cur.description]
        return self._row_to_episode_download(row, columns)

    def get_by_qbt_torrent_id(self, qbt_torrent_id: str) -> list[EpisodeDownload]:
        """Get all episode downloads for a specific torrent."""
        cur.execute(
            "SELECT * FROM episode_download WHERE qbt_torrent_id = ?",
            (qbt_torrent_id,),
        )
        rows = cur.fetchall()
        if not rows:
            return []
        columns = [desc[0] for desc in cur.description]
        return [self._row_to_episode_download(row, columns) for row in rows]

    def get_by_status(self, status: str) -> list[EpisodeDownload]:
        """Get all episode downloads with the given status."""
        cur.execute("SELECT * FROM episode_download WHERE status = ?", (status,))
        rows = cur.fetchall()
        if not rows:
            return []
        columns = [desc[0] for desc in cur.description]
        return [self._row_to_episode_download(row, columns) for row in rows]

    def get_all(self) -> list[EpisodeDownload]:
        """Get all episode downloads."""
        cur.execute("SELECT * FROM episode_download")
        rows = cur.fetchall()
        if not rows:
            return []
        columns = [desc[0] for desc in cur.description]
        return [self._row_to_episode_download(row, columns) for row in rows]

    def update(self, ep_id: int, **fields: Any) -> bool:
        """
        Update fields for an episode download.

        Valid fields: file_path_torrent, file_path_disk, file_type, status
        Returns True if a record was updated.
        """
        valid_fields = {"file_path_torrent", "file_path_disk", "file_type", "status"}
        update_fields = {k: v for k, v in fields.items() if k in valid_fields}

        if not update_fields:
            logger.warning("No valid fields to update for ep_id=%d", ep_id)
            return False

        # Add updated_at
        update_fields["updated_at"] = datetime.now().isoformat()

        set_clause = ", ".join(f"{k} = ?" for k in update_fields.keys())
        values = list(update_fields.values()) + [ep_id]

        cur.execute(
            f"UPDATE episode_download SET {set_clause} WHERE ep_id = ?",
            values,
        )
        con.commit()

        if cur.rowcount > 0:
            logger.info("Updated episode download for ep_id=%d: %s", ep_id, update_fields)
            return True
        return False

    def delete(self, ep_id: int) -> bool:
        """
        Delete an episode download record.

        Returns True if a record was deleted.
        """
        cur.execute("DELETE FROM episode_download WHERE ep_id = ?", (ep_id,))
        con.commit()

        if cur.rowcount > 0:
            logger.info("Deleted episode download for ep_id=%d", ep_id)
            return True
        return False
