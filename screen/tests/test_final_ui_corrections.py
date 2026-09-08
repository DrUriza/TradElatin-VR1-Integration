from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCREENS = ROOT / "screens"


def _source(name: str) -> str:
    path = SCREENS / name
    source = path.read_text(encoding="utf-8")
    ast.parse(source, filename=str(path))
    return source


def test_prices_generic_volume_is_colored_by_candle_direction() -> None:
    source = _source("prices.py")
    assert 'volume_title = "BUY / SELL VOLUME" if _has_buy_sell_volume(records) else "VOLUME"' in source
    assert 'rgba(0,199,140,0.82)' in source
    assert 'rgba(255,77,109,0.82)' in source
    assert 'float(record.get("close")) >= float(record.get("open"))' in source


def test_cvd_screen_b_restores_right_indicator_controls() -> None:
    source = _source("cvd_volume_orderflow.py")
    assert "def _analysis_indicator_controls" in source
    for component_id in (
        "cvd-derived-selectors",
        "cvd-momentum-selectors",
        "cvd-volatility-selectors",
    ):
        assert component_id in source
    assert "_analysis_indicator_controls(selection)" in source


def test_etf_screen_b_restores_right_indicator_controls() -> None:
    source = _source("etf_exchange_flows.py")
    assert "def _analysis_indicator_controls" in source
    for component_id in ("etf-derived", "etf-momentum", "etf-volatility"):
        assert component_id in source
    assert 'persistence_type="local"' in source


def test_current_state_summaries_are_explicit_for_range_based_families() -> None:
    assert "CURRENT MINER REGIME SUMMARY" in _source("on_chain_miners.py")
    assert "CURRENT VOLATILITY REGIME SUMMARY" in _source("volatility_market_regimes.py")
    assert 'summary_title = f"CURRENT {summary_title}"' in _source("long_short_liquidations.py")


def test_liquidations_screen_b_consumes_range_selector() -> None:
    source = _source("long_short_liquidations.py")
    assert "ANALYSIS_RANGE_SECONDS" in source
    assert "def _analysis_points_for_range" in source
    assert 'Input("range-selector", "value", allow_optional=True)' in source
    assert "_analysis_figure(contract, indicator_id, range_id=range_id" in source
    assert "fixed 500-record 15m source window" in source
