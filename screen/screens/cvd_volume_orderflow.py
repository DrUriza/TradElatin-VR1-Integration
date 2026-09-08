from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import Input, Output, State, callback, dcc, html

from screen_core.selection_state import (
    LOCAL_SELECTION_PERSISTENCE_TYPE,
    resolve_persisted_selection,
)
from screen_core.components import (
    kpi_grid,
    reference_gallery,
    screen_header,
    screen_page,
)
from screen_core.contextual_help import contextual_help_label
from screen_core.i18n import locale_context, localize_component_tree, localize_figure, localized_href, locale_from_search
from screen_core.contract_loader import load_contract
from screen_core.figures import apply_analysis_figure_layout
from screen_core.market_readers import FlowSnapshot, extract_flow_snapshot


ROUTE = "/cvd-orderflow"
LABEL = "CVD"
CONTRACT_FILE = "cvd_volume_orderflow_VR1_FINAL.json"
HAS_ANALYSIS = True
SCREEN_REVISION = "CVD_NATIVE_SCREEN_B_V5_KPI_COMPACT"

REFERENCE_IMAGES = [
    "CVD/02_CVD_A.png",
    "CVD/02_CVD_B_Spot.png",
    "CVD/02_CVD_B_Futuros.png",
]

GREEN = "#17d49b"
RED = "#ff506e"
BG = "#06111d"
PLOT_BG = "#071522"
GRID = "rgba(91,126,155,.16)"
TEXT = "#d9e8f5"
MUTED = "#7f96aa"

SELECTION_STORE_ID = "cvd-technical-selection"
ANALYSIS_CONTENT_ID = "cvd-analysis-content"

def _option_label(label: str, color: str) -> html.Span:
    return html.Span(
        [
            html.Span("●", style={"color": color, "fontSize": "11px", "marginRight": "6px", "lineHeight": "1"}),
            html.Span(label),
        ],
        style={"display": "inline-flex", "alignItems": "center", "gap": "0"},
    )


TREND_OPTIONS = [
    {"label": "EMA 9", "value": "ema_9"},
    {"label": "EMA 21", "value": "ema_21"},
    {"label": "SMA 20", "value": "sma_20"},
    {"label": "SMA 50", "value": "sma_50"},
    {"label": "WMA 20", "value": "wma_20"},
    {"label": "WMA 50", "value": "wma_50"},
]

DERIVED_OPTIONS = [
    {"label": _option_label("CVD Slope / Acceleration", "#20d05c"), "value": "cvd_slope_acceleration"},
    {"label": _option_label("Delta Z-Score", "#20d05c"), "value": "delta_zscore"},
    {"label": _option_label("Buy/Sell Imbalance", "#20d05c"), "value": "buy_sell_imbalance"},
]

MOMENTUM_OPTIONS = [
    {"label": _option_label("Price ↔ CVD Divergence", "#a65cff"), "value": "price_cvd_divergence"},
    {"label": _option_label("Spot ↔ Futures CVD Divergence", "#a65cff"), "value": "spot_futures_divergence"},
]

VOLATILITY_OPTIONS = [
    {"label": _option_label("Wasserstein Distance", "#2ea8ff"), "value": "wasserstein_distance"},
]

DEFAULT_TREND = ["ema_9", "ema_21", "sma_20", "sma_50", "wma_20", "wma_50"]
DEFAULT_DERIVED = ["cvd_slope_acceleration", "delta_zscore", "buy_sell_imbalance"]
DEFAULT_MOMENTUM = ["price_cvd_divergence", "spot_futures_divergence"]
DEFAULT_VOLATILITY = ["wasserstein_distance"]

ANALYSIS_ORDER = (
    "cvd_slope_acceleration",
    "delta_zscore",
    "buy_sell_imbalance",
    "price_cvd_divergence",
    "spot_futures_divergence",
    "wasserstein_distance",
)

INDICATOR_TITLES = {
    "cvd_slope_acceleration": "CVD SLOPE / ACCELERATION",
    "delta_zscore": "DELTA Z-SCORE",
    "buy_sell_imbalance": "BUY / SELL IMBALANCE",
    "price_cvd_divergence": "PRICE ↔ CVD DIVERGENCE",
    "spot_futures_divergence": "SPOT ↔ FUTURES CVD DIVERGENCE",
    "wasserstein_distance": "WASSERSTEIN DISTANCE",
}

TRACE_COLORS = {
    "slope": "#2f80ff",
    "acceleration": "#f2c94c",
    "zscore": "#00c2ff",
    "imbalance": "#00d4a8",
    "divergence": "#a879ff",
    "ema_9": "#2f80ff",
    "ema_21": "#00c2ff",
    "sma_20": "#00d4ff",
    "sma_50": "#f2c94c",
    "wma_20": "#a879ff",
    "wma_50": "#ff8a3d",
    "wasserstein_distance": "#3c94ed",
}

CVD_LOCAL_CSS = """
.cvd-main-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 286px;
    gap: 8px;
    align-items: stretch;
}

.cvd-market-stack-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
    height: 428px;
}

.cvd-market-stack {
    display: grid;
    min-width: 0;
    grid-template-rows: 235px 185px;
    gap: 8px;
    height: 428px;
}
.cvd-market-stack > .cvd-chart-card:first-child .js-plotly-plot,
.cvd-market-stack > .cvd-chart-card:first-child .plot-container,
.cvd-market-stack > .cvd-chart-card:first-child .svg-container { height:235px !important; max-height:235px !important; }
.cvd-market-stack > .cvd-chart-card:last-child .js-plotly-plot,
.cvd-market-stack > .cvd-chart-card:last-child .plot-container,
.cvd-market-stack > .cvd-chart-card:last-child .svg-container { height:185px !important; max-height:185px !important; }

.cvd-chart-card,
.cvd-indicator-panel,
.cvd-analysis-market {
    min-width: 0;
    border: 1px solid #123148;
    background: #06111d;
}

.cvd-indicator-panel {
    height: auto;
    align-self: start;
    padding: 8px 10px;
    color: #dbe7ef;
    overflow-y: auto;
    box-sizing: border-box;
}

.cvd-analysis-button {
    width: 100%;
    height: 28px;
    border: 1px solid #1766d6;
    border-radius: 4px;
    color: #3f8cff;
    background: #06111d;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: .4px;
    cursor: pointer;
}

.cvd-selector-heading {
    margin-top: 10px;
    margin-bottom: 8px;
    color: #dceaf5;
    font-size: 10px;
    font-weight: 700;
}

.cvd-selector-note {
    margin-bottom: 9px;
    color: #7f96aa;
    font-size: 8px;
    line-height: 1.35;
}

.cvd-indicator-group {
    border-top: 1px solid #10283a;
    padding-top: 8px;
    margin-top: 8px;
}

.cvd-indicator-group-title {
    margin-bottom: 5px;
    color: #7f91a0;
    font-size: 8px;
    text-transform: uppercase;
}

.cvd-analysis-only {
    border: 1px dashed #235274;
    border-radius: 4px;
    padding: 7px;
    background: rgba(18,54,78,.18);
}

.cvd-analysis-only .cvd-indicator-group-title {
    color: #5aa9e6;
}

.cvd-checklist label {
    display: inline-flex !important;
    width: 50%;
    gap: 5px;
    align-items: center;
    margin: 3px 0;
    color: #c6d5df;
    font-size: 8px;
}

.cvd-checklist input {
    accent-color: #2f80ff;
}


.cvd-analysis-shell {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.cvd-analysis-market {
    padding: 8px;
}

.cvd-analysis-market-title {
    color: #4fc3ff;
    font-size: 11px;
    font-weight: 700;
    margin: 1px 0 8px;
}

.cvd-analysis-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 5px;
    align-items: stretch;
}

.cvd-analysis-card {
    min-width: 0;
    height: 247px;
    min-height: 247px;
    max-height: 247px;
    border: 1px solid #123247;
    border-radius: 4px;
    background: linear-gradient(180deg, #061522 0%, #04111c 100%);
    overflow: hidden;
    box-sizing: border-box;
}

.cvd-analysis-card-title {
    height: 26px;
    display: flex;
    align-items: center;
    padding: 0 9px;
    border-bottom: 1px solid #102b3d;
    color: #dce6ec;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: .1px;
    box-sizing: border-box;
}

.cvd-analysis-card-graph {
    min-width: 0;
    width: 100%;
    height: 220px !important;
    min-height: 220px !important;
    max-height: 220px !important;
    overflow: hidden;
}

.cvd-analysis-card-graph .js-plotly-plot,
.cvd-analysis-card-graph .plot-container,
.cvd-analysis-card-graph .svg-container {
    height: 220px !important;
    min-height: 220px !important;
    max-height: 220px !important;
}

@media (max-width: 1200px) {
    .cvd-market-stack-grid {
        grid-template-columns: 1fr;
    }

    .cvd-analysis-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}

@media (max-width: 900px) {
    .cvd-main-grid {
        grid-template-columns: 1fr;
    }

    .cvd-analysis-grid {
        grid-template-columns: 1fr;
    }
}

.analysis-back-row {
    display: flex;
    align-items: center;
    justify-content: flex-start;
    margin: 0 0 7px;
}

.analysis-back-button {
    height: 27px;
    padding: 0 12px;
    border: 1px solid #1a5f86;
    border-radius: 4px;
    background: #06111d;
    color: #65c9ff;
    font-family: inherit;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: .25px;
    cursor: pointer;
}

.analysis-back-button:hover {
    border-color: #2ea8ff;
    background: #082033;
    color: #dff5ff;
}


.cvd-analysis-layout {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 286px;
    gap: 8px;
    align-items: start;
}

.cvd-analysis-main {
    min-width: 0;
}

.cvd-summary-column {
    min-width: 0;
    display: grid;
    gap: 6px;
    align-content: start;
}

.cvd-summary-panel,
.cvd-strength-legend,
.cvd-analysis-controls {
    border: 1px solid #123247;
    border-radius: 4px;
    background: linear-gradient(180deg, #061522 0%, #04111c 100%);
    overflow: hidden;
}

.cvd-analysis-controls .cvd-selector-group,
.cvd-analysis-controls .cvd-indicator-group {
    border-top: 1px solid #173247;
    padding: 8px 9px;
    margin: 0;
}
.cvd-analysis-controls .cvd-options-grid,
.cvd-analysis-controls .cvd-checklist {
    grid-template-columns: 1fr;
}
.cvd-analysis-controls label {
    color: #d9e8f5;
    font-size: 9px;
}

.cvd-summary-title,
.cvd-strength-title {
    min-height: 27px;
    display: flex;
    align-items: center;
    padding: 0 9px;
    border-bottom: 1px solid #102b3d;
    color: #dce6ec;
    font-size: 9px;
    font-weight: 700;
}

.cvd-summary-head {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 54px 73px 48px;
    gap: 4px;
    padding: 6px 8px;
    border-bottom: 1px solid #102b3d;
    color: #8194a4;
    font-size: 6.5px;
    text-transform: uppercase;
}

.cvd-summary-section {
    display: flex;
    align-items: center;
    gap: 5px;
    min-height: 23px;
    padding: 0 8px;
    border-bottom: 1px solid rgba(16,43,61,.8);
    font-size: 8px;
    font-weight: 700;
}

.cvd-summary-section-marker {
    width: 0;
    height: 0;
    border-top: 4px solid transparent;
    border-bottom: 4px solid transparent;
    border-left: 5px solid currentColor;
}

.cvd-summary-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 54px 73px 48px;
    gap: 4px;
    align-items: center;
    min-height: 24px;
    padding: 0 8px;
    border-bottom: 1px solid rgba(16,43,61,.62);
    font-size: 7.2px;
}

.cvd-summary-name {
    color: #c7d2da;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.cvd-summary-value {
    color: #dce6ec;
    text-align: right;
    font-variant-numeric: tabular-nums;
}

.cvd-summary-signal {
    text-align: right;
    font-size: 6.8px;
    font-weight: 700;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.cvd-summary-strength {
    display: inline-flex;
    justify-content: flex-end;
    gap: 2px;
}

.cvd-summary-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #46525d;
}

.cvd-strength-body {
    display: grid;
    gap: 4px;
    padding: 7px 9px 8px;
}

.cvd-strength-row {
    display: grid;
    grid-template-columns: 58px 1fr;
    align-items: center;
    color: #c0cbd2;
    font-size: 7px;
}

@media (max-width: 1320px) {
    .cvd-analysis-layout {
        grid-template-columns: minmax(0, 1fr) 290px;
    }
}

@media (max-width: 920px) {
    .cvd-analysis-layout {
        grid-template-columns: 1fr;
    }
}
"""


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _dt(value: Any) -> Any:
    try:
        return datetime.fromtimestamp(
            float(value),
            tz=timezone.utc,
        )
    except (TypeError, ValueError, OSError):
        return value


