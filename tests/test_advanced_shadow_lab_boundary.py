from __future__ import annotations

import ast
import importlib
from pathlib import Path

from app.advanced_shadow_lab.manifest import build_advanced_shadow_lab_manifest


ROOT = Path(__file__).resolve().parents[1]


def test_advanced_shadow_lab_manifest_is_dormant_and_non_semantic() -> None:
    manifest = build_advanced_shadow_lab_manifest()

    assert manifest["artifact_type"] == "advanced_shadow_lab_boundary_manifest"
    assert manifest["lab_namespace"] == "advanced_shadow_lab"
    assert manifest["activation_stage"] == "offline_sidecar"
    assert manifest["slice_mode"] == ["contract", "fixture_only", "diagnostic_only"]
    assert manifest["semantic_domains_implemented"] == []
    assert manifest["capability_payloads"] == []
    assert manifest["lab_complete_integration_allowed"] is True
    assert manifest["mainline_runtime_connected"] is False
    assert manifest["mainline_route_or_api_mount_allowed"] is False
    assert manifest["production_scheduler_delivery_allowed"] is False
    assert manifest["production_db_migration_allowed"] is False
    assert manifest["canonical_product_mutation_allowed"] is False
    assert manifest["manager_context_packet_changed"] is False
    assert manifest["user_facing_behavior_changed"] is False
    assert manifest["product_readiness_claimed"] is False
    assert manifest["retirement_trigger"] == "approved_advanced_runtime_activation_plan"


def test_advanced_shadow_lab_modules_declare_offline_activation_block() -> None:
    for module_name in [
        "app.advanced_shadow_lab",
        "app.advanced_shadow_lab.manifest",
    ]:
        module = importlib.import_module(module_name)
        contract = getattr(module, "SIDECAR_ACTIVATION_CONTRACT")

        assert contract.offline_only is True, module_name
        assert contract.activation_blocked is True, module_name
        assert contract.not_runtime_authority is True, module_name
        assert contract.user_facing_activation is False, module_name
        assert contract.mutation_authority is False, module_name


def test_advanced_shadow_lab_is_not_imported_by_active_runtime_surfaces() -> None:
    active_entrypoints = [
        ROOT / "app" / "main.py",
        ROOT / "app" / "routes.py",
        ROOT / "app" / "schemas.py",
        ROOT / "app" / "models.py",
        ROOT / "app" / "composition" / "intake_routes.py",
        ROOT / "app" / "composition" / "v2_routes.py",
        ROOT / "app" / "composition" / "intake_turn_orchestrator.py",
        ROOT / "app" / "composition" / "intake_execution_orchestrator.py",
        ROOT / "app" / "runtime" / "application" / "manager_service.py",
        ROOT / "app" / "runtime" / "interface" / "provider_runtime.py",
        ROOT / "app" / "runtime" / "agent" / "manager_context_payload.py",
    ]

    violations: list[str] = []
    for path in active_entrypoints:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8-sig")
        if "advanced_shadow_lab" in text:
            violations.append(f"{path.relative_to(ROOT)} references advanced_shadow_lab")
        for imported in _absolute_imports(path):
            if imported.startswith("app.advanced_shadow_lab"):
                violations.append(f"{path.relative_to(ROOT)} imports {imported}")

    assert not violations


def test_advanced_shadow_lab_has_no_route_scheduler_persistence_or_provider_imports() -> None:
    forbidden_import_prefixes = (
        "alembic",
        "app.database",
        "app.models",
        "app.providers",
        "app.runtime.agent.manager_context_payload",
        "app.runtime.application.manager_service",
        "fastapi",
        "httpx",
        "requests",
        "sqlalchemy",
    )
    forbidden_text = (
        "APIRouter",
        "FastAPI",
        "BackgroundTasks",
        "Scheduler(",
        "schedule_job",
        "send_notification",
        "notification_sender",
        "ManagerContextPacket",
        "create_engine",
        "SessionLocal",
    )

    for path in (ROOT / "app" / "advanced_shadow_lab").glob("**/*.py"):
        text = path.read_text(encoding="utf-8-sig")
        for token in forbidden_text:
            assert token not in text, f"{path.relative_to(ROOT)} contains {token}"
        for imported in _absolute_imports(path):
            assert not imported.startswith(forbidden_import_prefixes), (
                f"{path.relative_to(ROOT)} imports {imported}"
            )

    assert not list((ROOT / "alembic" / "versions").glob("*advanced_shadow_lab*"))


def _absolute_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports
