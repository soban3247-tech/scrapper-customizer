"""Temporary parsing helpers shared while legacy scrapers are migrated."""

import json
import re
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any


def parse_job_date(value: Any) -> date | None:
    """Convert common API date and timestamp formats into a date."""

    if value in (None, "", [], {}):
        return None

    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp /= 1000
        try:
            return datetime.fromtimestamp(timestamp, tz=timezone.utc).date()
        except (ValueError, OSError, OverflowError):
            return None

    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return parse_job_date(int(text))

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def text_matches_query(query: str, *values: Any) -> bool:
    """Require every query word to occur somewhere in the supplied job fields."""

    words = [word for word in re.split(r"\s+", query.casefold().strip()) if word]
    if not words:
        return True

    haystack = " ".join(
        json.dumps(value, default=str).casefold()
        if isinstance(value, (dict, list))
        else str(value).casefold()
        for value in values
        if value not in (None, "", [], {})
    )
    return all(word in haystack for word in words)


def string_list(value: Any) -> list[str]:
    """Return clean strings from source fields that should contain a list."""

    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def optional_decimal(value: Any) -> Decimal | None:
    """Convert a numeric API value while treating blanks and invalid data as absent."""

    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