def _numeric(value: Any) -> float | None:
    try:
        if isinstance(value, bool):
            return None
        return float(value)
    except (TypeError, ValueError, OverflowError):
        return None


def _event_anchor_timestamp(event: dict[str, Any]) -> Any:
    display = _safe_dict(event.get("display"))
    return (
        event.get("event_timestamp_exact")
        if event.get("event_timestamp_exact") is not None
        else display.get("anchor_timestamp")
        if display.get("anchor_timestamp") is not None
        else event.get("timestamp")
    )


def _event_anchor_value(
    event: dict[str, Any],
    fallback: Any = None,
) -> float | None:
    display = _safe_dict(event.get("display"))
    calculation = _safe_dict(event.get("calculation"))

    for candidate in (
        event.get("event_value_exact"),
        event.get("event_price"),
        display.get("anchor_value"),
        display.get("anchor_price"),
        calculation.get("event_value_exact"),
        calculation.get("crossing_value"),
        fallback,
    ):
        value = _numeric(candidate)
        if value is not None:
            return value

    first = _numeric(calculation.get("first_value"))
    second = _numeric(calculation.get("second_value"))
    if first is not None and second is not None:
        return (first + second) / 2.0

    return None


def _add_exact_event_arrow(
    fig: go.Figure,
    *,
    x: Any,
    y: float,
    signal: str,
    color: str,
) -> None:
    """Point the arrow tip exactly at the contractual event coordinate."""
    fig.add_annotation(
        x=_dt(x),
        y=y,
        text="",
        showarrow=True,
        arrowhead=2,
        arrowsize=1.0,
        arrowwidth=1.55,
        arrowcolor=color,
        ax=0,
        ay=18 if signal == "bullish" else -18,
        xref="x",
        yref="y",
        opacity=0.98,
    )


def _cvd_stylesheet() -> html.Link:
    return html.Link(
        rel="stylesheet",
        href=(
            "data:text/css;charset=utf-8,"
            + quote(CVD_LOCAL_CSS, safe="")
        ),
    )


def _checklist(
    component_id: str,
    options: list[dict[str, str]],
    value: list[str],
) -> dcc.Checklist:
    return dcc.Checklist(
        id=component_id,
        options=options,
        value=value,
        className="cvd-checklist",
        persistence="cvd-controls-v1",
        persistence_type=LOCAL_SELECTION_PERSISTENCE_TYPE,
    )


def _selector_group(
    title: str,
    checklist: dcc.Checklist,
    *,
    analysis_only: bool = False,
) -> html.Div:
    class_name = (
        "cvd-indicator-group cvd-analysis-only"
        if analysis_only
        else "cvd-indicator-group"
    )

    children: list[Any] = [
        html.Div(
            title,
            className="cvd-indicator-group-title",
        ),
    ]

    if analysis_only:
        children.append(
            html.Div(
                "Independent charts on Screen B; they are not overlaid on CVD candles.",
                className="cvd-selector-note",
            )
        )

    children.append(checklist)

    return html.Div(
        className=class_name,
        children=children,
    )


def _indicator_panel() -> html.Div:
    return html.Div(
        className="cvd-indicator-panel",
        children=[
            html.Div(
                className="analysis-launch-row",
                style={
                    "display": "grid",
                    "gridTemplateColumns": "minmax(0, 1fr) 34px",
                    "gap": "4px",
                    "marginBottom": "12px",
                },
                children=[
                    dcc.Link(
                        "CVD ANALYSIS · ORDER FLOW",
                        href=localized_href(f"{ROUTE}/analysis"),
                        className="cvd-analysis-button",
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center",
                            "width": "auto",
                            "marginBottom": "0",
                            "textDecoration": "none",
                        },
                    ),
                    html.A(
                        "↗",
                        href=localized_href(f"{ROUTE}/analysis"),
                        target="_blank",
                        rel="noopener noreferrer",
                        title="Open analysis in a new tab",
                        className="cvd-analysis-button",
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center",
                            "width": "auto",
                            "marginBottom": "0",
                            "padding": "0",
                            "textDecoration": "none",
                        },
                    ),
                ],
            ),
            html.Div("INDICATORS · SCREEN A", className="cvd-selector-heading"),
            _selector_group(
                "TREND · ON CVD",
                _checklist("cvd-trend-selectors", TREND_OPTIONS, DEFAULT_TREND),
            ),
        ],
    )


def _default_selection() -> dict[str, list[str]]:
    return {
        "trend": list(DEFAULT_TREND),
        "derived_analysis": list(DEFAULT_DERIVED),
        "momentum": list(DEFAULT_MOMENTUM),
        "volatility": list(DEFAULT_VOLATILITY),
    }


def _analysis_indicator_controls(selection: Any) -> html.Div:
    """Expose Screen-B indicator selection beside the analysis summaries.

    Screen A and Screen B are separate routes, so the canonical checklist IDs
    can be reused safely. Browser-local persistence keeps both views in sync.
    Trend overlays are intentionally omitted here because they only affect
    Screen A CVD candles.
    """
    payload = resolve_persisted_selection(selection, _default_selection)
    return html.Div(
        className="screen-b-selector cvd-analysis-controls",
        children=[
            html.Div("INDICATORS · SCREEN B", className="screen-b-selector-title cvd-summary-title"),
            html.Div(
                "Select the native Order Flow panels shown on this screen.",
                className="cvd-selector-note",
                style={"padding": "8px 9px 0", "marginBottom": "2px"},
            ),
            html.Div(
                style={"padding": "0 9px 9px"},
                children=[
                    _selector_group(
                        "FLOW DYNAMICS",
                        _checklist(
                            "cvd-derived-selectors",
                            DERIVED_OPTIONS,
                            list(payload.get("derived_analysis", [])),
                        ),
                    ),
                    _selector_group(
                        "DIVERGENCES",
                        _checklist(
                            "cvd-momentum-selectors",
                            MOMENTUM_OPTIONS,
                            list(payload.get("momentum", [])),
                        ),
                    ),
                    _selector_group(
                        "REGIME CHANGE",
                        _checklist(
                            "cvd-volatility-selectors",
                            VOLATILITY_OPTIONS,
                            list(payload.get("volatility", [])),
                        ),
                    ),
                ],
            ),
        ],
    )


