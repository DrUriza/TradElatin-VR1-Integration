# TradELATIN VR1 Integration

Build: `V4.2_FINAL_R10_GROK_RADAR_HF3.2`
Contract schema: `V4.2_CONTRACT_SCHEMA_R5`

This repository launches the Emulator, Processing runtime and Screen HMI as a
single local installation. The eight frozen VR1 contracts remain in `runtime/`;
Grok Radar is intentionally contractless.

## Windows quick start

1. Install Python 3.11 or newer and enable **Add Python to PATH**.
2. Copy `.env.example` to `.env`. Synthetic Emulator mode needs no provider
   credentials; add `XAI_API_KEY` only if Grok Radar will be used.
3. Run `start.bat` or, from PowerShell, `./start.ps1`.
4. Open the HMI URL printed by Integration.

The launch scripts create `.venv`, install the complete requirements set once,
and then run `main.py`. The launcher owns only the child processes it starts.
Its atomic `runtime/integration.lock.json` rejects a second live Integration,
recovers a demonstrably stale PID lock, and is removed during graceful shutdown.

## Validation

From the Integration root:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

The root suite discovers Integration, Emulator, Processing and Screen tests.

## Source control and multi-market boundary

For the current BTC runtime, Screen exposes `SYNTHETIC` and `LIVE`. Integration
starts Processing in automatic acquisition mode:

- `SYNTHETIC` uses the Emulator for all frozen C1–C8 inputs.
- `LIVE` validates each configured provider independently. A provider with a
  valid credential is used live; a missing, invalid or unreachable provider
  falls back to the Emulator for that provider. The HMI reports `LIVE`,
  `HYBRID`, or `SYNTHETIC FALLBACK` from the effective family results.
- One valid API key is therefore sufficient for a partial live run; it does not
  disable the other synthetic sources.

The source change is atomic and requests a refresh of all eight BTC families.
Provider credentials remain in the root `.env`; Screen never reads them and
never connects to a provider directly.

The embedded Emulator, Processing and Screen repositories also share a catalog
of 37 `PROPOSED EQUITIES OBSERVABLE` IDs and the conceptual
`vr1-observation-v1` projection. This is compatibility scaffolding only:
Integration does not currently start IBKR, acquire Equities data, publish an
Equities runtime contract or claim Equities end-to-end support. The existing
33 logical BTC/CRYPTO endpoints across C1–C8 remain frozen and unchanged.

## Runtime policy

- Prices publishes every 5 seconds.
- Liquidity KPI/snapshot/table updates publish every 5 seconds; structural
  graphs rebuild no slower than every 10 seconds.
- CVD publishes every 15 seconds.
- Open Interest, ETF, On-Chain, Volatility and Liquidations are manual-only.
- Open Interest supports `5m`, `15m` and `4h`; CVD also excludes `1m`.
- Prices, CVD and structural Liquidity use three supervised persistent workers;
  workers recycle after 120 jobs and fall back to one-shot execution if local
  multiprocessing is unavailable.
- CVD Futures `Price ↔ CVD Divergence` uses native Futures OHLC when supplied
  and the canonical BTC Spot price otherwise, so Emulator mode never publishes
  an all-null chart.
- Contextual-help popovers are portaled outside refreshed chart subtrees, so an
  open help card remains visually stable while its family contract refreshes.

## Future C9 / Stacks integration

**Status: PROPOSED / NOT IMPLEMENTED**

Current Integration launches and validates the existing C1–C8 Emulator,
Processing and Screen stack. Current C1–C8 public validation is primarily
emulator/synthetic/replay. Live-provider acquisition paths exist in Processing
but require external credentials and data access.

Current Integration does not include a Stacks adapter or C9 Stacks runtime. It
does not acquire or normalize Stacks data, calculate or render C9 observables,
start a Stacks process, publish a C9 contract, include C9 fixtures or run C9
end-to-end tests.

The shared C9 planning catalog contains 14 proposed logical source surfaces: 6 Core and 8 transversal. None is currently registered or executed by Integration.

Future funded C9 work would extend the same Integration orchestration pattern to
Stacks/sBTC:

```text
Emulator or Live Source
→ Processing Acquisition
→ C9 Normalization / Processing
→ Versioned C9 Contracts
→ Screen
→ End-to-End Integration Tests
```

Integration would orchestrate that future milestone flow. Processing would own
acquisition, normalization and computation; Emulator would own synthetic/replay
sources; and Screen would own representation.

End-to-end C9 validation is a future milestone, not current prior work. This
documentation does not claim that any grant milestone (M1, M2 or M3) has been
completed.

Future design documents:

- [C9 / Stacks Technical Specification](docs/c9/stacks/C9_STACKS_TECHNICAL_SPEC.md)
- [C9 / Stacks Endpoint Catalog](docs/c9/stacks/C9_STACKS_ENDPOINT_CATALOG.md)

Press `Ctrl+C` in the Integration console for a graceful shutdown.
