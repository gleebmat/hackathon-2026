"""Current campus time (Klagenfurt), in one place so tests can freeze it. Times are stored without a zone."""

from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Vienna")


def now() -> datetime:
    return datetime.now(TZ).replace(tzinfo=None, microsecond=0)


def to_local(dt: datetime) -> datetime:
    """Convert a time with a zone (e.g. '...Z') to campus time; times without a zone are taken as campus time."""
    return dt.astimezone(TZ).replace(tzinfo=None) if dt.tzinfo else dt
