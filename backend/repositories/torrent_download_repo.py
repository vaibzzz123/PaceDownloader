"""Torrent download repository for database access."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from db import get_connection
from logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class TorrentDownload:
    """Represents a torrent download record."""

    qbt_torrent_id: str
    torrent_magnet_link: str
    status: str
    download_path: str | None
    total_files: int | None
    selected_files: int
    created_at: str
    updated_at: str


class TorrentDownloadRepository:
    """Repository for torrent download database operations."""

    def _row_to_torrent_download(self, row) -> TorrentDownload:
        """Convert a database row to a TorrentDownload object."""
        return TorrentDownload(
            qbt_torrent_id=row["qbt_torrent_id"],
            torrent_magnet_link=row["torrent_magnet_link"],
            status=row["status"],
            download_path=row["download_path"],
            total_files=row["total_files"],
            selected_files=row["selected_files"] or 0,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def create(
        self,
        qbt_torrent_id: str,
        torrent_magnet_link: str,
        status: str = "pending",
        download_path: str | None = None,
        total_files: int | None = None,
        selected_files: int = 0,
    ) -> str:
        """
        Create a new torrent download record.

        Returns the qbt_torrent_id of the created record.
        """
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO torrent_download (
                    qbt_torrent_id, torrent_magnet_link, status,
                    download_path, total_files, selected_files
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    qbt_torrent_id,
                    torrent_magnet_link,
                    status,
                    download_path,
                    total_files,
                    selected_files,
                ),
            )
            conn.commit()
        logger.info("Created torrent download record for hash=%s", qbt_torrent_id)
        return qbt_torrent_id

    def get_by_hash(self, qbt_torrent_id: str) -> TorrentDownload | None:
        """Get a torrent download by its qBittorrent hash."""
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM torrent_download WHERE qbt_torrent_id = ?",
                (qbt_torrent_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_torrent_download(row)

    def get_by_magnet(self, magnet_link: str) -> TorrentDownload | None:
        """Get a torrent download by its magnet link."""
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM torrent_download WHERE torrent_magnet_link = ?",
                (magnet_link,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_torrent_download(row)

    def get_all(self) -> list[TorrentDownload]:
        """Get all torrent downloads."""
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM torrent_download")
            rows = cur.fetchall()
            return [self._row_to_torrent_download(row) for row in rows]

    def get_by_status(self, status: str) -> list[TorrentDownload]:
        """Get all torrent downloads with the given status."""
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM torrent_download WHERE status = ?", (status,))
            rows = cur.fetchall()
            return [self._row_to_torrent_download(row) for row in rows]

    def update(self, qbt_torrent_id: str, **fields: Any) -> bool:
        """
        Update fields for a torrent download.

        Valid fields: status, download_path, total_files, selected_files
        Returns True if a record was updated.
        """
        valid_fields = {"status", "download_path", "total_files", "selected_files"}
        update_fields = {k: v for k, v in fields.items() if k in valid_fields}

        if not update_fields:
            logger.warning("No valid fields to update for torrent hash=%s", qbt_torrent_id)
            return False

        # Add updated_at
        update_fields["updated_at"] = datetime.now().isoformat()

        set_clause = ", ".join(f"{k} = ?" for k in update_fields.keys())
        values = list(update_fields.values()) + [qbt_torrent_id]

        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f"UPDATE torrent_download SET {set_clause} WHERE qbt_torrent_id = ?",
                values,
            )
            conn.commit()
            rowcount = cur.rowcount

        if rowcount > 0:
            logger.info("Updated torrent download for hash=%s: %s", qbt_torrent_id, update_fields)
            return True
        return False

    def increment_selected_files(self, qbt_torrent_id: str) -> bool:
        """Increment the selected_files count for a torrent."""
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE torrent_download
                SET selected_files = selected_files + 1, updated_at = ?
                WHERE qbt_torrent_id = ?
                """,
                (datetime.now().isoformat(), qbt_torrent_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def decrement_selected_files(self, qbt_torrent_id: str) -> bool:
        """Decrement the selected_files count for a torrent."""
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE torrent_download
                SET selected_files = MAX(0, selected_files - 1), updated_at = ?
                WHERE qbt_torrent_id = ?
                """,
                (datetime.now().isoformat(), qbt_torrent_id),
            )
            conn.commit()
            return cur.rowcount > 0

    def delete(self, qbt_torrent_id: str) -> bool:
        """
        Delete a torrent download record and its junction table entries.

        Returns True if a record was deleted.
        """
        with get_connection() as conn:
            cur = conn.cursor()
            # Delete junction table entries first
            cur.execute("DELETE FROM torrent_episode WHERE torrent_id = ?", (qbt_torrent_id,))

            # Delete the torrent record
            cur.execute("DELETE FROM torrent_download WHERE qbt_torrent_id = ?", (qbt_torrent_id,))
            conn.commit()
            rowcount = cur.rowcount

        if rowcount > 0:
            logger.info("Deleted torrent download for hash=%s", qbt_torrent_id)
            return True
        return False

    # Junction table operations

    def add_episode(self, torrent_id: str, ep_id: int) -> bool:
        """Add an episode to a torrent in the junction table."""
        try:
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO torrent_episode (torrent_id, ep_id) VALUES (?, ?)",
                    (torrent_id, ep_id),
                )
                conn.commit()
            logger.debug("Added episode %d to torrent %s", ep_id, torrent_id)
            return True
        except Exception as e:
            logger.warning("Failed to add episode %d to torrent %s: %s", ep_id, torrent_id, e)
            return False

    def remove_episode(self, torrent_id: str, ep_id: int) -> bool:
        """Remove an episode from a torrent in the junction table."""
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM torrent_episode WHERE torrent_id = ? AND ep_id = ?",
                (torrent_id, ep_id),
            )
            conn.commit()
            rowcount = cur.rowcount

        if rowcount > 0:
            logger.debug("Removed episode %d from torrent %s", ep_id, torrent_id)
            return True
        return False

    def get_episode_ids(self, torrent_id: str) -> list[int]:
        """Get all episode IDs associated with a torrent."""
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT ep_id FROM torrent_episode WHERE torrent_id = ?",
                (torrent_id,),
            )
            rows = cur.fetchall()
            return [row["ep_id"] for row in rows]

    def get_torrent_for_episode(self, ep_id: int) -> str | None:
        """Get the torrent ID for an episode."""
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT torrent_id FROM torrent_episode WHERE ep_id = ?",
                (ep_id,),
            )
            row = cur.fetchone()
            return row["torrent_id"] if row else None