def _selection_payload(
    trend: list[str] | None,
    derived: list[str] | None,
    momentum: list[str] | None,
    volatility: list[str] | None,
) -> dict[str, list[str]]:
    return {
        "trend": _unique(trend or []),
        "derived_analysis": _unique(derived or []),
        "momentum": _unique(momentum or []),
        "volatility": _unique(volatility or []),
    }


def _technical_block(
    contract: dict[str, Any],
    market: str,
    timeframe: str | None,
) -> dict[str, Any]:
    technical = _safe_dict(
        contract.get("technical_analysis")
    )
    market_block = _safe_dict(
        _safe_dict(technical.get("markets")).get(market)
    )
    timeframes = _safe_dict(
        market_block.get("timeframes")
    )

    selected = (
        timeframe
        if timeframe in timeframes
        else next(iter(timeframes), "")
    )

    return _safe_dict(timeframes.get(selected))


def _source_chart(
    contract: dict[str, Any],
    market: str,
) -> dict[str, Any]:
    chart_id = {
        "spot": "cvd_spot",
        "futures": "cvd_futures",
    }[market]

    return _safe_dict(
        _safe_dict(contract.get("charts")).get(chart_id)
    )


def _source_points(
    contract: dict[str, Any],
    market: str,
    timeframe: str | None,
) -> tuple[list[dict[str, Any]], str]:
    chart = _source_chart(contract, market)
    timeframes = _safe_dict(
        chart.get("series_by_timeframe")
    )

    selected = (
        timeframe
        if timeframe in timeframes
        else str(chart.get("selected_timeframe") or "")
    )

    if selected not in timeframes:
        selected = next(iter(timeframes), "")

    block = _safe_dict(timeframes.get(selected))

    candles = [
        candle
        for candle in _safe_list(block.get("candles"))
        if isinstance(candle, dict)
    ]

    # CVD charts are contractually candlestick-only. Do not reinterpret
    # line points or fabricate OHLC in the HMI.
    required_fields = (
        "timestamp",
        "open",
        "high",
        "low",
        "close",
    )

    candles = [
        candle
        for candle in candles
        if all(
            candle.get(field) is not None
            for field in required_fields
        )
    ]

    return candles, selected


def _add_main_cross_markers(
    fig: go.Figure,
    technical_block: dict[str, Any],
    selected: set[str],
    points: list[dict[str, Any]],
) -> None:
    timestamps_to_point = {
        int(point["timestamp"]): point
        for point in points
        if point.get("timestamp") is not None
    }

    events = [
        event
        for event in _safe_list(
            technical_block.get("events")
        )
        if isinstance(event, dict)
        and event.get("event_group") == "moving_average_cross"
    ]

    grouped: dict[tuple[int, str], list[dict[str, Any]]] = {}

    for event in events:
        calculation = _safe_dict(
            event.get("calculation")
        )
        first = str(
            calculation.get("first_series") or ""
        )
        second = str(
            calculation.get("second_series") or ""
        )

        requirements = {first, second}

        if not requirements.issubset(selected):
            continue

        timestamp = event.get("timestamp")
        signal = str(event.get("signal") or "")

        try:
            key = (int(timestamp), signal)
        except (TypeError, ValueError):
            continue

        grouped.setdefault(key, []).append(event)

    for (timestamp, signal), cluster in grouped.items():
        point = timestamps_to_point.get(timestamp)

        if not point:
            continue

        # Keep one marker per direction/candle to avoid clutter, but anchor
        # the arrow tip at the exact interpolated cross coordinate from JSON.
        event = cluster[0]

        if signal == "bullish":
            color = GREEN
        elif signal == "bearish":
            color = RED
        else:
            continue

        y = _event_anchor_value(event)
        if y is None:
            continue

        _add_exact_event_arrow(
            fig,
            x=_event_anchor_timestamp(event),
            y=y,
            signal=signal,
            color=color,
        )


def _cvd_candlestick_figure(
    contract: dict[str, Any],
    market: str,
    timeframe: str | None,
    selected_overlays: list[str],
) -> go.Figure:
    points, selected_timeframe = _source_points(
        contract,
        market,
        timeframe,
    )
    technical = _technical_block(
        contract,
        market,
        selected_timeframe,
    )
    selected = set(selected_overlays)

    fig = go.Figure()

    if not points:
        fig.add_annotation(
            text="UNAVAILABLE",
            x=.5,
            y=.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font={"color": MUTED},
        )
        return fig

    x = [_dt(point.get("timestamp")) for point in points]

    fig.add_trace(
        go.Candlestick(
            x=x,
            open=[point.get("open") for point in points],
            high=[point.get("high") for point in points],
            low=[point.get("low") for point in points],
            close=[point.get("close") for point in points],
            increasing={
                "line": {"color": GREEN},
                "fillcolor": GREEN,
            },
            decreasing={
                "line": {"color": RED},
                "fillcolor": RED,
            },
            name="CVD",
            showlegend=False,
        )
    )

    overlays = _safe_dict(
        technical.get("overlays")
    )
    moving = _safe_dict(
        _safe_dict(
            overlays.get("moving_averages")
        ).get("series")
    )

    for indicator_id in (
        "ema_9",
        "ema_21",
        "sma_20",
        "sma_50",
        "wma_20",
        "wma_50",
    ):
        if indicator_id not in selected:
            continue

        values = _safe_list(
            moving.get(indicator_id)
        )

        if not values:
            continue

        size = min(len(x), len(values))

        fig.add_trace(
            go.Scatter(
                x=x[-size:],
                y=values[-size:],
                mode="lines",
                line={
                    "color": TRACE_COLORS[indicator_id],
                    "width": 1.05,
                },
                name=indicator_id.upper(),
                showlegend=False,
                hovertemplate=(
                    f"{indicator_id.upper()}: "
                    "%{y:,.2f}<extra></extra>"
                ),
            )
        )

    _add_main_cross_markers(
        fig,
        technical,
        selected,
        points,
    )

    title = {
        "spot": "CVD SPOT",
        "futures": "CVD FUTURES / PERPETUALS",
    }[market]

    fig.update_layout(
        title=None,
        height=235,
        paper_bgcolor=BG,
        plot_bgcolor=PLOT_BG,
        margin={
            "l": 42,
            "r": 12,
            "t": 38,
            "b": 28,
        },
        font={
            "family": "Inter, Segoe UI, sans-serif",
            "color": TEXT,
            "size": 8,
        },
        hovermode="x unified",
        showlegend=False,
        uirevision=(
            f"cvd-{market}-{selected_timeframe}"
        ),
        xaxis_rangeslider_visible=False,
    )

    fig.update_xaxes(
        gridcolor=GRID,
        zeroline=False,
        tickfont={
            "color": MUTED,
            "size": 7,
        },
    )
    fig.update_yaxes(
        gridcolor=GRID,
        zeroline=True,
        zerolinecolor="rgba(91,151,194,.42)",
        tickfont={
            "color": MUTED,
            "size": 7,
        },
    )

    return fig



