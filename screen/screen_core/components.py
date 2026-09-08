from __future__ import annotations

from typing import Any

from dash import dash_table, dcc, html

from .contextual_help import contextual_help_label
from .contract_loader import active_badges, screen_metadata
from .figures import make_chart_figure
from .formatting import compact_number, format_metric, format_timestamp, humanize_key


def _status(value: Any) -> str:
    status = str(value or "available").lower()
    if status in {"ok", "available", "active", "connected", "normal", "positive", "bullish", "buying", "expanding"}:
        return "ok"
    if status in {"partial", "warning", "degraded", "synthetic", "demo", "estimated", "mixed", "neutral"}:
        return "warning"
    if status in {"unavailable", "error", "critical", "negative", "bearish", "selling", "disconnected"}:
        return "danger"
    return "neutral"


def screen_header(contract: dict[str, Any], eyebrow: str | None = None) -> html.Div:
    meta = screen_metadata(contract)
    operational = contract.get("operational_status") if isinstance(contract.get("operational_status"), dict) else {}
    quality = contract.get("quality") if isinstance(contract.get("quality"), dict) else {}
    quality_status = operational.get("quality_status") or operational.get("status") or quality.get("status") or "unknown"

    badge_nodes = [
        html.Span(item["text"], className=f"status-badge status-{_status(item.get('status'))}")
        for item in active_badges(contract)
    ]
    if meta.get("data_mode"):
        badge_nodes.append(html.Span(str(meta["data_mode"]).upper(), className="status-badge status-warning"))
    badge_nodes.append(html.Span(str(quality_status).upper(), className=f"status-badge status-{_status(quality_status)}"))

    return html.Div(
        className="screen-heading",
        children=[
            html.Div(
                className="screen-heading-main",
                children=[
                    html.Div(eyebrow or "TRAD ELATIN TRADING TOOL", className="screen-eyebrow"),
                    html.H1(meta.get("title") or "TradELATIN", className="screen-title"),
                    html.Div(meta.get("subtitle") or humanize_key(meta.get("family") or ""), className="screen-subtitle"),
                ],
            ),
            html.Div(
                className="screen-heading-meta",
                children=[
                    html.Div(badge_nodes, className="badge-row"),
                    html.Div(
                        [html.Span("DATA AS OF", className="meta-label"), html.Span(format_timestamp(meta.get("data_as_of")), className="meta-value")],
                        className="meta-block",
                    ),
                ],
            ),
        ],
    )


def _normalize_kpis(kpis: Any) -> list[dict[str, Any]]:
    if isinstance(kpis, list):
        return [item for item in kpis if isinstance(item, dict)]
    if not isinstance(kpis, dict):
        return []
    if isinstance(kpis.get("items"), list):
        return [item for item in kpis["items"] if isinstance(item, dict)]

    items: list[dict[str, Any]] = []
    for key, value in kpis.items():
        if isinstance(value, dict):
            item = dict(value)
            item.setdefault("metric_id", key)
            items.append(item)
    return items


def kpi_grid(kpis: Any, max_items: int | None = None, help_family: str | None = None) -> html.Div:
    items = _normalize_kpis(kpis)
    if max_items:
        items = items[:max_items]
    cards: list[html.Div] = []
    for item in items:
        metric_id = item.get("metric_id") or item.get("kpi_id") or item.get("id") or "metric"
        label = item.get("label") or item.get("title") or humanize_key(metric_id)
        display = format_metric(item.get("value"), item.get("unit"), item.get("display_value"))
        secondary = item.get("secondary_value")
        if secondary is None and isinstance(item.get("secondary_values"), dict):
            secondary_values = item["secondary_values"]
            if secondary_values:
                first_key, first_value = next(iter(secondary_values.items()))
                if isinstance(first_value, dict):
                    secondary = f"{humanize_key(first_key)} {format_metric(first_value.get('value'), first_value.get('unit'))}"
                else:
                    secondary = f"{humanize_key(first_key)} {compact_number(first_value)}"
        elif secondary is not None:
            secondary = format_metric(secondary, item.get("secondary_unit"))
        classification = item.get("classification")
        if isinstance(classification, dict):
            classification = classification.get("state") or classification.get("direction")
        status = item.get("status") or classification or "available"

        cards.append(
            html.Div(
                className=f"kpi-card status-edge-{_status(status)}",
                children=[
                    html.Div(
                        contextual_help_label(
                            str(label),
                            family=help_family,
                            section="kpi",
                            key=str(metric_id),
                            class_name="kpi-label",
                        ),
                    ),
                    html.Div(display, className="kpi-value"),
                    html.Div(
                        [
                            html.Span(str(classification or status).upper(), className=f"kpi-state state-{_status(status)}"),
                            html.Span(str(secondary or ""), className="kpi-secondary"),
                        ],
                        className="kpi-footer",
                    ),
                ],
            )
        )
    return html.Div(cards or [html.Div("No KPI items in JSON", className="empty-inline")], className="kpi-grid")


