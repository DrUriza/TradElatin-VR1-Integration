# TradELATIN VR1 Integration

Build: `V4.2_FINAL_R10_GROK_RADAR_HF3.1`  
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

Press `Ctrl+C` in the Integration console for a graceful shutdown.