def _flow_chart_for_market(charts: dict[str, Any], market: str) -> dict[str, Any]:
    """Return the Processing-published flow block without deriving flow in HMI."""
    if market == "spot":
        keys = ("spot_flow", "spot_order_flow", "delta_buy_sell_spot")
    else:
        keys = ("perpetual_flow", "futures_flow", "futures_order_flow", "delta_buy_sell_futures")
    for key in keys:
        candidate = charts.get(key)
        if isinstance(candidate, dict):
            return candidate
    return {}


def _flow_label(chart: dict[str, Any], market: str) -> str:
    explicit = chart.get("flow_label") or chart.get("market_label")
    if explicit:
        label = str(explicit).upper()
        return label if "FLOW" in label else f"{label} FLOW"
    if market == "spot":
        return "SPOT FLOW"
    chart_id = str(chart.get("chart_id") or chart.get("id") or "").lower()
    if "perpetual" in chart_id:
        return "PERPETUAL FLOW"
    if "futures" in chart_id:
        return "FUTURES FLOW"
    return "FUTURES / PERPETUAL FLOW"


def _flow_net_text(snapshot: FlowSnapshot) -> str:
    if snapshot.net_value is None:
        return "NET —"
    field = str(snapshot.net_field or "").lower()
    value = float(snapshot.net_value)
    if "share" in field:
        value *= 100.0
    if "pct" in field or "percent" in field or "share" in field:
        return f"NET {value:+.1f}%"
    return f"NET {value:+,.2f}"


def _delta_buy_sell_figure(
    chart: dict[str, Any] | None,
    *,
    timeframe: str | None,
    height: int = 185,
) -> go.Figure:
    """Render Processing-published Spot/Futures flow as a fast 0–100% read.

    The legacy function name is retained so existing callback IDs remain stable.
    Dash never derives buy/sell shares from delta or a ratio.  If Processing does
    not publish the percentage/share fields, the flow card is unavailable.
    """
    chart_dict = chart if isinstance(chart, dict) else {}
    snapshot = extract_flow_snapshot(chart_dict, timeframe=timeframe)
    fig = make_subplots(
        rows=2,
        cols=1,
        row_heights=[0.58, 0.42],
        vertical_spacing=0.15,
        specs=[[{"type": "xy"}], [{"type": "xy"}]],
    )

    if snapshot.buy_percent is not None and snapshot.sell_percent is not None:
        buy = float(snapshot.buy_percent)
        sell = float(snapshot.sell_percent)
        fig.add_trace(
            go.Bar(
                x=[buy], y=["FLOW"], orientation="h", name="BUY FLOW",
                marker_color=GREEN,
                text=[f"BUY {buy:.1f}%"], textposition="inside",
                insidetextanchor="middle", hovertemplate="BUY %{x:.1f}%<extra></extra>",
            ),
            row=1, col=1,
        )
        fig.add_trace(
            go.Bar(
                x=[sell], y=["FLOW"], orientation="h", name="SELL FLOW",
                marker_color=RED,
                text=[f"SELL {sell:.1f}%"], textposition="inside",
                insidetextanchor="middle", hovertemplate="SELL %{x:.1f}%<extra></extra>",
            ),
            row=1, col=1,
        )
    else:
        state = "PARTIAL" if snapshot.status == "partial" else "UNAVAILABLE"
        fig.add_annotation(
            text=state,
            x=.5, y=.78, xref="paper", yref="paper", showarrow=False,
            font={"color": MUTED, "size": 11},
        )

    if snapshot.history:
        hx = [_dt(item[0]) for item in snapshot.history]
        hy = [item[1] for item in snapshot.history]
        fig.add_trace(
            go.Scatter(
                x=hx, y=hy, mode="lines", name="NET FLOW HISTORY",
                line={"color": "#22c7ff", "width": 1.35},
                showlegend=False,
                hovertemplate="NET %{y:,.2f}<extra></extra>",
            ),
            row=2, col=1,
        )
        fig.add_hline(
            y=0, line_dash="dot", line_width=.8,
            line_color="rgba(127,150,170,.55)", row=2, col=1,
        )
    else:
        fig.add_annotation(
            text="HISTORY —",
            x=.5, y=.12, xref="paper", yref="paper", showarrow=False,
            font={"color": MUTED, "size": 7},
        )

    exchange = snapshot.exchange or str(chart_dict.get("exchange") or chart_dict.get("exchange_name") or "—")
    tf = snapshot.timeframe or timeframe or "—"
    fig.add_annotation(
        text=f"{_flow_net_text(snapshot)}   ·   EXCHANGE {str(exchange).upper()}   ·   TF {tf}",
        x=.5, y=1.07, xref="paper", yref="paper", showarrow=False,
        font={"color": TEXT, "size": 8}, align="center",
    )
    fig.update_layout(
        height=height,
        barmode="stack",
        paper_bgcolor=BG,
        plot_bgcolor=PLOT_BG,
        margin={"l": 34, "r": 16, "t": 30, "b": 26},
        font={"family": "Inter, Segoe UI, sans-serif", "color": TEXT, "size": 8},
        showlegend=False,
        hovermode="x unified",
        uirevision=f"cvd-flow-{timeframe or 'default'}",
    )
    fig.update_xaxes(range=[0, 100], showgrid=False, zeroline=False, showticklabels=False, row=1, col=1)
    fig.update_yaxes(showgrid=False, zeroline=False, showticklabels=False, row=1, col=1)
    fig.update_xaxes(gridcolor=GRID, zeroline=False, tickfont={"color": MUTED, "size": 7}, row=2, col=1)
    fig.update_yaxes(gridcolor=GRID, zeroline=True, zerolinecolor="rgba(91,151,194,.42)", tickfont={"color": MUTED, "size": 7}, row=2, col=1)
    return fig

