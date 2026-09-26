from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from dash import html

from .formatting import humanize_key
from .i18n import current_locale, tr

_HELP_DIR = Path(__file__).resolve().parent.parent / "data" / "help"
_HELP_PATHS = {
    "en": _HELP_DIR / "contextual_help_vr1_en.json",
    "es": _HELP_DIR / "contextual_help_vr1_es.json",
}


@lru_cache(maxsize=2)
def _help_registry(locale: str) -> dict[str, Any]:
    path = _HELP_PATHS.get(locale, _HELP_PATHS["en"])
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
            return payload if isinstance(payload, dict) else {}
    except FileNotFoundError:
        return {}


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def lookup_help(
    family: str | None,
    section: str | None,
    key: str | None = None,
    *,
    locale: str | None = None,
) -> dict[str, Any] | None:
    active_locale = locale or current_locale()
    registry = _help_registry(active_locale)
    family_block = registry.get(_norm(family), {}) if family else {}
    if not isinstance(family_block, dict):
        family_block = {}

    section_name = _norm(section)
    family_defaults = registry.get("_family_defaults", {})
    global_defaults = registry.get("_global_defaults", {})

    candidates: list[dict[str, Any]] = []
    for block in (
        family_block.get(section_name),
        family_defaults.get(section_name) if isinstance(family_defaults, dict) else None,
        global_defaults.get(section_name) if isinstance(global_defaults, dict) else None,
    ):
        if isinstance(block, dict):
            candidates.append(block)

    key_name = _norm(key)
    for block in candidates:
        entry = block.get(key_name)
        if isinstance(entry, dict):
            return entry
        default_entry = block.get("__default__")
        if isinstance(default_entry, dict):
            return default_entry
    return None


def _section(title: str, value: Any) -> html.Div | None:
    if value in (None, "", [], {}):
        return None
    if isinstance(value, list):
        rendered = ", ".join(str(item) for item in value if item not in (None, ""))
    else:
        rendered = str(value)
    if not rendered:
        return None
    return html.Div(
        className="context-help-section",
        children=[
            html.Div(title, className="context-help-section-title"),
            html.Div(rendered, className="context-help-section-body"),
        ],
    )



def contextual_help_label(
    label: str,
    *,
    family: str | None,
    section: str,
    key: str | None,
    class_name: str = "",
    wrapper_class: str = "",
    title_override: str | None = None,
) -> html.Span:
    locale = current_locale()
    entry = lookup_help(family, section, key, locale=locale)
    localized_label = tr(label, locale)
    label_node = html.Span(localized_label, className=class_name) if class_name else html.Span(localized_label)
    if not isinstance(entry, dict):
        return label_node

    title = title_override or entry.get("title") or localized_label or humanize_key(key or section)
    families = entry.get("related_families")
    family_chips = []
    if isinstance(families, list):
        family_chips = [html.Span(tr(str(item), locale), className="context-help-chip") for item in families[:5]]

    sections = [
        _section(tr("WHAT IT MEASURES", locale), entry.get("what_measures")),
        _section(tr("PRICE RELATION", locale), entry.get("price_relation")),
        _section(tr("CROSS-FAMILY RELATION", locale), entry.get("cross_family_relation")),
        _section(tr("INTERPRETATION", locale), entry.get("interpretation")),
    ]
    if entry.get("variable_type"):
        sections.append(_section(tr("VARIABLE TYPE", locale), entry.get("variable_type")))

    popover_children: list[Any] = [
        html.Div(
            className="context-help-popover-header",
            children=[
                html.Div(title, className="context-help-popover-title"),
                html.Div(family_chips, className="context-help-chip-row") if family_chips else None,
            ],
        ),
        *[item for item in sections if item is not None],
    ]

    return html.Span(
        className=f"context-help-anchor {wrapper_class}".strip(),
        tabIndex=0,
        role="button",
        **{"aria-expanded": "false", "aria-haspopup": "dialog"},
        children=[
            label_node,
            html.Span("i", className="context-help-icon"),
            html.Span(
                className="context-help-popover",
                role="dialog",
                children=popover_children,
            ),
        ],
    )
