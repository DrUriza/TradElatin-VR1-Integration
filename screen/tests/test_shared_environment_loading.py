from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_integration_loads_one_shared_root_environment_before_delegating() -> None:
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    load_position = source.index("    _load_project_environment()")
    delegate_position = source.index("    delegated_result = _run_with_project_python()")

    assert 'ENV_FILE = ROOT / ".env"' in source
    assert "load_dotenv(dotenv_path=ENV_FILE, override=False" in source
    assert load_position < delegate_position


def test_root_environment_example_documents_all_external_credentials() -> None:
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    for variable in (
        "COINGLASS_API_KEY=",
        "CRYPTOQUANT_API_KEY=",
        "GLASSNODE_API_KEY=",
        "XAI_API_KEY=",
    ):
        assert variable in example

    assert not any(
        line.startswith("XAI_API_KEY=") and line != "XAI_API_KEY="
        for line in example.splitlines()
    )
