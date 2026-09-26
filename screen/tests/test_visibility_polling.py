from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_contract_polling_pauses_when_browser_tab_is_hidden() -> None:
    source = (ROOT / "app.py").read_text(encoding="utf-8")

    assert "dcc.Store(id='page-visibility'" in source
    assert "document.addEventListener(" in source
    assert "'visibilitychange'" in source
    assert "window.dash_clientside.set_props(" in source
    assert "Input('page-visibility', 'data')" in source
    assert "return reload_style, bool(page_hidden), int(interval)" in source


def test_visibility_hook_replaces_old_listener_on_route_change() -> None:
    source = (ROOT / "app.py").read_text(encoding="utf-8")

    assert "window.tradelatinVisibilityHandler" in source
    assert "document.removeEventListener(" in source
