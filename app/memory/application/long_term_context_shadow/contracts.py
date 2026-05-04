from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.utils import (
    _artifact_non_runtime_truth_reason,
    _artifact_promotion_path,
    _artifact_risk_if_wrong,
    _consumer_use_hints,
    _json_safe,
)

SHADOW_NON_CLAIM_FLAGS: dict[str, bool] = {
    "shadow_mode": True,
    "real_runtime_effect": False,
    "dogfood_db_mutated": False,
    "durable_memory_written": False,
    "manager_context_injected": False,
    "proactive_sent": False,
    "recommendation_served": False,
    "rescue_committed": False,
    "body_plan_mutated": False,
    "day_budget_mutated": False,
    "meal_thread_mutated": False,
    "product_readiness_claimed": False,
    "private_self_use_approved": False,
}

DOGFOOD_EXPORT_SECTIONS: tuple[str, ...] = (
    "meal_logs",
    "body_observations",
    "budget_summaries",
    "calibration_diagnostics",
    "language_observations",
    "intake_estimation_events",
    "app_usage_events",
    "interaction_events",
    "negative_preference_observations",
    "temporary_preference_observations",
    "conversation_history_summaries",
    "trace_metadata",
    "candidate_pool",
    "menu_scan_context",
    "review_actions",
)

CHAT_TRACE_SECTION_ALIASES: tuple[str, ...] = (
    "chat_trace_metadata",
    "chat_traces",
    "conversation_trace_metadata",
)

ARTIFACT_CONSUMER_CATALOG: dict[str, list[str]] = {
    "artifact_registry_manifest": ["human_review", "architecture_governance"],
    "long_term_memory_candidate_review": [
        "human_review",
        "recommendation",
        "intake_clarification",
        "calibration",
        "chat_context",
    ],
    "context_value_review_queue": ["human_review", "architecture_governance"],
    "context_signal_quality_scorecard": [
        "human_review",
        "architecture_governance",
    ],
    "candidate_extraction_engine_v2": [
        "human_review",
        "architecture_governance",
        "recommendation",
        "intake_clarification",
        "calibration",
    ],
    "derived_memory_views_shadow_eval": [
        "human_review",
        "architecture_governance",
        "recommendation",
        "intake_clarification",
        "calibration",
        "proactive",
        "rescue_later",
    ],
    "context_signal_lifecycle_shadow_eval": [
        "human_review",
        "architecture_governance",
        "recommendation",
        "intake_clarification",
        "calibration",
        "proactive",
        "rescue_later",
    ],
    "user_context_profile_shadow_eval": [
        "human_review",
        "architecture_governance",
        "recommendation",
        "intake_clarification",
        "chat_context",
        "calibration",
        "proactive",
    ],
    "scope_isolation_shadow_eval": [
        "architecture_governance",
        "privacy_review",
        "future_manager_context_retrieval",
        "chat_context",
    ],
    "context_value_scoring_v2": [
        "human_review",
        "architecture_governance",
        "recommendation",
        "intake_clarification",
        "calibration",
    ],
    "shadow_replay_evaluators": [
        "human_review",
        "recommendation",
        "intake_clarification",
        "calibration",
    ],
    "review_queue_reducer": ["human_review", "architecture_governance"],
    "context_pack_token_pressure_shadow_eval": [
        "context_packing_review",
        "architecture_governance",
    ],
    "proactive_no_send_simulation": ["proactive", "human_review"],
    "recommendation_shadow_eval": ["recommendation", "human_review"],
    "rescue_shadow_candidates": ["rescue_later", "human_review"],
    "memory_review_action_shadow_result": ["human_review", "memory_governance"],
    "memory_promotion_demotion_shadow_eval": ["human_review", "memory_governance"],
    "semantic_pattern_extraction_shadow_plan": [
        "recommendation",
        "nightly_insight",
        "confirmed_memory_candidate_review",
    ],
    "conversation_recall_shadow_eval": [
        "chat_context",
        "intake_clarification",
        "recommendation",
        "calibration",
    ],
    "conversation_recall_tool_shadow_plan": [
        "chat_context",
        "future_manager_context_retrieval",
    ],
    "conversation_recall_retrieval_shadow_eval": [
        "chat_context",
        "intake_clarification",
        "recommendation",
        "calibration",
    ],
    "context_ingress_decision_shadow_eval": [
        "architecture_governance",
        "future_manager_context_retrieval",
        "chat_context",
        "intake_clarification",
        "calibration",
    ],
    "entity_normalization_shadow_plan": [
        "architecture_governance",
        "recommendation",
        "intake_clarification",
        "calibration",
    ],
    "context_quality_contradiction_review_queue": [
        "human_review",
        "architecture_governance",
    ],
    "capability_scenario_fixture_pack": [
        "human_review",
        "architecture_governance",
    ],
    "pr_review_autopilot_closeout": ["human_review", "delivery_governance"],
    "long_term_context_pack_shadow_eval": [
        "recommendation",
        "intake_clarification",
        "chat_context",
        "calibration",
        "proactive",
        "rescue_later",
    ],
    "product_capability_context_map": [
        "architecture_governance",
        "human_review",
    ],
    "external_memory_framework_research_review": [
        "architecture_governance",
        "human_review",
    ],
    "local_memory_framework_review": ["architecture_governance", "human_review"],
    "local_memory_framework_deep_review": [
        "architecture_governance",
        "human_review",
    ],
}


def _base_artifact(
    *,
    artifact_type: str,
    fixture: dict[str, Any],
    extra: dict[str, Any],
) -> dict[str, Any]:
    generated_at = str(fixture.get("generated_at_utc") or "1970-01-01T00:00:00+00:00")
    contract = artifact_review_contract(artifact_type)
    payload = {
        "artifact_schema_version": "1.0",
        "artifact_type": artifact_type,
        "status": "generated",
        "generated_at_utc": generated_at,
        "claim_scope": "long_term_context_shadow_lab",
        "local_only": True,
        "diagnostic_only": True,
        "fixture_input_used": True,
        "real_dogfood_export_used": False,
        "input_reader": fixture.get("_input_reader")
        or {
            "source_shape": "top_level_fixture",
            "fixture_input_used": True,
            "real_dogfood_export_used": False,
            "real_dogfood_export_claim_ignored": False,
            "normalized_sections": [],
            "supported_sections": list(DOGFOOD_EXPORT_SECTIONS)
            + ["chat_trace_metadata"],
            "direct_db_access_used": False,
            "live_provider_called": False,
        },
        **SHADOW_NON_CLAIM_FLAGS,
        **contract,
        **extra,
    }
    payload["runtime_effect_allowed"] = False
    return _json_safe(payload)


def artifact_review_contract(artifact_type: str) -> dict[str, Any]:
    consumers = ARTIFACT_CONSUMER_CATALOG.get(
        artifact_type,
        ["human_review", "architecture_governance"],
    )
    return {
        "intended_consumers": consumers,
        "consumer_use_hints": _consumer_use_hints(consumers),
        "risk_if_wrong": _artifact_risk_if_wrong(artifact_type),
        "promotion_path": _artifact_promotion_path(artifact_type),
        "runtime_effect_allowed": False,
        "why_this_is_not_runtime_truth": _artifact_non_runtime_truth_reason(
            artifact_type
        ),
    }
