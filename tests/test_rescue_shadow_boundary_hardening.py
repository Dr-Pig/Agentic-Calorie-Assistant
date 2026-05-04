from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

FASTAPI_ROUTE_SURFACES = [
    "app/routes.py",
    "app/composition/v2_routes.py",
    "app/composition/intake_routes.py",
    "app/composition/today_routes.py",
    "app/composition/body_plan_routes.py",
    "app/composition/calibration_routes.py",
    "app/runtime/interface/base_routes.py",
    "app/runtime/interface/admin_routes.py",
]

UI_ACTION_SCHEMA_SURFACES = [
    "app/schemas.py",
    "app/models.py",
    "app/runtime/contracts/manager.py",
    "app/runtime/agent/manager_decision_contract.py",
    "app/runtime/agent/manager_branch_shapes.py",
    "app/runtime/agent/manager_branch_contract.py",
    "app/runtime/agent/manager_result_builder.py",
]

MANAGER_ACTION_SURFACES = [
    "app/composition/intake_manager_tool_batch.py",
    "app/runtime/application/manager_service.py",
    "app/runtime/agent/manager.py",
    "app/runtime/agent/manager_branch_constraints.py",
    "app/runtime/agent/manager_branch_validation.py",
    "app/runtime/agent/manager_system_prompt.py",
    "app/runtime/agent/manager_support_prompts.py",
]

PROACTIVE_OR_SCHEDULER_SURFACES = [
    "app/runtime/application/proactive_deterministic_gate.py",
    "app/runtime/contracts/proactive_gate.py",
]

RESCUE_ACCEPT_DISMISS_ACTIONS = {
    "accept_rescue_plan",
    "dismiss_rescue_plan",
}


def test_no_fastapi_route_exposes_rescue_accept_or_dismiss() -> None:
    violations: list[str] = []
    for relative_path in FASTAPI_ROUTE_SURFACES:
        path = ROOT / relative_path
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    route_literal = _route_path_literal(decorator)
                    if route_literal and _is_rescue_accept_dismiss_surface(route_literal):
                        violations.append(f"{relative_path}:{node.name}:{route_literal}")

    assert not violations, "Rescue accept/dismiss route surfaces are forbidden: " + ", ".join(violations)


def test_no_ui_action_schema_exposes_rescue_accept_or_dismiss() -> None:
    violations = _literal_action_violations(UI_ACTION_SCHEMA_SURFACES)

    assert not violations, "UI/action schemas must not expose rescue accept/dismiss: " + ", ".join(violations)


def test_no_manager_action_registry_registers_rescue_accept_or_dismiss() -> None:
    violations = _literal_action_violations(MANAGER_ACTION_SURFACES)

    assert not violations, "Manager action surfaces must not register rescue accept/dismiss: " + ", ".join(violations)


def test_no_scheduler_or_proactive_surface_imports_rescue_sidecar() -> None:
    violations: list[str] = []
    for relative_path in PROACTIVE_OR_SCHEDULER_SURFACES:
        path = ROOT / relative_path
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        for imported in _imports(tree):
            if imported.startswith("app.rescue"):
                violations.append(f"{relative_path} imports {imported}")

    assert not violations, "Scheduler/proactive surfaces must not import rescue sidecar: " + ", ".join(violations)


def test_no_proposal_container_write_path_exists_under_rescue_shadow() -> None:
    violations: list[str] = []
    for path in (ROOT / "app" / "rescue").rglob("*.py"):
        source = path.read_text(encoding="utf-8-sig")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and _looks_like_proposal_write_path(node.name):
                violations.append(f"{path.relative_to(ROOT)}:{node.name}")
            if isinstance(node, ast.AsyncFunctionDef) and _looks_like_proposal_write_path(node.name):
                violations.append(f"{path.relative_to(ROOT)}:{node.name}")
            if isinstance(node, ast.Call) and _call_name(node) in {
                "commit",
                "flush",
                "add",
                "merge",
                "execute",
            }:
                if "ProposalContainer" in source or "rescue_overlay" in source:
                    violations.append(f"{path.relative_to(ROOT)}:{_call_name(node)}")

    assert not violations, "Rescue shadow must not contain ProposalContainer write paths: " + ", ".join(violations)


def _route_path_literal(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr in {
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "api_route",
    }:
        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            return node.args[0].value
        for keyword in node.keywords:
            if (
                keyword.arg == "path"
                and isinstance(keyword.value, ast.Constant)
                and isinstance(keyword.value.value, str)
            ):
                return keyword.value.value
    return None


def _is_rescue_accept_dismiss_surface(value: str) -> bool:
    normalized = value.lower()
    return "rescue" in normalized and ("accept" in normalized or "dismiss" in normalized)


def _literal_action_violations(relative_paths: list[str]) -> list[str]:
    violations: list[str] = []
    for relative_path in relative_paths:
        path = ROOT / relative_path
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value in RESCUE_ACCEPT_DISMISS_ACTIONS:
                    violations.append(f"{relative_path}:{node.value}")
    return violations


def _imports(tree: ast.AST) -> list[str]:
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def _looks_like_proposal_write_path(name: str) -> bool:
    normalized = name.lower()
    return (
        ("proposal" in normalized or "container" in normalized)
        and any(token in normalized for token in ("accept", "commit", "write", "create", "persist", "mutate"))
    )


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None
