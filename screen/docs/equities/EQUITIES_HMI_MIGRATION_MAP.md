# Equities HMI Migration Map

## Document status

**Runtime status: PRE-IMPLEMENTATION / PROPOSED / NOT IMPLEMENTED.**

This map defines the proposed order and visual reuse for adding Equities to the
single VR1 HMI. Market/Asset selection and truthful pre-implementation states
are structurally implemented; family rendering remains gated by versioned
Processing contracts and end-to-end Integration validation.

## Current-screen reuse

| Current VR1 screen | Equities disposition | Reuse / adaptation | New view required |
| --- | --- | --- | --- |
| C1 Prices | First follow-on after C8 | Reuse OHLCV, price, return, volume, and indicator layout; add instrument/session context | No independent HMI; adapt the existing family |
| C2 CVD & Order Flow | Follow-on, `PARTIAL` | Reuse signed-flow visual grammar with estimated BUY/SELL/UNKNOWN, delta bounds, and coverage | Tape-quality and trade-size blocks may be required |
| C3 Open Interest / Funding | Hold, `PARTIAL` | Do not map shortable shares into OI/Funding | Future Equities options-positioning view after validated data exists |
| C4 ETF & Exchange Flows | Block, `UNSUPPORTED` | None from current SSL/IBKR surface | No view until an actual flow source is validated |
| C5 On-Chain & Miners | Block, `NOT APPLICABLE` | Preserve BTC meaning | None for current Equities scope |
| C6 Volatility / Market Regimes | Follow-on, `PARTIAL` | Reuse volatility layout for observed range and VIX context only | Remove/disable structural-regime semantics; future IV/HV views need sources |
| C7 Liquidations / Stress | Block, `UNSUPPORTED` | Do not reuse liquidation panels for halts or book stress | Possible future Equities stress view only after separate approval |
| C8 Liquidity Microstructure | First implementation candidate | Reuse the existing depth, large-order, large-trade, imbalance, spread, persistence, and aggression grammar | Add Level II ladder and Time & Sales detail where needed |
| C9 Blockchain Financial Networks | Block, `NOT APPLICABLE` | No SSL/IBKR role | None |

## Proposed C8 Equities composition

### Screen A — Current market surface

| Block | Equities contents | Guardrail |
| --- | --- | --- |
| Order Book Depth | Level II ladder, accumulated bid/ask depth, spread, midpoint, microprice | Visible/partial depth only |
| Large Visible Orders | Side, price, size, distance to midpoint, age/persistence, source scope | No participant identity or intent |
| Large Trades | Timestamp, price, size, exchange, estimated side, classification status | Threshold defined and versioned by Processing |
| KPI row | Bid depth, ask depth, spread, imbalance, midpoint; price impact only if formally derived | Missing metrics remain unavailable, never invented |

### Screen B — Liquidity dynamics

| Block | Proposed observable view | Guardrail |
| --- | --- | --- |
| Depth imbalance / pressure | Imbalance history and duration | Descriptive, not predictive |
| Spread / microprice / OFI | Top-of-book dynamics | OFI is not automatically CVD |
| Displayed liquidity change | Bid/ask visible size added and removed | Not proven execution/cancellation |
| Large-order persistence | Appearance, duration, movement, disappearance | `Large Visible Orders`, not whales |
| Executed liquidity response | Estimated aggression versus observed price displacement | Observable relation, not absorption state |
| Sweep and trade-size activity | Level traversal, large trades, size distribution | No setup, participant identity, or continuation claim |

## Proposed selector behavior

One global Market selector precedes an Asset selector. The C-family navigation
remains the existing family navigation.

| Market | Initial asset examples | Family behavior |
| --- | --- | --- |
| `CRYPTO` | `BTC` | Preserve the current C1-C8 implementation and frozen endpoint inventory |
| `EQUITIES` | `US:NVDA`, `US:AMD`, `US:TSLA`, `US:INTC`, `US:PLTR` | Render family availability and consume only versioned Equities contracts |

The selector must not create a separate SSL Market application. An Equities
asset may show `COMPLETE`, `PARTIAL`, `UNSUPPORTED`, `NOT APPLICABLE`, or a
separate temporarily unavailable/source-status condition.

## Conceptual Processing contract expectation

Screen will eventually require Processing to supply at least the following
context. This is a conceptual requirement, not a frozen JSON schema:

| Context item | Screen use |
| --- | --- |
| `market_class` | Distinguish CRYPTO and EQUITIES without changing family ownership |
| `asset_id` | Identify the selected instrument |
| `family` | Identify the rendered C-family |
| `source_status` | Render Processing-determined effective source state |
| `data_quality` | Render freshness, coverage, unknown/unclassified share, and limitations |
| `capabilities` | Determine which observable blocks are valid for the selected asset/source |

Processing must also provide timestamps, units, provenance, session/venue scope,
calculation versions, and unavailable reasons wherever applicable. Screen must
not infer these from missing values.

## Migration gates

1. Freeze the shared Equities logical-observable catalog across Screen,
   Processing, Emulator, and Integration.
2. Approve versioned Processing contracts and compatibility rules; do not alter
   the frozen BTC contracts or their 33-endpoint inventory.
3. Add deterministic Emulator scenarios for every contracted Equities state,
   including missing, stale, partial-depth, and unknown-aggressor conditions.
4. Validate the end-to-end Integration path and source-status propagation.
5. Implement the Market and Asset selectors in the existing HMI.
6. Implement C8 Equities first, then C1, C2, and partial C6.
7. Keep C3 gated by validated positioning/options sources and keep C4, C5, C7,
   and C9 blocked as documented.

No Screen implementation should begin before gates 1 through 4 are approved.

## Excluded SSL functionality

| Excluded information | Destination |
| --- | --- |
| Impulse, continuation, exhaustion, interpreted absorption, structural regimes | VR2 |
| LONG/SHORT, predictive scores, setup confirmation, READY, NO_TRADE | VR3 |
| Entry, stop, targets, sizing, risk, paper trading, execution | VR4 |
