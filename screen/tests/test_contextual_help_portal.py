from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_help_uses_persistent_body_portal():
    js=(ROOT/"assets/contextual_help.js").read_text(encoding="utf-8"); css=(ROOT/"assets/contextual_help.css").read_text(encoding="utf-8")
    assert "document.body.appendChild(node)" in js; assert "new MutationObserver" in js; assert "anchor.isConnected" in js
    assert ".context-help-anchor > .context-help-popover" in css; assert "display: none !important" in css; assert ".context-help-portal.context-help-portal-visible" in css
