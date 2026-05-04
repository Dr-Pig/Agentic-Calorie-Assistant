from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.contracts import _base_artifact


def _memory_dependency_graph_shadow_artifact(
    fixture: dict[str, Any],
) -> dict[str, Any]:
    return _base_artifact(
        artifact_type="memory_dependency_graph_shadow_eval",
        fixture=fixture,
        extra={
            "source_specs": [
                "docs/specs/L4A_MEMORY_MODEL_SPEC.md",
                "docs/specs/L4B_RETRIEVAL_POLICY_SPEC.md",
                "docs/specs/L4C_CONTEXT_PACKING_SPEC.md",
                "docs/specs/L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md",
                "docs/specs/L3_2_RECOMMENDATION_RUNTIME_INTERFACE_CONTRACT_SPEC.md",
                "docs/specs/L3_3A_DEFICIT_EXPENDITURE_CALIBRATION_MODEL_SPEC.md",
                "docs/specs/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md",
                "docs/specs/L3_6_PROACTIVE_SCHEDULER_SPEC.md",
            ],
            "live_consumer_activation_allowed": False,
            "topological_build_order": [
                "memory_candidate_substrate",
                "human_review_and_promotion_policy",
                "summary_first_context_pack_compiler",
                "durable_review_store_and_retrieval_index_later",
                "manager_context_injection_gate_later",
                "consumer_runtime_activation_later",
            ],
            "blocked_live_consumers": [
                "recommendation_runtime",
                "proactive_scheduler_runtime",
                "calibration_runtime_context_injection",
                "rescue_proposal_runtime",
            ],
            "consumer_dependencies": _consumer_dependencies(),
        },
    )


def _consumer_dependencies() -> dict[str, dict[str, Any]]:
    return {
        "recommendation": _recommendation_dependencies(),
        "intake_chat_context": _intake_chat_dependencies(),
        "calibration": _calibration_dependencies(),
        "proactive": _proactive_dependencies(),
        "rescue_later": _rescue_dependencies(),
    }


def _recommendation_dependencies() -> dict[str, Any]:
    return _dependency(
        memory_role="ranking_filtering_and_presentation_context",
        memory_required_before_live_runtime=True,
        shadow_buildable_now=[
            "preference_candidate_extraction",
            "negative_preference_filtering_eval",
            "golden_order_derived_view_eval",
            "recommendation_context_pack_eval",
        ],
        blocked_until=[
            "durable_memory_review_store",
            "reviewed_preference_profile_summary",
            "runtime_context_pack_injection_gate",
            "recommendation_graph_runtime",
        ],
        forbidden_effects=[
            "recommendation_served_to_user",
            "intake_commit",
            "fooddb_truth_change",
        ],
    )


def _intake_chat_dependencies() -> dict[str, Any]:
    return _dependency(
        memory_role="phrase_understanding_and_response_style_context",
        memory_required_before_live_runtime=True,
        shadow_buildable_now=[
            "user_language_candidate_extraction",
            "interaction_preference_eval",
            "conversation_recall_summary_eval",
        ],
        blocked_until=[
            "chat_review_correction_commands",
            "manager_context_retrieval_tool",
            "runtime_context_pack_injection_gate",
        ],
        forbidden_effects=[
            "raw_transcript_prompt_dump",
            "skip_required_clarification",
            "food_semantics_rewrite",
        ],
    )


def _calibration_dependencies() -> dict[str, Any]:
    return _dependency(
        memory_role="bias_attribution_and_quality_context",
        memory_required_before_live_runtime=True,
        shadow_buildable_now=[
            "logging_adherence_pattern_eval",
            "intake_estimation_bias_eval",
            "calibration_context_pack_eval",
        ],
        blocked_until=[
            "calibration_diagnostics_export",
            "bias_posture_handoff_contract",
            "runtime_context_pack_injection_gate",
        ],
        forbidden_effects=[
            "calorie_truth_rewrite",
            "body_plan_mutation",
            "day_budget_mutation",
        ],
    )


def _proactive_dependencies() -> dict[str, Any]:
    return _dependency(
        memory_role="timing_suppression_and_context_quality",
        memory_required_before_live_runtime=True,
        shadow_buildable_now=[
            "proactive_no_send_eval",
            "proactive_silence_policy_eval",
            "suppression_memory_candidate_eval",
        ],
        blocked_until=[
            "scheduler_activation",
            "dismiss_snooze_correction_surface",
            "send_skip_manager_trace_contract",
        ],
        forbidden_effects=[
            "channel_send",
            "scheduler_hook",
            "auto_action_without_undo_or_dismiss",
        ],
    )


def _rescue_dependencies() -> dict[str, Any]:
    return _dependency(
        memory_role="viability_context_after_budget_truth",
        memory_required_before_live_runtime=True,
        shadow_buildable_now=[
            "overshoot_pattern_eval",
            "adherence_pattern_eval",
            "rescue_viability_context_pack_eval",
        ],
        blocked_until=[
            "current_budget_truth_contract",
            "proposal_commit_runtime",
            "rescue_acceptance_ledger_effects",
        ],
        forbidden_effects=[
            "budget_overlay_mutation",
            "proposal_commit",
            "rescue_message_sent",
        ],
    )


def _dependency(
    *,
    memory_role: str,
    memory_required_before_live_runtime: bool,
    shadow_buildable_now: list[str],
    blocked_until: list[str],
    forbidden_effects: list[str],
) -> dict[str, Any]:
    return {
        "memory_role": memory_role,
        "memory_required_before_live_runtime": memory_required_before_live_runtime,
        "shadow_buildable_now": shadow_buildable_now,
        "blocked_until": blocked_until,
        "forbidden_effects": forbidden_effects,
        "deterministic_boundary": {
            "may_validate_scope": True,
            "may_score_review_priority": True,
            "may_block_runtime_effect": True,
            "may_decide_runtime_use": False,
        },
        "runtime_effect_allowed": False,
    }


__all__ = ["_memory_dependency_graph_shadow_artifact"]
