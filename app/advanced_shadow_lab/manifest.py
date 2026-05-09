from __future__ import annotations

from typing import Any

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.manifest"
)


def build_advanced_shadow_lab_manifest() -> dict[str, Any]:
    return {
        "artifact_type": "advanced_shadow_lab_boundary_manifest",
        "lab_namespace": "advanced_shadow_lab",
        "owner": "advanced_runtime_lab",
        "consumer": "advanced_shadow_lab_development_prs",
        "activation_stage": "offline_sidecar",
        "slice_mode": ["contract", "fixture_only", "diagnostic_only"],
        "semantic_domains_implemented": [],
        "capability_payloads": [],
        "lab_complete_integration_allowed": True,
        "mainline_runtime_connected": False,
        "mainline_route_or_api_mount_allowed": False,
        "production_scheduler_delivery_allowed": False,
        "production_db_migration_allowed": False,
        "canonical_product_mutation_allowed": False,
        "manager_context_packet_changed": False,
        "user_facing_behavior_changed": False,
        "product_readiness_claimed": False,
        "retirement_trigger": "approved_advanced_runtime_activation_plan",
        "non_claims": {
            "not_runtime_activation_evidence": True,
            "not_product_readiness_evidence": True,
            "not_user_facing_activation": True,
            "not_canonical_mutation_authority": True,
        },
    }


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_advanced_shadow_lab_manifest",
]
