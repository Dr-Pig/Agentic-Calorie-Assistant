from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.contracts import _base_artifact


def _context_ingress_decision_shadow_artifact(
    fixture: dict[str, Any],
) -> dict[str, Any]:
    return _base_artifact(
        artifact_type="context_ingress_decision_shadow_eval",
        fixture=fixture,
        extra={
            "source_specs": [
                "docs/specs/L4A_MEMORY_MODEL_SPEC.md",
                "docs/specs/L4C_CONTEXT_PACKING_SPEC.md",
                "docs/specs/L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md",
            ],
            "manager_tool_registered": False,
            "manager_tool_called": False,
            "manager_context_injected": False,
            "runtime_context_loaded": False,
            "context_ingress_modes": [
                "shadow_artifact_review",
                "summary_first_context_pack",
                "future_tool_mediated_recall",
            ],
            "memory_state_taxonomy": _memory_state_taxonomy(),
            "source_of_meaning_decisions": _source_of_meaning_decisions(),
            "future_manager_recall_boundary": {
                "tool_name": "conversation_recall.search",
                "allowed_now": False,
                "summary_first_required": True,
                "raw_transcript_returned": False,
                "scope_keys_required": [
                    "user_id",
                    "workspace_id",
                    "surface_id",
                    "retention_class",
                    "privacy_class",
                ],
            },
        },
    )


def _memory_state_taxonomy() -> list[dict[str, Any]]:
    return [
        {
            "state_class": "l1_typed_history_observation",
            "examples": ["MealThread", "BodyObservation", "DayBudgetLedger"],
            "truth_role": "canonical_source",
            "runtime_write_allowed_now": False,
            "raw_transcript_returned": False,
        },
        {
            "state_class": "l2_pattern_inference",
            "examples": ["food_preference", "intake_estimation_bias"],
            "truth_role": "derived_candidate",
            "runtime_write_allowed_now": False,
            "raw_transcript_returned": False,
        },
        {
            "state_class": "l3_profile_or_confirmed_memory_future",
            "examples": ["PreferenceProfileSummary", "confirmed_negative_preference"],
            "truth_role": "human_reviewed_memory_future",
            "runtime_write_allowed_now": False,
            "raw_transcript_returned": False,
        },
        {
            "state_class": "conversation_recall_summary",
            "examples": ["summary_first_prior_dialogue_context"],
            "truth_role": "context_ingress_candidate",
            "runtime_write_allowed_now": False,
            "raw_transcript_returned": False,
        },
    ]


def _source_of_meaning_decisions() -> list[dict[str, Any]]:
    return [
        {
            "decision_id": "canonical_truth_not_replaced_by_memory",
            "meaning_owner": "canonical_typed_history",
            "memory_role": "contextual_hint_only",
            "enforced_now": True,
        },
        {
            "decision_id": "profile_view_is_derived_not_durable_truth",
            "meaning_owner": "human_review_future_promotion",
            "memory_role": "reviewable_summary",
            "enforced_now": True,
        },
        {
            "decision_id": "conversation_recall_is_context_ingress_not_memory_write",
            "meaning_owner": "future_manager_recall_tool",
            "memory_role": "summary_first_context_source",
            "future_tool_call_allowed_now": False,
        },
    ]
