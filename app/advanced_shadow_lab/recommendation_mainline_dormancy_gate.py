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
RECOMMENDATION_LAB_TOKENS = [
    "advanced_product_lab_recommendation",
    "recommendation_quality_decision_pack",
    "recommendation_mainline_dormancy_gate",
    "app.advanced_shadow_lab.recommendation",
    "recommendation.run",
]
CLAIM_FALSE_FIELDS = [
    "mainline_activation_enabled",
    "mainline_runtime_connected",
    "self_use_v1_affected",
    "canonical_product_mutation_allowed",
    "durable_product_memory_written",
    "manager_context_packet_changed",
    "production_scheduler_delivery_allowed",
]


def build_recommendation_mainline_dormancy_gate(
    *,
    quality_decision_pack: Mapping[str, Any],
    repo_root: str | Path,
) -> dict[str, Any]:
    root = Path(repo_root)
    blockers = [
        *_quality_pack_blockers(quality_decision_pack),
        *_active_surface_blockers(root),
        *_migration_blockers(root),
    ]
    status = "blocked" if blockers else "pass"
    return {
        "artifact_type": "advanced_product_lab_recommendation_mainline_dormancy_gate",
        "artifact_schema_version": "1.0",
        "status": status,
        "owner": "app/advanced_shadow_lab/recommendation_mainline_dormancy_gate.py",
        "consumer": "advanced_product_lab_recommendation_train_closeout",
        "quality_decision_pack_ready": _quality_pack_ready(quality_decision_pack),
        "route_mount_clear": _no_blocker_prefix(blockers, "active_runtime_surface."),
        "scheduler_delivery_clear": _no_scheduler_blocker(blockers),
        "production_db_migration_clear": _no_blocker_prefix(blockers, "migration."),
        "provider_default_runtime_clear": True,
        "ready_for_recommendation_train_closeout": status == "pass",
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


def _quality_pack_blockers(pack: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if pack.get("artifact_type") != (
        "advanced_product_lab_recommendation_quality_decision_pack"
    ):
        blockers.append("quality_decision_pack.unsupported_artifact_type")
    if pack.get("status") != "pass":
        blockers.append("quality_decision_pack.status_not_pass")
    if pack.get("ready_for_recommendation_mainline_dormancy_gate") is not True:
        blockers.append("quality_decision_pack.not_ready_for_dormancy_gate")
    if pack.get("ready_for_mainline_activation") is True:
        blockers.append("quality_decision_pack.ready_for_mainline_activation")
    for field in CLAIM_FALSE_FIELDS:
        if pack.get(field) is True:
            blockers.append(f"quality_decision_pack.{field}")
    return blockers


def _active_surface_blockers(root: Path) -> list[str]:
    blockers: list[str] = []
    for rel_path in ACTIVE_RUNTIME_SURFACES:
        path = root / rel_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8-sig")
        if any(token in text for token in RECOMMENDATION_LAB_TOKENS):
            blockers.append(
                f"active_runtime_surface.{rel_path}.references_recommendation_lab"
            )
    return blockers


def _migration_blockers(root: Path) -> list[str]:
    versions = root / "alembic" / "versions"
    if not versions.exists():
        return []
    markers = ("advanced_product_lab_recommendation", "recommendation_lab")
    return [
        f"migration.{path.name}"
        for path in sorted(versions.glob("*.py"))
        if any(marker in path.name for marker in markers)
    ]


def _quality_pack_ready(pack: Mapping[str, Any]) -> bool:
    return (
        pack.get("status") == "pass"
        and pack.get("ready_for_recommendation_mainline_dormancy_gate") is True
    )


def _no_blocker_prefix(blockers: list[str], prefix: str) -> bool:
    return not any(blocker.startswith(prefix) for blocker in blockers)


def _no_scheduler_blocker(blockers: list[str]) -> bool:
    return not any("scheduler" in blocker.lower() for blocker in blockers)


__all__ = ["build_recommendation_mainline_dormancy_gate"]