def _indicator_figure(
    contract: dict[str, Any],
    market: str,
    timeframe: str | None,
    indicator_id: str,
) -> go.Figure:
    technical = _technical_block(
        contract,
        market,
        timeframe,
    )
    indicators = _safe_dict(
        technical.get("indicators")
    )
    block = _safe_dict(
        indicators.get(indicator_id)
    )
    timestamps = [
        _dt(value)
        for value in _safe_list(block.get("timestamps"))
    ]
    series = _safe_dict(block.get("series"))
    fig = go.Figure()

    for name, values_raw in series.items():
        values = _safe_list(values_raw)
        size = min(len(timestamps), len(values))

        if size <= 0:
            continue

        current_x = timestamps[-size:]
        current_y = values[-size:]


        color = TRACE_COLORS.get(
            name,
            TRACE_COLORS.get(
                indicator_id,
                "#22c7e8",
            ),
        )

        fig.add_trace(
            go.Scatter(
                x=current_x,
                y=current_y,
                mode="lines",
                name=name.replace("_", " ").title(),
                line={
                    "color": color,
                    "width": 1.15,
                },
                showlegend=False,
                connectgaps=False,
                hovertemplate=(
                    f"{name.upper()}: "
                    "%{y:.5f}<extra></extra>"
                ),
            )
        )

    for threshold in _safe_list(
        block.get("thresholds")
    ):
        if not isinstance(threshold, dict):
            continue

        value = threshold.get("value")

        if not isinstance(value, (int, float)):
            continue

        role = str(threshold.get("role") or "")
        color = (
            "rgba(255,80,110,.58)"
            if role == "overbought"
            else "rgba(23,212,155,.58)"
            if role == "oversold"
            else "rgba(140,155,168,.42)"
        )

        fig.add_hline(
            y=float(value),
            line_color=color,
            line_dash="dot",
            line_width=1,
        )

    # Native CVD Screen-B panels are direct Processing outputs; no legacy oscillator arrows.

    fig.update_layout(
        height=310,
        paper_bgcolor=BG,
        plot_bgcolor=PLOT_BG,
        margin={
            "l": 32,
            "r": 8,
            "t": 6,
            "b": 20,
        },
        font={
            "family": "Inter, Segoe UI, sans-serif",
            "size": 8,
            "color": MUTED,
        },
        hovermode="x unified",
        showlegend=False,
        barmode="relative",
        uirevision=(
            f"cvd-analysis-{market}-"
            f"{timeframe}-{indicator_id}"
        ),
    )

    fig.update_xaxes(
        showticklabels=True,
        tickformat="%H:%M<br>%d/%m",
        tickfont={"size": 7, "color": MUTED},
        nticks=5,
        ticks="outside",
        ticklen=3,
        title={"text": "UTC", "font": {"size": 7, "color": MUTED}, "standoff": 2},
        gridcolor=GRID,
        zeroline=False,
    )
    if indicator_id == "buy_sell_imbalance":
        fig.update_yaxes(
            gridcolor=GRID,
            zeroline=True,
            zerolinecolor="rgba(91,151,194,.35)",
            range=[-1, 1],
        )
    else:
        fig.update_yaxes(
            gridcolor=GRID,
            zeroline=True,
            zerolinecolor="rgba(91,151,194,.35)",
        )

    for trace in fig.data:
        if trace.name and trace.type in {"scatter", "bar"}:
            trace.showlegend = True
    return apply_analysis_figure_layout(fig, height=220)


def _selected_analysis_ids(
    selection: Any,
) -> list[str]:
    payload = _safe_dict(selection)

    chosen = set(
        _safe_list(
            payload.get("derived_analysis")
        )
        + _safe_list(payload.get("momentum"))
        + _safe_list(payload.get("volatility"))
    )

    return [
        indicator_id
        for indicator_id in ANALYSIS_ORDER
        if indicator_id in chosen
    ]


def _cvd_signal_color(summary: dict[str, Any]) -> str:
    raw = str(summary.get("signal_color") or "").strip().lower()
    if raw.startswith("#") and len(raw) in {4, 7, 9}:
        return raw
    semantic = raw or str(summary.get("signal") or "").strip().lower()
    if semantic in {"positive", "bullish", "buy", "buying", "expanding", "strong"}:
        return "#20d05c"
    if semantic in {"negative", "bearish", "sell", "selling", "contracting"}:
        return "#ff3d55"
    if semantic in {"neutral", "normal", "mixed", "balanced", "available", "ok"}:
        return "#ffab00"
    if semantic in {"unavailable", "missing", "error", "unknown", "—", ""}:
        return "#59636b"
    return "#22c7e8"


def _cvd_strength_count(value: Any, *, available: bool = True) -> int:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 3 if available else 0
    if number <= 0:
        return 1 if available else 0
    if number <= 1.0:
        import math
        return max(1, min(5, int(math.ceil(number * 5.0))))
    return max(1, min(5, int(round(number))))


def _cvd_strength_dots(count: Any, color: str) -> html.Span:
    try:
        strength = max(1, min(5, int(count)))
    except (TypeError, ValueError):
        strength = 1

    return html.Span(
        className="cvd-summary-strength",
        children=[
            html.Span(
                className="cvd-summary-dot",
                style={"background": color if index < strength else "#46525d"},
            )
            for index in range(5)
        ],
    )


def _cvd_summary_panel(
    block: dict[str, Any],
    selected_ids: list[str],
    title: str = "INDICATOR SUMMARY",
) -> html.Div:
    indicators = _safe_dict(block.get("indicators"))
    chosen = [
        indicator_id
        for indicator_id in ANALYSIS_ORDER
        if indicator_id in set(selected_ids)
    ]

    body: list[Any] = [
        html.Div(
            className="cvd-summary-head",
            children=[
                html.Span("INDICATOR"),
                html.Span("VALUE", style={"textAlign": "right"}),
                html.Span("SIGNAL", style={"textAlign": "right"}),
                html.Span("STRENGTH", style={"textAlign": "right"}),
            ],
        )
    ]

    sections = (
        ("flow", "FLOW DYNAMICS", "#20d05c"),
        ("divergence", "DIVERGENCES", "#a65cff"),
        ("regime", "REGIME CHANGE", "#2ea8ff"),
    )

    for section_id, section_title, section_color in sections:
        section_rows = []

        for indicator_id in chosen:
            indicator = _safe_dict(indicators.get(indicator_id))
            summary = _safe_dict(indicator.get("summary"))

            if summary.get("section") != section_id:
                continue

            signal_color = _cvd_signal_color(summary)
            strength_count = _cvd_strength_count(
                summary.get("strength"),
                available=str(summary.get("signal") or "").strip().lower() not in {"", "unavailable", "—"},
            )

            section_rows.append(
                html.Div(
                    className="cvd-summary-row",
                    children=[
                        html.Span(
                            str(summary.get("label") or indicator_id.upper()),
                            className="cvd-summary-name",
                        ),
                        html.Span(
                            str(summary.get("display_value") or "—"),
                            className="cvd-summary-value",
                        ),
                        html.Span(
                            str(summary.get("signal") or "—"),
                            className="cvd-summary-signal",
                            style={"color": signal_color},
                        ),
                        _cvd_strength_dots(
                            strength_count,
                            signal_color,
                        ),
                    ],
                )
            )

        if not section_rows:
            continue

        body.append(
            html.Div(
                className="cvd-summary-section",
                style={"color": section_color},
                children=[
                    html.Span(className="cvd-summary-section-marker"),
                    html.Span(section_title),
                ],
            )
        )
        body.extend(section_rows)

    return html.Div(
        className="cvd-summary-panel",
        children=[
            html.Div(title, className="cvd-summary-title"),
            *body,
        ],
    )


