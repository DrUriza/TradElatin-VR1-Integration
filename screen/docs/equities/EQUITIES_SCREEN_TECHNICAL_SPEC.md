# Equities Screen Technical Specification

## Document status

**Runtime status: PRE-IMPLEMENTATION / PROPOSED / NOT IMPLEMENTED.**

This document freezes the Screen-side multi-market design for adding Equities
observability to TradELATIN VR1. The non-operational Market/Asset navigation
scaffold and Processing compatibility validator now exist. No Equities family
contract, fixture, provider connection, acquisition route, or operational
Equities visualization exists.

The current operational HMI remains the implemented BTC/CRYPTO C1-C8 experience.
Its frozen inventory of **33 logical endpoints across C1-C8** is unchanged.
Equities observables are a separate proposed extension: they do not replace,
rename, renumber, or change the ownership of any existing BTC endpoint. C9
remains the independent, pre-implementation Blockchain Financial Networks
family and must not be used as a container for Equities data.

## VR1 boundary

VR1 answers: **What is happening in the market?**

Screen may render observed price, volume, transactions, quotes, displayed
liquidity, volatility, positioning inputs, source status, and data quality. It
must not convert those observations into:

- structural states or regimes (VR2)
- forecasts, directional scores, setups, or trade signals (VR3)
- entries, stops, targets, sizing, risk decisions, paper trading, or execution (VR4)

SSL Market is a capability and observable reference. It is not a new HMI and
its decision, structure, risk, and execution features are outside this scope.

## Multi-market navigation

TradELATIN keeps one VR1 HMI with this conceptual hierarchy:

`Market -> Asset -> C-family`

Examples:

- `CRYPTO -> BTC -> C8`
- `EQUITIES -> US:NVDA -> C8`
- `EQUITIES -> US:TSLA -> C6`

The proposed global selection context is:

| Field | Purpose | Examples |
| --- | --- | --- |
| `market_class` | Select the market universe without changing family semantics | `CRYPTO`, `EQUITIES` |
| `asset_id` | Select a canonical instrument identity in that universe | `BTC`, `US:NVDA`, `US:AMD`, `US:TSLA`, `US:INTC`, `US:PLTR` |
| `family` | Select the existing observation family | `C1` through `C9` |

These names define a conceptual Screen requirement only. They do not freeze a
wire schema, URL route, query parameter, or implementation mechanism.

## Availability states

Each market/asset/family combination must declare one of these states:

| State | Meaning |
| --- | --- |
| `COMPLETE` | The validated source surface covers the family's required Equities observable set |
| `PARTIAL` | Some valid observables exist, but the family is not fully covered |
| `UNSUPPORTED` | The selected source does not currently provide the required observables |
| `NOT APPLICABLE` | Applying the family would change its established meaning |

Source availability is separate from capability. A temporarily unallocated or
disconnected Level II stream must not be presented as an unsupported asset.

## C-family coverage

| Family | Proposed Equities status | SSL/IBKR contribution | Screen decision |
| --- | --- | --- | --- |
| C1 Prices | `COMPLETE` | OHLCV, last, bid/ask, sizes, WAP, trade count, market references | Adapt the current price visual grammar |
| C2 CVD & Order Flow | `PARTIAL` | Time & Sales, estimated aggressor side, classified/unknown volume, tape delta, simple OFI | Render as estimated flow with explicit coverage; do not imply true exchange-side CVD |
| C3 Open Interest / Positioning | `PARTIAL` | Indicative shortable shares only | Keep separate from OI; wait for validated options OI, put/call, Greeks, and provider borrow fee |
| C4 Flows | `UNSUPPORTED` | No ETF creations/redemptions or capital-flow feed | Do not relabel transactions or reference prices as fund flows |
| C5 On-Chain / Market State | `NOT APPLICABLE` | No on-chain or miner data for Equities | Preserve the current Bitcoin meaning; show index references outside C5 |
| C6 Volatility | `PARTIAL` | VIX reference and observed intraday range/movement | Exclude structural regimes; wait for formal historical volatility and options IV surfaces |
| C7 Liquidations / Stress | `UNSUPPORTED` | Halt state and microstructure stress context, but no liquidation feed | Do not label halts, spread widening, or depth withdrawal as liquidations |
| C8 Liquidity Microstructure | `COMPLETE` | Level I/II, depth, spread, imbalance, Time & Sales, displayed-liquidity dynamics | First proposed Equities HMI family |
| C9 Blockchain Financial Networks | `NOT APPLICABLE` | No blockchain-network data | Keep independent and pre-implementation |

## Semantic guardrails

### C2

- A quote-test classification is estimated `BUY`, `SELL`, or `UNKNOWN`.
- `UNKNOWN` volume and classification coverage must remain visible.
- Cumulative CVD may be named only after Processing defines, validates, and
  versions the calculation and its direction semantics.
- Transfers, raw prints, and unsigned volume are not automatically CVD.
- Screen does not assign participant identity or reinterpret provider data.

### C8

- Use `Large Trades`, `Large Visible Orders`, and
  `Inferred Large-Liquidity Activity`.
- Never claim that a visible order or large trade identifies a whale,
  institution, beneficial owner, or intent.
- Displayed liquidity added/removed does not prove execution or cancellation.
- SMART or venue-specific depth is partial visible coverage, not a complete
  consolidated market book.
- Observable aggression versus price response may be displayed, but not an
  interpreted absorption state.
- Observable sweep sequences may be displayed, but not as a setup, forecast,
  continuation signal, or execution instruction.

## Screen architecture boundary

The future data path remains:

`SSL/IBKR source -> Processing -> Versioned VR1 Contract -> Screen`

Screen must not connect to IBKR or another provider. Processing owns source
acquisition, normalization, calculation definitions, provenance, quality, and
effective live status. Screen renders the versioned contract and the status
reported by Processing; it does not calculate or reinterpret provider data.

Future implementation must begin from an approved, versioned Processing
contract shared with Emulator and Integration. No API route or JSON schema is
frozen by this specification.
