"""Shared indicator-selection persistence rules for Screen families.

The user selection is browser-owned UI state.  Defaults are only for a fresh
session where no persisted selection exists.  In particular, an explicit empty
selection (all checklists cleared) is valid state and must never be replaced by
DEFAULT_* values after a timeframe change or contract reread.
"""

from __future__ import annotations

from typing import Any, Callable

LOCAL_SELECTION_PERSISTENCE_TYPE = "local"


def resolve_persisted_selection(
    selection: Any,
    default_factory: Callable[[], dict[str, list[str]]],
) -> dict[str, list[str]]:
    """Return persisted UI selection verbatim; default only when it is missing.

    A dict whose lists are all empty is intentionally preserved.  We also keep
    an empty dict as explicit state instead of treating its falsiness as a cue
    to re-enable defaults.
    """
    if isinstance(selection, dict):
        return selection
    return default_factory()