def _cvd_strength_legend() -> html.Div:
    rows = (
        ("VERY STRONG", 5, "#20d05c"),
        ("STRONG", 4, "#20d05c"),
        ("MODERATE", 3, "#ffab00"),
        ("WEAK", 2, "#ff8a00"),
        ("VERY WEAK", 1, "#ff3d55"),
    )

    return html.Div(
        className="cvd-strength-legend",
        children=[
            html.Div("STRENGTH LEGEND", className="cvd-strength-title"),
            html.Div(
                className="cvd-strength-body",
                children=[
                    html.Div(
                        className="cvd-strength-row",
                        children=[
                            html.Span(label),
                            _cvd_strength_dots(count, color),
                        ],
                    )
                    for label, count, color in rows
                ],
            ),
        ],
    )

def build_analysis_screen(
    contract: dict[str, Any],
    timeframe: str | None,
    selection: Any,
) -> html.Div:
    selected_ids = _selected_analysis_ids(
        selection
    )

    if not selected_ids:
        empty = html.Div(
            "No indicators selected for analysis on Screen A.",
            className="contract-warning",
        )
        return html.Div(
            [
                html.Div(
                className="analysis-back-row",
                children=[
                    html.Div(
                            children=[
                                dcc.Link(
                                    "← BACK",
                                    href=localized_href(ROUTE),
                                    className="analysis-back-button",
                                    style={"textDecoration": "none"},
                                ),
                            ],
                        )
                ],
            ),
                empty,
            ]
        )

    cards: list[Any] = []

    for market, title in (
        ("spot", "CVD SPOT"),
        ("futures", "CVD FUTURES / PERPETUALS"),
    ):
        for indicator_id in selected_ids:
            cards.append(
                html.Div(
                    className="screen-b-card cvd-analysis-card",
                    children=[
                        html.Div(
                            contextual_help_label(
                                f"{title} · {INDICATOR_TITLES[indicator_id]}",
                                family="cvd",
                                section="screen_b",
                                key=indicator_id,
                            ),
                            className="screen-b-card-title cvd-analysis-card-title",
                        ),
                        dcc.Graph(
                            figure=_indicator_figure(
                                contract,
                                market,
                                timeframe,
                                indicator_id,
                            ),
                            config={
                                "displaylogo": False,
                                "responsive": False,
                            },
                            className="screen-b-graph cvd-analysis-card-graph",
                            animate=False,
                            style={
                                "height": "220px",
                                "minHeight": "220px",
                                "maxHeight": "220px",
                                "width": "100%",
                            },
                        ),
                    ],
                )
            )

    return html.Div(
        className="cvd-analysis-shell",
        children=[
            html.Div(
                className="analysis-back-row",
                children=[
                    html.Div(
                            children=[
                                dcc.Link(
                                    "← BACK",
                                    href=localized_href(ROUTE),
                                    className="analysis-back-button",
                                    style={"textDecoration": "none"},
                                ),
                            ],
                        )
                ],
            ),
            html.Div(
                className="screen-b-layout cvd-analysis-layout",
                children=[
                    html.Div(
                        cards,
                        className="screen-b-grid cvd-analysis-main cvd-analysis-grid",
                    ),
                    html.Div(
                        className="cvd-summary-column",
                        children=[
                            _analysis_indicator_controls(selection),
                            _cvd_summary_panel(
                                _technical_block(contract, "spot", timeframe),
                                selected_ids,
                                "SUMMARY · CVD SPOT",
                            ),
                            _cvd_summary_panel(
                                _technical_block(contract, "futures", timeframe),
                                selected_ids,
                                "SUMMARY · CVD FUTURES",
                            ),
                            _cvd_strength_legend(),
                        ],
                    ),
                ],
            ),
        ],
    )


def _main_candle_grid(
    contract: dict[str, Any],
    timeframe: str | None,
    selected_overlays: list[str],
) -> html.Div:
    charts = _safe_dict(
        contract.get("charts")
    )

    market_specs = (
        (
            "spot",
            "cvd-spot-candle",
            "delta_buy_sell_spot",
            "cvd-spot-delta",
        ),
        (
            "futures",
            "cvd-futures-candle",
            "delta_buy_sell_futures",
            "cvd-futures-delta",
        ),
    )

    columns: list[Any] = []

    for (
        market,
        candle_component_id,
        delta_chart_id,
        delta_component_id,
    ) in market_specs:
        columns.append(
            html.Div(
                className="cvd-market-stack",
                children=[
                    html.Div(
                        className="cvd-chart-card",
                        children=[
                            html.Div(
                                contextual_help_label(
                                    "CVD SPOT" if market == "spot" else "CVD FUTURES / PERPETUALS",
                                    family="cvd",
                                    section="screen_a",
                                    key="cvd_spot" if market == "spot" else "cvd_futures",
                                ),
                                className="context-help-card-title context-help-card-title-compact",
                            ),
                            dcc.Graph(
                                id=candle_component_id,
                                figure=(
                                    _cvd_candlestick_figure(
                                        contract,
                                        market,
                                        timeframe,
                                        selected_overlays,
                                    )
                                ),
                                config={
                                    "displaylogo": False,
                                    "responsive": True,
                                    "scrollZoom": True,
                                    "modeBarButtonsToRemove": [
                                        "lasso2d",
                                        "select2d",
                                    ],
                                },
                                style={
                                    "height": "235px",
                                    "minHeight": "235px",
                                    "maxHeight": "235px",
                                    "width": "100%",
                                },
                            )
                        ],
                    ),
                    html.Div(
                        className="cvd-chart-card",
                        children=[
                            html.Div(
                                contextual_help_label(
                                    _flow_label(_flow_chart_for_market(charts, market), market),
                                    family="cvd",
                                    section="screen_a",
                                    key="delta_buy_sell_spot" if market == "spot" else "delta_buy_sell_futures",
                                ),
                                className="context-help-card-title context-help-card-title-compact",
                            ),
                            dcc.Graph(
                                id=delta_component_id,
                                figure=(
                                    _delta_buy_sell_figure(
                                        _flow_chart_for_market(charts, market),
                                        timeframe=timeframe,
                                    )
                                ),
                                config={
                                    "displaylogo": False,
                                    "responsive": True,
                                },
                                style={
                                    "height": "185px",
                                    "minHeight": "185px",
                                    "maxHeight": "185px",
                                    "width": "100%",
                                },
                            )
                        ],
                    ),
                ],
            )
        )

    return html.Div(
        columns,
        className="cvd-market-stack-grid",
    )



