from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable
from urllib.parse import quote

import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html
from plotly.subplots import make_subplots

from screen_core.selection_state import (
    LOCAL_SELECTION_PERSISTENCE_TYPE,
    resolve_persisted_selection,
)
from screen_core.components import (
    reference_gallery,
    screen_header,
    screen_page,
)
from screen_core.contextual_help import contextual_help_label
from screen_core.i18n import locale_context, localize_component_tree, localize_figure, localized_href, locale_from_search
from screen_core.contract_loader import load_contract
from screen_core.formatting import compact_number
from screen_core.figures import apply_analysis_figure_layout


ROUTE = "/open-interest-and-funding"
LABEL = "Open Interest"
CONTRACT_FILE = "open_interest_and_funding_VR1_FINAL.json"
HAS_ANALYSIS = True
SCREEN_REVISION = "OI_NATIVE_SCREEN_B_V1"

REFERENCE_IMAGES = [
    "Open Interest/03_Open_Interest_A.png",
    "Open Interest/03_Open_Interest_B.png",
]


PRICE_KPI_SPEC = (
    ("open_interest_usd", "OPEN INTEREST USD", "default"),
    ("oi_change_24h", "OI CHANGE 24H", "change"),
    ("oi_funding_state", "OI FUNDING STATE", "default"),
    ("provider_availability", "PROVIDER AVAILABILITY", "default"),
    ("funding_rate", "FUNDING RATE", "change"),
    ("estimated_leverage_ratio", "EST. LEVERAGE RATIO", "default"),
)


TREND_OPTIONS = [
    {"label": "EMA 9", "value": "ema_9"},
    {"label": "EMA 21", "value": "ema_21"},
    {"label": "SMA 20", "value": "sma_20"},
    {"label": "SMA 50", "value": "sma_50"},
    {"label": "WMA 20", "value": "wma_20"},
    {"label": "WMA 50", "value": "wma_50"},
]

BAND_OPTIONS = [
    {"label": "Bollinger Bands (20, 2)", "value": "bollinger_bands"},
    {"label": "Regression Channel", "value": "regression_channel"},
]

DERIVED_ANALYSIS_OPTIONS = [
    {"label": "OI ROC / Slope / Acceleration", "value": "oi_dynamics"},
    {"label": "OI Z-Score / Percentile", "value": "oi_zscore_percentile"},
]

MOMENTUM_OPTIONS = [
    {"label": "Price × OI Regime", "value": "price_oi_regime"},
    {"label": "Price ↔ OI Divergence", "value": "price_oi_divergence"},
]

VOLATILITY_OPTIONS = [
    {"label": "Funding × OI Crowding", "value": "funding_oi_crowding"},
    {"label": "Wasserstein / Regime Shift", "value": "wasserstein_distance"},
]

# Kept as an empty hidden checklist because existing Dash callbacks consume this id.
OPEN_INTEREST_OPTIONS: list[dict[str, str]] = []

DEFAULT_TREND = ["ema_9", "ema_21", "sma_20", "sma_50", "wma_20", "wma_50"]
DEFAULT_BANDS = ["bollinger_bands"]
DEFAULT_DERIVED_ANALYSIS = ["oi_dynamics", "oi_zscore_percentile"]
DEFAULT_MOMENTUM = ["price_oi_regime", "price_oi_divergence"]
DEFAULT_VOLATILITY = ["funding_oi_crowding", "wasserstein_distance"]
DEFAULT_OPEN_INTEREST: list[str] = []

PRICE_OVERLAYS = {
    "ema_9",
    "ema_21",
    "sma_20",
    "sma_50",
    "wma_20",
    "wma_50",
    "bollinger_bands",
    "regression_channel",
}

SCREEN_A_CROSS_GROUPS = {
    "moving_average_cross",
    "channel_cross",
}

INDICATOR_TITLES = {
    "oi_dynamics": "OI ROC / SLOPE / ACCELERATION",
    "oi_zscore_percentile": "OI Z-SCORE / PERCENTILE",
    "price_oi_regime": "PRICE × OPEN INTEREST REGIME",
    "price_oi_divergence": "PRICE ↔ OPEN INTEREST DIVERGENCE",
    "funding_oi_crowding": "FUNDING × OPEN INTEREST CROWDING",
    "wasserstein_distance": "WASSERSTEIN / REGIME SHIFT",
}

SERIES_LABELS = {
    "oi_roc": "OI ROC %",
    "oi_slope_pct": "OI SLOPE %",
    "oi_acceleration_pct": "OI ACCELERATION %",
    "oi_zscore": "OI Z-SCORE",
    "oi_percentile": "OI PERCENTILE",
    "regime_score": "REGIME SCORE",
    "price_return_z": "PRICE RETURN Z",
    "oi_change_z": "OI CHANGE Z",
    "divergence_score": "DIVERGENCE SCORE",
    "funding_zscore": "FUNDING Z",
    "crowding_score": "CROWDING SCORE",
    "wasserstein_distance": "WASSERSTEIN",
    "value": "VALUE",
}

TRACE_COLORS = {
    "ema_9": "#2f80ff",
    "ema_21": "#00c2ff",
    "sma_20": "#00d4ff",
    "sma_50": "#f2c94c",
    "wma_20": "#a879ff",
    "wma_50": "#ff8a3d",
    "oi_roc": "#22c7e8",
    "oi_slope_pct": "#00e59b",
    "oi_acceleration_pct": "#f2c94c",
    "oi_zscore": "#22c7e8",
    "oi_percentile": "#a879ff",
    "regime_score": "#00e59b",
    "price_return_z": "#2f80ff",
    "oi_change_z": "#f2c94c",
    "divergence_score": "#ff4d6d",
    "funding_zscore": "#a879ff",
    "crowding_score": "#ff8a3d",
    "wasserstein_distance": "#3c94ed",
    "value": "#3c94ed",
}


