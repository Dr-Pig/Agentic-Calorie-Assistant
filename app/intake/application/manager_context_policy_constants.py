from __future__ import annotations

MANAGER_CONTEXT_POLICY_VERSION = "accurate_intake_mvp_context_policy_v1"

DEFERRED_CONTEXT_REASONS = {
    "debug_artifacts": "debug_surface_trace_only",
    "dogfood_review_artifacts": "operator_review_not_manager_input",
    "raw_trace_dump": "trace_dump_not_manager_input",
    "food_gap_candidates": "review_candidate_not_food_truth",
    "long_term_memory": "out_of_scope_for_mvp",
    "proactive_context": "out_of_scope_for_mvp",
    "rescue_context": "out_of_scope_for_mvp",
    "recommendation_context": "out_of_scope_for_mvp",
}

POLICY_EXCLUDED_CONTEXT_IDS = (
    "debug_artifacts",
    "dogfood_review_artifacts",
    "raw_trace_dump",
    "food_gap_candidates_as_truth",
    "full_day_transcript_by_default",
    "long_term_memory",
    "proactive_context",
    "rescue_context",
    "recommendation_context",
)

INTERACTION_EVENT_FIELDS = (
    "source",
    "surface_mode",
    "event_type",
    "raw_text",
    "action_id",
    "target_object_type",
    "target_object_id",
    "occurred_at",
)
DISPLAY_LABEL_FIELDS = ("display_name", "target_label", "label")
TARGET_CANDIDATE_FIELDS = (
    "item_id",
    "meal_item_id",
    "meal_thread_id",
    "meal_version_id",
    "target_object_type",
    "target_object_id",
    "display_name", "canonical_name", "estimated_kcal", "estimate_basis",
    "confidence_tier", "source", "evidence_role", "uniqueness_status",
)
TARGET_CANDIDATE_BOOL_FIELDS = ("removable", "eligible")
