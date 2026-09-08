from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .formatting import humanize_key

BG = "#06111d"
PLOT_BG = "#071522"
GRID = "rgba(91, 126, 155, 0.14)"
TEXT = "#d9e8f5"
MUTED = "#7f96aa"
GREEN = "#17d49b"
RED = "#ff506e"
CYAN = "#22c7ff"
AMBER = "#f5a524"
PURPLE = "#9a6cff"
BLUE = "#4f7cff"
SERIES_COLORS = [CYAN, PURPLE, AMBER, GREEN, RED, BLUE, "#d178ff", "#7bdff2", "#c4f26b"]


def apply_analysis_figure_layout(
    fig: go.Figure, *, height: int = 220, legend_y: float = 1.02,
    right_margin: int = 18,
) -> go.Figure:
    """Apply the compact Liquidations-derived Screen B visual grammar."""
    fig.update_layout(
        title=None,
        height=height,
        margin={"l": 38, "r": right_margin, "t": 28, "b": 30},
        paper_bgcolor=BG,
        plot_bgcolor=PLOT_BG,
        font={"family": "Inter, Segoe UI, sans-serif", "color": TEXT, "size": 9},
        showlegend=True,
        legend={
            "orientation": "h", "yanchor": "bottom", "y": legend_y,
            "xanchor": "left", "x": 0, "font": {"size": 7, "color": MUTED},
            "bgcolor": "rgba(0,0,0,0)",
        },
    )
    return fig


def _dt(value: Any) -> Any:
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return value


def _tail(items: list[Any], limit: int = 400) -> list[Any]:
    return items[-limit:] if len(items) > limit else items


def _base_layout(fig: go.Figure, title: str | None = None, height: int = 300) -> go.Figure:
    fig.update_layout(
        title={"text": title or "", "font": {"size": 13, "color": TEXT}, "x": 0.01, "xanchor": "left"},
        height=height,
        margin={"l": 42, "r": 20, "t": 42, "b": 34},
        paper_bgcolor=BG,
        plot_bgcolor=PLOT_BG,
        font={"family": "Inter, Segoe UI, sans-serif", "color": TEXT, "size": 10},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.01, "xanchor": "right", "x": 1, "font": {"size": 9}},
        hoverlabel={"bgcolor": "#0a1b2a", "font": {"color": TEXT}},
        hovermode="x unified",
        uirevision="contract-data",
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID, tickfont={"color": MUTED}, showline=False)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID, tickfont={"color": MUTED}, showline=False)
    return fig


def empty_figure(title: str, reason: Any = None, height: int = 300) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=f"UNAVAILABLE<br><span style='font-size:10px;color:{MUTED}'>{reason or 'No precomputed series in JSON'}</span>",
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"size": 14, "color": MUTED},
        align="center",
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return _base_layout(fig, title, height)


def _select_market_block(markets: dict[str, Any], market: str | None) -> Any:
    if not markets:
        return None
    if market in markets:
        return markets[market]
    for candidate in ("general", "aggregate", "spot", "futures", "perpetual"):
        if candidate in markets:
            return markets[candidate]
    return next(iter(markets.values()))


def select_chart_block(
    chart: dict[str, Any],
    market: str | None = None,
    timeframe: str | None = None,
    range_id: str | None = None,
) -> dict[str, Any]:
    block: Any = chart

    markets = chart.get("markets")
    if isinstance(markets, dict):
        block = _select_market_block(markets, market)
        if isinstance(block, dict) and isinstance(block.get("timeframes"), dict):
            timeframes = block["timeframes"]
            block = timeframes.get(timeframe) or timeframes.get(chart.get("selected_timeframe")) or next(iter(timeframes.values()))
        elif isinstance(block, dict) and timeframe in block and isinstance(block.get(timeframe), dict):
            block = block[timeframe]
        elif isinstance(block, dict):
            candidate = chart.get("selected_timeframe")
            if candidate in block and isinstance(block[candidate], dict):
                block = block[candidate]

    if isinstance(chart.get("series_by_timeframe"), dict):
        by_tf = chart["series_by_timeframe"]
        selected = timeframe or chart.get("selected_timeframe")
        block = by_tf.get(selected) or next(iter(by_tf.values()))

    if isinstance(chart.get("series_by_range"), dict):
        by_range = chart["series_by_range"]
        selected = range_id or chart.get("selected_range")
        block = by_range.get(selected) or next(iter(by_range.values()))

    return block if isinstance(block, dict) else chart


