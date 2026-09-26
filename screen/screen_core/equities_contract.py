"""Validation boundary for Processing's proposed Equities observations.

The module mirrors the frozen logical IDs and the ``vr1-observation-v1``
projection published by VR1 Processing.  It does not activate an Equities
runtime, choose a provider, derive values, or aggregate observations into HMI
contracts.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Mapping


PROPOSED_EQUITIES_STATUS = "PROPOSED EQUITIES OBSERVABLE — NOT IMPLEMENTED"

_IDS_BY_FAMILY = {
    "C1": (
        "eq_c1_trade_price", "eq_c1_best_quote", "eq_c1_ohlcv_bar",
        "eq_c1_previous_close", "eq_c1_wap", "eq_c1_reference_quote",
        "eq_c1_midpoint", "eq_c1_return",
    ),
    "C2": (
        "eq_c2_trade_size", "eq_c2_trade_count", "eq_c2_volume_rate",
        "eq_c2_trade_rate", "eq_c2_estimated_aggressor_volume",
        "eq_c2_estimated_cvd", "eq_c2_classification_coverage",
        "eq_c2_large_trade_activity",
    ),
    "C3": ("eq_c3_shortable_shares",),
    "C6": (
        "eq_c6_realized_volatility", "eq_c6_intraday_range", "eq_c6_gap",
        "eq_c6_vix_reference",
    ),
    "C8": (
        "eq_c8_top_of_book_size", "eq_c8_depth_level", "eq_c8_spread",
        "eq_c8_top_imbalance", "eq_c8_microprice", "eq_c8_visible_bid_depth",
        "eq_c8_visible_ask_depth", "eq_c8_depth_imbalance",
        "eq_c8_depth_concentration", "eq_c8_displayed_liquidity_change",
        "eq_c8_large_visible_order", "eq_c8_visible_liquidity_persistence",
        "eq_c8_time_sales", "eq_c8_large_liquidity_activity",
        "eq_c8_observable_sweep_behavior", "eq_c8_depth_tape_alignment",
    ),
}

EQUITIES_OBSERVABLE_IDS_BY_FAMILY: Mapping[str, tuple[str, ...]] = MappingProxyType(_IDS_BY_FAMILY)
EQUITIES_OBSERVABLE_FAMILY: Mapping[str, str] = MappingProxyType(
    {observable_id: family for family, ids in _IDS_BY_FAMILY.items() for observable_id in ids}
)

SOURCE_MODES = frozenset({"LIVE", "SYNTHETIC", "REPLAY"})
SOURCE_STATUSES = frozenset({"LIVE", "FROZEN", "DELAYED", "DELAYED_FROZEN", "REPLAY", "UNAVAILABLE"})
QUALITY_STATES = frozenset({"VALID", "PARTIAL", "STALE", "INVALID", "UNKNOWN"})
CAPABILITY_STATES = frozenset({"COMPLETE", "PARTIAL", "UNSUPPORTED", "NOT_APPLICABLE"})
DERIVATION_TYPES = frozenset({"RAW", "DERIVED", "INFERRED"})


class EquitiesObservationError(ValueError):
    """A proposed Equities observation violates the shared Processing boundary."""


def _required_text(payload: Mapping[str, Any], key: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise EquitiesObservationError(f"{key}_must_not_be_empty")
    return value


def _enum_value(payload: Mapping[str, Any], key: str, allowed: frozenset[str]) -> str:
    value = _required_text(payload, key).upper()
    if value not in allowed:
        raise EquitiesObservationError(f"unsupported_{key}:{value}")
    return value


def validate_vr1_observation_v1(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one Processing projection without calculating or reinterpreting it."""
    if not isinstance(payload, Mapping):
        raise EquitiesObservationError("observation_must_be_object")
    if payload.get("schema_version") != "vr1-observation-v1":
        raise EquitiesObservationError("unsupported_schema_version")
    if str(payload.get("market") or "").upper() != "EQUITIES":
        raise EquitiesObservationError("market_must_be_equities")

    asset = _required_text(payload, "asset").upper()
    if not asset.startswith("US:"):
        raise EquitiesObservationError("asset_id_must_use_canonical_namespace")
    family = _required_text(payload, "family").upper()
    observable_id = _required_text(payload, "observable_id")
    expected_family = EQUITIES_OBSERVABLE_FAMILY.get(observable_id)
    if expected_family is None:
        raise EquitiesObservationError(f"unknown_equities_observable:{observable_id}")
    if family != expected_family:
        raise EquitiesObservationError(f"observable_family_mismatch:{observable_id}:{family}")

    metadata = payload.get("metadata")
    if not isinstance(metadata, Mapping):
        raise EquitiesObservationError("metadata_must_be_object")
    _required_text(payload, "timestamp")
    _required_text(payload, "units")
    _required_text(payload, "source")
    _enum_value(payload, "source_mode", SOURCE_MODES)
    _enum_value(payload, "quality", QUALITY_STATES)
    _required_text(metadata, "contract_version")
    _required_text(metadata, "symbol")
    _required_text(metadata, "asset_class")
    _required_text(metadata, "venue")
    _enum_value(metadata, "source_status", SOURCE_STATUSES)
    _enum_value(metadata, "capability", CAPABILITY_STATES)
    derivation = _enum_value(metadata, "derivation_type", DERIVATION_TYPES)
    if derivation != "RAW" and not str(metadata.get("method_version") or "").strip():
        raise EquitiesObservationError("method_version_required_for_non_raw_observable")
    for key in ("data_quality", "provenance"):
        if not isinstance(metadata.get(key), Mapping):
            raise EquitiesObservationError(f"{key}_must_be_object")

    return dict(payload)
