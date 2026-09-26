from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _assignment(path: Path, name: str) -> ast.AST:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                return node.value
    raise AssertionError(f"missing assignment {name} in {path}")


def _emulator_ids() -> set[str]:
    node = _assignment(ROOT / "emulator/app/markets/equities_catalog.py", "_DEFINITIONS")
    assert isinstance(node, ast.Dict)
    return {ast.literal_eval(key) for key in node.keys}


def _processing_ids() -> set[str]:
    node = _assignment(
        ROOT / "processing/src/processing_signals/markets/registry.py", "_DEFINITIONS"
    )
    assert isinstance(node, ast.Tuple)
    return {
        ast.literal_eval(item.args[0])
        for item in node.elts
        if isinstance(item, ast.Call) and item.args
    }


def _screen_ids() -> set[str]:
    node = _assignment(ROOT / "screen/screen_core/equities_contract.py", "_IDS_BY_FAMILY")
    assert isinstance(node, ast.Dict)
    identifiers: set[str] = set()
    for values in node.values:
        assert isinstance(values, ast.Tuple)
        identifiers.update(ast.literal_eval(value) for value in values.elts)
    return identifiers


def test_proposed_equities_catalog_is_identical_across_embedded_repositories() -> None:
    emulator = _emulator_ids()
    processing = _processing_ids()
    screen = _screen_ids()

    assert len(emulator) == 37
    assert emulator == processing == screen


def test_operational_runtime_remains_eight_frozen_btc_families() -> None:
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    expected = None
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "EXPECTED_CONTRACTS":
            expected = ast.literal_eval(node.value)
            break
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "EXPECTED_CONTRACTS"
            for target in node.targets
        ):
            expected = ast.literal_eval(node.value)
            break

    assert expected is not None
    assert len(expected) == 8
    assert "C9" not in source
    assert "--source\", \"auto" in source


def test_equities_scaffolding_does_not_register_operational_endpoints() -> None:
    emulator_main = (ROOT / "emulator/app/main.py").read_text(encoding="utf-8")
    processing_main = (ROOT / "processing/main.py").read_text(encoding="utf-8")

    assert "eq_c1_trade_price" not in emulator_main
    assert "IBKR" not in processing_main.upper()
