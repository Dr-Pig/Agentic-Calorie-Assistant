from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Mapping

from app.advanced_shadow_lab.vertical_proof_lineage import (
    REAL_STAGE_ORDER,
    build_real_artifact_lineage,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.vertical_proof"
)

REQUIRED_SCOPE_KEYS = (
    "user_id",
    "workspace_id",
    "project_id",
    "surface",
    "run_id",
)

STAGE_ORDER = REAL_STAGE_ORDER

FALSE_ACTIVATION_FLAGS = {
    "mainline_runtime_connected": False,
    "mainline_route_or_api_mount_allowed": False,
    "production_scheduler_delivery_allowed": False,
    "production_db_migration_allowed": False,
    "canonical_product_mutation_allowed": False,
    "durable_product_memory_written": False,
    "manager_context_packet_changed": False,
    "user_facing_behavior_changed": False,
    "live_provider_used": False,
    "product_readiness_claimed": False,
}


def build_fixture_vertical_proof_input() -> dict[str, Any]:
    return {
        "scope": {
            "user_id": "user-fixture-1",
            "workspace_id": "workspace-fixture-1",
            "project_id": "advanced-shadow-lab",
            "surface": "fixture_lab",
            "run_id": "vertical-proof-run-1",
        },
        "requested_effects": dict(FALSE_ACTIVATION_FLAGS),
    }


def run_fixture_vertical_proof(
    payload: Mapping[str, Any],
    *,
    artifact_root: Path | str | None = None,
) -> dict[str, Any]:
    blockers = _scope_blockers(payload) + _effect_blockers(payload)
    if blockers:
        return _artifact(
            status="blocked",
            blockers=blockers,
            scope=_scope(payload),
            stage_order=[],
            stage_artifacts=[],
            artifact_lineage=[],
            lab_delivery_record=None,
        )

    if artifact_root is None:
        with TemporaryDirectory() as directory:
            lineage = _lineage(payload, directory)
    else:
        lineage = _lineage(payload, artifact_root)
    blockers = list(lineage["blockers"])
    return _artifact(
        status="blocked" if blockers else "pass",
        blockers=blockers,
        scope=_scope(payload),
        stage_order=STAGE_ORDER,
        stage_artifacts=lineage["stage_artifacts"],
        artifact_lineage=lineage["artifact_lineage"],
        lab_delivery_record=lineage["lab_delivery_record"],
    )


def _artifact(
    *,
    status: str,
    blockers: list[str],
    scope: dict[str, str],
    stage_order: list[str],
    stage_artifacts: list[dict[str, Any]],
    artifact_lineage: list[dict[str, str]],
    lab_delivery_record: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "artifact_type": "advanced_shadow_lab_vertical_proof_artifact",
        "status": status,
        "blockers": blockers,
        "lab_namespace": "advanced_shadow_lab",
        "scope": scope,
        "stage_order": stage_order,
        "stage_artifacts": stage_artifacts,
        "artifact_lineage": artifact_lineage,
        "lab_delivery_record": lab_delivery_record,
        "activation_flags": dict(FALSE_ACTIVATION_FLAGS),
        "non_claims": {
            "not_runtime_activation_evidence": True,
            "not_product_readiness_evidence": True,
            "not_user_facing_activation": True,
            "not_canonical_mutation_authority": True,
        },
    }


def _lineage(payload: Mapping[str, Any], artifact_root: Path | str) -> dict[str, Any]:
    return build_real_artifact_lineage(
        scope=_scope(payload),
        artifact_root=artifact_root,
    )


def _scope_blockers(payload: Mapping[str, Any]) -> list[str]:
    scope = _mapping(payload.get("scope"))
    return [f"scope.{key}_missing" for key in REQUIRED_SCOPE_KEYS if not scope.get(key)]


def _effect_blockers(payload: Mapping[str, Any]) -> list[str]:
    effects = _mapping(payload.get("requested_effects"))
    blockers: list[str] = []
    for key in FALSE_ACTIVATION_FLAGS:
        if effects.get(key) is True:
            blockers.append(f"requested_effects.{key}_not_allowed")
    return blockers


def _scope(payload: Mapping[str, Any]) -> dict[str, str]:
    scope = _mapping(payload.get("scope"))
    return {key: str(scope[key]) for key in REQUIRED_SCOPE_KEYS if scope.get(key)}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_fixture_vertical_proof_input",
    "run_fixture_vertical_proof",
]
