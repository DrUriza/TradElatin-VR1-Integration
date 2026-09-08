from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_all_screen_b_families_use_shared_fixed_visual_grammar() -> None:
    targets = {
        "prices.py",
        "cvd_volume_orderflow.py",
        "open_interest_and_funding.py",
        "liquidity_microstructure.py",
        "etf_exchange_flows.py",
        "on_chain_miners.py",
        "volatility_market_regimes.py",
        "long_short_liquidations.py",
    }
    for filename in targets:
        source = (ROOT / "screens" / filename).read_text(encoding="utf-8")
        for class_name in (
            "screen-b-layout",
            "screen-b-grid",
            "screen-b-card",
            "screen-b-card-title",
            "screen-b-graph",
            "screen-b-selector",
        ):
            assert class_name in source, (filename, class_name)
        assert '"height": "220px"' in source, filename
        assert '"minHeight": "220px"' in source, filename
        assert '"maxHeight": "220px"' in source, filename

    css = (ROOT / "assets" / "screen_b_homology.css").read_text(encoding="utf-8")
    assert "grid-template-columns: repeat(3, minmax(0, 1fr))" in css
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in css
    assert "grid-template-columns: minmax(0, 1fr)" in css
    assert "height: 220px !important" in css


def test_fixed_graph_css_prevents_responsive_height_bounce() -> None:
    checks = {
        "prices.py": ".prices-analysis-card-graph .js-plotly-plot",
        "cvd_volume_orderflow.py": ".cvd-analysis-card-graph .js-plotly-plot",
        "open_interest_and_funding.py": ".oi-analysis-card-graph .js-plotly-plot",
        "etf_exchange_flows.py": ".etf-analysis-card-graph .js-plotly-plot",
    }
    for filename, css_selector in checks.items():
        source = (ROOT / "screens" / filename).read_text(encoding="utf-8")
        assert css_selector in source, filename
        assert "max-height: 220px !important" in source, filename


def test_liquidity_selector_uses_shared_screen_b_visual_grammar() -> None:
    source = (ROOT / "screens" / "liquidity_microstructure.py").read_text(encoding="utf-8")
    css = (ROOT / "assets" / "tradelatin.css").read_text(encoding="utf-8")
    assert 'className="screen-b-selector liquidity-analysis-controls"' in source
    assert 'className="screen-b-selector-title liquidity-selector-title"' in source
    assert 'className="liquidity-selector-group"' in source
    assert 'className="liquidity-analysis-checklist"' in source
    assert 'accent-color: #2f80ff' in css
    assert '.liquidity-analysis-checklist label' in css
    assert 'color: #c7d2da !important' in css


def test_r6_build_identity_is_exact() -> None:
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert '"V4.2_FINAL_R10_GROK_RADAR_HF3.1"' in app


def test_modified_python_files_parse() -> None:
    for filename in (
        "prices.py",
        "cvd_volume_orderflow.py",
        "open_interest_and_funding.py",
        "liquidity_microstructure.py",
        "etf_exchange_flows.py",
        "on_chain_miners.py",
        "volatility_market_regimes.py",
        "long_short_liquidations.py",
    ):
        path = ROOT / "screens" / filename
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
