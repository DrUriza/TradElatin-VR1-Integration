# TradELATIN VR1 — Contextual Help Layer

This layer is presentation-only. It does not alter market contracts or calculate indicators.

## Runtime architecture

- `screen_core/contextual_help.py`: registry lookup and reusable help component.
- `data/help/contextual_help_vr1.json`: explanatory content for KPI, Screen A and Screen B labels.
- `assets/contextual_help.css`: visual behavior and mobile layout.
- `assets/contextual_help.js`: viewport-aware positioning so popovers do not clip inside cards or leave the visible screen.

## Interaction

- Desktop: hover/focus with a short delay.
- Keyboard: focusable contextual label.
- Touch/mobile: tap focuses the contextual label; the popover is pinned near the lower viewport edge.

## Popover sections

1. What it measures
2. Price relation
3. Cross-family relation
4. Interpretation
5. Variable type, when relevant

## Screen A coverage

All final Screen A KPI and principal graph names have registry coverage for the eight families:

- Prices
- CVD & Order Flow
- Open Interest & Funding
- ETF & Exchange Flows
- On-Chain & Miners
- Volatility & Market Regimes
- Liquidations & Positioning
- Liquidity Microstructure

No financial contract JSON was modified by this help layer.
