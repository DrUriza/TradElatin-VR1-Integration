from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any
from urllib.parse import quote

import plotly.graph_objects as go
from dash import Input, Output, callback, dcc, html

from screen_core.components import (
    graph_card,
    reference_gallery,
    screen_header,
    screen_page,
    widget_cards,
)
from screen_core.contextual_help import contextual_help_label
from screen_core.i18n import locale_context, localize_component_tree, localize_figure, localized_href, locale_from_search
from screen_core.contract_loader import load_contract
from screen_core.figures import apply_analysis_figure_layout


ROUTE = "/on-chain-miners"
LABEL = "On-Chain Miners"
CONTRACT_FILE = "on_chain_miners_VR1_FINAL.json"
HAS_ANALYSIS = True
SCREEN_REVISION = "ONCHAIN_NATIVE_MINERS_V2"

REFERENCE_IMAGES = [
    "On Chain/05_On_Chain_Miners_A.png",
    "On Chain/05_On_Chain_Miners_B_Reserve.png",
    "On Chain/05_On_Chain_Miners_B_SOPRD.png",
    "On Chain/05_On_Chain_Miners_B_HashRate.png",
    "On Chain/05_On_Chain_Miners_B_Difficulty.png",
]

GREEN = "#17d49b"
RED = "#ff506e"
BLUE = "#2f80ff"
CYAN = "#00c2ff"
PURPLE = "#8a7dff"
ORANGE = "#f2994a"
YELLOW = "#f2c94c"
BG = "#06111d"
PLOT_BG = "#071522"
GRID = "rgba(91,126,155,.16)"
TEXT = "#d9e8f5"
MUTED = "#7f96aa"

SELECTION_STORE_ID = "onchain-native-selection"
ANALYSIS_CONTENT_ID = "onchain-analysis-content"

TARGETS = ("miner_reserve", "sopr_7d", "hashrate", "difficulty")
ANALYSIS_ORDER = (
    "miner_reserve_change_zscore",
    "miner_selling_pressure",
    "puell_revenue_stress",
    "hashrate_momentum_hash_ribbon",
    "hashrate_difficulty_stress",
    "miner_capitulation_recovery_regime",
)

ANALYSIS_LABELS = {
    "miner_reserve_change_zscore": "MINER RESERVE CHANGE / Z-SCORE",
    "miner_selling_pressure": "MPI / MINER-TO-EXCHANGE PRESSURE",
    "puell_revenue_stress": "PUELL MULTIPLE / REVENUE STRESS",
    "hashrate_momentum_hash_ribbon": "HASHRATE MOMENTUM / HASH RIBBON",
    "hashrate_difficulty_stress": "HASHRATE × DIFFICULTY STRESS",
    "miner_capitulation_recovery_regime": "CAPITULATION / RECOVERY + WASSERSTEIN",
}

GROUPS = (
    (
        "MINER TREASURY · SCREEN B",
        "onchain-treasury",
        [{"label": "Miner Reserve Change / Z-Score", "value": "miner_reserve_change_zscore"}],
    ),
    (
        "SELLING PRESSURE / ECONOMICS · SCREEN B",
        "onchain-selling",
        [
            {"label": "MPI / Miner-to-Exchange Pressure", "value": "miner_selling_pressure"},
            {"label": "Puell Multiple / Revenue Stress", "value": "puell_revenue_stress"},
        ],
    ),
    (
        "NETWORK HEALTH · SCREEN B",
        "onchain-network",
        [
            {"label": "Hashrate Momentum / Hash Ribbon", "value": "hashrate_momentum_hash_ribbon"},
            {"label": "Hashrate × Difficulty Stress", "value": "hashrate_difficulty_stress"},
        ],
    ),
    (
        "MINER REGIME · SCREEN B",
        "onchain-regime",
        [{"label": "Capitulation / Recovery + Wasserstein", "value": "miner_capitulation_recovery_regime"}],
    ),
)

DEFAULT_SELECTED = list(ANALYSIS_ORDER)

