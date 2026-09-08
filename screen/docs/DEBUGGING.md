# Quick debugging

## Start one application

```powershell
.un.ps1
```

Open:

```text
http://127.0.0.1:8002/prices?lang=en
```

Use `EN | ES` in the top bar. The same Dash process stays alive; switching language updates only `url.search` and does not perform a browser reload.

## Language state

There is exactly one language state:

```text
?lang=en
?lang=es
```

There is no cookie, localStorage state, locale store, MutationObserver, DOM translator, or EN/ES process split.

Optional trace:

```powershell
$env:TRADELATIN_TRACE_I18N="1"
.un.ps1
```

## Chattering checklist

The repository deliberately contains no active:

- language MutationObserver;
- DOM translation;
- cookie/localStorage locale authority;
- `location.reload()` language switch;
- process-specific EN/ES launchers;
- callback that consumes `url.search` and writes `url.search`.

The language callback graph is regression-tested.

## Screen B language regression

Prices Screen B explicitly tests that English contains:

```text
INDICATOR SUMMARY
STRENGTH LEGEND
VERY STRONG / STRONG / MODERATE / WEAK / VERY WEAK
```

and Spanish contains:

```text
RESUMEN DE INDICADORES
LEYENDA DE FUERZA
MUY FUERTE / FUERTE / MODERADA / DÉBIL / MUY DÉBIL
```

## Run tests

```powershell
.\.venv\Scripts\Activate.ps1
pytest -q
```

Regression coverage includes:

- all 16 Screen A/B routes in EN and ES;
- Screen B summary localization;
- internal navigation preserving the selected locale;
- one-way language callback graph with no feedback;
- no secondary locale store;
- identical 144-ID help registries;
- specific contextual-help content rather than generic family placeholders.
