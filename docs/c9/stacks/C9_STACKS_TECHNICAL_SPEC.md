# C9 / Stacks Technical Specification

## Status and scope

**Status: PROPOSED / NOT IMPLEMENTED**

This document defines how a future funded C9/Stacks capability would be
integrated across the TradELATIN VR1 Emulator, Processing and Screen
repositories. It is architecture and grant-scope documentation only.

The current Integration repository remains an operational C1–C8 stack. It has
no Stacks adapter, no C9 acquisition path, no C9 runtime process, no C9
contracts, no C9 fixtures and no C9 end-to-end tests. Nothing in this document
asserts that Milestone 1, Milestone 2 or Milestone 3 has been completed.

## Proposed C9 architecture

The proposed domain flow is:

```text
Stacks/sBTC
→ Adapter
→ Normalization
→ Versioned C9 Contracts
→ Financial Observables
→ HMI
```

The proposed Integration orchestration is:

```text
Emulator or Live Source
↓
Processing Acquisition
↓
C9 Normalization/Processing
↓
Versioned C9 Contracts
↓
Screen
↓
End-to-End Integration Tests
```

"C9 owns the Stacks/sBTC data, while C1–C8 can consume C9 observables for cross-family contextual analysis."

C9 therefore owns acquisition semantics, normalization, provenance and contract
versioning for Stacks/sBTC. Cross-family consumption does not transfer ownership
to C1–C8 and must not relabel C9 primitives as native exchange, derivatives,
miner or order-book measurements.

## Current Integration boundary

Current Integration launches and validates the existing C1–C8 Emulator,
Processing and Screen stack. Its public validation is primarily based on
Emulator-generated synthetic/replay data. Processing contains live-provider
acquisition paths for the current families, but those paths require external
credentials and provider data access.

Current Integration does **not**:

- connect to Stacks, Hiro, Emily or an sBTC data source;
- configure or start a Stacks adapter;
- register C9 in `main.py`;
- create an additional process or scheduler family;
- publish or validate a C9 runtime contract;
- include C9 fixtures or replay scenarios;
- expose a C9 Screen route;
- execute C9 end-to-end tests.

## Future source substitution boundary

Future funded work should preserve one normalized contract boundary regardless
of whether data comes from a live adapter or the Emulator:

```text
Live Stacks/sBTC provider
              ↘
               Processing Acquisition
              ↗
Future C9 Emulator/replay
↓
C9 Normalization/Processing
↓
Versioned C9 Contracts
```

A live source would supply validated Stacks/sBTC payloads through a dedicated
adapter. A future Emulator extension would supply deterministic,
provider-compatible synthetic/replay scenarios. Processing would normalize
either source into the same versioned C9 contracts. Integration would select,
launch and observe the authorized source without moving normalization or market
logic into the launcher.

## Frozen C9 financial observables

The future C9 contract family freezes these three observables:

1. **C9.1 — sBTC Supply & Peg State**  
   Describes observable sBTC supply, reconciliation and peg-state context.
2. **C9.2 — sBTC Bridge Flow**  
   Describes normalized sBTC bridge deposits and withdrawals while preserving
   direction, amount, lifecycle status and time.
3. **C9.3 — sBTC Bridge Operational State**  
   Describes bridge limits, chain state and signer condition needed to explain
   operational availability and constraints.

These names are frozen for documentation and future contract design. Their
adapters, schemas, routes and runtime implementations remain
**PROPOSED / NOT IMPLEMENTED**.

## Frozen future data catalog

The C9 Core surfaces are:

- `sbtc_token_supply`
- `sbtc_bridge_deposits`
- `sbtc_bridge_withdrawals`
- `sbtc_bridge_limits`
- `sbtc_bridge_chainstate`
- `sbtc_signer_state`

The transversal surfaces are:

- `sbtc_ft_transfers`
- `sbtc_holder_distribution`
- `sbtc_dex_trades`
- `sbtc_amm_pool_state`
- `sbtc_lending_market_state`
- `sbtc_protocol_liquidations`
- `stacks_fee_state`
- `stacks_mempool_activity`

The identifiers match the shared C9 catalog used by the other VR1
repositories. They are catalog entries, not implemented Integration endpoints.

## Future Integration responsibilities

When funded and authorized, Integration would be responsible for:

- configuring an approved live or Emulator C9 source;
- propagating source configuration and credentials without exposing secrets;
- starting only the processes defined by the approved C9 architecture;
- verifying service readiness and version compatibility;
- routing C9 contract output to Screen without HMI-side recalculation;
- preserving atomic publication and last-valid-contract behavior;
- coordinating graceful shutdown and preventing orphaned C9 workers;
- exposing observability for source, contract version, freshness and failures;
- running reproducible end-to-end validation across Emulator/Live Source,
  Processing, versioned contracts and Screen.

Integration must remain orchestration-only. Provider acquisition belongs to
Processing adapters, financial transformations belong to Processing, and
presentation belongs to Screen.

## Future end-to-end acceptance model

Future C9 end-to-end tests should be introduced only with the funded runtime
implementation. The intended acceptance chain is:

1. Start the approved future C9 source.
2. Verify provider-shape or Emulator compatibility.
3. Acquire primitives through Processing.
4. Normalize identifiers, timestamps, units, amounts and status enums.
5. Publish a versioned C9 contract atomically.
6. Render the corresponding financial observables in Screen.
7. Verify provenance, freshness, fallback behavior and graceful shutdown.
8. Verify that cross-family consumers use only published C9 observables.

This is a future acceptance plan. It is not a description of tests that exist
today and is not evidence of completed grant work.

## Semantic safeguards

- Token transfers may contextualize C2, but **transfers != CVD automatically**.
- Lending state may contextualize C3, but **lending != Open Interest/Funding**.
- AMM pool state may contextualize C8, but **AMM liquidity != order-book depth**.
- Protocol liquidations may contextualize C7, but **protocol liquidations !=
  derivatives liquidations**.

Every future derivation must preserve source surface, transformation, contract
version, provenance and limitations.