def graph_card(
    chart: dict[str, Any] | None,
    *,
    chart_id: str,
    title: str | None = None,
    market: str | None = None,
    timeframe: str | None = None,
    range_id: str | None = None,
    height: int = 300,
    class_name: str = "panel-card",
    help_family: str | None = None,
    help_section: str = "screen_a",
    help_key: str | None = None,
    show_card_title: bool = False,
) -> html.Div:
    header_title = title or (chart.get("title") if isinstance(chart, dict) else None) or humanize_key(chart_id)
    figure_title = None if show_card_title else title
    figure = make_chart_figure(chart, title=figure_title, market=market, timeframe=timeframe, range_id=range_id, height=height)
    if show_card_title:
        current_margin = figure.layout.margin.to_plotly_json() if figure.layout.margin else {}
        figure.update_layout(
            title=None,
            margin={
                "l": current_margin.get("l", 42),
                "r": current_margin.get("r", 20),
                "t": max(34, min(int(current_margin.get("t", 42) or 42), 48)),
                "b": current_margin.get("b", 34),
            },
        )
    status = chart.get("status") if isinstance(chart, dict) else "unavailable"
    children: list[Any] = []
    if show_card_title:
        children.append(
            html.Div(
                contextual_help_label(
                    str(header_title),
                    family=help_family,
                    section=help_section,
                    key=help_key or chart_id,
                ),
                className="panel-title",
            )
        )
    children.append(
        dcc.Graph(
            id={"type": "contract-chart", "index": chart_id},
            figure=figure,
            config={"displaylogo": False, "responsive": True, "scrollZoom": True},
            className="contract-graph",
        )
    )
    return html.Div(
        className=f"{class_name} panel-status-{_status(status)}",
        children=children,
    )


def _flatten_cell(value: Any) -> Any:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (int, float, str)):
        return value
    if isinstance(value, dict):
        compact = []
        for key, nested in list(value.items())[:4]:
            if isinstance(nested, (str, int, float, bool)) or nested is None:
                compact.append(f"{humanize_key(key)}: {nested}")
        return " | ".join(compact) if compact else "{…}"
    if isinstance(value, list):
        return f"[{len(value)} items]"
    return str(value)