TRACE_COLORS = {
    "reserve_change_btc": CYAN,
    "reserve_change_zscore": PURPLE,
    "reserve_roc_30d_pct": YELLOW,
    "mpi": YELLOW,
    "miner_to_exchange_zscore": ORANGE,
    "selling_pressure_score": RED,
    "puell_multiple": BLUE,
    "revenue_stress_score": RED,
    "hashrate_eh_s": CYAN,
    "hash_ma_30": GREEN,
    "hash_ma_60": ORANGE,
    "hash_momentum_pct": PURPLE,
    "hashrate_change_zscore": CYAN,
    "difficulty_change_zscore": YELLOW,
    "network_stress_score": RED,
    "regime_score": GREEN,
    "capitulation_probability_pct": RED,
    "recovery_score_pct": CYAN,
    "wasserstein_distance": PURPLE,
}

LOCAL_CSS = """
.onchain-top-widgets .widget-grid { grid-template-columns: repeat(4,minmax(120px,1fr)); gap:3px; }
.onchain-top-widgets .widget-card { min-height:36px; padding:2px 7px; }
.onchain-main-grid { display:grid; grid-template-columns:minmax(0,1fr) 306px; gap:8px; align-items:stretch; }
.onchain-series-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); grid-template-rows:217px 217px; gap:8px; height:442px; }
.onchain-card { min-width:0; border:1px solid #173247; background:#06111d; overflow:hidden; }
.onchain-series-grid .onchain-card .js-plotly-plot,.onchain-series-grid .onchain-card .plot-container,.onchain-series-grid .onchain-card .svg-container{height:190px !important;min-height:190px !important;max-height:190px !important;}
.onchain-selector { border:1px solid #173247; background:#06111d; padding:10px; height:auto; align-self:start; overflow:auto; }
.onchain-button { border:1px solid #1677ff; color:#4da3ff; background:#071522; font-size:11px; font-weight:700; min-height:34px; }
.onchain-heading { color:#d9e8f5; font-size:11px; font-weight:700; margin:4px 0; }
.onchain-note { color:#7f96aa; font-size:8px; line-height:1.35; margin-bottom:10px; }
.onchain-group { border-top:1px solid #173247; padding:9px 0; }
.onchain-group-title { color:#6f8ca3; font-size:8px; margin-bottom:7px; }
.onchain-checklist label { display:block; color:#d9e8f5; font-size:9px; margin:5px 0; }
.onchain-checklist input { margin-right:7px; }
.onchain-analysis-shell { min-height:100vh; background:#06111d; }
.analysis-back-row { padding:8px 14px 0; }
.analysis-back-button { display:inline-flex; border:1px solid #1677ff; color:#4da3ff; background:#071522; padding:7px 12px; font-size:9px; text-decoration:none; }
.onchain-analysis-layout { display:grid; grid-template-columns:minmax(0,1fr) 286px; gap:8px; padding:8px 14px 18px; align-items:start; }
.onchain-analysis-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:8px; align-content:start; align-self:start; }
.onchain-analysis-card { border:1px solid #173247; background:#071522; min-width:0; height:247px; min-height:247px; max-height:247px; overflow:hidden; }
.onchain-analysis-card-title { color:#d9e8f5; font-size:8px; font-weight:700; padding:7px 8px; border-bottom:1px solid #173247; }
.onchain-summary-column { border:1px solid #173247; background:#071522; padding:10px; align-self:start; }
.onchain-summary-title { color:#4da3ff; font-size:10px; font-weight:700; margin-bottom:9px; }
.onchain-summary-row { padding:8px 0; border-top:1px solid rgba(23,50,71,.7); }
.onchain-summary-name { color:#d9e8f5; font-size:8px; font-weight:700; }
.onchain-summary-value { color:#fff; font-size:12px; font-weight:800; margin-top:2px; }
.onchain-summary-signal { color:#7f96aa; font-size:8px; margin-top:2px; }
@media(max-width:1100px){ .onchain-analysis-grid{grid-template-columns:repeat(2,minmax(0,1fr));} }
@media(max-width:900px){ .onchain-main-grid{grid-template-columns:1fr;} .onchain-selector{height:auto;} .onchain-series-grid{height:auto;grid-template-columns:1fr;grid-template-rows:none;} .onchain-analysis-layout{grid-template-columns:1fr;} }
@media(max-width:650px){ .onchain-analysis-grid{grid-template-columns:1fr;} .onchain-top-widgets .widget-grid{grid-template-columns:repeat(2,minmax(120px,1fr));} }
"""


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _finite_number(value: Any) -> float | None:
    """Return a finite numeric value for plotting, preserving missing data as gaps.

    Processing is allowed to emit ``None`` for legitimate warm-up / unavailable
    samples.  The HMI must never coerce those samples to zero and must not fail
    while choosing presentation attributes such as bar colors.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _dt(value: Any) -> Any:
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return value


def _stylesheet() -> html.Link:
    return html.Link(rel="stylesheet", href="data:text/css;charset=utf-8," + quote(LOCAL_CSS, safe=""))


def _default_selection() -> dict[str, list[str]]:
    return {"native": list(DEFAULT_SELECTED)}


def _range_block(contract: dict[str, Any], chart_id: str, range_id: str | None) -> dict[str, Any]:
    chart = _safe_dict(_safe_dict(contract.get("charts")).get(chart_id))
    by_range = _safe_dict(chart.get("series_by_range"))
    selected = str(range_id or _safe_dict(contract.get("context")).get("presentation_default_range") or "30D")
    if selected not in by_range:
        selected = next(iter(by_range), "")
    return _safe_dict(by_range.get(selected))


def _series_points(contract: dict[str, Any], chart_id: str, range_id: str | None) -> list[dict[str, Any]]:
    block = _range_block(contract, chart_id, range_id)
    points = [p for p in _safe_list(block.get("points")) if isinstance(p, dict) and p.get("timestamp") is not None and isinstance(p.get("value"), (int, float))]
    if points:
        return points
    # Compatibility fallback only. Production presentation contract is points[].
    return [
        {"timestamp": c.get("timestamp"), "value": c.get("close")}
        for c in _safe_list(block.get("candles"))
        if isinstance(c, dict) and c.get("timestamp") is not None and isinstance(c.get("close"), (int, float))
    ]


def _metric_figure(contract: dict[str, Any], chart_id: str, range_id: str | None) -> go.Figure:
    chart = _safe_dict(_safe_dict(contract.get("charts")).get(chart_id))
    points = _series_points(contract, chart_id, range_id)
    fig = go.Figure()

    if not points:
        fig.add_annotation(text="UNAVAILABLE", x=.5, y=.5, xref="paper", yref="paper", showarrow=False, font={"color": MUTED})
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
    else:
        x = [_dt(p["timestamp"]) for p in points]
        y = [float(p["value"]) for p in points]
        trace_kwargs: dict[str, Any] = {
            "x": x,
            "y": y,
            "mode": "lines",
            "name": chart.get("title") or chart_id,
            "hovertemplate": "%{y:,.4f}<extra></extra>",
        }

        if chart_id == "miner_reserve":
            trace_kwargs.update(line={"color": BLUE, "width": 1.7})
        elif chart_id == "sopr_7d":
            trace_kwargs.update(line={"color": PURPLE, "width": 1.7})
        elif chart_id == "hashrate":
            trace_kwargs.update(line={"color": CYAN, "width": 1.7})
        else:
            trace_kwargs.update(line={"color": YELLOW, "width": 1.65, "shape": "hv"})

        fig.add_trace(go.Scatter(**trace_kwargs))

        if chart_id == "sopr_7d":
            fig.add_hline(y=1.0, line_dash="dot", line_width=1, line_color="rgba(217,232,245,.6)", annotation_text="SOPR = 1", annotation_position="right", annotation_font={"size": 7, "color": MUTED})

        ymin, ymax = min(y), max(y)
        span = ymax - ymin
        pad = span * .12 if span > 0 else max(abs(ymax) * .02, 1e-6)
        fig.update_yaxes(range=[ymin - pad, ymax + pad])

    fig.update_layout(
        title=None,
        height=190,
        paper_bgcolor=BG,
        plot_bgcolor=PLOT_BG,
        margin={"l": 44, "r": 10, "t": 20, "b": 34},
        font={"family": "Inter, Segoe UI, sans-serif", "color": TEXT, "size": 8},
        showlegend=False,
        hovermode="x unified",
        uirevision=f"onchain-{chart_id}-{range_id}",
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, nticks=5, tickfont={"size": 7}, tickformat="%b %d<br>%Y", automargin=True)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, tickfont={"size": 7})
    return fig


def _native_block(contract: dict[str, Any], indicator_id: str, range_id: str | None) -> tuple[dict[str, Any], dict[str, Any]]:
    root = _safe_dict(contract.get("miner_analysis"))
    indicator = _safe_dict(_safe_dict(root.get("indicators")).get(indicator_id))
    by_range = _safe_dict(indicator.get("series_by_range"))
    selected = str(range_id or _safe_dict(contract.get("context")).get("presentation_default_range") or "30D")
    if selected not in by_range:
        selected = next(iter(by_range), "")
    return indicator, _safe_dict(by_range.get(selected))


def _add_line(fig: go.Figure, x: list[Any], values: list[Any], name: str, *, secondary: bool = False, dash: str = "solid", width: float = 1.35) -> None:
    if len(values) != len(x):
        return
    numeric_values = [_finite_number(value) for value in values]
    if not any(value is not None for value in numeric_values):
        return
    fig.add_trace(go.Scatter(x=x, y=numeric_values, mode="lines", name=name.replace("_", " ").upper(), line={"color": TRACE_COLORS.get(name, BLUE), "width": width, "dash": dash}, yaxis="y2" if secondary else "y", connectgaps=False))


def _native_indicator_figure(contract: dict[str, Any], indicator_id: str, range_id: str | None) -> go.Figure:
    indicator, block = _native_block(contract, indicator_id, range_id)
    timestamps = _safe_list(block.get("timestamps"))
    series = _safe_dict(block.get("series"))
    fig = go.Figure()

    if not timestamps or not series:
        fig.add_annotation(text="UNAVAILABLE", x=.5, y=.5, xref="paper", yref="paper", showarrow=False, font={"color": MUTED})
    else:
        x = [_dt(v) for v in timestamps]
        if indicator_id == "miner_reserve_change_zscore":
            vals = [_finite_number(value) for value in _safe_list(series.get("reserve_change_btc"))]
            if len(vals) == len(x) and any(value is not None for value in vals):
                neutral = "rgba(127,150,170,.28)"
                colors = [neutral if value is None else (GREEN if value >= 0 else RED) for value in vals]
                fig.add_trace(go.Bar(x=x, y=vals, name="RESERVE CHANGE BTC", marker_color=colors, opacity=.58))
            _add_line(fig, x, _safe_list(series.get("reserve_change_zscore")), "reserve_change_zscore", secondary=True, width=1.6)
            _add_line(fig, x, _safe_list(series.get("reserve_roc_30d_pct")), "reserve_roc_30d_pct", secondary=True, dash="dot")
        elif indicator_id == "hashrate_momentum_hash_ribbon":
            _add_line(fig, x, _safe_list(series.get("hashrate_eh_s")), "hashrate_eh_s", width=1.0)
            _add_line(fig, x, _safe_list(series.get("hash_ma_30")), "hash_ma_30", width=1.45)
            _add_line(fig, x, _safe_list(series.get("hash_ma_60")), "hash_ma_60", width=1.45)
            _add_line(fig, x, _safe_list(series.get("hash_momentum_pct")), "hash_momentum_pct", secondary=True, dash="dot")
        elif indicator_id == "miner_capitulation_recovery_regime":
            _add_line(fig, x, _safe_list(series.get("regime_score")), "regime_score", width=1.7)
            _add_line(fig, x, _safe_list(series.get("wasserstein_distance")), "wasserstein_distance", dash="dot")
            _add_line(fig, x, _safe_list(series.get("capitulation_probability_pct")), "capitulation_probability_pct", secondary=True)
            _add_line(fig, x, _safe_list(series.get("recovery_score_pct")), "recovery_score_pct", secondary=True)
        else:
            for name, values in series.items():
                if isinstance(values, list):
                    _add_line(fig, x, values, str(name))

        for threshold in _safe_list(indicator.get("thresholds")):
            if isinstance(threshold, dict) and isinstance(threshold.get("value"), (int, float)):
                fig.add_hline(y=float(threshold["value"]), line_dash="dot", line_width=.8, line_color="rgba(127,150,170,.45)", annotation_text=str(threshold.get("label") or ""), annotation_position="right", annotation_font={"size": 6, "color": MUTED})

    layout: dict[str, Any] = {
        "height": 190,
        "paper_bgcolor": BG,
        "plot_bgcolor": PLOT_BG,
        "margin": {"l": 38, "r": 38, "t": 8, "b": 28},
        "font": {"size": 7, "color": MUTED},
        "showlegend": True,
        "legend": {"orientation": "h", "font": {"size": 6}, "y": 1.01, "x": 0},
        "hovermode": "x unified",
        "uirevision": f"onchain-native-{indicator_id}-{range_id}",
    }
    if indicator_id in {"miner_reserve_change_zscore", "hashrate_momentum_hash_ribbon", "miner_capitulation_recovery_regime"}:
        layout["yaxis2"] = {"overlaying": "y", "side": "right", "showgrid": False, "tickfont": {"size": 6, "color": MUTED}}
    fig.update_layout(**layout)
    compact = {
        "RESERVE CHANGE BTC": "Reserve Change BTC", "RESERVE CHANGE ZSCORE": "Reserve Z",
        "RESERVE ROC 30D PCT": "Reserve ROC 30D", "MINER TO EXCHANGE ZSCORE": "M2E Z",
        "CAPITULATION PROBABILITY PCT": "Capitulation %", "RECOVERY SCORE PCT": "Recovery %",
        "WASSERSTEIN DISTANCE": "Wasserstein", "REGIME SCORE": "Regime Score",
        "SELLING PRESSURE SCORE": "Selling Pressure", "NETWORK STRESS SCORE": "Network Stress",
    }
    secondary = {
        "miner_reserve_change_zscore": {"Reserve ROC 30D"},
        "miner_selling_pressure": {"M2E Z"},
        "hashrate_momentum_hash_ribbon": {"Hashrate Eh S", "Hash Ma 60"},
        "hashrate_difficulty_stress": {"Difficulty Change Zscore"},
        "miner_capitulation_recovery_regime": {"Capitulation %", "Recovery %"},
    }.get(indicator_id, set())
    for trace in fig.data:
        trace.name = compact.get(str(trace.name), str(trace.name).title())
        if trace.name in secondary:
            trace.visible = "legendonly"
    apply_analysis_figure_layout(fig, height=220, right_margin=42)
    fig.update_xaxes(gridcolor=GRID, zeroline=False, nticks=4, tickfont={"size": 6})
    fig.update_yaxes(gridcolor=GRID, zeroline=False, tickfont={"size": 6})
    return fig


def _checklist(component_id: str, options: list[dict[str, str]]) -> dcc.Checklist:
    values = [str(item["value"]) for item in options]
    return dcc.Checklist(id=component_id, options=options, value=values, className="onchain-checklist", persistence="onchain-native-controls-v2", persistence_type="local")


def _selector_panel() -> html.Div:
    return html.Div(className="onchain-selector", children=[
        html.Div(
            style={"display": "grid", "gridTemplateColumns": "minmax(0,1fr) 34px", "gap": "4px", "marginBottom": "12px"},
            children=[
                dcc.Link("ON-CHAIN & MINERS ANALYSIS", href=localized_href(f"{ROUTE}/analysis"), className="onchain-button", style={"display": "flex", "alignItems": "center", "justifyContent": "center", "textDecoration": "none"}),
                html.A("↗", href=localized_href(f"{ROUTE}/analysis"), target="_blank", rel="noopener noreferrer", className="onchain-button", style={"display": "flex", "alignItems": "center", "justifyContent": "center", "textDecoration": "none"}),
            ],
        ),
    ])


def _analysis_selector_controls(selection: Any) -> html.Div:
    selected = set(_safe_list(_safe_dict(selection).get("native")))
    children: list[Any] = [
        html.Div("INDICATORS · SCREEN B", className="screen-b-selector-title onchain-heading"),
        html.Div("Select the native miner-analysis panels shown on this screen.", className="onchain-note"),
    ]
    for title, component_id, options in GROUPS:
        checklist = _checklist(component_id, options)
        checklist.value = [str(item["value"]) for item in options if str(item["value"]) in selected]
        children.append(html.Div(className="onchain-group", children=[html.Div(title.replace(" · SCREEN B", ""), className="onchain-group-title"), checklist]))
    return html.Div(className="screen-b-selector onchain-selector", children=children)


def _selected_analysis(selection: Any) -> list[str]:
    chosen = set(_safe_list(_safe_dict(selection).get("native")))
    return [iid for iid in ANALYSIS_ORDER if iid in chosen]


def _summary_column(contract: dict[str, Any], selected: list[str]) -> html.Div:
    indicators = _safe_dict(_safe_dict(contract.get("miner_analysis")).get("indicators"))
    rows=[]
    for iid in selected:
        summary=_safe_dict(_safe_dict(indicators.get(iid)).get("summary"))
        rows.append(html.Div(className="onchain-summary-row", children=[
            html.Div(str(summary.get("label") or ANALYSIS_LABELS[iid]), className="onchain-summary-name"),
            html.Div(str(summary.get("display_value") or "—"), className="onchain-summary-value"),
            html.Div(str(summary.get("signal") or "—"), className="onchain-summary-signal"),
            html.Div(str(summary.get("secondary") or ""), className="onchain-summary-signal"),
        ]))
    return html.Div(className="onchain-summary-column", children=[
        html.Div("CURRENT MINER REGIME SUMMARY", className="onchain-summary-title"),
        html.Div(
            "Latest-state snapshot. The 7D / 30D selector changes historical charts, not this current-state summary.",
            className="onchain-summary-signal",
            style={"padding": "0 10px 8px"},
        ),
        *rows,
    ])


def _analysis_screen(contract: dict[str, Any], range_id: str | None, selection: Any) -> html.Div:
    selected = _selected_analysis(selection)
    cards=[]
    for iid in selected:
        cards.append(html.Div(className="screen-b-card onchain-analysis-card", children=[
            html.Div(contextual_help_label(ANALYSIS_LABELS[iid], family="miners", section="screen_b", key=iid), className="screen-b-card-title onchain-analysis-card-title"),
            dcc.Graph(className="screen-b-graph", figure=_native_indicator_figure(contract, iid, range_id), config={"displaylogo": False, "responsive": False}, animate=False, style={"height": "220px", "minHeight": "220px", "maxHeight": "220px", "width": "100%"}),
        ]))
    body = html.Div(cards, className="screen-b-grid onchain-analysis-grid") if cards else html.Div("No metrics selected for Screen B.", className="contract-warning")
    return html.Div(className="onchain-analysis-shell", children=[
        html.Div(className="analysis-back-row", children=[dcc.Link("← BACK", href=localized_href(ROUTE), className="analysis-back-button")]),
        html.Div(className="screen-b-layout onchain-analysis-layout", children=[body, html.Div([_analysis_selector_controls(selection), _summary_column(contract, selected)])]),
    ])


@callback(
    Output("onchain-reserve", "figure"),
    Output("onchain-sopr", "figure"),
    Output("onchain-hashrate", "figure"),
    Output("onchain-difficulty", "figure"),
    Input("range-selector", "value"),
    Input("reload-json", "n_clicks"),
    Input("url", "search"),
    prevent_initial_call=True,
)
def update_main_charts(range_id: str | None, _reload: int | None, search: str | None):
    locale = locale_from_search(search)
    contract = load_contract(CONTRACT_FILE)
    return tuple(localize_figure(_metric_figure(contract, chart_id, range_id), locale) for chart_id in TARGETS)


@callback(
    Output(SELECTION_STORE_ID, "data"),
    Input("onchain-treasury", "value", allow_optional=True),
    Input("onchain-selling", "value", allow_optional=True),
    Input("onchain-network", "value", allow_optional=True),
    Input("onchain-regime", "value", allow_optional=True),
    prevent_initial_call=True,
)
def persist_selection(treasury: list[str] | None, selling: list[str] | None, network: list[str] | None, regime: list[str] | None):
    return {"native": _unique([*(treasury or []), *(selling or []), *(network or []), *(regime or [])])}


@callback(
    Output(ANALYSIS_CONTENT_ID, "children"),
    Input(SELECTION_STORE_ID, "data"),
    Input("range-selector", "value"),
    Input("reload-json", "n_clicks"),
    Input("url", "search"),
    prevent_initial_call=False,
)
def update_analysis(selection: Any, range_id: str | None, _reload: int | None, search: str | None):
    locale = locale_from_search(search)
    contract = load_contract(CONTRACT_FILE)
    with locale_context(locale):
        effective_selection = selection if isinstance(selection, dict) else _default_selection()
        return localize_component_tree(_analysis_screen(contract, range_id, effective_selection), locale)


def render(contract: dict[str, Any], view: str, market: str | None, timeframe: str | None, range_id: str | None) -> html.Div:
    del market, timeframe

    if view == "reference":
        return screen_page(_stylesheet(), screen_header(contract), reference_gallery(REFERENCE_IMAGES))

    if view == "analysis":
        return screen_page(
            _stylesheet(),
            dcc.Store(id=SELECTION_STORE_ID, storage_type="local"),
            html.Div([
                dcc.Graph(id="onchain-reserve"), dcc.Graph(id="onchain-sopr"), dcc.Graph(id="onchain-hashrate"), dcc.Graph(id="onchain-difficulty")
            ], style={"display": "none"}),
            html.Div(id=ANALYSIS_CONTENT_ID, children=_analysis_screen(contract, range_id, _default_selection())),
        )

    charts = _safe_dict(contract.get("charts"))
    graph_ids = {
        "miner_reserve": "onchain-reserve",
        "sopr_7d": "onchain-sopr",
        "hashrate": "onchain-hashrate",
        "difficulty": "onchain-difficulty",
    }
    main_grid = html.Div(className="onchain-main-grid", style={"gridTemplateColumns": "minmax(0,1fr)"}, children=[
        html.Div(className="onchain-series-grid", children=[
            html.Div(className="onchain-card", children=[
                html.Div(
                    contextual_help_label(
                        str(_safe_dict(charts.get(cid)).get("title") or cid).upper(),
                        family="miners",
                        section="screen_a",
                        key=cid,
                    ),
                    className="context-help-card-title context-help-card-title-compact",
                ),
                dcc.Graph(id=graph_ids[cid], figure=_metric_figure(contract, cid, range_id), config={"displaylogo": False, "responsive": False, "scrollZoom": True}, animate=False, style={"height": "190px", "minHeight": "190px", "maxHeight": "190px", "width": "100%"})
            ])
            for cid in TARGETS
        ]),
    ])

    top_widgets = html.Div(widget_cards(contract.get("widgets"), max_items=4, help_family="miners"), className="onchain-top-widgets")
    bottom = graph_card(charts.get("miner_net_position_change"), chart_id="miner-net-position", title="Miner Net Position Change", range_id=range_id, height=190, help_family="miners", help_section="screen_a", help_key="miner_net_position_change", show_card_title=True)

    return screen_page(
        _stylesheet(),
        dcc.Store(id=SELECTION_STORE_ID, storage_type="local"),
        screen_header(contract),
        top_widgets,
        main_grid,
        bottom,
        html.Div(id=ANALYSIS_CONTENT_ID, style={"display": "none"}),
    )
