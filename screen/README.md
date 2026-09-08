# TradELATIN VR1 Screen V4.2

Standalone Dash/HMI repository. It does **not** contain or start the Emulator and it does not start Processing.
The repository includes the latest eight validated contracts as initial data,
so the HMI is usable immediately after cloning; a separately running Processing
repository can replace them through `TRADELATIN_CONTRACT_DIR`.

## Configuration

- `TRADELATIN_CONTRACT_DIR`: directory containing the eight final JSON contracts. Default: `./data/contracts`.
- `TRADELATIN_REFRESH_DIR`: directory where manual refresh requests are written. Default: `./data/refresh_requests`.
- `TRADELATIN_HOST`: default `127.0.0.1`.
- `TRADELATIN_PORT`: default `8002`.

Automatic UI reread policy:

- Prices: 5 s
- Liquidity: 5 s
- CVD: 15 s

CVD timeframes: `5m`, `15m`, `4h` only. Screen rejects stale CVD contracts outside this set.

OI, ETF, On-Chain, Volatility and Liquidations use the manual Reload button.

## Run

On Windows, `start.bat` or `./start.ps1` creates the local virtual environment
and starts the HMI. Manual setup:

```powershell
python -m pip install -r requirements.txt
python main.py
```

## Indicator selection persistence

All eight Screen B families keep indicator checklist state in browser local
storage. Timeframe changes do not rebuild `page-content` for Prices, CVD and
Open Interest; their dedicated callbacks update the figures instead. An
explicit empty selection is valid state and is never replaced by defaults. The
same selection therefore survives timeframe changes, contract rereads, A/B
navigation and browser refreshes until the user changes it.

## Final UI corrections

- Prices generic OHLCV volume is colored by candle direction when no true taker buy/sell split exists.
- CVD and ETF Screen B include native indicator selectors in the right column.
- On-Chain and Volatility right summaries are current-state snapshots; 7D/30D changes historical charts only.
- Liquidations Screen B consumes the 1D/7D/30D range selector and reports when the requested window exceeds the frozen 500×15m history available in the contract.
- While a manual family is updating, contract-completion polling runs every 250 ms.


## Grok Radar

`/grok-radar` is a contractless, on-demand route. It uses `XAI_API_KEY` from the process environment and does not participate in the eight market-family contract refresh pipeline.
