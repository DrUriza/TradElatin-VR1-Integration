"""Multi-market Screen context without provider or contract acquisition.

This module owns only navigation capabilities.  It deliberately contains no
IBKR connection, JSON schema, market calculation, or synthetic Equities data.
"""

from __future__ import annotations

from dataclasses import dataclass


CRYPTO = "crypto"
EQUITIES = "equities"
DEFAULT_MARKET_CLASS = CRYPTO

ASSETS_BY_MARKET: dict[str, tuple[str, ...]] = {
    CRYPTO: ("BTC",),
    EQUITIES: ("US:NVDA", "US:AMD", "US:TSLA", "US:INTC", "US:PLTR"),
}


@dataclass(frozen=True)
class FamilyCapability:
    family: str
    status: str
    reason: str


EQUITIES_CAPABILITIES: dict[str, FamilyCapability] = {
    "C1": FamilyCapability("C1", "COMPLETE", "OHLCV, Level I quotes, price, volume, WAP, and market references are proposed."),
    "C2": FamilyCapability("C2", "PARTIAL", "Time & Sales and estimated BUY/SELL/UNKNOWN flow are proposed; validated cumulative CVD is not implemented."),
    "C3": FamilyCapability("C3", "PARTIAL", "Indicative shortable shares are proposed; options OI, put/call, Greeks, and provider borrow fee are unavailable."),
    "C4": FamilyCapability("C4", "UNSUPPORTED", "SSL/IBKR does not currently provide validated ETF creations/redemptions or capital-flow observations."),
    "C5": FamilyCapability("C5", "NOT APPLICABLE", "The existing family retains its Bitcoin on-chain and miner meaning."),
    "C6": FamilyCapability("C6", "PARTIAL", "VIX reference and observed intraday range are proposed; formal HV and options IV are unavailable."),
    "C7": FamilyCapability("C7", "UNSUPPORTED", "Halt and microstructure stress are not liquidation events."),
    "C8": FamilyCapability("C8", "COMPLETE", "Level I/II, depth, spread, imbalance, Time & Sales, and displayed-liquidity dynamics are proposed."),
    "C9": FamilyCapability("C9", "NOT APPLICABLE", "Blockchain Financial Networks remains independent from SSL/IBKR Equities."),
}


def normalize_market_class(value: str | None) -> str:
    candidate = str(value or "").strip().lower()
    return candidate if candidate in ASSETS_BY_MARKET else DEFAULT_MARKET_CLASS


def assets_for_market(value: str | None) -> tuple[str, ...]:
    return ASSETS_BY_MARKET[normalize_market_class(value)]


def resolve_asset(market_class: str | None, asset_id: str | None) -> str:
    assets = assets_for_market(market_class)
    candidate = str(asset_id or "").strip().upper()
    return candidate if candidate in assets else assets[0]


def asset_symbol(asset_id: str | None) -> str:
    """Return a visual symbol without discarding the canonical asset ID."""
    normalized = str(asset_id or "").strip().upper()
    return normalized.rsplit(":", 1)[-1] if normalized else ""


def asset_options(market_class: str | None) -> list[dict[str, str]]:
    return [
        {"label": asset_symbol(asset_id), "value": asset_id}
        for asset_id in assets_for_market(market_class)
    ]


def equities_capability(family: str | None) -> FamilyCapability:
    key = str(family or "").strip().upper()
    return EQUITIES_CAPABILITIES.get(
        key,
        FamilyCapability(key or "UNKNOWN", "UNSUPPORTED", "No Equities capability is declared for this route."),
    )