def _numeric_fields(records: list[dict[str, Any]]) -> list[str]:
    excluded = {
        "timestamp", "time", "date", "id", "row_id", "side", "status", "reason", "provider", "endpoint_id",
        "exchange", "exchange_name", "symbol", "market", "market_type", "timeframe", "classification", "state",
        "color_token", "label", "unit", "pair_status", "is_partial", "is_closed", "continuity_status", "region",
        "construction", "asset", "window", "range_id", "series_id", "source_path", "source_dataset",
    }
    fields: list[str] = []
    for record in records[:25]:
        for key, value in record.items():
            if key in excluded or key in fields or isinstance(value, bool):
                continue
            if isinstance(value, (int, float)) and value is not None:
                fields.append(key)
    return fields[:8]


def _x_values(records: list[dict[str, Any]]) -> list[Any]:
    if records and any("timestamp" in item for item in records):
        return [_dt(item.get("timestamp")) for item in records]
    if records and any("price" in item for item in records):
        return [item.get("price") for item in records]
    if records and any("center_price" in item for item in records):
        return [item.get("center_price") for item in records]
    if records and any("window" in item for item in records):
        return [item.get("window") for item in records]
    if records and any("label" in item for item in records):
        return [item.get("label") for item in records]
    return list(range(len(records)))


def _add_thresholds(fig: go.Figure, chart: dict[str, Any]) -> None:
    thresholds = chart.get("thresholds")
    if not isinstance(thresholds, list):
        return
    for threshold in thresholds:
        if not isinstance(threshold, dict) or threshold.get("value") is None:
            continue
        fig.add_hline(
            y=threshold["value"],
            line_dash="dot",
            line_color="rgba(245,165,36,0.65)",
            annotation_text=str(threshold.get("role") or threshold.get("label") or ""),
            annotation_font_color=MUTED,
        )


def _figure_from_timestamp_series(chart: dict[str, Any], block: dict[str, Any], title: str, height: int) -> go.Figure | None:
    timestamps = block.get("timestamps")
    series = block.get("series")
    if not isinstance(timestamps, list) or not isinstance(series, dict):
        return None
    fig = go.Figure()
    x = [_dt(value) for value in _tail(timestamps)]
    for index, (name, values) in enumerate(series.items()):
        if not isinstance(values, list):
            continue
        y = _tail(values)
        if len(y) != len(x):
            size = min(len(x), len(y))
            x_values, y_values = x[-size:], y[-size:]
        else:
            x_values, y_values = x, y
        mode = "lines"
        fig.add_trace(go.Scatter(x=x_values, y=y_values, mode=mode, name=humanize_key(name), line={"color": SERIES_COLORS[index % len(SERIES_COLORS)], "width": 1.5}))
    _add_thresholds(fig, chart)
    return _base_layout(fig, title, height)


