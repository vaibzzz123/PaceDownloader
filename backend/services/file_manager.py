"""File management service for hardlink creation, copying, and file operations."""

import os
import shutil
from pathlib import Path
from typing import Literal

from logging_config import get_logger

logger = get_logger(__name__)


FileType = Literal["hardlink", "copy"]


class FileManager:
    """Manages file operations for completed downloads."""

    def create_destination_file(
        self,
        source_path: str,
        dest_path: str,
        prefer_hardlink: bool = True,
    ) -> tuple[bool, FileType | None, str | None]:
        """
        Create destination file from source (hardlink preferred, copy fallback).

        Args:
            source_path: Path to source file (in torrent directory)
            dest_path: Path where file should appear (media directory)
            prefer_hardlink: If True, try hardlink first

        Returns:
            Tuple of (success, file_type, error_message)
            file_type is 'hardlink' or 'copy' on success, None on failure
        """
        source = Path(source_path)
        dest = Path(dest_path)

        if not source.exists():
            error_msg = f"Source file does not exist: {source_path}"
            logger.error(error_msg)
            return False, None, error_msg

        # Ensure destination directory exists
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            error_msg = f"Failed to create destination directory: {e}"
            logger.error(error_msg)
            return False, None, error_msg

        # Remove existing destination if present
        if dest.exists():
            try:
                dest.unlink()
                logger.debug("Removed existing destination file: %s", dest_path)
            except Exception as e:
                error_msg = f"Failed to remove existing destination file: {e}"
                logger.error(error_msg)
                return False, None, error_msg

        if prefer_hardlink:
            try:
                os.link(source_path, dest_path)
                logger.info("Created hardlink: %s -> %s", source_path, dest_path)
                return True, "hardlink", None
            except OSError as e:
                logger.warning(
                    "Hardlink failed (%s), falling back to copy: %s -> %s",
                    e,
                    source_path,
                    dest_path,
                )

        # Fallback to copy
        try:
            shutil.copy2(source_path, dest_path)
            logger.info("Created copy: %s -> %s", source_path, dest_path)
            return True, "copy", None
        except Exception as e:
            error_msg = f"Failed to copy file: {e}"
            logger.error(error_msg)
            return False, None, error_msg

    def delete_file(self, file_path: str) -> tuple[bool, str | None]:
        """
        Delete a file.

        Args:
            file_path: Path to file to delete

        Returns:
            Tuple of (success, error_message)
        """
        path = Path(file_path)

        if not path.exists():
            logger.debug("File already deleted or doesn't exist: %s", file_path)
            return True, None

        try:
            path.unlink()
            logger.info("Deleted file: %s", file_path)
            return True, None
        except Exception as e:
            error_msg = f"Failed to delete file: {e}"
            logger.error(error_msg)
            return False, error_msg

    def find_file_by_crc32(
        self,
        directory: str,
        crc32: str,
        file_extension: str = ".mkv",
    ) -> str | None:
        """
        Find a file containing CRC32 hash in its filename.

        One Pace filenames contain CRC32 in brackets: [E5F09F49]

        Args:
            directory: Directory to search
            crc32: 8-character CRC32 hex string
            file_extension: File extension to match (default: .mkv)

        Returns:
            Full path to matching file, or None if not found
        """
        search_dir = Path(directory)
        crc32_upper = crc32.upper()
        crc32_pattern = f"[{crc32_upper}]"

        if not search_dir.exists():
            logger.warning("Directory does not exist: %s", directory)
            return None

        # Search recursively for files with matching CRC32
        for file_path in search_dir.rglob(f"*{file_extension}"):
            filename_upper = file_path.name.upper()
            if crc32_pattern in filename_upper:
                logger.debug("Found file with CRC32 %s: %s", crc32, file_path)
                return str(file_path)

        logger.debug("No file found with CRC32 %s in %s", crc32, directory)
        return None

    def file_exists(self, file_path: str) -> bool:
        """Check if a file exists."""
        return Path(file_path).exists()

    def get_file_size(self, file_path: str) -> int | None:
        """Get the size of a file in bytes."""
        path = Path(file_path)
        if path.exists():
            return path.stat().st_size
        return None
