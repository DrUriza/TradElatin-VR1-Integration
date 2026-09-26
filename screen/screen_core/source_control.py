from __future__ import annotations
import json, os, tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4
BASE_DIR = Path(__file__).resolve().parent.parent
FAMILIES=("prices_ohlcv","cvd_volume_orderflow","open_interest_and_funding","etf_exchange_flows","on_chain_miners","volatility_market_regimes","long_short_liquidations","liquidity_microstructure")
PROVIDERS=("coinglass","cryptoquant","glassnode")
def source_control_path():
    value=os.getenv("TRADELATIN_SOURCE_CONTROL_PATH","").strip(); return Path(value) if value else BASE_DIR/"data/runtime/source_control.json"
def source_status_dir():
    value=os.getenv("TRADELATIN_SOURCE_STATUS_DIR","").strip(); return Path(value) if value else BASE_DIR/"data/runtime/source_status"
def read_source_control():
    try: payload=json.loads(source_control_path().read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError): payload={}
    mode=str(payload.get("requested_mode") or "synthetic").lower(); mode=mode if mode in {"live","synthetic"} else "synthetic"
    return {"requested_mode":mode,"generation":str(payload.get("generation") or "default")}
def write_source_control(requested_mode):
    mode=str(requested_mode).lower()
    if mode not in {"live","synthetic"}: raise ValueError(f"unsupported_requested_source:{requested_mode}")
    payload={"schema":"tradelatin.hmi.source-control.v1","requested_mode":mode,"generation":uuid4().hex,"updated_at":datetime.now(tz=UTC).isoformat().replace("+00:00","Z")}
    destination=source_control_path(); destination.parent.mkdir(parents=True,exist_ok=True); fd,tmp=tempfile.mkstemp(prefix=f".{destination.name}.",suffix=".tmp",dir=destination.parent)
    try:
        with os.fdopen(fd,"w",encoding="utf-8",newline="\n") as handle: json.dump(payload,handle,ensure_ascii=False,allow_nan=False,indent=2); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(tmp,destination)
    except Exception:
        try: os.unlink(tmp)
        except OSError: pass
        raise
    return payload
def aggregate_source_status():
    control=read_source_control(); requested,generation=control["requested_mode"],control["generation"]; records={}
    for family in FAMILIES:
        try: payload=json.loads((source_status_dir()/f"{family}.json").read_text(encoding="utf-8"))
        except (OSError,json.JSONDecodeError): continue
        if isinstance(payload,dict) and payload.get("generation")==generation: records[family]=payload
    if requested=="synthetic": effective="synthetic"
    else:
        live=sum(x.get("effective_mode")=="live" for x in records.values()); synthetic=sum(x.get("effective_mode")=="synthetic" for x in records.values())
        effective="live" if live==len(FAMILIES) else "hybrid" if live else "synthetic_fallback" if synthetic else "validating"
    providers={}
    for provider in PROVIDERS:
        states=[str(x.get("providers",{}).get(provider) or "") for x in records.values() if isinstance(x.get("providers"),dict)]
        providers[provider]="live" if "live" in states else "invalid_or_unreachable" if "invalid_or_unreachable" in states else "missing_key" if "missing_key" in states else "emulator"
    reasons=[f"{family}: {item.get('fallback_reason')}" for family,item in records.items() if item.get("fallback_reason")]
    return {"requested_mode":requested,"effective_mode":effective,"generation":generation,"completed_families":len(records),"total_families":len(FAMILIES),"providers":providers,"reasons":reasons}
