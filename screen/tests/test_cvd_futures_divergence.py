from __future__ import annotations

import json
import math
from pathlib import Path

from screens.cvd_volume_orderflow import _indicator_figure


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "data" / "contracts" / "cvd_volume_orderflow_VR1_FINAL.json"


def _contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_bundled_futures_price_cvd_divergence_has_real_points_in_every_timeframe():
    contract = _contract()

    for timeframe in ("5m", "15m", "4h"):
        indicator = contract["technical_analysis"]["markets"]["futures"][
            "timeframes"
        ][timeframe]["indicators"]["price_cvd_divergence"]
        values = indicator["series"]["divergence"]

        assert indicator["status"] == "available"
        assert any(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
            for value in values
        )
        assert indicator["current"]["divergence"] is not None


def test_futures_price_cvd_divergence_figure_contains_visible_data():
    figure = _indicator_figure(
        _contract(), "futures", "15m", "price_cvd_divergence"
    )

    assert figure.data
    assert any(
        value is not None
        for trace in figure.data
        for value in trace.y
    )