def _figure_from_series_points(chart: dict[str, Any], block: dict[str, Any], title: str, height: int) -> go.Figure | None:
    series = block.get("series")
    if not isinstance(series, list) or not series or not all(isinstance(item, dict) for item in series):
        return None
    if not any(isinstance(item.get("points"), list) for item in series):
        return None

    fig = go.Figure()
    for index, item in enumerate(series):
        points = _tail(item.get("points") or [])
        if not points:
            continue
        representation = str(item.get("representation") or chart.get("chart_type") or "line").lower()
        name = humanize_key(item.get("label") or item.get("id") or f"Series {index + 1}")
        color = SERIES_COLORS[index % len(SERIES_COLORS)]
        if all(all(key in point for key in ("open", "high", "low", "close")) for point in points):
            fig.add_trace(go.Candlestick(
                x=[_dt(point.get("timestamp")) for point in points],
                open=[point.get("open") for point in points],
                high=[point.get("high") for point in points],
                low=[point.get("low") for point in points],
                close=[point.get("close") for point in points],
                name=name,
                increasing_line_color=GREEN,
                decreasing_line_color=RED,
            ))
        elif representation in {"bar", "histogram", "column"}:
            fig.add_trace(go.Bar(
                x=[_dt(point.get("timestamp")) if point.get("timestamp") is not None else index for index, point in enumerate(points)],
                y=[point.get("value") for point in points],
                name=name,
                marker_color=color,
            ))
        else:
            fig.add_trace(go.Scatter(
                x=[_dt(point.get("timestamp")) if point.get("timestamp") is not None else index for index, point in enumerate(points)],
                y=[point.get("value") for point in points],
                name=name,
                mode="lines",
                line={"color": color, "width": 1.6},
            ))
    if not fig.data:
        return None
    _add_thresholds(fig, chart)
    return _base_layout(fig, title, height)


def _figure_from_ohlc_records(chart: dict[str, Any], block: dict[str, Any], title: str, height: int) -> go.Figure | None:
    records = block.get("records") or block.get("points")
    if not isinstance(records, list) or not records:
        return None
    records = _tail([record for record in records if isinstance(record, dict)])
    if not records or not all(key in records[0] for key in ("open", "high", "low", "close")):
        return None

    has_volume = any(any(field in record for field in ("combined_volume_usd", "volume", "volume_usd", "spot_volume_usd")) for record in records)
    if has_volume:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.76, 0.24])
    else:
        fig = go.Figure()

    x = [_dt(record.get("timestamp")) for record in records]
    candle = go.Candlestick(
        x=x,
        open=[record.get("open") for record in records],
        high=[record.get("high") for record in records],
        low=[record.get("low") for record in records],
        close=[record.get("close") for record in records],
        name="OHLC",
        increasing_line_color=GREEN,
        decreasing_line_color=RED,
        increasing_fillcolor=GREEN,
        decreasing_fillcolor=RED,
    )
    if has_volume:
        fig.add_trace(candle, row=1, col=1)
    else:
        fig.add_trace(candle)

    overlays = block.get("overlays") if isinstance(block.get("overlays"), dict) else {}
    moving = overlays.get("moving_averages") if isinstance(overlays.get("moving_averages"), dict) else {}
    moving_series = moving.get("series") if isinstance(moving.get("series"), dict) else {}
    for index, (name, values) in enumerate(moving_series.items()):
        if not isinstance(values, list):
            continue
        size = min(len(x), len(values))
        trace = go.Scatter(x=x[-size:], y=values[-size:], mode="lines", name=name.upper(), line={"width": 1.1, "color": SERIES_COLORS[index % len(SERIES_COLORS)]})
        if has_volume:
            fig.add_trace(trace, row=1, col=1)
        else:
            fig.add_trace(trace)

    bollinger = overlays.get("bollinger_bands") if isinstance(overlays.get("bollinger_bands"), dict) else {}
    bb_series = bollinger.get("series") if isinstance(bollinger.get("series"), dict) else {}
    for index, name in enumerate(("upper", "middle", "lower")):
        values = bb_series.get(name)
        if not isinstance(values, list):
            continue
        size = min(len(x), len(values))
        trace = go.Scatter(x=x[-size:], y=values[-size:], mode="lines", name=f"BB {name.title()}", line={"width": 1, "dash": "dot" if name != "middle" else "solid", "color": [PURPLE, AMBER, PURPLE][index]})
        if has_volume:
            fig.add_trace(trace, row=1, col=1)
        else:
            fig.add_trace(trace)

    if has_volume:
        volume_field = next((field for field in ("combined_volume_usd", "volume_usd", "volume", "spot_volume_usd") if any(field in record for record in records)), None)
        if volume_field:
            colors = [GREEN if record.get("close", 0) >= record.get("open", 0) else RED for record in records]
            fig.add_trace(go.Bar(x=x, y=[record.get(volume_field) for record in records], name="Volume", marker_color=colors, opacity=0.65), row=2, col=1)
        fig.update_xaxes(rangeslider_visible=False, row=1, col=1)
        fig.update_xaxes(rangeslider_visible=False, row=2, col=1)
    else:
        fig.update_xaxes(rangeslider_visible=False)

    return _base_layout(fig, title, height)


