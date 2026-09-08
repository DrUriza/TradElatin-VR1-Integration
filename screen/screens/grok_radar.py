from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any

import requests
from dash import Input, Output, callback, dcc, html, no_update

ROUTE = "/grok-radar"
LABEL = "Grok Radar"
HAS_ANALYSIS = False
USES_CONTRACT = False
STATIC_REVISION = "grok-radar-v1"
STATIC_CONTRACT: dict[str, Any] = {
    "screen": {
        "id": "grok_radar",
        "family": "grok_radar",
        "title": "Grok Radar",
        "subtitle": "On-demand BTC macro and news briefing powered by xAI",
        "route": ROUTE,
    },
    "context": {
        "data_mode": "xAI",
        "data_as_of": None,
    },
    "badges": [
        {"text": "ON DEMAND", "status": "available"},
    ],
    "quality": {"status": "available"},
    "selectors": {},
}

XAI_URL = "https://api.x.ai/v1/chat/completions"
XAI_MODEL = os.getenv("XAI_MODEL", "grok-4")
XAI_TIMEOUT_SECONDS = 90

SYSTEM_PROMPT = """Eres el módulo Grok Radar de TradeLATIN.
Analiza noticias, macro, ETF flows, Fed, dólar, geopolítica y estructura de BTC.
Responde SOLO JSON válido, sin markdown, con esta forma exacta:
{
  "price_context": "string corta",
  "short_bias": "alcista|mixto|bajista",
  "medium_bias": "alcista|mixto|bajista",
  "long_bias": "alcista|mixto|bajista",
  "verdict": "2 a 4 frases en español",
  "bullish": ["...", "...", "..."],
  "bearish": ["...", "...", "..."],
  "levels": {"support": "...", "resistance": "..."},
  "watch": ["...", "..."]
}
No des consejo financiero. Sé concreto.
"""

_CARD = {
    "background": "#0a1825",
    "border": "1px solid #17354a",
    "borderRadius": "4px",
    "padding": "14px",
    "minWidth": "0",
}
_LABEL = {
    "color": "#6fa2c4",
    "fontSize": "9px",
    "letterSpacing": "0.08em",
    "textTransform": "uppercase",
    "marginBottom": "7px",
    "fontWeight": "700",
}
_TEXT = "#d9e8f5"
_MUTED = "#7f96aa"


def _extract_json(text: str) -> dict[str, Any]:
    if not text or not str(text).strip():
        raise ValueError("Respuesta vacía de xAI")

    cleaned = str(text).strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned, re.I)
    if fence:
        cleaned = fence.group(1).strip()

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise
        payload = json.loads(cleaned[start : end + 1])

    if not isinstance(payload, dict):
        raise ValueError("La respuesta JSON de xAI no es un objeto")
    return payload


def _message_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("xAI no devolvió choices")
    first = choices[0] if isinstance(choices[0], dict) else {}
    message = first.get("message") if isinstance(first.get("message"), dict) else {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                value = item.get("text") or item.get("content")
                if isinstance(value, str):
                    parts.append(value)
        if parts:
            return "\n".join(parts)
    raise ValueError("xAI devolvió un mensaje sin contenido de texto")


def _string_list(value: Any, *, limit: int = 8) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()][:limit]


def _normalize_briefing(payload: dict[str, Any]) -> dict[str, Any]:
    allowed_bias = {"alcista", "mixto", "bajista"}

    def bias(key: str) -> str:
        value = str(payload.get(key) or "mixto").strip().lower()
        return value if value in allowed_bias else "mixto"

    levels_raw = payload.get("levels") if isinstance(payload.get("levels"), dict) else {}
    return {
        "price_context": str(payload.get("price_context") or "").strip(),
        "short_bias": bias("short_bias"),
        "medium_bias": bias("medium_bias"),
        "long_bias": bias("long_bias"),
        "verdict": str(payload.get("verdict") or "").strip(),
        "bullish": _string_list(payload.get("bullish")),
        "bearish": _string_list(payload.get("bearish")),
        "levels": {
            "support": str(levels_raw.get("support") or "—").strip(),
            "resistance": str(levels_raw.get("resistance") or "—").strip(),
        },
        "watch": _string_list(payload.get("watch")),
    }


