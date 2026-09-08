from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _first_scalar(mapping: dict[str, Any], keys: Iterable[str]) -> tuple[Any, str | None]:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value, key
    return None, None


def _first_text(mapping: dict[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if value not in (None, "") and not isinstance(value, (dict, list)):
            return str(value)
    return None


def _percent_display(value: Any, field_name: str | None) -> float | None:
    """Convert an already-computed share/percentage into display percent.

    This function does not infer market analytics.  It only formats values that
    Processing has already published explicitly as a share or percentage.
    ``*_share`` fields are decimals by contract convention; ``*_pct`` and
    ``*_percent`` fields are already percentage points.
    """
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    numeric = float(value)
    field = (field_name or "").lower()
    if "share" in field and "percent" not in field and "pct" not in field:
        numeric *= 100.0
    return numeric


FLOW_BUY_FIELDS = (
    "buy_flow_pct",
    "buy_flow_percent",
    "buy_percent",
    "buy_pct",
    "buy_flow_share",
    "buy_share",
)
FLOW_SELL_FIELDS = (
    "sell_flow_pct",
    "sell_flow_percent",
    "sell_percent",
    "sell_pct",
    "sell_flow_share",
    "sell_share",
)
FLOW_NET_FIELDS = (
    "net_flow_pct",
    "net_flow_percent",
    "net_pressure_pct",
    "net_pressure_percent",
    "net_flow",
    "net_pressure",
)


@dataclass(frozen=True)
class FlowSnapshot:
    status: str
    buy_percent: float | None
    sell_percent: float | None
    net_value: float | None
    net_field: str | None
    timeframe: str | None
    exchange: str | None
    history: tuple[tuple[Any, float], ...]
    reason: str | None = None


def _timeframe_block(chart: dict[str, Any], timeframe: str | None) -> tuple[dict[str, Any], str | None]:
    by_tf = _dict(chart.get("series_by_timeframe"))
    if not by_tf:
        by_tf = _dict(chart.get("timeframes"))
    if by_tf:
        selected = str(timeframe or chart.get("selected_timeframe") or "")
        if selected and selected in by_tf:
            return _dict(by_tf.get(selected)), selected
        if timeframe:
            # Explicit user selection with no published block must not fall back
            # to a different timeframe.
            return {}, str(timeframe)
        default = str(chart.get("selected_timeframe") or "")
        if default in by_tf:
            return _dict(by_tf.get(default)), default
        if by_tf:
            first = next(iter(by_tf))
            return _dict(by_tf.get(first)), str(first)
    return chart, str(timeframe or chart.get("selected_timeframe") or chart.get("timeframe") or "") or None


def _current_record(block: dict[str, Any], chart: dict[str, Any]) -> dict[str, Any]:
    candidates = (block.get("current"),) if block is not chart else (block.get("current"), chart.get("current"))
    for candidate in candidates:
        if isinstance(candidate, dict):
            return candidate
    for key in ("points", "bars", "records", "history"):
        rows = _list(block.get(key))
        if not rows and block is chart:
            rows = _list(chart.get(key))
        rows = [item for item in rows if isinstance(item, dict)]
        if rows:
            return rows[-1]
    return block if block is not chart else chart



def _flow_exchange_block(chart: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    selected = _first_text(chart, ("selected_exchange", "exchange", "exchange_name", "venue"))
    for key in ("series_by_exchange", "by_exchange", "exchanges"):
        blocks = _dict(chart.get(key))
        if not blocks:
            continue
        if selected and selected in blocks:
            return _dict(blocks.get(selected)), selected
        lowered = {str(name).lower(): name for name in blocks}
        if selected and selected.lower() in lowered:
            original = lowered[selected.lower()]
            return _dict(blocks.get(original)), str(original)
        if "aggregate" in lowered:
            original = lowered["aggregate"]
            return _dict(blocks.get(original)), str(original)
        first = next(iter(blocks))
        return _dict(blocks.get(first)), str(first)
    return chart, selected

def extract_flow_snapshot(chart: dict[str, Any] | None, timeframe: str | None = None) -> FlowSnapshot:
    if not isinstance(chart, dict):
        return FlowSnapshot("unavailable", None, None, None, None, timeframe, None, (), "flow_chart_missing")

    exchange_block, selected_exchange = _flow_exchange_block(chart)
    block, selected_tf = _timeframe_block(exchange_block, timeframe)
    if timeframe and not block:
        return FlowSnapshot("unavailable", None, None, None, None, selected_tf, selected_exchange, (), "timeframe_not_published")

    current = _current_record(block, exchange_block)
    buy_raw, buy_field = _first_scalar(current, FLOW_BUY_FIELDS)
    if buy_field is None:
        buy_raw, buy_field = _first_scalar(block, FLOW_BUY_FIELDS)
    if buy_field is None:
        buy_raw, buy_field = _first_scalar(chart, FLOW_BUY_FIELDS)

    sell_raw, sell_field = _first_scalar(current, FLOW_SELL_FIELDS)
    if sell_field is None:
        sell_raw, sell_field = _first_scalar(block, FLOW_SELL_FIELDS)
    if sell_field is None:
        sell_raw, sell_field = _first_scalar(chart, FLOW_SELL_FIELDS)

    net_value, net_field = _first_scalar(current, FLOW_NET_FIELDS)
    if net_field is None:
        net_value, net_field = _first_scalar(block, FLOW_NET_FIELDS)
    if net_field is None:
        net_value, net_field = _first_scalar(chart, FLOW_NET_FIELDS)

    buy_percent = _percent_display(buy_raw, buy_field)
    sell_percent = _percent_display(sell_raw, sell_field)

    exchange = (
        _first_text(current, ("exchange", "exchange_name", "venue"))
        or _first_text(block, ("exchange", "exchange_name", "venue"))
        or selected_exchange
        or _first_text(chart, ("exchange", "exchange_name", "venue"))
    )

    rows: list[dict[str, Any]] = []
    for key in ("points", "bars", "records", "history"):
        candidate = _list(block.get(key))
        if candidate:
            rows = [item for item in candidate if isinstance(item, dict)]
            break
    history: list[tuple[Any, float]] = []
    for row in rows:
        value, field = _first_scalar(row, FLOW_NET_FIELDS)
        if field is None or not isinstance(value, (int, float)):
            continue
        timestamp = row.get("timestamp") or row.get("time") or row.get("date")
        history.append((timestamp, float(value)))

    published_status = str(block.get("status") or chart.get("status") or "available").lower()
    if buy_percent is None and sell_percent is None:
        status = "unavailable"
        reason = "buy_sell_flow_percentages_not_published"
    elif buy_percent is None or sell_percent is None:
        status = "partial"
        reason = "partial_flow_percentages"
    else:
        status = published_status if published_status in {"available", "partial", "unavailable"} else "available"
        reason = None

    return FlowSnapshot(
        status=status,
        buy_percent=buy_percent,
        sell_percent=sell_percent,
        net_value=float(net_value) if isinstance(net_value, (int, float)) else None,
        net_field=net_field,
        timeframe=selected_tf,
        exchange=exchange,
        history=tuple(history),
        reason=reason,
    )



POSITIONING_EXPECTED_TIMEFRAMES = ("1m", "5m", "15m", "4h")

POSITIONING_FIELDS: dict[str, tuple[str, ...]] = {
    "long": ("long_share", "long_percent"),
    "short": ("short_share", "short_percent"),
    "ratio": ("long_short_ratio",),
}


@dataclass(frozen=True)
class PositioningSnapshot:
    status: str
    long_percent: float | None
    short_percent: float | None
    ratio: float | None
    exchange: str | None
    timeframe: str | None
    history: tuple[tuple[Any, float], ...]
    reason: str | None = None


def _select_exchange_block(chart: dict[str, Any], exchange: str | None) -> tuple[dict[str, Any], bool]:
    selected = str(exchange or "").strip()
    for key in ("series_by_exchange", "by_exchange", "exchanges"):
        blocks = _dict(chart.get(key))
        if blocks:
            if selected and selected in blocks:
                return _dict(blocks.get(selected)), True
            lowered = {str(k).lower(): k for k in blocks}
            if selected and selected.lower() in lowered:
                return _dict(blocks.get(lowered[selected.lower()])), True
            if selected and selected.lower() != "aggregate":
                return {}, True
            if "aggregate" in lowered:
                return _dict(blocks.get(lowered["aggregate"])), True
            if not selected and blocks:
                first = next(iter(blocks))
                return _dict(blocks.get(first)), True
    # Flat positioning series is only safely treated as aggregate.
    if selected and selected.lower() not in {"", "aggregate", "all"}:
        return {}, False
    return chart, False


def _select_positioning_timeframe(block: dict[str, Any], timeframe: str | None) -> tuple[dict[str, Any], str | None, bool]:
    for key in ("series_by_timeframe", "timeframes"):
        blocks = _dict(block.get(key))
        if blocks:
            selected = str(timeframe or block.get("selected_timeframe") or "")
            if selected in blocks:
                return _dict(blocks.get(selected)), selected, True
            if timeframe:
                return {}, str(timeframe), True
            if blocks:
                first = next(iter(blocks))
                return _dict(blocks.get(first)), str(first), True
    if timeframe:
        # A flat series with no timeframe declaration must not be presented as
        # if it were the selected timeframe.
        declared = _first_text(block, ("timeframe", "window", "interval"))
        if declared and declared == str(timeframe):
            return block, declared, False
        return {}, str(timeframe), False
    declared = _first_text(block, ("timeframe", "window", "interval"))
    return block, declared, False


def extract_positioning_snapshot(
    contract: dict[str, Any],
    *,
    exchange: str | None = None,
    timeframe: str | None = None,
) -> PositioningSnapshot:
    chart = _dict(_dict(contract.get("charts")).get("long_short_positioning"))
    if not chart:
        return PositioningSnapshot("unavailable", None, None, None, exchange, timeframe, (), "positioning_chart_missing")

    selected_exchange = exchange
    if selected_exchange is None:
        selector = _dict(_dict(contract.get("selectors")).get("exchange"))
        selected_exchange = str(selector.get("selected") or "aggregate")

    exchange_block, had_exchange_map = _select_exchange_block(chart, selected_exchange)
    if not exchange_block:
        return PositioningSnapshot("unavailable", None, None, None, selected_exchange, timeframe, (), "exchange_not_published")

    tf_block, selected_tf, had_tf_map = _select_positioning_timeframe(exchange_block, timeframe)
    if timeframe and not tf_block:
        return PositioningSnapshot("unavailable", None, None, None, selected_exchange, selected_tf, (), "timeframe_not_published")

    specs = POSITIONING_FIELDS
    current = _current_record(tf_block, exchange_block)

    long_raw, long_field = _first_scalar(current, specs["long"])
    if long_field is None:
        long_raw, long_field = _first_scalar(tf_block, specs["long"])
    short_raw, short_field = _first_scalar(current, specs["short"])
    if short_field is None:
        short_raw, short_field = _first_scalar(tf_block, specs["short"])
    ratio, ratio_field = _first_scalar(current, specs["ratio"])
    if ratio_field is None:
        ratio, ratio_field = _first_scalar(tf_block, specs["ratio"])

    long_percent = _percent_display(long_raw, long_field)
    short_percent = _percent_display(short_raw, short_field)

    points: list[dict[str, Any]] = []
    for key in ("points", "records", "history"):
        rows = _list(tf_block.get(key)) or _list(exchange_block.get(key)) or _list(chart.get(key))
        if rows:
            points = [item for item in rows if isinstance(item, dict)]
            break
    history: list[tuple[Any, float]] = []
    for row in points:
        value, field = _first_scalar(row, specs["ratio"])
        if field is None or not isinstance(value, (int, float)):
            continue
        timestamp = row.get("timestamp") or row.get("time") or row.get("date")
        history.append((timestamp, float(value)))

    published_status = str(tf_block.get("status") or exchange_block.get("status") or chart.get("status") or "available").lower()
    if long_percent is None and short_percent is None:
        status = "unavailable"
        reason = "long_short_percentage_shares_not_published"
    elif long_percent is None or short_percent is None:
        status = "partial"
        reason = "partial_long_short_percentage_shares"
    else:
        status = published_status if published_status in {"available", "partial", "unavailable"} else "available"
        reason = None

    if not had_exchange_map and selected_exchange and selected_exchange.lower() not in {"aggregate", "all"}:
        status = "unavailable"
        reason = "exchange_not_published"
    if timeframe and not had_tf_map and selected_tf != timeframe:
        status = "unavailable"
        reason = "timeframe_not_published"

    return PositioningSnapshot(
        status=status,
        long_percent=long_percent,
        short_percent=short_percent,
        ratio=float(ratio) if isinstance(ratio, (int, float)) else None,
        exchange=selected_exchange,
        timeframe=selected_tf,
        history=tuple(history),
        reason=reason,
    )


def selector_values(contract: dict[str, Any], selector_name: str) -> tuple[list[str], str | None]:
    selector = _dict(_dict(contract.get("selectors")).get(selector_name))
    values: list[str] = []
    for item in _list(selector.get("options")):
        if isinstance(item, dict):
            value = item.get("id") or item.get("value") or item.get("key") or item.get("label")
        else:
            value = item
        if value not in (None, ""):
            values.append(str(value))
    selected = selector.get("selected") or selector.get("default")
    return values, str(selected) if selected not in (None, "") else (values[0] if values else None)


def positioning_timeframes(contract: dict[str, Any]) -> tuple[list[str], str | None]:
    """Return selectable L/S timeframes without inventing market data.

    Preference order:
    1. Explicit selector options published by Processing.
    2. Explicit timeframe blocks published by Processing.
    3. The HMI's allowed selector domain for the feature.

    The fallback in step 3 only keeps the control usable. Selecting one of those
    values still yields UNAVAILABLE unless Processing publishes the matching
    timeframe block; no ratio/share values are derived in Dash.
    """
    values, selected = selector_values(contract, "timeframe")
    if values:
        return values, selected

    chart = _dict(_dict(contract.get("charts")).get("long_short_positioning"))
    for key in ("series_by_timeframe", "timeframes"):
        blocks = _dict(chart.get(key))
        if blocks:
            keys = [str(item) for item in blocks.keys()]
            current = str(chart.get("selected_timeframe") or "") or None
            if current not in keys:
                current = None
            return keys, current

    # Selector vocabulary is presentation metadata, not a market calculation.
    # Do not choose a synthetic/default timeframe when the contract does not
    # publish one; the user may select a value and the chart will correctly
    # remain UNAVAILABLE until Processing supplies that timeframe.
    return list(POSITIONING_EXPECTED_TIMEFRAMES), None
