from datetime import datetime, timezone


def utcnow() -> datetime:
    """Naive UTC datetime, matching TIMESTAMP WITHOUT TIME ZONE columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
