from enum import Enum
from datetime import datetime, timezone, timedelta


class Region(str, Enum):
    AMERICAS = "AMERICAS"
    EMEA = "EMEA"
    APAC = "APAC"


REGION_LABELS: dict[Region, str] = {
    Region.AMERICAS: "Americas (UTC-11 to UTC-3)",
    Region.EMEA: "EMEA (UTC-2 to UTC+4)",
    Region.APAC: "APAC (UTC+5 to UTC+14)",
}

# Representative UTC offset used to compute "local midnight" per region
_REGION_OFFSETS: dict[Region, int] = {
    Region.AMERICAS: -7,   # MST
    Region.EMEA: 1,        # CET
    Region.APAC: 9,        # JST
}


def get_region_date(region: Region):
    """Return the calendar date that is 'today' at midnight in this region's center timezone."""
    offset = _REGION_OFFSETS[region]
    return (datetime.now(timezone.utc) + timedelta(hours=offset)).date()


def is_valid_region(value: str) -> bool:
    return value in {r.value for r in Region}
