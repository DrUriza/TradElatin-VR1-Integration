from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_prices_cvd_oi_etf_are_compact_like_volatility() -> None:
    files = (
        "prices.py",
        "cvd_volume_orderflow.py",
        "open_interest_and_funding.py",
        "etf_exchange_flows.py",
    )
    for filename in files:
        source = (ROOT / "screens" / filename).read_text(encoding="utf-8")
        assert 'height=220' in source, filename
        assert '"height": "220px"' in source, filename
        assert '"minHeight": "220px"' in source, filename
        assert '"maxHeight": "220px"' in source, filename
        assert '"responsive": False' in source, filename
        assert 'animate=False' in source, filename


def test_prices_cvd_oi_indicator_columns_match_compact_volatility_width() -> None:
    for filename in ("prices.py", "cvd_volume_orderflow.py", "open_interest_and_funding.py"):
        source = (ROOT / "screens" / filename).read_text(encoding="utf-8")
        assert 'grid-template-columns: minmax(0, 1fr) 286px;' in source, filename
    assert 'className="screen-b-selector prices-analysis-controls"' in (ROOT / "screens" / "prices.py").read_text(encoding="utf-8")
    assert 'className="screen-b-selector cvd-analysis-controls"' in (ROOT / "screens" / "cvd_volume_orderflow.py").read_text(encoding="utf-8")
    assert 'className="screen-b-selector oi-analysis-controls"' in (ROOT / "screens" / "open_interest_and_funding.py").read_text(encoding="utf-8")


def test_onchain_screen_a_and_b_are_compact() -> None:
    source = (ROOT / "screens" / "on_chain_miners.py").read_text(encoding="utf-8")
    assert 'grid-template-rows:217px 217px' in source
    assert 'height:442px' in source
    assert 'height=220' in source
    assert '"height": "220px"' in source
    assert '"responsive": False' in source
    assert 'animate=False' in source


def test_r8_python_files_parse() -> None:
    for filename in (
        "prices.py", "cvd_volume_orderflow.py", "open_interest_and_funding.py",
        "on_chain_miners.py", "etf_exchange_flows.py"
    ):
        path = ROOT / "screens" / filename
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
