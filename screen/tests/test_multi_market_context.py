from __future__ import annotations

import ast
from pathlib import Path

from screen_core.market_context import (
    ASSETS_BY_MARKET,
    CRYPTO,
    EQUITIES,
    assets_for_market,
    asset_options,
    asset_symbol,
    equities_capability,
    normalize_market_class,
    resolve_asset,
)
from screen_core.equities_contract import (
    EQUITIES_OBSERVABLE_FAMILY,
    EquitiesObservationError,
    validate_vr1_observation_v1,
)


ROOT = Path(__file__).resolve().parents[1]


def test_crypto_btc_remains_the_default_context() -> None:
    assert normalize_market_class(None) == CRYPTO
    assert assets_for_market(None) == ("BTC",)
    assert resolve_asset(None, None) == "BTC"


def test_equities_universe_is_explicit_and_deterministic() -> None:
    assert ASSETS_BY_MARKET[EQUITIES] == ("US:NVDA", "US:AMD", "US:TSLA", "US:INTC", "US:PLTR")
    assert resolve_asset(EQUITIES, "us:tsla") == "US:TSLA"
    assert resolve_asset(EQUITIES, "BTC") == "US:NVDA"
    assert asset_symbol("US:NVDA") == "NVDA"
    assert asset_options(EQUITIES)[0] == {"label": "NVDA", "value": "US:NVDA"}


def test_equities_family_capability_matrix_is_not_forced() -> None:
    assert equities_capability("C1").status == "COMPLETE"
    assert equities_capability("C2").status == "PARTIAL"
    assert equities_capability("C3").status == "PARTIAL"
    assert equities_capability("C4").status == "UNSUPPORTED"
    assert equities_capability("C5").status == "NOT APPLICABLE"
    assert equities_capability("C6").status == "PARTIAL"
    assert equities_capability("C7").status == "UNSUPPORTED"
    assert equities_capability("C8").status == "COMPLETE"
    assert equities_capability("C9").status == "NOT APPLICABLE"


def test_screen_declares_separate_market_class_and_contract_market_selectors() -> None:
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "'market-class-selector'" in source
    assert "'asset-selector'" in source
    assert "'market-selector'" in source
    assert "No Equities contract is active" in source


def _valid_observation() -> dict:
    return {
        "schema_version": "vr1-observation-v1",
        "market": "EQUITIES",
        "asset": "US:NVDA",
        "timestamp": "2026-09-26T12:00:00Z",
        "family": "C8",
        "observable_id": "eq_c8_spread",
        "value": 1.25,
        "units": "bps",
        "source": "ibkr",
        "source_mode": "REPLAY",
        "quality": "VALID",
        "metadata": {
            "contract_version": "vr1-observable-v2-draft",
            "symbol": "NVDA",
            "asset_class": "equity",
            "venue": "SMART",
            "source_status": "REPLAY",
            "capability": "COMPLETE",
            "derivation_type": "DERIVED",
            "method_version": "spread-bps-v1",
            "received_timestamp": "2026-09-26T12:00:01Z",
            "calculated_timestamp": "2026-09-26T12:00:02Z",
            "data_quality": {"quote_stale": False},
            "provenance": {},
        },
    }


def test_screen_registry_matches_processing_37_ids() -> None:
    assert len(EQUITIES_OBSERVABLE_FAMILY) == 37
    assert set(EQUITIES_OBSERVABLE_FAMILY.values()) == {"C1", "C2", "C3", "C6", "C8"}


def test_processing_observation_projection_is_accepted_without_reinterpretation() -> None:
    payload = _valid_observation()
    assert validate_vr1_observation_v1(payload) == payload


def test_unknown_or_cross_family_observations_are_rejected() -> None:
    payload = _valid_observation()
    payload["family"] = "C2"
    try:
        validate_vr1_observation_v1(payload)
    except EquitiesObservationError as exc:
        assert "observable_family_mismatch" in str(exc)
    else:
        raise AssertionError("cross-family observation was accepted")


def test_structural_python_files_parse() -> None:
    for relative in ("app.py", "screen_core/market_context.py", "screen_core/equities_contract.py"):
        path = ROOT / relative
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
