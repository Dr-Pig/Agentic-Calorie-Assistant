from __future__ import annotations

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "recommendation.application.offer_shadow_packet_policy"
)

QUALITY_REPORT = "recommendation_shadow_summary_consumer_quality_report"
THREE_NODE_ARTIFACT = "recommendation_three_node_shadow_artifact"
FALSE_FLAGS = {
    "runtime_effect_allowed": False,
    "mainline_runtime_connected": False,
    "mainline_route_or_api_mount_allowed": False,
    "production_scheduler_delivery_allowed": False,
    "production_db_migration_allowed": False,
    "canonical_product_mutation_allowed": False,
    "canonical_mutation_changed": False,
    "durable_product_memory_written": False,
    "manager_context_packet_changed": False,
    "manager_context_injected": False,
    "user_facing_behavior_changed": False,
    "live_provider_used": False,
    "recommendation_served": False,
    "proactive_sent": False,
    "intake_committed": False,
    "intake_handoff_created": False,
    "pending_meal_intent_created": False,
    "meal_thread_mutated": False,
    "day_budget_mutated": False,
    "body_plan_mutated": False,
    "mutation_changed": False,
    "product_readiness_claimed": False,
}
REPORT_FORBIDDEN_TRUE_FLAGS = (
    "recommendation_served",
    "proactive_sent",
    "live_search_used",
    "ranking_llm_invoked",
    "intake_handoff_created",
    "mutation_changed",
    "meal_thread_mutated",
    "day_budget_mutated",
    "body_plan_mutated",
    "durable_memory_written",
    "manager_context_packet_changed",
    "manager_context_injected",
)
MEMORY_MATCH_SIGNALS = {
    "memory_positive_summary_match",
    "memory_golden_order_projection_match",
}


def decision_ownership() -> dict[str, str]:
    return {
        "recommendation_planning": "llm_fixture",
        "candidate_retrieval_guard_scoring": "deterministic",
        "offer_synthesis": "llm_fixture",
        "deterministic_role": "validate_filter_score_and_reject_only",
        "llm_role": "plan_and_synthesize_without_mutation",
    }


__all__ = [
    "FALSE_FLAGS",
    "MEMORY_MATCH_SIGNALS",
    "QUALITY_REPORT",
    "REPORT_FORBIDDEN_TRUE_FLAGS",
    "SIDECAR_ACTIVATION_CONTRACT",
    "THREE_NODE_ARTIFACT",
    "decision_ownership",
]
