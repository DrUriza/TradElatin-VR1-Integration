from __future__ import annotations

import ast
from pathlib import Path

from screen_core.selection_state import resolve_persisted_selection

ROOT = Path(__file__).resolve().parents[1]
FAMILY_FILES = (
    ROOT / "screens" / "prices.py",
    ROOT / "screens" / "cvd_volume_orderflow.py",
    ROOT / "screens" / "open_interest_and_funding.py",
)
ALL_SCREEN_B_FILES = FAMILY_FILES + (
    ROOT / "screens" / "liquidity_microstructure.py",
    ROOT / "screens" / "etf_exchange_flows.py",
    ROOT / "screens" / "on_chain_miners.py",
    ROOT / "screens" / "volatility_market_regimes.py",
    ROOT / "screens" / "long_short_liquidations.py",
)


def test_empty_selection_is_not_replaced_by_defaults() -> None:
    defaults = lambda: {"trend": ["ema_9"], "volume": ["volume"]}
    empty = {"trend": [], "volume": []}
    assert resolve_persisted_selection(empty, defaults) is empty
    assert resolve_persisted_selection({}, defaults) == {}


def test_partial_selection_is_preserved_exactly() -> None:
    defaults = lambda: {"trend": ["ema_9", "ema_21"], "volume": ["volume"]}
    partial = {"trend": ["ema_9"], "bands": ["bollinger_bands"], "volume": ["volume"]}
    assert resolve_persisted_selection(partial, defaults) is partial


def test_defaults_only_apply_when_selection_is_missing_or_invalid() -> None:
    defaults = lambda: {"trend": ["ema_9"]}
    assert resolve_persisted_selection(None, defaults) == {"trend": ["ema_9"]}
    assert resolve_persisted_selection([], defaults) == {"trend": ["ema_9"]}


def test_frozen_timeframe_matrix_keeps_explicit_empty_selection() -> None:
    defaults = lambda: {"trend": ["ema_9"], "bands": ["bollinger_bands"], "volume": ["volume"]}
    matrices = {
        "prices": ("1m", "5m", "15m", "4h"),
        "cvd": ("5m", "15m", "4h"),
        "open_interest": ("5m", "15m", "4h"),
    }
    for family, timeframes in matrices.items():
        selection = {"trend": [], "bands": [], "derived_analysis": [], "momentum": [], "volatility": [], "volume": []}
        original = selection.copy()
        for _timeframe in timeframes:
            selection = resolve_persisted_selection(selection, defaults)
            assert selection == original, (family, _timeframe)


def test_prices_requested_partial_selection_survives_all_timeframes() -> None:
    defaults = lambda: {"trend": ["ema_9", "ema_21"], "bands": ["bollinger_bands"], "volume": ["volume"]}
    selection = {
        "trend": ["ema_9"],
        "bands": ["bollinger_bands"],
        "derived_analysis": [],
        "momentum": [],
        "volatility": [],
        "volume": ["volume"],
    }
    expected = {key: list(value) for key, value in selection.items()}
    for _timeframe in ("1m", "5m", "15m", "4h"):
        selection = resolve_persisted_selection(selection, defaults)
        assert selection == expected


def test_all_three_families_use_local_checklist_persistence() -> None:
    for path in FAMILY_FILES:
        source = path.read_text(encoding="utf-8")
        assert "persistence_type=LOCAL_SELECTION_PERSISTENCE_TYPE" in source, path.name
        assert 'persistence_type="memory"' not in source, path.name


def test_analysis_callbacks_do_not_use_truthiness_fallback() -> None:
    for path in FAMILY_FILES:
        source = path.read_text(encoding="utf-8")
        assert "resolve_persisted_selection(selection," in source, path.name
        assert "selection or _default_selection" not in source, path.name


def test_all_screen_b_families_keep_selection_in_local_storage() -> None:
    for path in ALL_SCREEN_B_FILES:
        source = path.read_text(encoding="utf-8")
        assert (
            'storage_type="local"' in source
            or 'persistence_type="local"' in source
            or "LOCAL_SELECTION_PERSISTENCE_TYPE" in source
        ), path.name
        assert 'storage_type="session"' not in source, path.name
        assert 'persistence_type="memory"' not in source, path.name


def test_list_based_screen_b_selectors_preserve_explicit_empty_lists() -> None:
    from screens.long_short_liquidations import _validated_selection as liquidations_selection
    from screens.volatility_market_regimes import _validated_selection as volatility_selection

    assert liquidations_selection([]) == []
    assert volatility_selection([]) == []
    assert liquidations_selection(None)
    assert volatility_selection(None)


def test_timeframe_change_does_not_rebuild_indicator_pages() -> None:
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "PERSISTENT_INDICATOR_TIMEFRAME_ROUTES" in source
    assert "ctx.triggered_id == 'timeframe-selector'" in source
    for symbol in ("prices.ROUTE", "cvd_volume_orderflow.ROUTE", "open_interest_and_funding.ROUTE"):
        assert symbol in source


def test_main_figures_rehydrate_from_persisted_values_on_page_load() -> None:
    targets = {
        "prices.py": "update_price_figure",
        "cvd_volume_orderflow.py": "update_cvd_candles",
        "open_interest_and_funding.py": "update_open_interest_figure",
    }
    for filename, function_name in targets.items():
        source = (ROOT / "screens" / filename).read_text(encoding="utf-8")
        function_index = source.index(f"def {function_name}(")
        callback_index = source.rfind("@callback(", 0, function_index)
        decorator = source[callback_index:function_index]
        assert "prevent_initial_call=False" in decorator, filename


def test_modified_python_files_parse() -> None:
    for path in (*FAMILY_FILES, ROOT / "app.py", ROOT / "screen_core" / "selection_state.py"):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
