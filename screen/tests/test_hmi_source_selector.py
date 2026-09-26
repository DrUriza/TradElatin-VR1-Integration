import json
from pathlib import Path
from screen_core.source_control import aggregate_source_status, write_source_control
def test_hmi_has_only_desired_live_and_synthetic():
    source=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")
    assert "'source-mode-selector'" in source; assert "'value':'synthetic'" in source; assert "'value':'live'" in source; assert "'value':'hybrid'" not in source
def test_effective_status_can_be_hybrid(monkeypatch,tmp_path):
    monkeypatch.setenv("TRADELATIN_SOURCE_CONTROL_PATH",str(tmp_path/"control.json")); monkeypatch.setenv("TRADELATIN_SOURCE_STATUS_DIR",str(tmp_path/"status")); control=write_source_control("live"); (tmp_path/"status").mkdir()
    common={"generation":control["generation"],"requested_mode":"live","providers":{}}
    (tmp_path/"status/prices_ohlcv.json").write_text(json.dumps({**common,"effective_mode":"live"}),encoding="utf-8"); (tmp_path/"status/etf_exchange_flows.json").write_text(json.dumps({**common,"effective_mode":"synthetic"}),encoding="utf-8")
    assert aggregate_source_status()["effective_mode"]=="hybrid"
