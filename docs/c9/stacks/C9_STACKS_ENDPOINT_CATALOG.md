# C9 / Stacks Endpoint Catalog

## Catalog status

**Entire catalog status: PROPOSED / NOT IMPLEMENTED**

This catalog freezes the future C9 Core and transversal data surfaces shared
across the VR1 repositories. It does not register endpoints, modify
`main.py`, add processes, create fixtures, publish runtime contracts or add C9
tests to Integration.

Current Integration continues to launch and validate only C1–C8. The proposed
C9 surface count is not part of the current C1–C8 runtime inventory.

## Frozen observables

| ID | Observable | Intended purpose | Status |
|---|---|---|---|
| C9.1 | sBTC Supply & Peg State | Describe sBTC supply, reconciliation and peg context. | PROPOSED / NOT IMPLEMENTED |
| C9.2 | sBTC Bridge Flow | Describe normalized bridge deposits and withdrawals. | PROPOSED / NOT IMPLEMENTED |
| C9.3 | sBTC Bridge Operational State | Describe limits, chain state and signer condition. | PROPOSED / NOT IMPLEMENTED |

## C9 Core surfaces

| Proposed surface | Primary observable support | Intended future Integration role | Status |
|---|---|---|---|
| `sbtc_token_supply` | C9.1 | Route the selected source through Processing to the versioned supply/peg contract. | PROPOSED / NOT IMPLEMENTED |
| `sbtc_bridge_deposits` | C9.2 | Orchestrate acquisition-to-contract validation for bridge deposit lifecycle data. | PROPOSED / NOT IMPLEMENTED |
| `sbtc_bridge_withdrawals` | C9.2 | Orchestrate acquisition-to-contract validation for bridge withdrawal lifecycle data. | PROPOSED / NOT IMPLEMENTED |
| `sbtc_bridge_limits` | C9.3 | Validate that bridge constraints reach the versioned operational-state contract. | PROPOSED / NOT IMPLEMENTED |
| `sbtc_bridge_chainstate` | C9.3 | Validate source, freshness and contract publication for bridge chain state. | PROPOSED / NOT IMPLEMENTED |
| `sbtc_signer_state` | C9.3 | Validate source, freshness and contract publication for signer state. | PROPOSED / NOT IMPLEMENTED |

## Transversal surfaces

| Proposed surface | Potential contextual consumer | Semantic constraint | Status |
|---|---|---|---|
| `sbtc_ft_transfers` | C2, C4, C8 | transfers != CVD automatically | PROPOSED / NOT IMPLEMENTED |
| `sbtc_holder_distribution` | C4, C5 | Holder concentration is not exchange flow or miner state. | PROPOSED / NOT IMPLEMENTED |
| `sbtc_dex_trades` | C1, C2, C8 | DEX trades require explicit venue and aggressor semantics. | PROPOSED / NOT IMPLEMENTED |
| `sbtc_amm_pool_state` | C1, C8 | AMM liquidity != order-book depth | PROPOSED / NOT IMPLEMENTED |
| `sbtc_lending_market_state` | C3, C6 | lending != Open Interest/Funding | PROPOSED / NOT IMPLEMENTED |
| `sbtc_protocol_liquidations` | C6, C7 | protocol liquidations != derivatives liquidations | PROPOSED / NOT IMPLEMENTED |
| `stacks_fee_state` | C6, C9 | Network fees are not market spread or volatility. | PROPOSED / NOT IMPLEMENTED |
| `stacks_mempool_activity` | C6, C9 | Mempool load is operational context, not traded volume. | PROPOSED / NOT IMPLEMENTED |

## Proposed Integration flow

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

Integration would validate the chain as an orchestrated system. It would not
own provider parsing, normalization, financial calculations or HMI
recalculation.

"C9 owns the Stacks/sBTC data, while C1–C8 can consume C9 observables for cross-family contextual analysis."

## Source and validation policy

Future implementation may use either an authorized live adapter or a future C9
Emulator/replay source. Both must converge on the same normalized, versioned C9
contract boundary.

Current C1–C8 public validation is primarily emulator/synthetic/replay.
Live-provider acquisition paths exist in Processing but require external
credentials and data access. Current Integration contains no equivalent Stacks
adapter or C9 runtime.

No route paths, request parameters, response schemas, provider assignments,
contract versions or process topology are frozen by this catalog. Those details
require source validation and explicit implementation during future funded
work.

## Inventory exclusion

None of the fourteen proposed surfaces is currently implemented by Integration.
They must not be counted as runtime endpoints or completed prior work until
their adapters, normalization, versioned contracts, Screen surfaces and
end-to-end tests have been implemented and validated in a future authorized
milestone.

End-to-end C9 validation is a future milestone, not current prior work. This
catalog does not assert that M1, M2 or M3 is complete.
