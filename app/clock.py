"""Current local time, in one place so tests can freeze it."""

from datetime import datetime


def now() -> datetime:
    return datetime.now().replace(microsecond=0)