OPEN_INTEREST_LOCAL_CSS = """
.oi-main-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 286px;
    gap: 8px;
    align-items: stretch;
}

.oi-chart-card,
.oi-indicator-panel {
    min-width: 0;
    border: 1px solid #10283a;
    background: #06111d;
}

.oi-chart-card {
    height: 590px;
    overflow: hidden;
    box-sizing: border-box;
}

.oi-main-chart-header {
    min-height: 34px;
    display: flex;
    align-items: center;
    padding: 7px 10px 4px;
    border-bottom: 1px solid rgba(23,50,71,.55);
    color: #e4edf4;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: .15px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.oi-main-graph {
    width: 100%;
    height: 556px;
    min-height: 556px;
}

.oi-indicator-panel {
    height: 590px;
    padding: 8px 10px 12px;
    color: #dbe7ef;
    overflow-y: auto;
    box-sizing: border-box;
}

.oi-analysis-button {
    height: 26px;
    border: 1px solid #1766d6;
    border-radius: 4px;
    color: #3f8cff;
    background: #06111d;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: .15px;
    margin-bottom: 12px;
}

.oi-selector-heading {
    color: #f1f5f8;
    font-size: 10px;
    line-height: 1.2;
    margin-bottom: 7px;
}

.oi-selector-heading span {
    color: #8c9ba8;
    font-size: 8px;
}

.oi-selector-help {
    display: flex;
    gap: 6px;
    align-items: flex-start;
    color: #8c9ba8;
    font-size: 8px;
    line-height: 1.35;
    margin-bottom: 11px;
}

.oi-selector-help-mark {
    flex: 0 0 auto;
    width: 11px;
    height: 11px;
    border: 1px solid #2f80ff;
    border-radius: 50%;
    color: #2f80ff;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 7px;
    margin-top: 1px;
}

.oi-indicator-group {
    border-top: 1px solid #12283a;
    padding-top: 7px;
    margin-top: 7px;
}

.oi-indicator-group:first-of-type {
    margin-top: 0;
}

.oi-indicator-group-title {
    color: #7f91a0;
    font-size: 8px;
    line-height: 1;
    margin-bottom: 6px;
    text-transform: uppercase;
}

.oi-analysis-only-group {
    margin-top: 9px;
    padding: 8px;
    border: 1px dashed #235274;
    border-radius: 4px;
    background: rgba(18, 54, 78, .18);
}

.oi-analysis-only-group .oi-indicator-group-title {
    color: #5aa9e6;
    margin-bottom: 5px;
}

.oi-analysis-only-note {
    margin-bottom: 7px;
    color: #8fa6b7;
    font-size: 8px;
    line-height: 1.35;
}

.oi-analysis-only-note strong {
    color: #c8d9e5;
    font-weight: 600;
}

.oi-options-grid {
    display: grid !important;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    column-gap: 8px;
    row-gap: 6px;
}

.oi-options-grid label {
    display: flex !important;
    align-items: center;
    min-width: 0;
    margin: 0 !important;
    color: #c7d2da;
    font-size: 9px;
    line-height: 1.15;
    white-space: nowrap;
}

.oi-options-grid input[type="checkbox"] {
    width: 11px;
    height: 11px;
    min-width: 11px;
    margin: 0 6px 0 0 !important;
    accent-color: #2f80ff;
    cursor: pointer;
}

.oi-options-grid label:hover {
    color: #ffffff;
}


.oi-analysis-button {
    width: 100%;
    padding: 0 8px;
    font-family: inherit;
    cursor: pointer;
}

.oi-analysis-button:hover {
    background: #081b2d;
    border-color: #2d8cff;
    color: #66a8ff;
}

.oi-analysis-screen {
    min-width: 0;
    padding: 0;
    color: #d8e2e9;
}

.oi-analysis-layout {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 286px;
    gap: 8px;
    align-items: start;
}

.oi-analysis-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 5px;
    align-items: stretch;
}

.oi-analysis-card {
    min-width: 0;
    height: 247px;
    min-height: 247px;
    max-height: 247px;
    border: 1px solid #123247;
    border-radius: 4px;
    background: linear-gradient(180deg, #061522 0%, #04111c 100%);
    overflow: hidden;
    box-shadow: inset 0 0 0 1px rgba(0, 194, 255, .015);
}

.oi-analysis-card-header {
    height: 26px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 9px;
    border-bottom: 1px solid #102b3d;
    color: #dce6ec;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: .1px;
    box-sizing: border-box;
}

.oi-analysis-info {
    width: 12px;
    height: 12px;
    border: 1px solid #00aeea;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: #00bff3;
    font-size: 7px;
    line-height: 1;
}

.oi-analysis-card-body {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 68px;
    min-height: 220px;
}

.oi-analysis-card-graph {
    min-width: 0;
    width: 100%;
    height: 220px !important;
    min-height: 220px !important;
    max-height: 220px !important;
    overflow: hidden;
}

.oi-analysis-card-graph .js-plotly-plot,
.oi-analysis-card-graph .plot-container,
.oi-analysis-card-graph .svg-container {
    height: 220px !important;
    min-height: 220px !important;
    max-height: 220px !important;
}

.oi-analysis-card-values {
    min-width: 0;
    padding: 10px 6px 7px;
    border-left: 1px solid #102b3d;
    background: rgba(2, 14, 24, .5);
    box-sizing: border-box;
}

.oi-analysis-metric-label {
    color: #8295a2;
    font-size: 7px;
    line-height: 1.1;
    text-transform: uppercase;
}

.oi-analysis-metric-value {
    margin: 1px 0 7px;
    font-size: 11px;
    font-weight: 700;
    line-height: 1.05;
}

.oi-analysis-signal-label {
    margin-top: 4px;
    color: #8295a2;
    font-size: 7px;
    line-height: 1.1;
    text-transform: uppercase;
}

.oi-analysis-signal-value {
    margin-top: 2px;
    font-size: 9px;
    font-weight: 700;
    line-height: 1.1;
    text-transform: uppercase;
}

.oi-analysis-empty {
    min-height: 370px;
    border: 1px solid #123247;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 28px;
    color: #718593;
    background: #05131f;
    font-size: 11px;
    text-align: center;
}

.oi-summary-column {
    display: grid;
    gap: 7px;
}

.oi-analysis-controls {
    border: 1px solid #173247;
    border-radius: 4px;
    background: #06111d;
    overflow: hidden;
    align-self: start;
}
.oi-analysis-controls .oi-indicator-group {
    border-top: 1px solid #173247;
    padding: 8px 9px;
    margin: 0;
}
.oi-analysis-controls .oi-indicator-group-title {
    color: #718da3;
    font-size: 8px;
    margin-bottom: 6px;
}
.oi-analysis-controls .oi-options-grid {
    grid-template-columns: 1fr;
    gap: 0;
}
.oi-analysis-controls .oi-options-grid label {
    color: #d9e8f5;
    font-size: 9px;
    min-height: 20px;
}

.oi-summary-panel,
.oi-strength-legend {
    border: 1px solid #123247;
    border-radius: 4px;
    background: linear-gradient(180deg, #061522 0%, #04111c 100%);
    overflow: hidden;
}

.oi-summary-title,
.oi-strength-title {
    height: 28px;
    display: flex;
    align-items: center;
    padding: 0 10px;
    border-bottom: 1px solid #173247;
    color: #e1e8ed;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: .15px;
    box-sizing: border-box;
}

.oi-summary-head,
.oi-summary-row {
    display: grid;
    grid-template-columns: minmax(0, 1.45fr) 58px 58px 66px;
    align-items: center;
    min-height: 23px;
    padding: 0 8px;
    column-gap: 4px;
    box-sizing: border-box;
}

.oi-summary-head {
    min-height: 24px;
    border-bottom: 1px solid #102b3d;
    color: #8496a2;
    font-size: 7px;
    text-transform: uppercase;
}

.oi-summary-section {
    min-height: 25px;
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 0 8px;
    border-top: 1px solid #102b3d;
    color: #00e59b;
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
}

.oi-summary-section:first-of-type {
    border-top: none;
}

.oi-summary-section-marker {
    width: 0;
    height: 0;
    border-top: 4px solid transparent;
    border-bottom: 4px solid transparent;
    border-left: 5px solid currentColor;
}

.oi-summary-row {
    border-top: 1px solid rgba(16, 43, 61, .55);
    color: #c0ccd4;
    font-size: 7.5px;
}

.oi-summary-name {
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
}

.oi-summary-value {
    color: #dbe4ea;
    text-align: right;
    font-variant-numeric: tabular-nums;
}

.oi-summary-signal {
    text-align: right;
    font-size: 7.5px;
    font-weight: 700;
    text-transform: uppercase;
}

.oi-strength-dots {
    display: flex;
    justify-content: flex-end;
    gap: 3px;
}

.oi-strength-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #59636b;
}

.oi-strength-legend-body {
    display: grid;
    grid-template-columns: 1fr 1.25fr;
    gap: 10px;
    padding: 9px 10px 10px;
}

.oi-strength-legend-rows {
    display: grid;
    gap: 5px;
}

.oi-strength-legend-row {
    display: grid;
    grid-template-columns: 58px 1fr;
    align-items: center;
    color: #c0cbd2;
    font-size: 7.5px;
    text-transform: uppercase;
}

.oi-strength-copy {
    color: #93a2ad;
    font-size: 7px;
    line-height: 1.45;
}

@media (max-width: 1320px) {
    .oi-analysis-layout {
        grid-template-columns: minmax(0, 1fr) 290px;
    }

    .oi-analysis-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }
}

@media (max-width: 920px) {
    .oi-analysis-layout {
        grid-template-columns: 1fr;
    }

    .oi-analysis-grid {
        grid-template-columns: 1fr;
    }
}

@media (max-width: 1180px) {
    .oi-main-grid {
        grid-template-columns: 1fr;
    }

    .oi-indicator-panel {
        width: auto;
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
"""


KPI_STRIP_STYLE = {
    "display": "grid",
    "gridTemplateColumns": "repeat(6, minmax(110px, 1fr))",
    "width": "100%",
    "minWidth": "720px",
    "background": "#06111d",
    "borderTop": "1px solid #102536",
    "borderBottom": "1px solid #102536",
    "overflowX": "auto",
    "boxSizing": "border-box",
}

KPI_CELL_STYLE = {
    "minWidth": "0",
    "minHeight": "34px",
    "padding": "1px 6px 1px",
    "borderRight": "1px solid #173043",
    "textAlign": "center",
    "boxSizing": "border-box",
}

KPI_LABEL_STYLE = {
    "minHeight": "8px",
    "fontSize": "7px",
    "fontWeight": "500",
    "lineHeight": "1.15",
    "letterSpacing": "0.2px",
    "color": "#9cadbb",
    "textTransform": "uppercase",
    "whiteSpace": "nowrap",
    "overflow": "hidden",
    "textOverflow": "ellipsis",
}

KPI_VALUE_STYLE = {
    "marginTop": "1px",
    "fontSize": "13px",
    "fontWeight": "700",
    "lineHeight": "1.1",
    "color": "#eef6fb",
    "whiteSpace": "nowrap",
    "overflow": "hidden",
    "textOverflow": "ellipsis",
}

KPI_UNIT_STYLE = {
    "minHeight": "6px",
    "marginTop": "0",
    "fontSize": "7px",
    "lineHeight": "1",
    "color": "#8998a5",
    "textTransform": "uppercase",
}

KPI_SECONDARY_STYLE = {
    "minHeight": "0",
    "marginTop": "0",
    "fontSize": "7px",
    "fontWeight": "700",
    "lineHeight": "1",
}


# -----------------------------------------------------------------------------
# Generic helpers
# -----------------------------------------------------------------------------


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _utc_datetime(timestamp: Any) -> datetime | None:
    if timestamp is None:
        return None

    try:
        return datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _line_color(name: str, index: int = 0) -> str:
    fallback = ("#2f80ff", "#00c2ff", "#f2c94c", "#bb6bd9", "#27ae60")
    return TRACE_COLORS.get(name, fallback[index % len(fallback)])


# -----------------------------------------------------------------------------
# KPI strip
# -----------------------------------------------------------------------------


