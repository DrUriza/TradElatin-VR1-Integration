from __future__ import annotations

import json
import os
import importlib.util
from pathlib import Path

import pytest

ROOT_MAIN = Path(__file__).resolve().parents[1] / "main.py"
SPEC = importlib.util.spec_from_file_location("tradelatin_integration_main", ROOT_MAIN)
assert SPEC and SPEC.loader
main = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(main)


def _environment() -> dict[str, str]:
    return {
        "TRADELATIN_EMULATOR_PORT": "8000",
        "TRADELATIN_PORT": "8002",
    }


def test_second_live_integration_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "integration.lock.json"
    token = main._acquire_integration_lock(path, _environment())
    try:
        with pytest.raises(RuntimeError, match="already running"):
            main._acquire_integration_lock(path, _environment())
    finally:
        main._release_integration_lock(path, token)
    assert not path.exists()


def test_stale_integration_lock_is_recovered(tmp_path: Path) -> None:
    path = tmp_path / "integration.lock.json"
    path.write_text(
        json.dumps(
            {
                "pid": max(os.getpid() + 10_000_000, 2_000_000_000),
                "build_id": "STALE",
            }
        ),
        encoding="utf-8",
    )

    token = main._acquire_integration_lock(path, _environment())
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["pid"] == os.getpid()
        assert payload["build_id"] == main.BUILD_ID
        assert payload["contracts_dir"] == str(main.CONTRACTS.resolve())
    finally:
        main._release_integration_lock(path, token)
    assert not path.exists()
