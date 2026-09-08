from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_cvd_and_etf_analysis_controls_have_colored_bullets() -> None:
    targets = {
        "cvd_volume_orderflow.py": ["#20d05c", "#a65cff", "#2ea8ff"],
        "etf_exchange_flows.py": ["#2ea8ff", "#b36bff", "#ffb000", "#20d05c"],
    }
    for filename, colors in targets.items():
        source = (ROOT / "screens" / filename).read_text(encoding="utf-8")
        assert 'def _option_label(' in source, filename
        assert 'html.Span("●"' in source, filename
        for color in colors:
            assert color in source, (filename, color)


def test_liquidations_analysis_screen_reads_range_selector_and_filters_points() -> None:
    source = (ROOT / "screens" / "long_short_liquidations.py").read_text(encoding="utf-8")
    assert 'def _filter_points_for_range(' in source
    assert 'Input("range-selector", "value", allow_optional=True)' in source
    assert '_analysis_screen(load_contract(CONTRACT_FILE), selection, range_id)' in source
    assert 'def _analysis_figure(contract: dict[str, Any], indicator_id: str, range_id: str | None = None' in source
    assert "uirevision=f\"liq-analysis-{indicator_id}-{block.get('selected_range', '1d')}\"" in source


def test_modified_files_parse() -> None:
    for filename in (
        "cvd_volume_orderflow.py",
        "etf_exchange_flows.py",
        "long_short_liquidations.py",
    ):
        path = ROOT / "screens" / filename
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
