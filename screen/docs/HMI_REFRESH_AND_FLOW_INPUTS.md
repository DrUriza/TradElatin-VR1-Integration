# TradELATIN VR1 — HMI refresh and flow input boundary

This document describes the **Screens/HMI consumption boundary only**. Screens never computes market percentages, delta normalization, positioning shares, or market classifications.

## Family refresh ownership

Processing owns all automatic work. Screens/HMI never schedules Prices, CVD, or Open Interest acquisition.

| Family | Processing policy | HMI request policy |
| --- | --- | --- |
| Prices | continuous, run-to-completion | observe contract only |
| CVD | scheduled every 15 s | observe contract only |
| Open Interest | on demand | manual Reload |
| ETF | on demand | manual Reload |
| On-Chain | on demand | manual Reload |
| Volatility | on demand | manual Reload |
| Liquidations | on demand | manual Reload |
| Liquidity | scheduled every 5 s | observe contract only |

For the five on-demand families, HMI atomically creates one request in
`TradElatin-VR1-Proccesing/data/refresh_requests`. The directory can be
overridden with `TRADELATIN_PROCESSING_REFRESH_DIR`. Requests use canonical
Processing family names and a unique filename beginning with `HMI_REFRESH_`:

```json
{
  "schema": "tradelatin.hmi.refresh-request.v1",
  "request_id": "HMI_REFRESH_open_interest_and_funding_<unique>",
  "family": "open_interest_and_funding",
  "reason": "manual",
  "contract_file": "liquidity_microstructure_VR1_FINAL.json",
  "requested_at": "2026-08-22T12:00:00+00:00",
  "requested_at_epoch": 1787400000.0
}
```

Processing validates the canonical family name, runs only that family, writes
the final contract atomically to Screens `data/contracts`, and removes the
request after success. There is no HTTP fallback and no short-name alias map.

The HMI `dcc.Interval` is only a contract observer. It never requests work.
While a manual family is updating, HMI keeps the last valid contract visible,
displays `UPDATING`, and swaps the visible state only after the new JSON parses
successfully.

If the filesystem mailbox is not configured, a manual Reload only re-reads the
current local contract; it does not invent data or start a second scheduler.


## Incremental chart mutation policy

The provider/Emulator transport contract may return a fixed **500 records per request**, but those 500 rows are a synchronization window, **not permission to rewrite historical candles on every refresh**.

After bootstrap, timestamped market series follow live-chart semantics:

- closed historical buckets are immutable in normal incremental operation;
- the current/open bucket may be replaced while it is forming;
- when a bucket closes, the new bucket is appended;
- if polling was interrupted, only genuinely missing newer buckets are appended;
- older rows returned again inside the provider's 500-record window are ignored for normal incremental display updates;
- event streams keep their event-id/watermark logic; current snapshots such as order books/maps remain full snapshots and can replace their current state.

This is the same operational distinction used by market terminals: bootstrap/history is bulk, while the live lane mutates only the right edge of a time series. The HMI still reads one atomic JSON contract and performs no market calculation.

## Spot / Futures / Perpetual Flow

Preferred runtime chart names:

- `charts.spot_flow`
- `charts.perpetual_flow` or `charts.futures_flow`

Preferred per-timeframe shape:

```json
{
  "series_by_timeframe": {
    "5m": {
      "timeframe": "5m",
      "current": {
        "buy_flow_pct": 63.0,
        "sell_flow_pct": 37.0,
        "net_flow_pct": 26.0,
        "exchange": "Binance"
      },
      "bars": [
        {"timestamp": 0, "net_flow_pct": 12.0}
      ]
    }
  }
}
```

HMI does **not** derive `buy_flow_pct`/`sell_flow_pct` from `delta_buy_sell_usd`, a ratio, volume, or any other field. If the percentage shares are absent, the visual is `UNAVAILABLE` or `PARTIAL`.

The renderer supports the legacy `delta_buy_sell_spot` / `delta_buy_sell_futures` chart paths only as containers for future Processing-published flow fields; legacy delta is never converted into percentages by HMI.

## Long / Short Ratio

Long/Short exposes one canonical positioning view per exchange and timeframe. Processing publishes the already-computed fields `long_share`, `short_share`, `long_percent`, `short_percent`, and `long_short_ratio`; HMI never derives them. No positioning-variant selector is part of the public contract.

HMI supports exchange/timeframe nested structures when Processing publishes them, for example:

```text
charts.long_short_positioning
└── series_by_exchange
    └── Binance
        └── series_by_timeframe
            ├── 1m
            ├── 5m
            ├── 15m
            └── 4h
```

HMI never derives Long% / Short% from an L/S ratio. A variant with only a ratio but no published percentage shares remains unavailable in the 0–100% primary bar.
