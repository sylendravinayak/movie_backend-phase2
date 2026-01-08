
import datetime


def to_utc(dt: datetime.datetime) -> datetime.datetime:
    # If dt is None, return as-is
    if dt is None:
        return dt
    # If dt is naive, attach UTC offset
    if dt.tzinfo is None:
        return dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(datetime.timezone.utc)