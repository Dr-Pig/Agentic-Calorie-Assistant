from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.product_lab_activation_wall_audit"
)
SUPPORTED_CLOSURE_PACK = "advanced_product_lab_memory_record_closure_pack"
ACTIVE_RUNTIME_SURFACES = [
    "app/main.py",
    "app/routes.py",
    "app/schemas.py",
    "app/models.py",
    "app/composition/intake_routes.py",
    "app/composition/v2_routes.py",
    "app/composition/intake_turn_orchestrator.py",
    "app/composition/intake_execution_orchestrator.py",
    "app/runtime/application/manager_service.py",
    "app/runtime/interface/provider_runtime.py",
    "app/runtime/agent/manager_context_payload.py",
]
ADVANCED_LAB_FORBIDDEN_TEXT = [
    "API" + "Router",
    "Fast" + "API",
    "Background" + "Tasks",
    "Scheduler" + "(",
    "schedule" + "_job",
    "send" + "_notification",
    "notification" + "_sender",
    "Manager" + "ContextPacket",
    "create" + "_engine",
    "Session" + "Local",
]
ADVANCED_LAB_FORBIDDEN_IMPORT_TEXT = [
    "from app." + "database",
    "import app." + "database",
    "from app." + "models",
    "import app." + "models",
    "from app." + "providers",
    "import app." + "providers",
    "from app.runtime.application." + "manager_service",
    "from app.runtime.agent." + "manager_context_payload",
    "from " + "fastapi",
    "import " + "fastapi",
    "from " + "sqlalchemy",
    "import " + "sqlalchemy",
]
CLAIM_FALSE_FIELDS = [
    "mainline_activation_enabled",
    "mainline_runtime_connected",
    "self_use_v1_affected",
    "durable_product_memory_written",
    "canonical_product_mutation_allowed",
    "production_scheduler_delivery_allowed",
]
NEXT_ALLOWED_SLICES = [
    "lab_debt_retirement_plan",
    "golden_set_manifest_alignment",
]
NON_CLAIMS = [
    "not_mainline_runtime_activation",
    "not_self_use_v1_activation",
    "not_production_scheduler_delivery",
    "not_canonical_mutation",
    "not_durable_product_memory",
]


def build_product_lab_activation_wall_audit(
    *,
    closure_pack: Mapping[str, Any],
    repo_root: str | Path,
    source_closure_pack_path: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root)
    blockers = [
        *_closure_blockers(closure_pack),
        *_active_surface_blockers(root),
        *_advanced_lab_blockers(root),
        *_migration_blockers(root),
    ]
    status = "blocked" if blockers else "pass"
    return {
        "artifact_type": "advanced_product_lab_activation_wall_audit",
        "artifact_schema_version": "1.0",
        "status": status,
        "owner": "app/advanced_shadow_lab/product_lab_activation_wall_audit.py",
        "consumer": "advanced_product_lab_merge_back_dormancy_gate",
        "retirement_trigger": "approved_advanced_product_lab_activation_plan",
        "source_closure_pack_path": str(source_closure_pack_path or ""),
        "source_closure_pack_type": str(closure_pack.get("artifact_type") or ""),
        "source_closure_pack_status": str(closure_pack.get("status") or ""),
        "route_mount_clear": _no_blocker_prefix(blockers, "active_runtime_surface."),
        "scheduler_delivery_clear": _no_scheduler_blocker(blockers),
        "production_db_migration_clear": _no_blocker_prefix(blockers, "migration."),
        "provider_default_runtime_clear": _no_provider_blocker(blockers),
        "blockers": blockers,
        "next_allowed_slices": list(NEXT_ALLOWED_SLICES) if status == "pass" else [],
        "lab_enabled": bool(closure_pack.get("lab_enabled")),
        "lab_product_loop_closed": status == "pass",
        "mainline_activation_enabled": False,
        "mainline_runtime_connected": False,
        "self_use_v1_affected": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "production_scheduler_delivery_allowed": False,
        "non_claims": list(NON_CLAIMS),
        **dict(FALSE_FLAGS),
    }


def _closure_blockers(closure_pack: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if closure_pack.get("artifact_type") != SUPPORTED_CLOSURE_PACK:
        blockers.append("closure_pack.artifact_type_mismatch")
    if closure_pack.get("status") != "pass":
        blockers.append(f"closure_pack.status_{closure_pack.get('status')}")
        blockers.extend(f"closure_pack.{item}" for item in closure_pack.get("blockers") or [])
    if closure_pack.get("lab_product_loop_closed") is not True:
        blockers.append("closure_pack.lab_product_loop_not_closed")
    for field in CLAIM_FALSE_FIELDS:
        if closure_pack.get(field) is True:
            blockers.append(f"closure_pack.{field}.claim_drift")
    return blockers


def _active_surface_blockers(root: Path) -> list[str]:
    blockers: list[str] = []
    for rel_path in ACTIVE_RUNTIME_SURFACES:
        path = root / rel_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8-sig")
        if "advanced_shadow_lab" in text or "product_lab_memory_record" in text:
            blockers.append(f"active_runtime_surface.{rel_path}.references_advanced_shadow_lab")
    return blockers


def _advanced_lab_blockers(root: Path) -> list[str]:
    lab_root = root / "app" / "advanced_shadow_lab"
    if not lab_root.exists():
        return []
    blockers: list[str] = []
    for path in sorted(lab_root.glob("**/*.py")):
        rel_path = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8-sig")
        for token in ADVANCED_LAB_FORBIDDEN_TEXT:
            if token in text:
                blockers.append(f"advanced_lab.{rel_path}.contains_{token}")
        for token in ADVANCED_LAB_FORBIDDEN_IMPORT_TEXT:
            if token in text:
                blockers.append(
                    f"advanced_lab.{rel_path}.imports_{_import_label(token)}"
                )
    return blockers


def _migration_blockers(root: Path) -> list[str]:
    versions = root / "alembic" / "versions"
    if not versions.exists():
        return []
    markers = ("advanced_shadow_lab", "advanced_product_lab", "product_lab_memory")
    return [
        f"migration.{path.name}"
        for path in sorted(versions.glob("*.py"))
        if any(marker in path.name for marker in markers)
    ]


def _import_label(token: str) -> str:
    return token.replace("from ", "").replace("import ", "").replace(" ", "_")


def _no_blocker_prefix(blockers: list[str], prefix: str) -> bool:
    return not any(blocker.startswith(prefix) for blocker in blockers)


def _no_scheduler_blocker(blockers: list[str]) -> bool:
    return not any("Scheduler" in blocker or "schedule" in blocker for blocker in blockers)


def _no_provider_blocker(blockers: list[str]) -> bool:
    return not any(".imports_app.providers" in blocker for blocker in blockers)


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_product_lab_activation_wall_audit",
]