def fetch_grok_briefing() -> dict[str, Any]:
    key = os.getenv("XAI_API_KEY")
    if not key:
        raise RuntimeError("Falta XAI_API_KEY en el entorno")

    payload = {
        "model": XAI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Briefing BTC ahora (UTC "
                    f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}). "
                    "Incluye Fed, ETF spot flows, liquidez, geopolítica y sesgo."
                ),
            },
        ],
        "temperature": 0.2,
    }

    try:
        response = requests.post(
            XAI_URL,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=XAI_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"No se pudo conectar con xAI: {exc}") from exc

    if response.status_code >= 400:
        body = (response.text or "").replace("\n", " ").strip()
        raise RuntimeError(f"xAI {response.status_code}: {body[:400] or 'error sin detalle'}")

    try:
        envelope = response.json()
    except ValueError as exc:
        raise RuntimeError("xAI devolvió una respuesta HTTP que no es JSON") from exc

    if not isinstance(envelope, dict):
        raise RuntimeError("xAI devolvió un envelope inválido")

    data = _normalize_briefing(_extract_json(_message_content(envelope)))
    data["_ts"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return data


def _pill(bias: str) -> html.Span:
    normalized = str(bias or "mixto").lower()
    colors = {
        "alcista": ("#20d05c", "rgba(32,208,92,.12)"),
        "bajista": ("#ff506e", "rgba(255,80,110,.12)"),
        "mixto": ("#ffab00", "rgba(255,171,0,.12)"),
    }
    color, background = colors.get(normalized, colors["mixto"])
    return html.Span(
        normalized.upper(),
        style={
            "display": "inline-flex",
            "alignItems": "center",
            "padding": "3px 9px",
            "borderRadius": "999px",
            "fontSize": "9px",
            "fontWeight": "800",
            "letterSpacing": "0.06em",
            "color": color,
            "background": background,
            "border": f"1px solid {color}",
        },
    )


def _card(title: str, children: Any) -> html.Div:
    return html.Div(
        [html.Div(title, style=_LABEL), html.Div(children, style={"minWidth": "0"})],
        style=_CARD,
    )


def render_briefing(data: dict[str, Any]) -> html.Div:
    bullish = _string_list(data.get("bullish"))
    bearish = _string_list(data.get("bearish"))
    watch = _string_list(data.get("watch"))
    levels = data.get("levels") if isinstance(data.get("levels"), dict) else {}

    return html.Div(
        [
            html.Div(
                [
                    _card(
                        "CORTO PLAZO",
                        [
                            _pill(str(data.get("short_bias") or "mixto")),
                            html.P(
                                str(data.get("price_context") or ""),
                                style={"margin": "9px 0 0", "color": _MUTED, "fontSize": "11px", "lineHeight": "1.45"},
                            ),
                        ],
                    ),
                    _card("MEDIO PLAZO", _pill(str(data.get("medium_bias") or "mixto"))),
                    _card("LARGO PLAZO", _pill(str(data.get("long_bias") or "mixto"))),
                ],
                className="grok-radar-bias-grid",
            ),
            _card(
                f"VEREDICTO · {data.get('_ts', '')}",
                [
                    html.P(
                        str(data.get("verdict") or "—"),
                        style={"color": _TEXT, "fontSize": "12px", "lineHeight": "1.55", "margin": "0 0 10px"},
                    ),
                    html.Div(
                        [
                            html.Span(f"SOPORTE: {levels.get('support', '—')}", className="grok-radar-level"),
                            html.Span(f"RESISTENCIA: {levels.get('resistance', '—')}", className="grok-radar-level"),
                        ],
                        className="grok-radar-levels",
                    ),
                ],
            ),
            html.Div(
                [
                    _card("CATALIZADORES ALCISTAS", html.Ul([html.Li(item) for item in bullish]) if bullish else "—"),
                    _card("RIESGOS BAJISTAS", html.Ul([html.Li(item) for item in bearish]) if bearish else "—"),
                ],
                className="grok-radar-factor-grid",
            ),
            _card("VIGILAR", html.Ul([html.Li(item) for item in watch]) if watch else "—"),
            html.P(
                "No es consejo financiero. Contrasta este briefing con los datos cuantitativos de TradeLATIN.",
                className="grok-radar-disclaimer",
            ),
        ],
        className="grok-radar-results",
    )


def render(
    contract: dict[str, Any],
    view: str,
    market: str | None,
    timeframe: str | None,
    range_id: str | None,
) -> html.Div:
    del contract, view, market, timeframe, range_id
    return html.Div(
        className="grok-radar-page",
        children=[
            html.Div(
                className="grok-radar-toolbar",
                children=[
                    html.Div(
                        [
                            html.Div("GROK RADAR", style=_LABEL),
                            html.Div(
                                "Briefing BTC macro, noticias y contexto externo bajo demanda.",
                                className="grok-radar-intro",
                            ),
                        ]
                    ),
                    html.Button(
                        "ACTUALIZAR BRIEFING",
                        id="grok-refresh-btn",
                        n_clicks=0,
                        disabled=False,
                        className="reload-button grok-radar-button",
                    ),
                ],
            ),
            dcc.Loading(
                id="grok-radar-loading",
                type="dot",
                color="#00c2ff",
                children=html.Div(
                    id="grok-radar-out",
                    className="grok-radar-output",
                    children=html.Div(
                        [
                            html.Div("LISTO", style=_LABEL),
                            html.Div(
                                "Pulsa ACTUALIZAR BRIEFING para consultar xAI.",
                                style={"color": _MUTED, "fontSize": "12px"},
                            ),
                        ],
                        style=_CARD,
                    ),
                ),
            ),
        ],
    )


@callback(
    Output("grok-radar-out", "children"),
    Input("grok-refresh-btn", "n_clicks"),
    prevent_initial_call=True,
    running=[(Output("grok-refresh-btn", "disabled"), True, False)],
)
def _on_refresh(n_clicks: int | None):
    if not n_clicks:
        return no_update
    try:
        return render_briefing(fetch_grok_briefing())
    except Exception as exc:
        return html.Div(
            [
                html.Div("GROK RADAR ERROR", style={**_LABEL, "color": "#ff506e"}),
                html.Div(str(exc), style={"color": "#ff8ca0", "fontSize": "12px", "lineHeight": "1.5"}),
            ],
            style={**_CARD, "borderColor": "#652538"},
        )
