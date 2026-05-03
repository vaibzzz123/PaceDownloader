"""CRC32 normalization and file-name matching helpers."""

from collections.abc import Iterable


def normalize_crc32(value: object) -> str | None:
    """Normalize a CRC32 value to uppercase text, returning None for empty input."""
    if not isinstance(value, str):
        return None
    crc32 = value.strip().upper()
    return crc32 or None


def file_names_contain_crc32(file_names: Iterable[str], crc32: str | None) -> bool:
    """Return True when any file name contains the target CRC32."""
    normalized_crc32 = normalize_crc32(crc32)
    if not normalized_crc32:
        return False

    normalized_crc32_lower = normalized_crc32.lower()
    for file_name in file_names:
        if normalized_crc32_lower in file_name.lower():
            return True
    return False
