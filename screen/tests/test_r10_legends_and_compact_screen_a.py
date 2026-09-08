from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCREENS = ROOT / "screens"


def test_prices_cvd_oi_screen_b_traces_have_explicit_names_for_legends() -> None:
    prices = (SCREENS / "prices.py").read_text(encoding="utf-8")
    cvd = (SCREENS / "cvd_volume_orderflow.py").read_text(encoding="utf-8")
    oi = (SCREENS / "open_interest_and_funding.py").read_text(encoding="utf-8")

    assert 'name="HISTOGRAM"' in prices
    assert 'name=SERIES_LABELS.get(series_name' in prices
    assert 'name=name.replace("_", " ").title()' in cvd
    assert 'name="HISTOGRAM"' in oi
    assert 'name=SERIES_LABELS.get(series_name' in oi

    for source in (prices, cvd, oi):
        assert 'trace.showlegend = True' in source
        assert 'apply_analysis_figure_layout(fig, height=220' in source


def test_four_block_screen_a_families_are_compact() -> None:
    cvd = (SCREENS / "cvd_volume_orderflow.py").read_text(encoding="utf-8")
    etf = (SCREENS / "etf_exchange_flows.py").read_text(encoding="utf-8")
    vol = (SCREENS / "volatility_market_regimes.py").read_text(encoding="utf-8")
    liq = (SCREENS / "long_short_liquidations.py").read_text(encoding="utf-8")

    assert 'grid-template-rows: 235px 185px;' in cvd
    assert 'height: 428px;' in cvd
    assert '"height": "235px"' in cvd
    assert '"height": "185px"' in cvd

    assert 'grid-template-rows: 225px 225px;' in etf
    assert 'height: 458px;' in etf
    assert 'max_rows=6' in etf
    assert 'height=225' in etf

    assert 'height:210px;min-height:210px;max-height:210px' in vol
    assert '"height":"210px","minHeight":"210px","maxHeight":"210px"' in vol

    for chart_id in (
        'hyperliquid-liquidation-map',
        'exchange-liquidation-maps',
        'binance-liquidation-map',
    ):
        assert f'graph_id="{chart_id}", height=220' in liq
    assert '_positioning_card(contract, height=220)' in liq


def test_onchain_five_block_screen_a_is_smaller_but_screen_b_stays_220() -> None:
    source = (SCREENS / "on_chain_miners.py").read_text(encoding="utf-8")
    assert 'grid-template-rows:217px 217px; gap:8px; height:442px;' in source
    assert 'figure=_metric_figure(contract, cid, range_id)' in source
    assert 'style={"height": "190px", "minHeight": "190px", "maxHeight": "190px", "width": "100%"}' in source
    assert 'chart_id="miner-net-position"' in source and 'height=190' in source
    # Screen B was not requested to shrink further.
    assert 'figure=_native_indicator_figure(contract, iid, range_id)' in source
    assert 'style={"height": "220px", "minHeight": "220px", "maxHeight": "220px", "width": "100%"}' in source


def test_modified_files_parse() -> None:
    for filename in (
        "prices.py",
        "cvd_volume_orderflow.py",
        "open_interest_and_funding.py",
        "etf_exchange_flows.py",
        "volatility_market_regimes.py",
        "long_short_liquidations.py",
        "on_chain_miners.py",
    ):
        path = SCREENS / filename
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
