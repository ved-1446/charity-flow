from datetime import datetime
from typing import Any

def serialize_date(val: Any) -> str:
    """
    Safely converts a datetime or legacy date string to an ISO 8601 string.
    Returns empty string if val is None or empty.
    Never crashes on legacy string formats stored in MongoDB.
    """
    if val is None or val == "":
        return ""
    if isinstance(val, datetime):
        return val.isoformat()
    if hasattr(val, "isoformat"):
        return val.isoformat()
    if isinstance(val, str):
        val = val.strip()
        # Attempt to parse common legacy formats into standard ISO
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(val, fmt).isoformat()
            except ValueError:
                pass
        return val
    return str(val)