def _get_kpis(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    kpis = _safe_dict(contract.get("kpis"))
    items = _safe_list(kpis.get("items"))
    result: dict[str, dict[str, Any]] = {}

    for item in items:
        if not isinstance(item, dict):
            continue

        metric_id = item.get("metric_id") or item.get("kpi_id") or item.get("id")
        if metric_id:
            result[str(metric_id)] = item

    return result


def _unit_label(unit: Any) -> str:
    if unit == "quote_currency":
        return "USDT"
    if unit in {"percent", "percentage", "percent_points", None, "", "ratio", "decimal", "state"}:
        return ""
    return str(unit).upper()


def _format_value(metric: dict[str, Any], *, signed: bool = False) -> str:
    display_value = metric.get("display_value")

    if display_value not in {None, ""}:
        text = str(display_value)
    else:
        value = metric.get("value")
        if value is None:
            return "—"

        text = compact_number(value)
        if metric.get("unit") in {"percent", "percentage", "percent_points"}:
            text = f"{text}%"

    if signed:
        try:
            value = float(metric.get("value"))
            if value > 0 and not text.startswith("+"):
                text = f"+{text}"
        except (TypeError, ValueError):
            pass

    return text


def _format_secondary(metric: dict[str, Any]) -> str:
    display_value = metric.get("secondary_display_value")
    if display_value not in {None, ""}:
        return str(display_value)

    value = metric.get("secondary_value")
    if value is None:
        return ""

    text = compact_number(value)
    if metric.get("secondary_unit") in {"percent", "percentage", "percent_points"}:
        text = f"{text}%"
    return text


def _change_color(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "#eef6fb"

    if number > 0:
        return "#00e49a"
    if number < 0:
        return "#ff3d61"
    return "#eef6fb"


def _metric_color(metric: dict[str, Any], tone: str) -> str:
    if metric.get("value") is None:
        return "#7f8b95"
    if tone == "change":
        return _change_color(metric.get("value"))
    return "#eef6fb"


def _label_color(tone: str) -> str:
    return "#9cadbb"


def _open_interest_kpi_strip(contract: dict[str, Any]) -> html.Div:
    kpis = _get_kpis(contract)
    cells: list[html.Div] = []

    for index, (metric_id, label, tone) in enumerate(PRICE_KPI_SPEC):
        metric = kpis.get(
            metric_id,
            {
                "metric_id": metric_id,
                "value": None,
                "unit": None,
                "status": "unavailable",
            },
        )

        value_color = _metric_color(metric, tone)
        cell_style = dict(KPI_CELL_STYLE)
        if index == len(PRICE_KPI_SPEC) - 1:
            cell_style["borderRight"] = "none"

        cells.append(
            html.Div(
                style=cell_style,
                children=[
                    html.Div(
                        contextual_help_label(
                            label,
                            family="open_interest",
                            section="kpi",
                            key=metric_id,
                        ),
                        style={**KPI_LABEL_STYLE, "color": _label_color(tone)},
                    ),
                    html.Div(
                        _format_value(metric, signed=metric_id == "change_24h"),
                        style={**KPI_VALUE_STYLE, "color": value_color},
                    ),
                    html.Div(_unit_label(metric.get("unit")), style=KPI_UNIT_STYLE),
                    html.Div(
                        _format_secondary(metric),
                        style={**KPI_SECONDARY_STYLE, "color": value_color},
                    ),
                ],
            )
        )

    return html.Div(
        style={"width": "100%", "overflowX": "auto", "marginBottom": "2px"},
        children=[html.Div(cells, style=KPI_STRIP_STYLE)],
    )


# -----------------------------------------------------------------------------
# Indicator selector panel
# -----------------------------------------------------------------------------


def _checklist(component_id: str, options: list[dict[str, str]], values: list[str]) -> dcc.Checklist:
    return dcc.Checklist(
        id=component_id,
        options=options,
        value=values,
        className="oi-options-grid",
        persistence="oi-controls-v2",
        persistence_type=LOCAL_SELECTION_PERSISTENCE_TYPE,
    )


def _selector_group(title: str, checklist: dcc.Checklist) -> html.Div:
    return html.Div(
        className="oi-indicator-group",
        children=[
            html.Div(title, className="oi-indicator-group-title"),
            checklist,
        ],
    )


def _analysis_only_selector_group(checklist: dcc.Checklist) -> html.Div:
    return html.Div(
        className="oi-analysis-only-group",
        children=[
            html.Div(
                "DERIVED ANALYSIS · SCREEN B",
                className="oi-indicator-group-title",
            ),
            html.Div(
                [
                    html.Strong("Independent charts."),
                    " They are not overlaid on or used to modify the candle reading.",
                ],
                className="oi-analysis-only-note",
            ),
            checklist,
        ],
    )


def _indicator_panel() -> html.Div:
    return html.Div(
        className="oi-indicator-panel",
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
                        "FUNDAMENTAL TECHNICAL ANALYSIS",
                        href=localized_href(f"{ROUTE}/analysis"),
                        className="oi-analysis-button",
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
                        className="oi-analysis-button",
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
            html.Div(
                [
                    "INDICATORS ",
                    html.Span("(Select to display)"),
                ],
                className="oi-selector-heading",
            ),
            html.Div(
                [
                    html.Span("i", className="oi-selector-help-mark"),
                    html.Span("Select indicators and open the analysis screen."),
                ],
                className="oi-selector-help",
            ),
            _selector_group(
                "TREND",
                _checklist("oi-trend-selectors", TREND_OPTIONS, DEFAULT_TREND),
            ),
            _selector_group(
                "BANDS & CHANNELS · ON OPEN INTEREST",
                _checklist("oi-band-selectors", BAND_OPTIONS, DEFAULT_BANDS),
            ),
        ],
    )


def _analysis_indicator_controls(selection: Any) -> html.Div:
    payload = resolve_persisted_selection(selection, _default_selection_payload)
    return html.Div(
        className="screen-b-selector oi-analysis-controls",
        children=[
            html.Div("INDICATORS · SCREEN B", className="screen-b-selector-title oi-summary-title"),
            _selector_group("PARTICIPATION DYNAMICS", _checklist("oi-derived-selectors", DERIVED_ANALYSIS_OPTIONS, list(payload.get("derived_analysis", [])))),
            _selector_group("PRICE × PARTICIPATION", _checklist("oi-momentum-selectors", MOMENTUM_OPTIONS, list(payload.get("momentum", [])))),
            _selector_group("LEVERAGE / REGIME CHANGE", _checklist("oi-volatility-selectors", VOLATILITY_OPTIONS, list(payload.get("volatility", [])))),
            _selector_group("OPEN INTEREST", _checklist("oi-native-selectors", OPEN_INTEREST_OPTIONS, list(payload.get("open_interest", [])))),
        ],
    )


# -----------------------------------------------------------------------------
# JSON selection helpers
# -----------------------------------------------------------------------------


def _selected_ohlcv(
    contract: dict[str, Any],
    market: str | None,
    timeframe: str | None,
) -> tuple[dict[str, Any], str, str]:
    charts = _safe_dict(contract.get("charts"))
    ohlcv = _safe_dict(charts.get("open_interest_candlestick"))

    selected_market = market or str(ohlcv.get("selected_market") or "all_exchanges")
    selected_timeframe = timeframe or str(ohlcv.get("selected_timeframe") or "15m")

    markets = _safe_dict(ohlcv.get("markets"))
    market_block = _safe_dict(markets.get(selected_market))

    if not market_block:
        selected_market = str(ohlcv.get("selected_market") or next(iter(markets), "all_exchanges"))
        market_block = _safe_dict(markets.get(selected_market))

    timeframes = _safe_dict(market_block.get("timeframes"))
    timeframe_block = _safe_dict(timeframes.get(selected_timeframe))

    if not timeframe_block:
        selected_timeframe = str(ohlcv.get("selected_timeframe") or next(iter(timeframes), "15m"))
        timeframe_block = _safe_dict(timeframes.get(selected_timeframe))

    return timeframe_block, selected_market, selected_timeframe


def _standard_indicator_block(
    contract: dict[str, Any],
    indicator_id: str,
    market: str,
    timeframe: str,
) -> dict[str, Any]:
    charts = _safe_dict(contract.get("charts"))
    chart = _safe_dict(charts.get(indicator_id))
    markets = _safe_dict(chart.get("markets"))
    market_block = _safe_dict(markets.get(market))
    return _safe_dict(market_block.get(timeframe))


def _wasserstein_block(
    contract: dict[str, Any],
    market: str,
    timeframe: str,
) -> dict[str, Any]:
    charts = _safe_dict(contract.get("charts"))
    ohlcv = _safe_dict(charts.get("open_interest_candlestick"))
    analysis = _safe_dict(ohlcv.get("technical_fundamental_analysis"))
    identity = _safe_dict(analysis.get("identity"))

    packaged_market = identity.get("market")
    packaged_timeframe = identity.get("timeframe")

    if packaged_market not in {None, market} or packaged_timeframe not in {None, timeframe}:
        return {}

    panels = _safe_dict(analysis.get("panels"))
    return _safe_dict(panels.get("wasserstein_distance"))


def _points_from_panel(panel: dict[str, Any]) -> tuple[list[Any], dict[str, list[Any]]]:
    raw_series = _safe_dict(panel.get("series"))
    result: dict[str, list[Any]] = {}
    timestamps: list[Any] = []

    for series_name, points in raw_series.items():
        if not isinstance(points, list):
            continue

        valid_points = [point for point in points if isinstance(point, dict)]
        if not valid_points:
            continue

        if not timestamps:
            timestamps = [point.get("timestamp") for point in valid_points]
        result[str(series_name)] = [point.get("value") for point in valid_points]

    return timestamps, result


def _timestamp_key(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError, OverflowError):
        return None


def _cross_selection_id(series_id: Any) -> str | None:
    """Map a contract series path to its Screen A selector id."""

    value = str(series_id or "").strip()

    if not value:
        return None

    if value.startswith("regression_channel."):
        return "regression_channel"

    if value.startswith("linear_regression_channel."):
        return "regression_channel"

    if value.startswith("bollinger_bands."):
        return "bollinger_bands"

    return value


def _event_selection_requirements(event: dict[str, Any]) -> set[str]:
    """Resolve the lines that must be visible for one contractual event."""

    explicit = {
        str(item)
        for item in _safe_list(event.get("selection_requirements"))
        if str(item)
    }

    if explicit:
        return explicit

    calculation = _safe_dict(event.get("calculation"))
    inferred = {
        selection_id
        for selection_id in (
            _cross_selection_id(calculation.get("first_series")),
            _cross_selection_id(calculation.get("second_series")),
        )
        if selection_id
    }

    if inferred:
        return inferred

    # OI cross events are already classified in the contract and include an
    # explicit event_id/marker, but some omit calculation details. Infer only
    # the participating overlay ids from that event_id; never calculate a cross.
    event_id = str(event.get("event_id") or "")
    for separator in ("_above_", "_below_"):
        if separator in event_id:
            first_series, second_series = event_id.split(separator, 1)
            return {
                selection_id
                for selection_id in (
                    _cross_selection_id(first_series),
                    _cross_selection_id(second_series),
                )
                if selection_id
            }

    return set()


def _event_importance_score(event: dict[str, Any]) -> float:
    """Read the precomputed contractual importance score."""

    importance = _safe_dict(event.get("importance"))
    value = importance.get("score")

    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _event_cluster_id(event: dict[str, Any]) -> str:
    """Read the contractual collision cluster for Screen A."""

    display = _safe_dict(event.get("display"))
    screen_a = _safe_dict(display.get("screen_a"))
    cluster_id = screen_a.get("cluster_id")

    if cluster_id:
        return str(cluster_id)

    # Backward-compatible fallback: do not merge unrelated legacy events.
    return str(event.get("event_uid") or event.get("event_id") or id(event))


def _event_cluster_rank(event: dict[str, Any]) -> int:
    display = _safe_dict(event.get("display"))
    screen_a = _safe_dict(display.get("screen_a"))

    try:
        return int(screen_a.get("rank_in_cluster"))
    except (TypeError, ValueError):
        return 10**9


def _select_primary_crosses(
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Keep the most important eligible arrow in each contractual cluster.

    Eligibility is resolved before this function, so when the globally
    strongest pair is not selected, the highest-ranked selected pair becomes
    visible automatically.
    """

    grouped: dict[str, list[dict[str, Any]]] = {}

    for event in events:
        grouped.setdefault(_event_cluster_id(event), []).append(event)

    selected_events: list[dict[str, Any]] = []

    for cluster_events in grouped.values():
        best_event = max(
            cluster_events,
            key=lambda event: (
                _event_importance_score(event),
                -_event_cluster_rank(event),
                str(event.get("event_id") or ""),
            ),
        )
        selected_events.append(best_event)

    selected_events.sort(
        key=lambda item: (
            _timestamp_key(item.get("timestamp")) or 0,
            str(item.get("signal") or ""),
            -_event_importance_score(item),
        )
    )
    return selected_events


def _screen_a_cross_events(
    contract: dict[str, Any],
    market: str,
    timeframe: str,
    selected: set[str],
) -> list[dict[str, Any]]:
    """Read and prioritize Screen A crosses already packaged in the JSON."""

    events = _safe_dict(contract.get("events"))
    by_id = _safe_dict(events.get("by_id"))
    ordered_ids = _safe_list(events.get("technical_cross_ids"))

    if ordered_ids:
        candidates = [
            by_id.get(str(event_uid))
            for event_uid in ordered_ids
        ]
    else:
        candidates = list(by_id.values())

    eligible: list[dict[str, Any]] = []

    for raw_event in candidates:
        event = _safe_dict(raw_event)

        if event.get("event_type") != "technical_cross":
            continue

        event_group = str(event.get("event_group") or "")
        requirements = _event_selection_requirements(event)

        # Oscillator crosses belong to Screen B.
        if event_group:
            if event_group not in SCREEN_A_CROSS_GROUPS:
                continue
        elif not requirements or not requirements.issubset(PRICE_OVERLAYS):
            continue

        if not requirements or not requirements.issubset(PRICE_OVERLAYS):
            continue

        # All participating overlays must be selected.
        if not requirements.issubset(selected):
            continue

        source = _safe_dict(event.get("source"))

        if source.get("market") not in {None, market}:
            continue

        if source.get("timeframe") not in {None, timeframe}:
            continue

        if _timestamp_key(event.get("timestamp")) is None:
            continue

        eligible.append(event)

    return _select_primary_crosses(eligible)


# -----------------------------------------------------------------------------
# Interactive Plotly figure
# -----------------------------------------------------------------------------


def _add_aligned_line(
    fig: go.Figure,
    x: list[datetime | None],
    values: Any,
    *,
    name: str,
    row: int,
    color: str,
    dash: str = "solid",
    width: float = 1.35,
    fill: str | None = None,
    fillcolor: str | None = None,
    showlegend: bool = True,
) -> None:
    if not isinstance(values, list) or not values:
        return

    size = min(len(x), len(values))
    if size <= 0:
        return

    fig.add_trace(
        go.Scatter(
            x=x[-size:],
            y=values[-size:],
            mode="lines",
            name=name,
            line={"color": color, "width": width, "dash": dash},
            fill=fill,
            fillcolor=fillcolor,
            connectgaps=False,
            showlegend=showlegend,
            hovertemplate=f"{name}: %{{y:.4f}}<extra></extra>",
        ),
        row=row,
        col=1,
    )


def _add_screen_a_cross_markers(
    fig: go.Figure,
    contract: dict[str, Any],
    records: list[dict[str, Any]],
    selected: set[str],
    market: str,
    timeframe: str,
) -> None:
    """Draw exact contractual arrows only inside the visible OI data window.

    Processing remains responsible for producing coherent events. This HMI
    guard prevents stale/out-of-window events from being drawn over periods for
    which the currently displayed OI OHLC series has no observations.
    """
    visible_timestamps = [
        _timestamp_key(record.get("timestamp"))
        for record in records
        if isinstance(record, dict)
    ]
    visible_timestamps = [value for value in visible_timestamps if value is not None]
    if not visible_timestamps:
        return

    first_visible = min(visible_timestamps)
    last_visible = max(visible_timestamps)

    for event in _screen_a_cross_events(contract, market, timeframe, selected):
        signal = str(event.get("signal") or "").lower()
        timestamp_exact = event.get("event_timestamp_exact")
        value_exact = event.get("event_value_exact")
        display = _safe_dict(event.get("display"))
        anchor_price = display.get("anchor_price")

        event_timestamp = _timestamp_key(timestamp_exact)
        if signal not in {"bullish", "bearish"} or event_timestamp is None:
            continue
        if not (first_visible <= event_timestamp <= last_visible):
            continue
        if not isinstance(value_exact, (int, float)):
            continue

        y_value = (
            float(anchor_price)
            if isinstance(anchor_price, (int, float))
            else float(value_exact)
        )
        fig.add_annotation(
            x=_utc_datetime(timestamp_exact),
            y=y_value,
            text="",
            showarrow=True,
            arrowhead=2,
            arrowsize=1.0,
            arrowwidth=1.55,
            arrowcolor="#00e59b" if signal == "bullish" else "#ff4d6d",
            ax=0,
            ay=18 if signal == "bullish" else -18,
            xref="x",
            yref="y",
            row=1,
            col=1,
        )


def _add_price_overlays(
    fig: go.Figure,
    records_x: list[datetime | None],
    timeframe_block: dict[str, Any],
    selected: set[str],
    unavailable: list[str],
) -> None:
    overlays = _safe_dict(timeframe_block.get("overlays"))
    moving = _safe_dict(overlays.get("moving_averages"))
    moving_series = _safe_dict(moving.get("series"))

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

        values = moving_series.get(indicator_id)
        if not isinstance(values, list):
            unavailable.append(indicator_id.upper())
            continue

        _add_aligned_line(
            fig,
            records_x,
            values,
            name=indicator_id.replace("_", " ").upper(),
            row=1,
            color=_line_color(indicator_id),
        )

    if "bollinger_bands" in selected:
        bollinger = _safe_dict(overlays.get("bollinger_bands"))
        bb_series = _safe_dict(bollinger.get("series"))

        upper = bb_series.get("upper")
        middle = bb_series.get("middle")
        lower = bb_series.get("lower")

        if not any(isinstance(values, list) for values in (upper, middle, lower)):
            unavailable.append("BOLLINGER BANDS")
        else:
            _add_aligned_line(
                fig,
                records_x,
                upper,
                name="BB UPPER",
                row=1,
                color="#2f80ff",
                width=1.0,
            )
            _add_aligned_line(
                fig,
                records_x,
                lower,
                name="BB LOWER",
                row=1,
                color="#2f80ff",
                width=1.0,
                fill="tonexty",
                fillcolor="rgba(47,128,255,0.08)",
            )
            _add_aligned_line(
                fig,
                records_x,
                middle,
                name="BB MIDDLE",
                row=1,
                color="#8aa7bd",
                width=0.9,
                dash="dot",
            )

    if "regression_channel" in selected:
        regression = _safe_dict(overlays.get("regression_channel"))
        if not regression:
            regression = _safe_dict(overlays.get("linear_regression_channel"))

        regression_series = _safe_dict(regression.get("series"))
        if not regression_series:
            unavailable.append("REGRESSION CHANNEL")
        else:
            for name, color in (
                ("upper", "#f2994a"),
                ("middle", "#f2c94c"),
                ("lower", "#f2994a"),
            ):
                _add_aligned_line(
                    fig,
                    records_x,
                    regression_series.get(name),
                    name=f"REGRESSION {name.upper()}",
                    row=1,
                    color=color,
                    dash="dot" if name != "middle" else "solid",
                    width=1.0,
                )


def _indicator_series(
    contract: dict[str, Any],
    indicator_id: str,
    market: str,
    timeframe: str,
) -> tuple[list[Any], dict[str, list[Any]]]:
    if indicator_id == "wasserstein_distance":
        panel = _wasserstein_block(contract, market, timeframe)
        return _points_from_panel(panel)

    block = _standard_indicator_block(contract, indicator_id, market, timeframe)
    timestamps = _safe_list(block.get("timestamps"))
    series = _safe_dict(block.get("series"))
    normalized = {
        str(name): values
        for name, values in series.items()
        if isinstance(values, list)
    }
    return timestamps, normalized


def _add_reference_lines(fig: go.Figure, indicator_id: str, row: int) -> None:
    levels: tuple[tuple[float, str], ...] = ()

    if indicator_id == "rsi":
        levels = ((70, "70"), (30, "30"))
    elif indicator_id == "stochastic":
        levels = ((80, "80"), (20, "20"))
    elif indicator_id == "tsi":
        levels = ((25, "+25"), (0, "0"), (-25, "-25"))
    elif indicator_id == "williams_r":
        levels = ((-20, "-20"), (-80, "-80"))

    for value, label in levels:
        fig.add_hline(
            y=value,
            row=row,
            col=1,
            line_color="rgba(140,155,168,0.45)",
            line_dash="dot",
            line_width=1,
            annotation_text=label,
            annotation_font={"size": 8, "color": "#7f91a0"},
            annotation_position="right",
        )


def _add_oscillator(
    fig: go.Figure,
    contract: dict[str, Any],
    indicator_id: str,
    market: str,
    timeframe: str,
    row: int,
    unavailable: list[str],
) -> None:
    timestamps, series = _indicator_series(contract, indicator_id, market, timeframe)

    if not timestamps or not series:
        unavailable.append(INDICATOR_TITLES.get(indicator_id, indicator_id.upper()))
        return

    x = [_utc_datetime(timestamp) for timestamp in timestamps]

    for index, (series_name, values) in enumerate(series.items()):
        size = min(len(x), len(values))
        if size <= 0:
            continue

        trace_name = SERIES_LABELS.get(series_name, series_name.replace("_", " ").upper())
        color = _line_color(series_name if series_name in TRACE_COLORS else indicator_id, index)

        if indicator_id == "macd" and series_name == "histogram":
            fig.add_trace(
                go.Bar(
                    x=x[-size:],
                    y=values[-size:],
                    name="MACD HISTOGRAM",
                    marker_color=[
                        "#00c78c" if value is not None and value >= 0 else "#ff4d6d"
                        for value in values[-size:]
                    ],
                    opacity=0.65,
                    hovertemplate="MACD HISTOGRAM: %{y:.5f}<extra></extra>",
                ),
                row=row,
                col=1,
            )
        else:
            fig.add_trace(
                go.Scatter(
                    x=x[-size:],
                    y=values[-size:],
                    mode="lines",
                    name=trace_name,
                    line={"color": color, "width": 1.25},
                    connectgaps=False,
                    hovertemplate=f"{trace_name}: %{{y:.5f}}<extra></extra>",
                ),
                row=row,
                col=1,
            )

    _add_reference_lines(fig, indicator_id, row)

    # Oscillator reference lines are anchored to the full indicator domain,
    # never to the last scalar value or to the sum of the visible series.
    if indicator_id in {"rsi", "stochastic"}:
        fig.update_yaxes(range=[0, 100], row=row, col=1)
    elif indicator_id == "tsi":
        fig.update_yaxes(range=[-100, 100], row=row, col=1)


def _empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        height=556,
        paper_bgcolor="#06111d",
        plot_bgcolor="#06111d",
        font={"color": "#c9d5de"},
        margin={"l": 45, "r": 20, "t": 45, "b": 35},
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[
            {
                "text": message,
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.5,
                "showarrow": False,
                "font": {"size": 12, "color": "#ff4d6d"},
            }
        ],
    )
    return fig


def build_open_interest_figure(
    contract: dict[str, Any],
    market: str | None,
    timeframe: str | None,
    selected_indicators: Iterable[str],
) -> go.Figure:
    timeframe_block, selected_market, selected_timeframe = _selected_ohlcv(contract, market, timeframe)
    raw_records = _safe_list(timeframe_block.get("records"))
    records = [record for record in raw_records if isinstance(record, dict)]

    if not records:
        return _empty_figure("OPEN INTEREST OHLC NO DISPONIBLE EN EL JSON")

    selected = set(selected_indicators)
    fig = make_subplots(
        rows=1,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.0,
        row_heights=[1.0],
        subplot_titles=None,
    )

    x = [_utc_datetime(record.get("timestamp")) for record in records]
    x_padding = (x[-1] - x[-2]) / 2 if len(x) > 1 else None
    open_values = [record.get("open") for record in records]
    high_values = [record.get("high") for record in records]
    low_values = [record.get("low") for record in records]
    close_values = [record.get("close") for record in records]

    fig.add_trace(
        go.Candlestick(
            x=x,
            open=open_values,
            high=high_values,
            low=low_values,
            close=close_values,
            name="OPEN INTEREST OHLC",
            increasing_line_color="#00c78c",
            decreasing_line_color="#ff4d6d",
            increasing_fillcolor="#00c78c",
            decreasing_fillcolor="#ff4d6d",
            whiskerwidth=0.35,
        ),
        row=1,
        col=1,
    )

    missing: list[str] = []
    _add_price_overlays(
        fig,
        x,
        timeframe_block,
        selected & PRICE_OVERLAYS,
        missing,
    )
    _add_screen_a_cross_markers(
        fig,
        contract,
        records,
        selected,
        selected_market,
        selected_timeframe,
    )

    fig.update_layout(
        height=556,
        paper_bgcolor="#06111d",
        plot_bgcolor="#06111d",
        font={"family": "Arial, sans-serif", "size": 9, "color": "#aebdca"},
        margin={"l": 48, "r": 18, "t": 34, "b": 52},
        hovermode="x unified",
        dragmode="pan",
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.015,
            "xanchor": "left",
            "x": 0,
            "font": {"size": 8},
            "bgcolor": "rgba(0,0,0,0)",
        },
        uirevision=f"open-interest-{selected_market}-{selected_timeframe}",
        transition={"duration": 0},
    )
    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        rangeslider_visible=False,
        linecolor="#173247",
        tickfont={"size": 8, "color": "#9eb1bf"},
        showticklabels=True,
        ticks="outside",
        ticklen=4,
        nticks=7,
        tickformat="%b %d<br>%H:%M",
        automargin=True,
        range=[x[0] - x_padding, x[-1] + x_padding] if x_padding is not None else None,
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="rgba(67,91,108,.24)",
        zeroline=False,
        linecolor="#173247",
        tickfont={"size": 8, "color": "#8295a2"},
        title_text="USD",
    )

    if missing:
        fig.add_annotation(
            xref="paper",
            yref="paper",
            x=0.995,
            y=0.01,
            xanchor="right",
            yanchor="bottom",
            text="SIN SERIE: " + ", ".join(missing),
            showarrow=False,
            font={"size": 7, "color": "#ff9f00"},
            bgcolor="rgba(6,17,29,.82)",
            bordercolor="#173247",
            borderwidth=1,
        )

    return fig


# -----------------------------------------------------------------------------
# Screen B helpers
# -----------------------------------------------------------------------------


SELECTION_STORE_ID = "oi-selection-store"
ANALYSIS_CONTENT_ID = "oi-analysis-content"

ANALYSIS_GRAPH_ORDER = (
    "oi_dynamics",
    "oi_zscore_percentile",
    "price_oi_regime",
    "price_oi_divergence",
    "funding_oi_crowding",
    "wasserstein_distance",
)

ANALYSIS_CARD_NUMBERS = {
    "oi_dynamics": 1,
    "oi_zscore_percentile": 2,
    "price_oi_regime": 3,
    "price_oi_divergence": 4,
    "funding_oi_crowding": 5,
    "wasserstein_distance": 6,
}

SUMMARY_SECTIONS = (
    ("PARTICIPATION DYNAMICS", "#22c7e8", ("oi_dynamics", "oi_zscore_percentile")),
    ("PRICE × PARTICIPATION", "#00e59b", ("price_oi_regime", "price_oi_divergence")),
    ("LEVERAGE / CROWDING", "#ffab00", ("funding_oi_crowding",)),
    ("REGIME CHANGE", "#a879ff", ("wasserstein_distance",)),
)

SUMMARY_LABELS = {
    "oi_dynamics": "OI ROC / SLOPE / ACCEL.",
    "oi_zscore_percentile": "OI Z-SCORE / PERCENTILE",
    "price_oi_regime": "PRICE × OI REGIME",
    "price_oi_divergence": "PRICE ↔ OI DIVERGENCE",
    "funding_oi_crowding": "FUNDING × OI CROWDING",
    "wasserstein_distance": "WASSERSTEIN / REGIME SHIFT",
}

ANALYSIS_LINE_COLORS = {
    "oi_dynamics": "#22c7e8",
    "oi_roc": "#22c7e8",
    "oi_slope_pct": "#00e59b",
    "oi_acceleration_pct": "#f2c94c",
    "oi_zscore_percentile": "#22c7e8",
    "oi_zscore": "#22c7e8",
    "oi_percentile": "#a879ff",
    "price_oi_regime": "#00e59b",
    "regime_score": "#00e59b",
    "price_oi_divergence": "#ff4d6d",
    "price_return_z": "#2f80ff",
    "oi_change_z": "#f2c94c",
    "divergence_score": "#ff4d6d",
    "funding_oi_crowding": "#ff8a3d",
    "funding_zscore": "#a879ff",
    "crowding_score": "#ff8a3d",
    "wasserstein_distance": "#3c94ed",
    "value": "#3c94ed",
}


ANALYSIS_CROSS_EVENT_IDS: dict[str, set[str]] = {}
ANALYSIS_CROSS_SERIES: dict[str, tuple[str, str]] = {}



def _default_selection_payload() -> dict[str, list[str]]:
    return {
        "trend": list(DEFAULT_TREND),
        "bands": list(DEFAULT_BANDS),
        "derived_analysis": list(DEFAULT_DERIVED_ANALYSIS),
        "momentum": list(DEFAULT_MOMENTUM),
        "volatility": list(DEFAULT_VOLATILITY),
        "open_interest": list(DEFAULT_OPEN_INTEREST),
    }


def _option_ids(options: list[dict[str, str]]) -> set[str]:
    return {str(option["value"]) for option in options}


def _selection_payload(
    trend: list[str] | None,
    bands: list[str] | None,
    derived_analysis: list[str] | None,
    momentum: list[str] | None,
    volatility: list[str] | None,
    open_interest: list[str] | None,
) -> dict[str, list[str]]:
    raw_trend = _unique(trend or [])
    raw_bands = _unique(bands or [])
    raw_derived = _unique(derived_analysis or [])

    migrated_derived = [
        *raw_derived,
        *(["adx"] if "adx" in raw_trend else []),
        *(["bollinger_band_width"] if "bollinger_band_width" in raw_bands else []),
    ]

    return {
        "trend": [item for item in raw_trend if item in _option_ids(TREND_OPTIONS)],
        "bands": [item for item in raw_bands if item in _option_ids(BAND_OPTIONS)],
        "derived_analysis": [
            item for item in _unique(migrated_derived)
            if item in _option_ids(DERIVED_ANALYSIS_OPTIONS)
        ],
        "momentum": [
            item for item in _unique(momentum or [])
            if item in _option_ids(MOMENTUM_OPTIONS)
        ],
        "volatility": [
            item for item in _unique(volatility or [])
            if item in _option_ids(VOLATILITY_OPTIONS)
        ],
        "open_interest": [
            item for item in _unique(open_interest or [])
            if item in _option_ids(OPEN_INTEREST_OPTIONS)
        ],
    }


def _selected_analysis_ids(selection: Any) -> list[str]:
    payload = _safe_dict(selection)
    chosen = set(
        _safe_list(payload.get("derived_analysis"))
        + _safe_list(payload.get("momentum"))
        + _safe_list(payload.get("volatility"))
        + _safe_list(payload.get("open_interest"))
    )
    return [
        indicator_id
        for indicator_id in ANALYSIS_GRAPH_ORDER
        if indicator_id in chosen
    ]


def _analysis_panel(
    contract: dict[str, Any],
    indicator_id: str,
    market: str,
    timeframe: str,
) -> dict[str, Any]:
    """Return Screen B data aligned to the contractual display window.

    Standard indicator series and their technical-cross events share the
    same 120-record window. Prefer that block so every arrow is distributed
    over the visible chart instead of being compressed at the far right of
    a longer packaged history.
    """

    block = _standard_indicator_block(
        contract,
        indicator_id,
        market,
        timeframe,
    )

    if block:
        current_raw = _safe_dict(block.get("current"))
        primary = current_raw.get(indicator_id)

        if primary is None and current_raw:
            primary = next(iter(current_raw.values()), None)

        return {
            "indicator_id": indicator_id,
            "title": INDICATOR_TITLES.get(
                indicator_id,
                indicator_id.upper(),
            ),
            "status": (
                "available"
                if _safe_dict(block.get("series"))
                else "unavailable"
            ),
            "current": {
                "value": primary,
                "secondary_values": {
                    key: value
                    for key, value in current_raw.items()
                    if key != indicator_id
                },
            },
            "reference_lines": _safe_list(
                block.get("reference_lines")
            ),
            "series": {
                key: [
                    {
                        "timestamp": timestamp,
                        "value": value,
                    }
                    for timestamp, value in zip(
                        _safe_list(block.get("timestamps")),
                        values,
                    )
                ]
                for key, values
                in _safe_dict(block.get("series")).items()
                if isinstance(values, list)
            },
        }

    # Special indicators without a standard market/timeframe chart retain
    # the packaged analysis panel as fallback.
    charts = _safe_dict(contract.get("charts"))
    ohlcv = _safe_dict(charts.get("open_interest_ohlc"))
    analysis = _safe_dict(
        ohlcv.get("technical_fundamental_analysis")
    )
    identity = _safe_dict(analysis.get("identity"))

    if (
        identity.get("market") in {None, market}
        and identity.get("timeframe") in {None, timeframe}
    ):
        return _safe_dict(
            _safe_dict(analysis.get("panels")).get(indicator_id)
        )

    return {}


def _analysis_series(panel: dict[str, Any]) -> tuple[list[datetime | None], dict[str, list[Any]]]:
    timestamps, raw_series = _points_from_panel(panel)
    return [_utc_datetime(timestamp) for timestamp in timestamps], raw_series


def _table_indicator_rows(
    contract: dict[str, Any],
    market: str,
    timeframe: str,
) -> dict[str, dict[str, Any]]:
    tables = _safe_dict(contract.get("tables"))
    package = _safe_dict(_safe_dict(tables.get("indicators_metrics")).get("indicator_package"))
    markets = _safe_dict(package.get("markets"))
    market_block = _safe_dict(markets.get(market))
    rows = _safe_list(market_block.get(timeframe))

    if not rows:
        rows = _safe_list(package.get("rows"))

    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict) and row.get("metric_id"):
            result[str(row["metric_id"])] = row
    return result


def _panel_current_value(panel: dict[str, Any]) -> Any:
    return _safe_dict(panel.get("current")).get("value")


def _format_analysis_number(value: Any) -> str:
    if value is None:
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)

    absolute = abs(number)
    if absolute >= 1000:
        return f"{number:,.0f}"
    if absolute >= 100:
        return f"{number:.2f}"
    if absolute >= 1:
        return f"{number:.2f}"
    return f"{number:.3f}"


def _signal_descriptor(row: dict[str, Any], panel: dict[str, Any], indicator_id: str) -> tuple[str, str]:
    signal = str(row.get("signal") or "").lower()
    state = str(row.get("state") or row.get("display_signal") or "").lower()

    native_states = {
        "expanding": ("EXPANDING", "#00e59b"),
        "contracting": ("CONTRACTING", "#ffab00"),
        "bullish_expansion": ("BULLISH EXPANSION", "#00e59b"),
        "bearish_expansion": ("BEARISH EXPANSION", "#ff4d6d"),
        "short_covering": ("SHORT COVERING", "#2f80ff"),
        "long_liquidation": ("LONG DELEVERAGING", "#ff8a3d"),
        "long_crowding": ("LONG CROWDING", "#ff8a3d"),
        "short_crowding": ("SHORT CROWDING", "#a879ff"),
        "divergence": ("DIVERGENCIA", "#ff4d6d"),
        "confirmation": ("CONFIRMATION", "#00e59b"),
        "regime_shift": ("REGIME SHIFT", "#ff4d6d"),
        "normal": ("NORMAL", "#22c7e8"),
    }
    if indicator_id in ANALYSIS_GRAPH_ORDER and state in native_states:
        return native_states[state]

    if indicator_id == "adx" and state in {"strong", "very_strong", "developing"}:
        return "TREND", "#20d05c"
    if signal in {"bullish", "positive", "buy", "buying"}:
        return "ALCISTA", "#20d05c"
    if signal in {"bearish", "negative", "sell", "selling"}:
        return "BAJISTA", "#ff3d55"
    if state in {"low", "very_low", "compressed"}:
        return "BAJA", "#20d05c"
    if state in {"high", "extreme", "elevated"}:
        return "NEUTRAL", "#ffab00"
    if row:
        label = str(row.get("display_signal") or row.get("state") or row.get("signal") or "NEUTRAL")
        return label.upper(), "#ffab00"

    status = str(panel.get("status") or "unavailable").lower()
    if status in {"available", "ok", "partial"}:
        return "DISPONIBLE", "#22c7e8"
    return "—", "#6f7c84"


def _strength_count(row: dict[str, Any], panel: dict[str, Any]) -> int:
    confidence = row.get("confidence")
    try:
        value = float(confidence)
        return max(1, min(5, int(value * 5 + 0.999999)))
    except (TypeError, ValueError):
        return 3 if str(panel.get("status") or "").lower() in {"available", "ok", "partial"} else 0


def _strength_dots(count: int, color: str) -> html.Div:
    return html.Div(
        className="oi-strength-dots",
        children=[
            html.Span(
                className="oi-strength-dot",
                style={"background": color if index < count else "#59636b"},
            )
            for index in range(5)
        ],
    )


def _analysis_reference_lines(
    contract: dict[str, Any],
    indicator_id: str,
    panel: dict[str, Any],
) -> list[dict[str, Any]]:
    """Read reference levels from the visual contract."""

    panel_lines = [
        item
        for item in _safe_list(panel.get("reference_lines"))
        if isinstance(item, dict) and item.get("value") is not None
    ]

    if panel_lines:
        return panel_lines

    charts = _safe_dict(contract.get("charts"))
    indicator_chart = _safe_dict(charts.get(indicator_id))

    return [
        item
        for item in _safe_list(indicator_chart.get("thresholds"))
        if isinstance(item, dict) and item.get("value") is not None
    ]


def _analysis_cross_events(
    contract: dict[str, Any],
    indicator_id: str,
    market: str,
    timeframe: str,
) -> list[dict[str, Any]]:
    """Read the indicator cross events already classified in the JSON."""

    allowed_ids = ANALYSIS_CROSS_EVENT_IDS.get(indicator_id)

    if not allowed_ids:
        return []

    events = _safe_dict(contract.get("events"))
    by_id = _safe_dict(events.get("by_id"))
    ordered_ids = _safe_list(events.get("technical_cross_ids"))

    if ordered_ids:
        candidates = [
            by_id.get(str(event_uid))
            for event_uid in ordered_ids
        ]
    else:
        candidates = list(by_id.values())

    result: list[dict[str, Any]] = []

    for raw_event in candidates:
        event = _safe_dict(raw_event)

        if event.get("event_type") != "technical_cross":
            continue

        if str(event.get("event_id") or "") not in allowed_ids:
            continue

        source = _safe_dict(event.get("source"))

        if source.get("market") not in {None, market}:
            continue

        if source.get("timeframe") not in {None, timeframe}:
            continue

        if _timestamp_key(event.get("timestamp")) is None:
            continue

        result.append(event)

    result.sort(
        key=lambda event: (
            _timestamp_key(event.get("timestamp")) or 0,
            str(event.get("event_id") or ""),
        )
    )
    return result


def _add_analysis_cross_markers(
    fig: go.Figure,
    contract: dict[str, Any],
    indicator_id: str,
    market: str,
    timeframe: str,
    x: list[datetime | None],
    series: dict[str, list[Any]],
) -> None:
    """Draw buy/sell arrows at contractual indicator cross events."""

    series_pair = ANALYSIS_CROSS_SERIES.get(indicator_id)

    if not series_pair:
        return

    first_name, second_name = series_pair
    first_values = _safe_list(series.get(first_name))
    second_values = _safe_list(series.get(second_name))
    size = min(len(x), len(first_values), len(second_values))

    if size <= 0:
        return

    current_x = x[-size:]
    current_first = first_values[-size:]
    current_second = second_values[-size:]

    point_by_timestamp: dict[int, tuple[datetime, float]] = {}
    numeric_values: list[float] = []

    for current_time, first_value, second_value in zip(
        current_x,
        current_first,
        current_second,
    ):
        if current_time is None:
            continue

        if not isinstance(first_value, (int, float)):
            continue

        if not isinstance(second_value, (int, float)):
            continue

        timestamp = int(current_time.timestamp())
        crossing_value = (
            float(first_value) + float(second_value)
        ) / 2.0

        point_by_timestamp[timestamp] = (
            current_time,
            crossing_value,
        )
        numeric_values.extend(
            [
                float(first_value),
                float(second_value),
            ]
        )

    if not point_by_timestamp:
        return

    visible_span = (
        max(numeric_values) - min(numeric_values)
        if numeric_values
        else 0.0
    )
    marker_offset = max(visible_span * 0.035, 1e-9)

    groups: dict[str, dict[str, list[Any]]] = {
        "bullish": {
            "x": [],
            "y": [],
            "customdata": [],
        },
        "bearish": {
            "x": [],
            "y": [],
            "customdata": [],
        },
    }

    for event in _analysis_cross_events(
        contract,
        indicator_id,
        market,
        timeframe,
    ):
        timestamp = _timestamp_key(event.get("timestamp"))

        if timestamp is None or timestamp not in point_by_timestamp:
            continue

        current_time, crossing_value = point_by_timestamp[timestamp]
        signal = str(event.get("signal") or "").lower()

        if signal == "bullish":
            y_value = crossing_value - marker_offset
        elif signal == "bearish":
            y_value = crossing_value + marker_offset
        else:
            continue

        groups[signal]["x"].append(current_time)
        groups[signal]["y"].append(y_value)
        groups[signal]["customdata"].append(
            [
                str(
                    event.get("label")
                    or event.get("event_id")
                    or "Technical cross"
                ),
                str(event.get("event_id") or ""),
            ]
        )

    marker_specs = {
        "bullish": {
            "name": "BUY",
            "symbol": "arrow-up",
            "color": "#00e59b",
        },
        "bearish": {
            "name": "SELL",
            "symbol": "arrow-down",
            "color": "#ff4d6d",
        },
    }

    for signal, values in groups.items():
        if not values["x"]:
            continue

        specification = marker_specs[signal]

        fig.add_trace(
            go.Scatter(
                x=values["x"],
                y=values["y"],
                mode="markers",
                name=specification["name"],
                marker={
                    "symbol": specification["symbol"],
                    "size": 10,
                    "color": specification["color"],
                    "line": {
                        "width": 1,
                        "color": "#04111c",
                    },
                },
                customdata=values["customdata"],
                cliponaxis=False,
                showlegend=False,
                hovertemplate=(
                    "<b>%{customdata[0]}</b>"
                    "<br>Evento: %{customdata[1]}"
                    "<br>%{x|%Y-%m-%d %H:%M UTC}"
                    "<extra></extra>"
                ),
            )
        )


def _analysis_figure(
    contract: dict[str, Any],
    indicator_id: str,
    panel: dict[str, Any],
    market: str,
    timeframe: str,
) -> go.Figure:
    x, series = _analysis_series(panel)
    use_secondary_percentile_axis = indicator_id == "oi_zscore_percentile"
    fig = (
        make_subplots(specs=[[{"secondary_y": True}]])
        if use_secondary_percentile_axis
        else go.Figure()
    )

    for index, (series_name, values) in enumerate(series.items()):
        size = min(len(x), len(values))
        if size <= 0:
            continue

        current_x = x[-size:]
        current_y = values[-size:]

        if indicator_id == "macd" and series_name == "histogram":
            fig.add_trace(
                go.Bar(
                    x=current_x,
                    y=current_y,
                    name="HISTOGRAM",
                    marker_color=[
                        "#22c868" if value is not None and value >= 0 else "#ff4c43"
                        for value in current_y
                    ],
                    opacity=.82,
                    hovertemplate="HISTOGRAM: %{y:.5f}<extra></extra>",
                    showlegend=False,
                )
            )
            continue

        color_key = series_name if series_name in ANALYSIS_LINE_COLORS else indicator_id
        trace = go.Scatter(
            x=current_x,
            y=current_y,
            mode="lines",
            name=SERIES_LABELS.get(series_name, series_name.replace("_", " ").upper()),
            line={
                "color": ANALYSIS_LINE_COLORS.get(color_key, "#22c7e8"),
                "width": 1.25,
            },
            connectgaps=False,
            hovertemplate=f"{SERIES_LABELS.get(series_name, series_name.upper())}: %{{y:.5f}}<extra></extra>",
            showlegend=False,
        )
        if use_secondary_percentile_axis:
            fig.add_trace(trace, secondary_y=(series_name == "oi_percentile"))
        else:
            fig.add_trace(trace)

    for reference_line in _analysis_reference_lines(
        contract,
        indicator_id,
        panel,
    ):
        level = reference_line.get("value")
        role = str(reference_line.get("role") or "")

        try:
            numeric_level = float(level)
        except (TypeError, ValueError):
            continue

        line_color = (
            "rgba(255,77,109,.62)"
            if role == "overbought"
            else "rgba(0,229,155,.62)"
            if role == "oversold"
            else "rgba(140,155,168,.42)"
        )

        fig.add_hline(
            y=numeric_level,
            line_color=line_color,
            line_dash="dot",
            line_width=1,
        )

    _add_analysis_cross_markers(
        fig,
        contract,
        indicator_id,
        market,
        timeframe,
        x,
        series,
    )

    visible_x = [
        current_time
        for current_time in x
        if current_time is not None
    ]

    fig.update_layout(
        height=310,
        paper_bgcolor="#04111c",
        plot_bgcolor="#04111c",
        margin={"l": 30, "r": 5, "t": 6, "b": 18},
        font={"family": "Arial, sans-serif", "size": 7, "color": "#8fa0ab"},
        hovermode="x unified",
        bargap=.08,
        showlegend=False,
        uirevision=f"analysis-{indicator_id}-{market}-{timeframe}",
    )
    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        showticklabels=True,
        tickformat="%H:%M<br>%d/%m",
        tickfont={"size": 7, "color": "#83949f"},
        nticks=5,
        ticks="outside",
        ticklen=3,
        title={"text": "UTC", "font": {"size": 7, "color": "#718593"}, "standoff": 2},
        linecolor="#173247",
        fixedrange=True,
        **(
            {
                "range": [
                    visible_x[0],
                    visible_x[-1],
                ]
            }
            if visible_x
            else {}
        ),
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="rgba(67,91,108,.24)",
        zeroline=False,
        linecolor="#173247",
        tickfont={"size": 7, "color": "#83949f"},
        nticks=4,
        fixedrange=True,
    )
    if indicator_id == "oi_zscore_percentile":
        fig.update_yaxes(range=[0, 100], secondary_y=True, showgrid=False, nticks=5)
    if indicator_id == "price_oi_regime":
        fig.update_yaxes(
            tickmode="array",
            tickvals=[-2, -1, 0, 1, 2],
            ticktext=["BEAR EXP.", "LONG DELEV.", "NEUTRAL", "SHORT COVER", "BULL EXP."],
            range=[-2.4, 2.4],
        )
    for trace in fig.data:
        if trace.name and trace.type in {"scatter", "bar"}:
            trace.showlegend = True
    return apply_analysis_figure_layout(fig, height=220, right_margin=42)


def _analysis_value_rows(
    indicator_id: str,
    panel: dict[str, Any],
    row: dict[str, Any],
) -> list[html.Div]:
    current = _safe_dict(panel.get("current"))
    primary_value = current.get("value")
    secondary = _safe_dict(current.get("secondary_values"))
    signal_text, signal_color = _signal_descriptor(row, panel, indicator_id)

    values: list[tuple[str, Any, str]] = []
    if indicator_id == "oi_dynamics":
        values = [
            ("OI ROC %", primary_value, ANALYSIS_LINE_COLORS["oi_roc"]),
            ("SLOPE %", secondary.get("oi_slope_pct"), ANALYSIS_LINE_COLORS["oi_slope_pct"]),
            ("ACCEL %", secondary.get("oi_acceleration_pct"), ANALYSIS_LINE_COLORS["oi_acceleration_pct"]),
        ]
    elif indicator_id == "oi_zscore_percentile":
        values = [
            ("OI Z-SCORE", primary_value, ANALYSIS_LINE_COLORS["oi_zscore"]),
            ("PERCENTILE", secondary.get("oi_percentile"), ANALYSIS_LINE_COLORS["oi_percentile"]),
        ]
    elif indicator_id == "price_oi_regime":
        values = [
            ("REGIME SCORE", primary_value, ANALYSIS_LINE_COLORS["regime_score"]),
            ("STATE", secondary.get("regime_state"), "#e4edf4"),
        ]
    elif indicator_id == "price_oi_divergence":
        values = [
            ("DIVERGENCE", primary_value, ANALYSIS_LINE_COLORS["divergence_score"]),
            ("PRICE Z", secondary.get("price_return_z"), ANALYSIS_LINE_COLORS["price_return_z"]),
            ("OI Z", secondary.get("oi_change_z"), ANALYSIS_LINE_COLORS["oi_change_z"]),
        ]
    elif indicator_id == "funding_oi_crowding":
        values = [
            ("CROWDING", primary_value, ANALYSIS_LINE_COLORS["crowding_score"]),
            ("FUNDING Z", secondary.get("funding_zscore"), ANALYSIS_LINE_COLORS["funding_zscore"]),
            ("OI Z", secondary.get("oi_zscore"), ANALYSIS_LINE_COLORS["oi_zscore"]),
        ]
    else:
        values = [
            (SERIES_LABELS.get(indicator_id, indicator_id.upper()), primary_value, ANALYSIS_LINE_COLORS.get(indicator_id, "#22c7e8"))
        ]


    children: list[html.Div] = []
    for label, value, color in values:
        children.extend(
            [
                html.Div(label, className="oi-analysis-metric-label"),
                html.Div(
                    _format_analysis_number(value),
                    className="oi-analysis-metric-value",
                    style={"color": color},
                ),
            ]
        )

    children.extend(
        [
            html.Div("SIGNAL", className="oi-analysis-signal-label"),
            html.Div(
                signal_text,
                className="oi-analysis-signal-value",
                style={"color": signal_color},
            ),
        ]
    )
    return children


def _analysis_card(
    contract: dict[str, Any],
    indicator_id: str,
    market: str,
    timeframe: str,
    rows: dict[str, dict[str, Any]],
) -> html.Div:
    panel = _analysis_panel(contract, indicator_id, market, timeframe)
    row = rows.get(indicator_id, {})
    number = ANALYSIS_CARD_NUMBERS.get(indicator_id, 0)
    title = INDICATOR_TITLES.get(indicator_id, indicator_id.upper())

    return html.Div(
        className="screen-b-card oi-analysis-card",
        children=[
            html.Div(
                className="screen-b-card-title oi-analysis-card-header",
                children=[
                    contextual_help_label(
                        f"{number}. {title}",
                        family="open_interest",
                        section="screen_b",
                        key=indicator_id,
                    ),
                ],
            ),
            dcc.Graph(
                figure=_analysis_figure(contract, indicator_id, panel, market, timeframe),
                config={"displayModeBar": False, "displaylogo": False, "responsive": False},
                animate=False,
                className="screen-b-graph oi-analysis-card-graph",
                style={"height": "220px", "minHeight": "220px", "maxHeight": "220px", "width": "100%"},
            ),
        ],
    )


def _summary_panel(
    contract: dict[str, Any],
    market: str,
    timeframe: str,
) -> html.Div:
    rows = _table_indicator_rows(contract, market, timeframe)
    body: list[Any] = [
        html.Div(
            className="oi-summary-head",
            children=[
                html.Span("INDICATOR"),
                html.Span("VALUE", style={"textAlign": "right"}),
                html.Span("SIGNAL", style={"textAlign": "right"}),
                html.Span("STRENGTH", style={"textAlign": "right"}),
            ],
        )
    ]

    for section_title, section_color, indicator_ids in SUMMARY_SECTIONS:
        body.append(
            html.Div(
                className="oi-summary-section",
                style={"color": section_color},
                children=[
                    html.Span(className="oi-summary-section-marker"),
                    html.Span(section_title),
                ],
            )
        )

        for indicator_id in indicator_ids:
            panel = _analysis_panel(contract, indicator_id, market, timeframe)
            row = rows.get(indicator_id, {})
            value = row.get("value")
            if value is None:
                value = _panel_current_value(panel)
            signal_text, signal_color = _signal_descriptor(row, panel, indicator_id)
            strength = _strength_count(row, panel)

            body.append(
                html.Div(
                    className="oi-summary-row",
                    children=[
                        html.Span(SUMMARY_LABELS[indicator_id], className="oi-summary-name"),
                        html.Span(_format_analysis_number(value), className="oi-summary-value"),
                        html.Span(
                            signal_text,
                            className="oi-summary-signal",
                            style={"color": signal_color},
                        ),
                        _strength_dots(strength, signal_color),
                    ],
                )
            )

    return html.Div(
        className="oi-summary-panel",
        children=[
            html.Div("INDICATOR SUMMARY", className="oi-summary-title"),
            *body,
        ],
    )


def _strength_legend() -> html.Div:
    legend_rows = (
        ("VERY STRONG", 5, "#20d05c"),
        ("STRONG", 4, "#20d05c"),
        ("MODERATE", 3, "#ffab00"),
        ("WEAK", 2, "#ff8a00"),
        ("VERY WEAK", 1, "#ff3d55"),
    )

    return html.Div(
        className="oi-strength-legend",
        children=[
            html.Div("STRENGTH LEGEND", className="oi-strength-title"),
            html.Div(
                className="oi-strength-legend-body",
                children=[
                    html.Div(
                        className="oi-strength-legend-rows",
                        children=[
                            html.Div(
                                className="oi-strength-legend-row",
                                children=[html.Span(label), _strength_dots(count, color)],
                            )
                            for label, count, color in legend_rows
                        ],
                    ),
                    html.Div(
                        className="oi-strength-copy",
                        children=[
                            html.P("Based on the indicator direction and current relative strength."),
                            html.P("Values can change with the next candle close."),
                        ],
                    ),
                ],
            ),
        ],
    )


def build_analysis_screen(
    contract: dict[str, Any],
    market: str | None,
    timeframe: str | None,
    selection: Any,
) -> html.Div:
    timeframe_block, selected_market, selected_timeframe = _selected_ohlcv(contract, market, timeframe)
    del timeframe_block
    selected_ids = _selected_analysis_ids(selection)
    rows = _table_indicator_rows(contract, selected_market, selected_timeframe)

    if selected_ids:
        chart_area: Any = html.Div(
            className="screen-b-grid oi-analysis-grid",
            children=[
                _analysis_card(
                    contract,
                    indicator_id,
                    selected_market,
                    selected_timeframe,
                    rows,
                )
                for indicator_id in selected_ids
            ],
        )
    else:
        chart_area = html.Div(
            "No metrics selected for Screen B. Return to Screen A, select Dynamics, Price × Participation, Crowding or Regime Shift and open the analysis.",
            className="oi-analysis-empty",
        )

    return html.Div(
        className="oi-analysis-screen",
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
                className="screen-b-layout oi-analysis-layout",
                children=[
                    chart_area,
                    html.Div(
                        className="oi-summary-column",
                        children=[
                            _analysis_indicator_controls(selection),
                            _summary_panel(contract, selected_market, selected_timeframe),
                            _strength_legend(),
                        ],
                    ),
                ],
            )
        ],
    )



# -----------------------------------------------------------------------------
# Dash callbacks
# -----------------------------------------------------------------------------


@callback(
    Output("oi-main-graph", "figure"),
    Input("oi-trend-selectors", "value"),
    Input("oi-band-selectors", "value"),
    Input("oi-derived-selectors", "value", allow_optional=True),
    Input("oi-momentum-selectors", "value", allow_optional=True),
    Input("oi-volatility-selectors", "value", allow_optional=True),
    Input("oi-native-selectors", "value", allow_optional=True),
    Input("market-selector", "value"),
    Input("timeframe-selector", "value"),
    Input("reload-json", "n_clicks"),
    Input("url", "search"),
    prevent_initial_call=False,
)
def update_open_interest_figure(
    trend_values: list[str] | None,
    band_values: list[str] | None,
    derived_values: list[str] | None,
    momentum_values: list[str] | None,
    volatility_values: list[str] | None,
    native_values: list[str] | None,
    market: str | None,
    timeframe: str | None,
    _reload_clicks: int | None,
    search: str | None,
) -> go.Figure:
    locale = locale_from_search(search)
    del derived_values, momentum_values, volatility_values, native_values
    selected = _unique([
        *(trend_values or []),
        *(band_values or []),
    ])
    contract = load_contract(CONTRACT_FILE)
    return localize_figure(build_open_interest_figure(contract, market, timeframe, selected), locale)


@callback(
    Output(SELECTION_STORE_ID, "data"),
    Input("oi-trend-selectors", "value", allow_optional=True),
    Input("oi-band-selectors", "value", allow_optional=True),
    Input("oi-derived-selectors", "value", allow_optional=True),
    Input("oi-momentum-selectors", "value", allow_optional=True),
    Input("oi-volatility-selectors", "value", allow_optional=True),
    Input("oi-native-selectors", "value", allow_optional=True),
    State(SELECTION_STORE_ID, "data"),
    prevent_initial_call=True,
)
def persist_open_interest_selection(
    trend_values: list[str] | None,
    band_values: list[str] | None,
    derived_values: list[str] | None,
    momentum_values: list[str] | None,
    volatility_values: list[str] | None,
    native_values: list[str] | None,
    current: Any,
) -> dict[str, list[str]]:
    stored = resolve_persisted_selection(current, _default_selection_payload)
    return _selection_payload(
        list(stored.get("trend", [])) if trend_values is None else trend_values,
        list(stored.get("bands", [])) if band_values is None else band_values,
        list(stored.get("derived_analysis", [])) if derived_values is None else derived_values,
        list(stored.get("momentum", [])) if momentum_values is None else momentum_values,
        list(stored.get("volatility", [])) if volatility_values is None else volatility_values,
        list(stored.get("open_interest", [])) if native_values is None else native_values,
    )


@callback(
    Output(ANALYSIS_CONTENT_ID, "children"),
    Input(SELECTION_STORE_ID, "data"),
    Input("market-selector", "value"),
    Input("timeframe-selector", "value"),
    Input("reload-json", "n_clicks"),
    Input("url", "search"),
    prevent_initial_call=False,
)
def update_analysis_screen(
    selection: Any,
    market: str | None,
    timeframe: str | None,
    _reload_clicks: int | None,
    search: str | None,
) -> html.Div:
    locale = locale_from_search(search)
    contract = load_contract(CONTRACT_FILE)
    with locale_context(locale):
        return localize_component_tree(
            build_analysis_screen(
                contract,
                market,
                timeframe,
                resolve_persisted_selection(selection, _default_selection_payload),
            ),
            locale,
        )


def _open_interest_stylesheet() -> html.Link:
    """Load Open Interest CSS without relying on html.Style."""
    return html.Link(
        rel="stylesheet",
        href="data:text/css;charset=utf-8," + quote(OPEN_INTEREST_LOCAL_CSS, safe=""),
    )


# -----------------------------------------------------------------------------
# Screen renderer
# -----------------------------------------------------------------------------


def render(
    contract: dict[str, Any],
    view: str,
    market: str | None,
    timeframe: str | None,
    range_id: str | None,
) -> html.Div:
    del range_id

    if view == "reference":
        return screen_page(
            _open_interest_stylesheet(),
            screen_header(contract),
            reference_gallery(REFERENCE_IMAGES),
        )

    if view == "analysis":
        default_payload = _default_selection_payload()
        return screen_page(
            _open_interest_stylesheet(),
            dcc.Store(
                id=SELECTION_STORE_ID,
                storage_type="local",
            ),
            html.Div(
                id=ANALYSIS_CONTENT_ID,
                children=build_analysis_screen(
                    contract,
                    market,
                    timeframe,
                    default_payload,
                ),
            ),
        )

    initial_payload = _default_selection_payload()
    initial_selection = _unique([
        *initial_payload["trend"],
        *initial_payload["bands"],
    ])

    return screen_page(
        _open_interest_stylesheet(),
        dcc.Store(
            id=SELECTION_STORE_ID,
            storage_type="local",
        ),
        screen_header(contract),
        _open_interest_kpi_strip(contract),
        html.Div(
            className="oi-main-grid",
            children=[
                html.Div(
                    className="oi-chart-card",
                    children=[
                        html.Div(
                            contextual_help_label(
                                "OPEN INTEREST",
                                family="open_interest",
                                section="screen_a",
                                key="open_interest_ohlc",
                            ),
                            className="oi-main-chart-header",
                            title="OPEN INTEREST",
                        ),
                        dcc.Graph(
                            id="oi-main-graph",
                            figure=build_open_interest_figure(
                                contract,
                                market,
                                timeframe,
                                initial_selection,
                            ),
                            config={
                                "displaylogo": False,
                                "responsive": True,
                                "scrollZoom": True,
                                "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                            },
                            className="oi-main-graph",
                        )
                    ],
                ),
                _indicator_panel(),
            ],
        ),
    )
