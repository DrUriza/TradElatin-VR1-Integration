from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4
from .source_control import FAMILIES, write_source_control

# HMI contract-watch cadence.  Processing still owns the market-data cadence
# (Prices=5 s, Liquidity=5 s, CVD=15 s). Prices and Liquidity are watched every
# second so a contract written just after a UI tick is displayed promptly;
# app.py only repaints when the contract revision actually changes.
FAMILY_AUTO_REFRESH_MS: dict[str, int] = {
    "prices": 1_000,
    "liquidity": 1_000,
    "cvd": 15_000,
}

DEFAULT_REFRESH_TIMEOUT_S = 120.0

BASE_DIR = Path(__file__).resolve().parent.parent


CANONICAL_FAMILY_NAMES = {
    "prices": "prices_ohlcv",
    "cvd": "cvd_volume_orderflow",
    "open_interest": "open_interest_and_funding",
    "etf": "etf_exchange_flows",
    "on_chain": "on_chain_miners",
    "volatility": "volatility_market_regimes",
    "liquidations": "long_short_liquidations",
    "liquidity": "liquidity_microstructure",
}


@dataclass(frozen=True)
class RefreshDispatch:
    configured: bool
    started: bool
    family: str
    endpoint: str | None
    request_id: str | None = None


def processing_refresh_dir() -> Path:
    value = os.getenv("TRADELATIN_REFRESH_DIR", "").strip() or os.getenv("TRADELATIN_PROCESSING_REFRESH_DIR", "").strip()
    return Path(value) if value else BASE_DIR / "data" / "refresh_requests"


def refresh_timeout_seconds() -> float:
    raw = os.getenv("TRADELATIN_REFRESH_TIMEOUT_S", str(DEFAULT_REFRESH_TIMEOUT_S))
    try:
        return max(5.0, float(raw))
    except (TypeError, ValueError):
        return DEFAULT_REFRESH_TIMEOUT_S


def _trace(message: str) -> None:
    if os.getenv("TRADELATIN_TRACE_REFRESH", "0").lower() in {"1", "true", "yes"}:
        print(f"[REFRESH] {message}", flush=True)


def _write_request(path: Path, payload: dict[str, object]) -> None:
    """Publish JSON atomically so Processing never observes a partial file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, allow_nan=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def request_family_refresh_async(*, family: str, reason: str, contract_file: str) -> RefreshDispatch:
    """Atomically create one filesystem request for every refresh action."""
    canonical_family = CANONICAL_FAMILY_NAMES.get(family, family)
    request_root = processing_refresh_dir()
    unique = f"{time.time_ns()}_{uuid4().hex}"
    request_id = f"HMI_REFRESH_{canonical_family}_{unique}"
    requested_at_epoch = time.time()
    payload: dict[str, object] = {
        "schema": "tradelatin.hmi.refresh-request.v1",
        "request_id": request_id,
        "family": canonical_family,
        "reason": reason,
        "contract_file": contract_file,
        "requested_at": datetime.now(tz=UTC).isoformat(),
        "requested_at_epoch": requested_at_epoch,
    }
    destination = request_root / f"{request_id}.json"
    try:
        _write_request(destination, payload)
    except OSError as exc:
        _trace(f"family={canonical_family} request failed: {exc}")
        return RefreshDispatch(False, False, canonical_family, str(destination), request_id)
    _trace(f"family={canonical_family} request={destination}")
    return RefreshDispatch(True, True, canonical_family, str(destination), request_id)

def request_source_mode_async(*, requested_mode: str, contract_file: str) -> RefreshDispatch:
    control=write_source_control(requested_mode); request_root=processing_refresh_dir(); unique=f"{time.time_ns()}_{uuid4().hex}"; request_id=f"HMI_SOURCE_{requested_mode.upper()}_{unique}"
    payload={"schema":"tradelatin.hmi.source-refresh-request.v1","request_id":request_id,"families":list(FAMILIES),"reason":"source_mode","requested_mode":requested_mode,"source_generation":control["generation"],"contract_file":contract_file,"requested_at":datetime.now(tz=UTC).isoformat(),"requested_at_epoch":time.time()}
    destination=request_root/f"{request_id}.json"
    try: _write_request(destination,payload)
    except OSError as exc:
        _trace(f"source={requested_mode} request failed: {exc}"); return RefreshDispatch(False,False,"all",str(destination),request_id)
    return RefreshDispatch(True,True,"all",str(destination),request_id)