@callback(
    Output("cvd-spot-candle", "figure"),
    Output("cvd-futures-candle", "figure"),
    Output("cvd-spot-delta", "figure"),
    Output("cvd-futures-delta", "figure"),
    Input("cvd-trend-selectors", "value", allow_optional=True),
    Input("timeframe-selector", "value"),
    Input("reload-json", "n_clicks"),
    Input("url", "search"),
    prevent_initial_call=False,
)
def update_cvd_candles(
    trend: list[str] | None,
    timeframe: str | None,
    _reload_clicks: int | None,
    search: str | None,
):
    locale = locale_from_search(search)
    selected = _unique(DEFAULT_TREND if trend is None else trend)
    contract = load_contract(CONTRACT_FILE)

    charts = _safe_dict(
        contract.get("charts")
    )

    figures = (
        _cvd_candlestick_figure(
            contract,
            "spot",
            timeframe,
            selected,
        ),
        _cvd_candlestick_figure(
            contract,
            "futures",
            timeframe,
            selected,
        ),
        _delta_buy_sell_figure(
            _flow_chart_for_market(charts, "spot"),
            timeframe=timeframe,
        ),
        _delta_buy_sell_figure(
            _flow_chart_for_market(charts, "futures"),
            timeframe=timeframe,
        ),
    )
    return tuple(localize_figure(figure, locale) for figure in figures)


@callback(
    Output(SELECTION_STORE_ID, "data"),
    Input("cvd-trend-selectors", "value", allow_optional=True),
    Input("cvd-derived-selectors", "value", allow_optional=True),
    Input("cvd-momentum-selectors", "value", allow_optional=True),
    Input("cvd-volatility-selectors", "value", allow_optional=True),
    State(SELECTION_STORE_ID, "data"),
    prevent_initial_call=True,
)
def persist_cvd_selection(
    trend: list[str] | None,
    derived: list[str] | None,
    momentum: list[str] | None,
    volatility: list[str] | None,
    current: Any,
) -> dict[str, list[str]]:
    # On Screen B the trend checklist is intentionally absent. None therefore
    # means "component not mounted" and must retain the stored Screen-A trend
    # selection; [] still means the user explicitly deselected everything.
    stored = resolve_persisted_selection(current, _default_selection)
    return _selection_payload(
        list(stored.get("trend", [])) if trend is None else trend,
        list(stored.get("derived_analysis", [])) if derived is None else derived,
        list(stored.get("momentum", [])) if momentum is None else momentum,
        list(stored.get("volatility", [])) if volatility is None else volatility,
    )


@callback(
    Output(
        ANALYSIS_CONTENT_ID,
        "children",
    ),
    Input(SELECTION_STORE_ID, "data"),
    Input("timeframe-selector", "value"),
    Input("reload-json", "n_clicks"),
    Input("url", "search"),
    prevent_initial_call=False,
)
def update_cvd_analysis_screen(
    selection: Any,
    timeframe: str | None,
    _reload_clicks: int | None,
    search: str | None,
):
    locale = locale_from_search(search)
    contract = load_contract(CONTRACT_FILE)

    with locale_context(locale):
        return localize_component_tree(
            build_analysis_screen(
                contract,
                timeframe,
                resolve_persisted_selection(selection, _default_selection),
            ),
            locale,
        )


def _display_kpis(contract: dict[str, Any]) -> dict[str, Any]:
    """Return only KPI cards explicitly selected by the CVD layout contract.

    Processing intentionally keeps a richer KPI inventory for downstream analysis,
    but Screen A should not render every internal metric as a top-level card.  The
    presentation contract owns the compact top-KPI list.
    """
    kpis = _safe_dict(contract.get("kpis"))
    screen = _safe_dict(contract.get("screen"))
    layout = _safe_dict(screen.get("layout_contract"))
    top_ids = layout.get("top_kpis")
    if not isinstance(top_ids, list) or not top_ids:
        return kpis
    return {
        str(kpi_id): kpis[str(kpi_id)]
        for kpi_id in top_ids
        if str(kpi_id) in kpis and isinstance(kpis[str(kpi_id)], dict)
    }


def render(
    contract: dict[str, Any],
    view: str,
    market: str | None,
    timeframe: str | None,
    range_id: str | None,
) -> html.Div:
    del market, range_id

    if view == "reference":
        return screen_page(
            _cvd_stylesheet(),
            screen_header(contract),
            reference_gallery(REFERENCE_IMAGES),
        )

    if view == "analysis":
        return screen_page(
            _cvd_stylesheet(),
            dcc.Store(
                id=SELECTION_STORE_ID,
                storage_type="local",
            ),
            html.Div(
                id=ANALYSIS_CONTENT_ID,
                children=build_analysis_screen(
                    contract,
                    timeframe,
                    _default_selection(),
                ),
            ),
        )

    initial = _default_selection()
    selected_overlays = _unique(initial["trend"])

    return screen_page(
        _cvd_stylesheet(),
        dcc.Store(
            id=SELECTION_STORE_ID,
            storage_type="local",
        ),
        screen_header(contract),
        kpi_grid(_display_kpis(contract), help_family="cvd"),
        html.Div(
            className="cvd-main-grid",
            children=[
                _main_candle_grid(
                    contract,
                    timeframe,
                    selected_overlays,
                ),
                _indicator_panel(),
            ],
        )
    )
