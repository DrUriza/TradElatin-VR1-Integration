from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def humanize_key(value: str) -> str:
    return str(value).replace("_", " ").replace("-", " ").strip().title()


def format_timestamp(value: Any) -> str:
    if value in (None, "", "—"):
        return "—"
    try:
        if isinstance(value, str) and not value.isdigit():
            normalized = value.strip().replace("Z", "+00:00")
            dt = datetime.fromisoformat(normalized)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt = dt.astimezone(timezone.utc)
        else:
            timestamp = float(value)
            # Accept Unix timestamps expressed in either seconds or milliseconds.
            if abs(timestamp) >= 100_000_000_000:
                timestamp /= 1000
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return dt.strftime("%H:%M:%S de %d/%m/%Y")
    except (TypeError, ValueError, OSError):
        return str(value)


def compact_number(value: Any, decimals: int = 2) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, str):
        return value
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)

    absolute = abs(number)
    suffix = ""
    scale = 1.0
    if absolute >= 1_000_000_000_000:
        suffix, scale = "T", 1_000_000_000_000
    elif absolute >= 1_000_000_000:
        suffix, scale = "B", 1_000_000_000
    elif absolute >= 1_000_000:
        suffix, scale = "M", 1_000_000
    elif absolute >= 1_000:
        suffix, scale = "K", 1_000

    scaled = number / scale
    if suffix:
        return f"{scaled:,.{decimals}f}{suffix}"
    if absolute >= 100:
        return f"{number:,.2f}"
    if absolute >= 1:
        return f"{number:,.3f}".rstrip("0").rstrip(".")
    if absolute == 0:
        return "0"
    return f"{number:.5f}".rstrip("0").rstrip(".")


def format_metric(value: Any, unit: Any = None, display_value: Any = None) -> str:
    if display_value not in (None, ""):
        return str(display_value)
    text = compact_number(value)
    if text == "—" or unit in (None, "", "state", "ratio", "decimal"):
        return text
    unit_text = str(unit)
    if unit_text in {"percent", "percentage", "percent_points"}:
        return f"{text}%"
    if unit_text == "quote_currency":
        unit_text = "USDT"
    return f"{text} {unit_text}"


