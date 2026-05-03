"""Small date parsing helpers shared across backend modules."""

from datetime import date


def parse_iso_date(value: object) -> date | None:
    """Parse a YYYY-MM-DD string into a date, returning None for invalid input."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None
