from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
GROK = ROOT / "screens" / "grok_radar.py"


def test_grok_radar_is_contractless_nav_route() -> None:
    app_source = APP.read_text(encoding="utf-8")
    grok_source = GROK.read_text(encoding="utf-8")
    assert 'ROUTE = "/grok-radar"' in grok_source
    assert 'USES_CONTRACT = False' in grok_source
    assert 'grok_radar,' in app_source
    assert "repeat({len(SCREENS)}" in app_source
    assert 'EXPECTED_CONTRACTS' not in grok_source


def test_xai_key_is_environment_only_and_callback_is_safe() -> None:
    source = GROK.read_text(encoding="utf-8")
    assert 'os.getenv("XAI_API_KEY")' in source
    assert 'Authorization": f"Bearer {key}"' in source
    assert 'timeout=XAI_TIMEOUT_SECONDS' in source
    assert 'except Exception as exc:' in source
    assert 'running=[(Output("grok-refresh-btn", "disabled"), True, False)]' in source
    assert 'dcc.Loading(' in source


def test_parser_handles_markdown_fences_and_json_substrings() -> None:
    source = GROK.read_text(encoding="utf-8")
    assert '```(?:json)?' in source
    assert 'cleaned.find("{")' in source
    assert 'cleaned.rfind("}")' in source


def test_requests_dependency_is_declared_in_screen() -> None:
    screen_req = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "requests>=2.32,<3" in screen_req


def test_contract_schema_remains_unchanged() -> None:
    source = APP.read_text(encoding="utf-8")
    assert 'SCREEN_BUILD_ID = os.getenv("TRADELATIN_SCREEN_BUILD_ID", "V4.2_FINAL_R10_GROK_RADAR_HF3.1")' in source


def test_modified_python_files_parse() -> None:
    for path in (APP, GROK, ROOT / "screens" / "__init__.py"):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
