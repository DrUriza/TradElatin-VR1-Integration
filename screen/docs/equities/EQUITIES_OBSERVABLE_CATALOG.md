# Proposed Equities Observable Catalog

**Status for every entry:** PROPOSED EQUITIES OBSERVABLE — NOT IMPLEMENTED
**Canonical source:** TradELATIN VR1 Processing registry

These are proposed logical observable IDs, not active endpoints, routes, JSON
fields, or additions to the frozen **33 BTC/CRYPTO logical endpoints across
C1-C8**. Screen mirrors Processing's isolated 37-ID registry so Integration can
verify ownership and reject unknown or cross-family observations. C4, C5, C7,
and C9 intentionally have no Equities IDs.

## C1 — Prices

| Logical observable ID | Type | Purpose | Principal restriction |
| --- | --- | --- | --- |
| `eq_c1_trade_price` | RAW | Execution or last price | Preserve source granularity |
| `eq_c1_best_quote` | RAW | Reported best bid and ask | Preserve routing, data type, and staleness |
| `eq_c1_ohlcv_bar` | RAW | OHLCV for an explicit interval | Declare session and adjustment policy |
| `eq_c1_previous_close` | RAW | Provider previous close | Declare session and adjustment basis |
| `eq_c1_wap` | RAW | Provider weighted average price for a bar | Do not relabel as session VWAP |
| `eq_c1_reference_quote` | RAW | ES/NQ/VIX reference quote | Context is not causality |
| `eq_c1_midpoint` | DERIVED | Bid/ask midpoint | Suppress invalid or crossed quotes |
| `eq_c1_return` | DERIVED | Return over an explicit window | Declare basis, window, and missing-data policy |

## C2 — CVD & Order Flow

| Logical observable ID | Type | Purpose | Principal restriction |
| --- | --- | --- | --- |
| `eq_c2_trade_size` | RAW | Reported executed size | Preserve feed coverage and units |
| `eq_c2_trade_count` | RAW | Provider trade count per bar | Does not reconstruct trade sequence |
| `eq_c2_volume_rate` | DERIVED | Executed volume per unit time | Declare granularity and gaps |
| `eq_c2_trade_rate` | DERIVED | Trades per unit time | Do not silently mix bar and tick counts |
| `eq_c2_estimated_aggressor_volume` | INFERRED | Estimated BUY/SELL/UNKNOWN volume | Quote-test estimate, not provider fact |
| `eq_c2_estimated_cvd` | INFERRED | Estimated cumulative volume delta | Publish coverage and unknown volume |
| `eq_c2_classification_coverage` | DERIVED | Fraction classified BUY or SELL | Quality fact, not predictive confidence |
| `eq_c2_large_trade_activity` | DERIVED | Trades above a versioned threshold | No participant identity or intent |

## C3 — Open Interest / Positioning

| Logical observable ID | Type | Purpose | Principal restriction |
| --- | --- | --- | --- |
| `eq_c3_shortable_shares` | RAW | Indicative shortable shares | Not OI, borrow fee, locate, short interest, or positioning |

## C6 — Volatility

| Logical observable ID | Type | Purpose | Principal restriction |
| --- | --- | --- | --- |
| `eq_c6_realized_volatility` | DERIVED | Realized variability by estimator/window | No structural regime label |
| `eq_c6_intraday_range` | DERIVED | High-low range | Declare interval, session, and gaps |
| `eq_c6_gap` | DERIVED | Session price gap | Adjustment policy required |
| `eq_c6_vix_reference` | RAW | Observed VIX reference | Separate instrument, not asset realized volatility |

## C8 — Liquidity Microstructure

| Logical observable ID | Type | Purpose | Principal restriction |
| --- | --- | --- | --- |
| `eq_c8_top_of_book_size` | RAW | Displayed best bid/ask size | Venue and units required |
| `eq_c8_depth_level` | RAW | Visible price/size/side level | Handle operations, resets, and sequence integrity |
| `eq_c8_spread` | DERIVED | Absolute and bps spread | Suppress stale, crossed, or mismatched quotes |
| `eq_c8_top_imbalance` | DERIVED | Top-of-book imbalance | Version formula and missing-size behavior |
| `eq_c8_microprice` | DERIVED | Size-weighted top price | Descriptive, not forecast or fair value |
| `eq_c8_visible_bid_depth` | DERIVED | Displayed bid depth by scope | Publish levels, completeness, and venue |
| `eq_c8_visible_ask_depth` | DERIVED | Displayed ask depth by scope | Publish levels, completeness, and venue |
| `eq_c8_depth_imbalance` | DERIVED | Relative visible-depth imbalance | Require matched scopes and valid snapshot |
| `eq_c8_depth_concentration` | DERIVED | Concentration across depth levels | Publish formula and book scope |
| `eq_c8_displayed_liquidity_change` | DERIVED | Added/removed displayed size | Removal is not necessarily cancellation or execution |
| `eq_c8_large_visible_order` | DERIVED | Visible size above threshold | No whale, institution, or intent claim |
| `eq_c8_visible_liquidity_persistence` | DERIVED | Duration/recurrence of visible liquidity | Does not prove one participant |
| `eq_c8_time_sales` | RAW | Normalized execution sequence | Preserve coverage and event/receipt times |
| `eq_c8_large_liquidity_activity` | INFERRED | Concurrence of large executed/displayed activity | No identity, intent, absorption, or causality |
| `eq_c8_observable_sweep_behavior` | INFERRED | Rapid executions across visible levels | No signal or structural state |
| `eq_c8_depth_tape_alignment` | INFERRED | Quantitative depth/tape alignment or conflict | Not confirmation or causality |

## Unsupported or non-applicable families

| Family | Capability | Reason |
| --- | --- | --- |
| C4 — Flows | UNSUPPORTED | Volume, signed volume, and depth changes are not ETF/fund/capital flows |
| C5 — On-Chain / Market State | NOT_APPLICABLE | Equities data is not the BTC on-chain/miner domain |
| C7 — Liquidations / Stress | UNSUPPORTED | Halts, VIX, spread, and depth withdrawal are not liquidations |
| C9 — Blockchain Financial Networks | NOT_APPLICABLE | SSL/IBKR is not a blockchain source |

## Shared contract boundary

Screen accepts the Processing compatibility projection only after it validates:

- `schema_version = vr1-observation-v1`
- `market = EQUITIES`
- canonical `asset` identity such as `US:NVDA`
- exact family/observable ownership
- `source_mode`, `quality`, `source_status`, and `capability` enums
- `RAW`, `DERIVED`, or `INFERRED` derivation metadata
- a method version for every non-RAW observation
- data-quality and provenance objects

This validator does not activate acquisition or aggregate individual
observations into a Screen family contract. Until Processing and Integration
publish that versioned aggregation, the Equities HMI remains explicitly
`NOT IMPLEMENTED` and never displays BTC data under an Equities selection.