def _figure_from_depth(chart: dict[str, Any], title: str, height: int) -> go.Figure | None:
    records = chart.get("records")
    if not isinstance(records, list) or not records:
        return None
    bids = sorted([item for item in records if isinstance(item, dict) and str(item.get("side", "")).lower() == "bid"], key=lambda item: item.get("price") or 0)
    asks = sorted([item for item in records if isinstance(item, dict) and str(item.get("side", "")).lower() == "ask"], key=lambda item: item.get("price") or 0)
    if not bids and not asks:
        return None
    fig = go.Figure()
    if bids:
        fig.add_trace(go.Scatter(
            x=[item.get("price") for item in bids],
            y=[item.get("cumulative_quantity_base") or item.get("quantity_base") for item in bids],
            name="Bids",
            mode="lines",
            fill="tozeroy",
            line={"color": GREEN, "shape": "hv"},
            fillcolor="rgba(23,212,155,0.24)",
        ))
    if asks:
        fig.add_trace(go.Scatter(
            x=[item.get("price") for item in asks],
            y=[item.get("cumulative_quantity_base") or item.get("quantity_base") for item in asks],
            name="Asks",
            mode="lines",
            fill="tozeroy",
            line={"color": RED, "shape": "hv"},
            fillcolor="rgba(255,80,110,0.24)",
        ))
    return _base_layout(fig, title, height)


def _figure_from_liquidation_map(chart: dict[str, Any], title: str, height: int) -> go.Figure | None:
    buckets = chart.get("buckets")
    if isinstance(buckets, dict):
        buckets = buckets.get("items")
    if not isinstance(buckets, list) or not buckets:
        buckets = chart.get("stacked_buckets")
    if not isinstance(buckets, list) or not buckets:
        return None

    records = [item for item in buckets if isinstance(item, dict)]
    x = [item.get("center_price") or item.get("price") for item in records]
    values = [item.get("level_total") or item.get("total_level") or 0 for item in records]
    reference = chart.get("reference_price") if isinstance(chart.get("reference_price"), dict) else {}
    reference_value = reference.get("value")
    colors = [GREEN if reference_value is not None and (price or 0) < reference_value else RED for price in x]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=x, y=values, name="Liquidation level", marker_color=colors, opacity=0.72))
    for curve_name, color in (("estimated_long_curve", GREEN), ("estimated_short_curve", RED)):
        curve = chart.get(curve_name)
        if isinstance(curve, list) and curve:
            fig.add_trace(go.Scatter(
                x=[point.get("price") for point in curve if isinstance(point, dict)],
                y=[point.get("value") or point.get("estimated_value") for point in curve if isinstance(point, dict)],
                name=humanize_key(curve_name),
                mode="lines",
                line={"color": color, "width": 2},
            ))
    if reference_value is not None:
        fig.add_vline(x=reference_value, line_dash="dot", line_color=AMBER, annotation_text="Reference")
    return _base_layout(fig, title, height)


def _figure_from_pie(chart: dict[str, Any], title: str, height: int) -> go.Figure | None:
    records = chart.get("records") or chart.get("items")
    if not isinstance(records, list) or not records:
        return None
    labels: list[Any] = []
    values: list[Any] = []
    for item in records:
        if not isinstance(item, dict):
            continue
        label = item.get("label") or item.get("regime") or item.get("name") or item.get("id")
        value = item.get("share") or item.get("empirical_share") or item.get("value") or item.get("count")
        if label is not None and isinstance(value, (int, float)):
            labels.append(label)
            values.append(value)
    if not labels:
        return None
    fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.58, marker={"colors": SERIES_COLORS[: len(labels)]}, textinfo="label+percent"))
    return _base_layout(fig, title, height)