def _table_rows(table: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(table.get("rows"), list):
        return [item for item in table["rows"] if isinstance(item, dict)]
    if isinstance(table.get("items"), list):
        return [item for item in table["items"] if isinstance(item, dict)]
    bids = table.get("bids") if isinstance(table.get("bids"), list) else []
    asks = table.get("asks") if isinstance(table.get("asks"), list) else []
    return [item for item in bids + asks if isinstance(item, dict)]


def data_table_card(table: dict[str, Any] | None, table_id: str, title: str | None = None, max_rows: int = 14, help_family: str | None = None, help_section: str = "screen_a") -> html.Div:
    if not isinstance(table, dict):
        return html.Div([html.Div(contextual_help_label(title or humanize_key(table_id), family=help_family, section=help_section, key=table_id), className="panel-title"), html.Div("Table missing in JSON", className="empty-inline")], className="panel-card")

    rows = _table_rows(table)
    if not rows:
        return html.Div(
            [
                html.Div(contextual_help_label(title or table.get("title") or humanize_key(table_id), family=help_family, section=help_section, key=table_id), className="panel-title"),
                html.Div(str(table.get("reason") or "No rows in JSON"), className="empty-inline"),
            ],
            className="panel-card",
        )
    rows = rows[:max_rows]
    keys: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in keys and key not in {"provenance", "source_paths", "warnings", "errors", "evidence"}:
                keys.append(key)
    keys = keys[:8]
    display_rows = [{key: _flatten_cell(row.get(key)) for key in keys} for row in rows]

    return html.Div(
        className="panel-card table-card",
        children=[
            html.Div(contextual_help_label(title or table.get("title") or humanize_key(table_id), family=help_family, section=help_section, key=table_id), className="panel-title"),
            dash_table.DataTable(
                id={"type": "contract-table", "index": table_id},
                data=display_rows,
                columns=[{"name": humanize_key(key), "id": key} for key in keys],
                page_size=min(max_rows, len(display_rows)),
                page_action="none",
                sort_action="native",
                style_table={"overflowX": "auto", "maxHeight": "340px", "overflowY": "auto"},
                style_header={"backgroundColor": "#0b1b29", "color": "#8da6bb", "border": "1px solid #153149", "fontWeight": 600, "fontSize": "10px"},
                style_cell={"backgroundColor": "#071522", "color": "#d9e8f5", "border": "1px solid #10283d", "fontFamily": "Inter, Segoe UI, sans-serif", "fontSize": "10px", "padding": "7px", "textAlign": "left", "minWidth": "78px", "maxWidth": "180px", "whiteSpace": "normal"},
                style_data_conditional=[
                    {"if": {"filter_query": '{status} = "available"', "column_id": "status"}, "color": "#17d49b"},
                    {"if": {"filter_query": '{status} = "unavailable"', "column_id": "status"}, "color": "#ff506e"},
                    {"if": {"filter_query": '{status} = "partial"', "column_id": "status"}, "color": "#f5a524"},
                ],
            ),
        ],
    )


def widget_cards(widgets: Any, max_items: int = 6, help_family: str | None = None) -> html.Div:
    if not isinstance(widgets, dict):
        return html.Div("No widgets in JSON", className="empty-inline")
    cards: list[Any] = []
    for key, value in list(widgets.items())[:max_items]:
        if not isinstance(value, dict):
            continue
        label = value.get("label") or value.get("title") or humanize_key(key)
        status = value.get("status") or value.get("classification") or "available"
        state = value.get("state") or value.get("classification")
        if isinstance(state, dict):
            state = state.get("state") or state.get("label")
        display = value.get("display_value")
        if display is None:
            display = format_metric(value.get("value"), value.get("unit"))
        if display == "—" and isinstance(value.get("values"), dict):
            display = " · ".join(f"{humanize_key(k)} {compact_number(v)}" for k, v in list(value["values"].items())[:3])
        cards.append(
            html.Div(
                className=f"widget-card status-edge-{_status(status)}",
                children=[
                    html.Div(
                        contextual_help_label(
                            str(label),
                            family=help_family,
                            section="kpi",
                            key=str(key),
                            class_name="widget-label",
                        ),
                    ),
                    html.Div(display, className="widget-value"),
                    html.Div(str(state or status).upper(), className=f"widget-state state-{_status(status)}"),
                ],
            )
        )
    return html.Div(cards or [html.Div("Widget values are not present", className="empty-inline")], className="widget-grid")


def reference_gallery(image_paths: list[str]) -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.Div(path.split("/")[-1], className="reference-title"),
                    html.Img(src=f"/assets/reference/{path}", className="reference-image"),
                ],
                className="reference-card",
            )
            for path in image_paths
        ],
        className="reference-gallery",
    )


def screen_page(header: Any, *sections: Any) -> html.Div:
    return html.Div([header, *sections], className="screen-page")
