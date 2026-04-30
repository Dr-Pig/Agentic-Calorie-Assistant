from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _absolute_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def test_calibration_action_router_is_not_mounted_in_root_routes() -> None:
    root_routes = ROOT / "app" / "routes.py"
    source = root_routes.read_text(encoding="utf-8")

    assert "calibration_routes" not in source
    assert "calibration_router" not in source
    assert "app.body.interface.calibration_routes" not in _absolute_imports(root_routes)