def _figure_from_records(chart: dict[str, Any], block: dict[str, Any], title: str, height: int) -> go.Figure | None:
    records = block.get("records") or block.get("points") or block.get("items")
    if not isinstance(records, list) or not records:
        return None
    records = _tail([item for item in records if isinstance(item, dict)])
    if not records:
        return None

    if all(key in records[0] for key in ("open", "high", "low", "close")):
        return _figure_from_ohlc_records(chart, {"records": records, "overlays": block.get("overlays")}, title, height)

    if "side" in records[0] and "price" in records[0]:
        return _figure_from_depth({"records": records}, title, height)

    chart_type = str(chart.get("chart_type") or block.get("chart_type") or "line").lower()
    fields = _numeric_fields(records)
    if not fields:
        return None

    if chart_type in {"donut", "pie", "distribution"} or "distribution" in str(chart.get("chart_id", "")):
        pie = _figure_from_pie({"records": records}, title, height)
        if pie is not None:
            return pie

    x = _x_values(records)
    fig = go.Figure()
    for index, field in enumerate(fields):
        y = [record.get(field) for record in records]
        color = SERIES_COLORS[index % len(SERIES_COLORS)]
        use_bar = chart_type in {"bar", "histogram", "column", "stacked_bar"} or field in {"volume_delta_usd", "net_flow_usd", "count", "event_count"}
        if use_bar:
            marker_color: Any = color
            if field in {"volume_delta_usd", "net_flow_usd", "spread_volatility_points"}:
                marker_color = [GREEN if isinstance(value, (int, float)) and value >= 0 else RED for value in y]
            fig.add_trace(go.Bar(x=x, y=y, name=humanize_key(field), marker_color=marker_color, opacity=0.78))
        else:
            fig.add_trace(go.Scatter(x=x, y=y, name=humanize_key(field), mode="lines", line={"color": color, "width": 1.6}))
    _add_thresholds(fig, chart)
    return _base_layout(fig, title, height)


def make_chart_figure(
    chart: dict[str, Any] | None,
    *,
    title: str | None = None,
    market: str | None = None,
    timeframe: str | None = None,
    range_id: str | None = None,
    height: int = 300,
) -> go.Figure:
    if not isinstance(chart, dict):
        return empty_figure(title or "Chart", "Chart object missing", height)

    chart_title = title or chart.get("title") or humanize_key(chart.get("chart_id") or chart.get("id") or "Chart")
    status = str(chart.get("status") or "available").lower()
    reason = chart.get("reason")
    if status == "unavailable" and not any(chart.get(key) for key in ("records", "points", "series", "items", "buckets")):
        return empty_figure(chart_title, reason, height)

    chart_id = str(chart.get("chart_id") or chart.get("id") or "").lower()
    if "order_depth" in chart_id or (isinstance(chart.get("records"), list) and chart.get("records") and isinstance(chart["records"][0], dict) and "side" in chart["records"][0]):
        figure = _figure_from_depth(chart, chart_title, height)
        return figure or empty_figure(chart_title, reason, height)

    if "liquidation" in chart_id or "map" in chart_id or "buckets" in chart:
        figure = _figure_from_liquidation_map(chart, chart_title, height)
        return figure or empty_figure(chart_title, reason, height)

    if "distribution" in chart_id or str(chart.get("chart_type", "")).lower() in {"pie", "donut"}:
        figure = _figure_from_pie(chart, chart_title, height)
        if figure is not None:
            return figure

    block = select_chart_block(chart, market=market, timeframe=timeframe, range_id=range_id)

    for builder in (
        _figure_from_timestamp_series,
        _figure_from_series_points,
        _figure_from_ohlc_records,
        _figure_from_records,
    ):
        figure = builder(chart, block, chart_title, height)
        if figure is not None:
            return figure

    # Some contracts keep chart records at the chart level while the selected block is metadata-only.
    figure = _figure_from_records(chart, chart, chart_title, height)
    if figure is not None:
        return figure

    return empty_figure(chart_title, reason or block.get("reason") if isinstance(block, dict) else reason, height)

