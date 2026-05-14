from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS


ACTIVE_RUNTIME_SURFACES = [
    "app/main.py",
    "app/routes.py",
    "app/schemas.py",
    "app/models.py",
    "app/composition/intake_routes.py",
    "app/composition/intake_turn_orchestrator.py",
    "app/composition/intake_execution_orchestrator.py",
    "app/runtime/application/manager_service.py",
    "app/runtime/interface/provider_runtime.py",
]
PROACTIVE_LAB_TOKENS = [
    "advanced_product_lab_proactive",
    "product_lab_proactive",
    "proactive_mainline_dormancy_gate",
    "app.advanced_shadow_lab.product_lab_proactive",
    "proactive.run",
]
REQUIRED_FALSE_FLAGS = [
    "mainline_activation_enabled",
    "mainline_runtime_connected",
    "served_to_mainline_user",
    "production_notification_delivery_allowed",
    "production_scheduler_delivery_allowed",
    "production_route_or_api_mount_allowed",
    "production_db_migration_allowed",
    "canonical_product_mutation_allowed_on_main",
    "durable_product_memory_activation_on_main",
    "manager_context_packet_changed",
]


def build_proactive_mainline_dormancy_gate(
    *,
    proactive_pr_train: Mapping[str, Any],
    repo_root: str | Path,
) -> dict[str, Any]:
    root = Path(repo_root)
    blockers = [
        *_train_blockers(proactive_pr_train),
        *_active_surface_blockers(root),
        *_migration_blockers(root),
    ]
    status = "blocked" if blockers else "pass"
    return {
        "artifact_type": "advanced_product_lab_proactive_mainline_dormancy_gate",
        "artifact_schema_version": "1.0",
        "status": status,
        "owner": "app/advanced_shadow_lab/proactive_mainline_dormancy_gate.py",
        "consumer": "advanced_product_lab_proactive_train_closeout",
        "proactive_train_ready": _train_ready(proactive_pr_train),
        "route_mount_clear": _no_blocker_prefix(blockers, "active_runtime_surface."),
        "scheduler_delivery_clear": _no_scheduler_blocker(blockers),
        "production_db_migration_clear": _no_blocker_prefix(blockers, "migration."),
        "durable_memory_activation_clear": True,
        "ready_for_proactive_train_closeout": status == "pass",
        "ready_for_mainline_activation": False,
        "mainline_activation_enabled": False,
        "mainline_runtime_connected": False,
        "self_use_v1_affected": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "production_scheduler_delivery_allowed": False,
        "blockers": blockers,
        **dict(FALSE_FLAGS),
    }


def _train_blockers(train: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if train.get("artifact_type") != "advanced_product_lab_proactive_chat_first_pr_train":
        blockers.append("proactive_pr_train.unsupported_artifact_type")
    if train.get("status") != "active":
        blockers.append("proactive_pr_train.status_not_active")
    if int(train.get("last_completed_pr_number") or 0) < 22:
        blockers.append("proactive_pr_train.pr22_not_completed")
    flags = _mapping(train.get("required_artifact_flags"))
    for field in REQUIRED_FALSE_FLAGS:
        if flags.get(field) is True:
            blockers.append(f"proactive_pr_train.required_artifact_flags.{field}")
    return blockers


def _active_surface_blockers(root: Path) -> list[str]:
    blockers: list[str] = []
    for rel_path in ACTIVE_RUNTIME_SURFACES:
        path = root / rel_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8-sig")
        if any(token in text for token in PROACTIVE_LAB_TOKENS):
            blockers.append(f"active_runtime_surface.{rel_path}.references_proactive_lab")
    return blockers


def _migration_blockers(root: Path) -> list[str]:
    versions = root / "alembic" / "versions"
    if not versions.exists():
        return []
    markers = ("advanced_product_lab_proactive", "proactive_lab")
    return [
        f"migration.{path.name}"
        for path in sorted(versions.glob("*.py"))
        if any(marker in path.name for marker in markers)
    ]


def _train_ready(train: Mapping[str, Any]) -> bool:
    return (
        train.get("status") == "active"
        and int(train.get("last_completed_pr_number") or 0) >= 22
    )


def _no_blocker_prefix(blockers: list[str], prefix: str) -> bool:
    return not any(blocker.startswith(prefix) for blocker in blockers)


def _no_scheduler_blocker(blockers: list[str]) -> bool:
    return not any("scheduler" in blocker.lower() for blocker in blockers)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["build_proactive_mainline_dormancy_gate"]
