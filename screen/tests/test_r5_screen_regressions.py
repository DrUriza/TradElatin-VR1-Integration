from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _load_liquidation_filter():
    path = ROOT / "screens" / "long_short_liquidations.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = {target.id for target in node.targets if isinstance(target, ast.Name)}
            if "LIQUIDATION_ANALYSIS_RANGE_SECONDS" in names:
                selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name == "_filter_points_for_range":
            selected.append(node)
    module = ast.Module(body=selected, type_ignores=[])
    namespace: dict[str, Any] = {"Any": Any}
    exec(compile(module, str(path), "exec"), namespace)
    return namespace["_filter_points_for_range"]


def test_liquidations_screen_b_filters_unix_seconds_by_range() -> None:
    fn = _load_liquidation_filter()
    base = 1_800_000_000
    points = [{"timestamp": base + index * 900, "value": index} for index in range(500)]
    one_day = fn(points, "1d")
    seven_days = fn(points, "7d")
    thirty_days = fn(points, "30d")
    assert 90 <= len(one_day) <= 100
    assert len(seven_days) == 500
    assert len(thirty_days) == 500
    assert one_day[0]["timestamp"] > points[0]["timestamp"]


def test_liquidations_filter_is_unit_safe_for_milliseconds() -> None:
    fn = _load_liquidation_filter()
    base = 1_800_000_000_000
    points = [{"timestamp": base + index * 900_000, "value": index} for index in range(500)]
    assert 90 <= len(fn(points, "1d")) <= 100


def test_cvd_and_etf_strength_rows_use_semantic_color_fallbacks() -> None:
    cvd = (ROOT / "screens" / "cvd_volume_orderflow.py").read_text(encoding="utf-8")
    etf = (ROOT / "screens" / "etf_exchange_flows.py").read_text(encoding="utf-8")
    for source, prefix in ((cvd, "cvd"), (etf, "etf")):
        assert f"def _{prefix}_signal_color(" in source
        assert f"def _{prefix}_strength_count(" in source
        assert '"#20d05c"' in source
        assert '"#ff3d55"' in source
        assert '"#ffab00"' in source
        assert f"_{prefix}_strength_dots(\n                            strength_count," in source or f"_{prefix}_strength_dots(strength_count, signal_color)" in source


def test_liquidity_hmi_watch_is_fast_but_data_cadence_remains_five_seconds() -> None:
    refresh = (ROOT / "screen_core" / "refresh.py").read_text(encoding="utf-8")
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert '"liquidity": 1_000' in refresh
    assert "current_revision = contract_revision(module.CONTRACT_FILE)" in app
    assert "previous_revision == current_revision" in app
    assert '"liquidity_data_seconds": 5' in app


def test_screen_exposes_exact_build_health_identity() -> None:
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert 'SCREEN_BUILD_ID = os.getenv("TRADELATIN_SCREEN_BUILD_ID", "V4.2_FINAL_R10_GROK_RADAR_HF3.1")' in app
    assert '@server.route("/__tradelatin__/health", methods=["GET"])' in app
    assert '"build_id": SCREEN_BUILD_ID' in app


def test_modified_screen_python_parses() -> None:
    for rel in (
        "app.py",
        "screen_core/refresh.py",
        "screens/cvd_volume_orderflow.py",
        "screens/etf_exchange_flows.py",
        "screens/long_short_liquidations.py",
    ):
        path = ROOT / rel
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
