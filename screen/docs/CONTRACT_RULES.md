# Contract rendering rules

The deployment follows the frozen TradELATIN architecture:

`Input → Processing → Classification → Contract Builder → Vertical → Screen JSON → Dash HMI`

Dash only renders contract data. It does not calculate OHLC, technical indicators, classifications, market states, interpolations, estimates, or missing series. When a required block is absent, the screen displays `UNAVAILABLE` so the missing backend contract remains visible.

The `RELOAD JSON` button reloads the active family using the file modification timestamp and file size as the cache key.
