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


def _legacy_provider_token(prefix: str) -> str:
    return prefix + "_provider"


def _legacy_request_support_token() -> str:
    return "text_meal_" + "request_support"


def test_v2_routes_use_manager_provider_entrypoint() -> None:
    canonical = ROOT / "app" / "composition" / "v2_routes.py"
    source = canonical.read_text(encoding="utf-8")

    assert "manager_provider" in source
    assert "search_provider" in source
    assert "extract_provider" in source
    assert "manager_provider=manager_provider" in source
    assert "search_port=search_provider" in source
    assert "extract_port=extract_provider" in source
    assert f'{_legacy_provider_token("planner")}={_legacy_provider_token("planner")}' not in source
    assert f'{_legacy_provider_token("primary")}={_legacy_provider_token("primary")}' not in source


def test_runtime_trace_contract_exports_manager_stage_names() -> None:
    source = (ROOT / "app" / "runtime" / "contracts" / "trace.py").read_text(encoding="utf-8")

    assert 'MANAGER_LOOP_STAGE = "intake_manager_round"' in source


def test_v2_manager_tools_compatibility_facade_is_deleted() -> None:
    assert not (ROOT / "app" / "intake" / "application" / ("manager_" + "tools.py")).exists()


def test_v2_schemas_no_longer_exports_archived_recommendation_contracts() -> None:
    source = (ROOT / "app" / "schemas.py").read_text(encoding="utf-8")

    assert "RecommendationCandidate" not in source
    assert "RecommendationResponseResult" not in source
    assert "HintPacket" not in source


def test_v2_services_import_intake_domain_tools_and_ignore_legacy_provider_split() -> None:
    intake_turn = (ROOT / "app" / "composition" / "intake_turn_orchestrator.py").read_text(encoding="utf-8")
    intake_execution = (ROOT / "app" / "composition" / "intake_execution_orchestrator.py").read_text(encoding="utf-8")
    intake_execution_tools = (ROOT / "app" / "composition" / "intake_manager_tool_batch.py").read_text(encoding="utf-8")
    estimation = (ROOT / "app" / "composition" / "intake_estimation_tools.py").read_text(encoding="utf-8")

    assert "manager_tools" not in intake_turn
    assert "manager_tools" not in intake_execution
    assert "from app.intake.application.intake_trace_tools import append_trace_event_tool" in intake_turn
    assert "from app.intake.application.intake_trace_tools import append_trace_event_tool, resolve_correction_target_tool" in intake_execution
    assert _legacy_provider_token("planner") not in intake_turn
    assert _legacy_provider_token("primary") not in intake_turn
    assert _legacy_provider_token("planner") not in intake_execution
    assert _legacy_provider_token("primary") not in intake_execution
    assert "search_adapter" not in intake_turn
    assert "search_adapter" not in intake_execution
    assert "search_adapter" not in intake_execution_tools
    assert "search_adapter" not in estimation


def test_offline_sidecar_stack_is_not_imported_by_active_runtime_entrypoints() -> None:
    active_entrypoints = [
        ROOT / "app" / "main.py",
        ROOT / "app" / "routes.py",
        ROOT / "app" / "schemas.py",
        ROOT / "app" / "models.py",
        ROOT / "app" / "composition" / "v2_routes.py",
        ROOT / "app" / "composition" / "intake_routes.py",
        ROOT / "app" / "composition" / "today_routes.py",
        ROOT / "app" / "composition" / "body_plan_routes.py",
        ROOT / "app" / "runtime" / "application" / "manager_service.py",
        ROOT / "app" / "composition" / "intake_manager_tool_batch.py",
        ROOT / "app" / "composition" / "intake_execution_response.py",
        ROOT / "app" / "runtime" / "application" / "sidecar_service.py",
    ]
    forbidden_prefixes = (
        "app.memory",
        "app.recommendation",
        "app.rescue",
        "app.runtime.application.proactive_deterministic_gate",
        "app.runtime.application.proactive_no_send_shadow_evaluator",
        "app.runtime.contracts.pending_meal_intent",
        "app.runtime.contracts.proactive_gate",
    )

    violations: list[str] = []
    for path in active_entrypoints:
        for imported in _absolute_imports(path):
            if imported.startswith(forbidden_prefixes):
                violations.append(f"{path.relative_to(ROOT)} imports {imported}")

    assert not violations, "Offline sidecar modules must stay out of active runtime entrypoints: " + ", ".join(violations)


def test_root_compatibility_files_do_not_absorb_sidecar_stack() -> None:
    protected_files = [
        ROOT / "app" / "routes.py",
        ROOT / "app" / "schemas.py",
        ROOT / "app" / "models.py",
    ]
    forbidden_import_prefixes = (
        "app.memory",
        "app.recommendation",
        "app.rescue",
    )
    forbidden_tokens = [
        "PendingMealIntent",
        "ProactiveGateInput",
        "RecommendationCandidateQuality",
        "PreferenceProfileSummary",
        "GoldenOrderSummary",
        "SuppressionSummary",
        "RescueProposalRead",
        "dismiss_rescue_plan",
    ]

    violations: list[str] = []
    for path in protected_files:
        source = path.read_text(encoding="utf-8")
        for imported in _absolute_imports(path):
            if imported.startswith(forbidden_import_prefixes):
                violations.append(f"{path.relative_to(ROOT)} imports {imported}")
        for token in forbidden_tokens:
            if token in source:
                violations.append(f"{path.relative_to(ROOT)} contains {token}")

    assert not violations, "Protected root files must not absorb sidecar contracts: " + ", ".join(violations)


def test_root_routes_mount_only_public_calibration_router_after_activation_plan() -> None:
    root_routes = ROOT / "app" / "routes.py"
    source = root_routes.read_text(encoding="utf-8")
    imports = _absolute_imports(root_routes)

    assert "from app.composition.calibration_routes import public_router as calibration_router" in source
    assert "from app.composition.calibration_routes import router as calibration_router" not in source
    assert "router.include_router(calibration_router)" in source
    assert "app.composition.calibration_routes" in imports
    assert "app.body.interface.calibration_routes" not in _absolute_imports(root_routes)
