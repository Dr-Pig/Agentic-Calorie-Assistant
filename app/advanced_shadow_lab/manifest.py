from __future__ import annotations

from typing import Any

from app.advanced_shadow_lab.model_profiles import advanced_lab_model_profile_policy
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.manifest"
)

ADVANCED_LAB_CAPABILITY_DOMAINS = [
    "long_term_memory",
    "recommendation",
    "rescue",
    "proactive_chat",
]

REQUIRED_MAINLINE_FALSE_FLAGS = [
    "mainline_runtime_connected",
    "mainline_route_or_api_mount_allowed",
    "production_manager_mount_allowed",
    "production_scheduler_delivery_allowed",
    "production_db_migration_allowed",
    "canonical_product_mutation_allowed",
    "manager_context_packet_changed",
    "user_facing_behavior_changed",
    "live_provider_calls_allowed",
    "kimi_live_calls_allowed",
    "recommendation_served",
    "rescue_proposal_committed",
    "proactive_sent",
    "notification_delivery_allowed",
    "fooddb_expansion_allowed",
]


def build_advanced_shadow_lab_manifest() -> dict[str, Any]:
    return {
        "artifact_type": "advanced_shadow_lab_boundary_manifest",
        "lab_namespace": "advanced_shadow_lab",
        "owner": "advanced_runtime_lab",
        "consumer": "advanced_shadow_lab_development_prs",
        "activation_stage": "offline_sidecar",
        "slice_mode": ["contract", "fixture_only", "diagnostic_only", "offline_runtime"],
        "capability_domains_planned": list(ADVANCED_LAB_CAPABILITY_DOMAINS),
        "semantic_domains_implemented": [],
        "capability_payloads": [],
        "lab_complete_integration_allowed": True,
        "mainline_runtime_connected": False,
        "mainline_route_or_api_mount_allowed": False,
        "production_manager_mount_allowed": False,
        "production_scheduler_delivery_allowed": False,
        "production_db_migration_allowed": False,
        "canonical_product_mutation_allowed": False,
        "manager_context_packet_changed": False,
        "user_facing_behavior_changed": False,
        "live_provider_calls_allowed": False,
        "kimi_live_calls_allowed": False,
        "recommendation_served": False,
        "rescue_proposal_committed": False,
        "proactive_sent": False,
        "notification_delivery_allowed": False,
        "fooddb_expansion_allowed": False,
        "product_readiness_claimed": False,
        "live_provider_policy": {
            "current_slice_live_provider_calls_allowed": False,
            "later_lab_live_diagnostics_allowed_after_dormancy_gate": True,
            "provider_family": "builderspace",
            "diagnostic_live_model": "grok-4-fast",
            "target_reasoning_model": "kimi-k2.5",
            "kimi_live_calls_allowed": False,
            "provider_specific_product_semantics_allowed": False,
        },
        "model_profile_policy": advanced_lab_model_profile_policy(),
        "proactive_surface_policy": {
            "chat_only": True,
            "inbox_mirror_allowed": False,
            "push_line_or_os_notification_allowed": False,
            "scheduler_delivery_allowed": False,
        },
        "fooddb_policy": {
            "expansion_allowed": False,
            "self_use_required_before_expansion": True,
            "fixtures_or_approved_packets_only": True,
        },
        "merge_back_dormancy_contract": {
            "required_false_flags": list(REQUIRED_MAINLINE_FALSE_FLAGS),
            "mainline_activation_requires_separate_pr": True,
        },
        "retirement_trigger": "approved_advanced_runtime_activation_plan",
        "non_claims": {
            "not_runtime_activation_evidence": True,
            "not_product_readiness_evidence": True,
            "not_user_facing_activation": True,
            "not_canonical_mutation_authority": True,
            "not_live_provider_activation": True,
            "not_kimi_activation": True,
            "not_fooddb_expansion": True,
        },
    }


def build_advanced_shadow_lab_stage_snapshot_manifest(
    *,
    memory_stage_decision: dict[str, Any],
    recommendation_stage_decision: dict[str, Any],
    rescue_stage_decision: dict[str, Any],
    proactive_stage_decision: dict[str, Any],
) -> dict[str, Any]:
    from app.advanced_shadow_lab.stage_snapshot import (
        build_advanced_shadow_lab_stage_snapshot_manifest as build_stage_snapshot,
    )
    return build_stage_snapshot(
        memory_stage_decision=memory_stage_decision,
        recommendation_stage_decision=recommendation_stage_decision,
        rescue_stage_decision=rescue_stage_decision,
        proactive_stage_decision=proactive_stage_decision,
    )


__all__ = [
    "ADVANCED_LAB_CAPABILITY_DOMAINS",
    "REQUIRED_MAINLINE_FALSE_FLAGS",
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_advanced_shadow_lab_manifest",
    "build_advanced_shadow_lab_stage_snapshot_manifest",
]
