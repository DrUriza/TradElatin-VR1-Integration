from __future__ import annotations

import json
from pathlib import Path

from processing_signals.input import acquisition


REQUEST = {
    "provider": "coinglass",
    "endpoint_id": "spot_ohlcv",
    "path": "/api/spot/ohlcv",
    "params": {"symbol": "BTC"},
}


def _configure(monkeypatch, tmp_path: Path, mode: str) -> tuple[Path, Path]:
    control = tmp_path / "source_control.json"
    status = tmp_path / "source_status"
    control.write_text(
        json.dumps({"requested_mode": mode, "generation": "test-generation"}),
        encoding="utf-8",
    )
    monkeypatch.setenv("TRADELATIN_SOURCE_CONTROL_PATH", str(control))
    monkeypatch.setenv("TRADELATIN_SOURCE_STATUS_DIR", str(status))
    monkeypatch.setenv("TRADELATIN_EMULATOR_BASE_URL", "http://127.0.0.1:8000")
    return control, status


def test_auto_synthetic_uses_emulator(monkeypatch, tmp_path: Path) -> None:
    _, status = _configure(monkeypatch, tmp_path, "synthetic")
    monkeypatch.setattr(acquisition, "_fetch_emulator", lambda **_: b'{"data": []}')

    result = acquisition.AcquisitionClient(tmp_path, "prices_ohlcv", "auto").fetch(
        **REQUEST
    )

    assert result == {"data": []}
    record = json.loads((status / "prices_ohlcv.json").read_text(encoding="utf-8"))
    assert record["effective_mode"] == "synthetic"
    assert record["providers"]["coinglass"] == "emulator"


def test_auto_live_missing_key_falls_back_to_emulator(monkeypatch, tmp_path: Path) -> None:
    _, status = _configure(monkeypatch, tmp_path, "live")
    monkeypatch.delenv("COINGLASS_API_KEY", raising=False)
    monkeypatch.setattr(acquisition, "_fetch_emulator", lambda **_: b'{"data": [1]}')

    result = acquisition.AcquisitionClient(tmp_path, "prices_ohlcv", "auto").fetch(
        **REQUEST
    )

    assert result == {"data": [1]}
    record = json.loads((status / "prices_ohlcv.json").read_text(encoding="utf-8"))
    assert record["effective_mode"] == "synthetic"
    assert record["providers"]["coinglass"] == "missing_key"
    assert "coinglass" in record["fallback_reason"]
