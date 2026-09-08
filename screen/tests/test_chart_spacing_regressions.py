from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_open_interest_main_chart_forces_current_data_range():
    source = (ROOT / "screens" / "open_interest_and_funding.py").read_text(encoding="utf-8")
    assert "x_padding = (x[-1] - x[-2]) / 2" in source
    assert "range=[x[0] - x_padding, x[-1] + x_padding]" in source


def test_onchain_analysis_grid_does_not_stretch_to_sidebar_height():
    source = (ROOT / "screens" / "on_chain_miners.py").read_text(encoding="utf-8")
    assert "align-items:start" in source
    assert "align-content:start; align-self:start" in source
