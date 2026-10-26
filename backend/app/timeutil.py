from datetime import date, datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

from app.config import get_settings


@lru_cache()
def app_timezone() -> ZoneInfo:
    return ZoneInfo(get_settings().app_timezone)


def today() -> date:
    """Today's date in the app's timezone (Asia/Dhaka), not the server's.

    Servers usually run in UTC; between 00:00 and 06:00 in Dhaka the server's
    date is still yesterday.
    """
    return datetime.now(app_timezone()).date()
