from datetime import date, datetime

from .constants import DEFAULT_PROJECT_ICON, PROJECT_ICON_MAP


def parse_due_date(due_date_raw: str):
    """Parse an ISO date string, returning None for blank or invalid input."""
    raw_value = (due_date_raw or "").strip()
    if not raw_value:
        return None
    try:
        return date.fromisoformat(raw_value)
    except ValueError:
        return None


def parse_due_at(due_at_raw: str):
    """Parse an ISO datetime string, returning None for blank or invalid input."""
    raw_value = (due_at_raw or "").strip()
    if not raw_value:
        return None
    try:
        return datetime.fromisoformat(raw_value)
    except ValueError:
        return None


def parse_project_icon(icon_raw: str) -> str:
    """Return a known project icon key or the default icon key."""
    icon_key = (icon_raw or "").strip()
    if icon_key in PROJECT_ICON_MAP:
        return icon_key
    return DEFAULT_PROJECT_ICON


def parse_tag_color(color_raw: str) -> str:
    """Normalize a hex tag color or return the default color."""
    color = (color_raw or "").strip()
    if len(color) == 7 and color.startswith("#") and all(char in "0123456789abcdefABCDEF" for char in color[1:]):
        return color.lower()
    if len(color) == 4 and color.startswith("#") and all(char in "0123456789abcdefABCDEF" for char in color[1:]):
        red, green, blue = color[1], color[2], color[3]
        return f"#{red}{red}{green}{green}{blue}{blue}".lower()
    return "#5b7cfa"


def format_iso_datetime(value: datetime | None) -> str:
    """Format a datetime as ISO text for backups."""
    return value.isoformat() if value else ""


def parse_iso_datetime(value: str) -> datetime:
    """Parse an ISO datetime, falling back to the current UTC time."""
    raw = (value or "").strip()
    if not raw:
        return datetime.utcnow()
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return datetime.utcnow()


def parse_csv_bool(value: str) -> bool:
    """Parse a truthy CSV field value into a boolean."""
    return (value or "").strip().lower() in {"1", "true", "yes", "y"}
