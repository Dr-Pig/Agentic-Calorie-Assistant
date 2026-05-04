from __future__ import annotations

from typing import Any


def memory_extraction_lanes() -> list[dict[str, Any]]:
    return [
        _explicit_user_statement_lane(),
        _canonical_history_consolidation_lane(),
        _correction_lineage_lane(),
        _recommendation_feedback_lane(),
        _proactive_suppression_feedback_lane(),
        _conversation_summary_recall_lane(),
    ]


def _explicit_user_statement_lane() -> dict[str, Any]:
    return _lane(
        lane_id="explicit_user_statement",
        input_sources=["chat_trace_metadata", "language_observations"],
        candidate_types=[
            "interaction_preference",
            "negative_preference",
            "temporary_preference",
            "user_language_pattern",
        ],
        product_capability_value="chat_context_and_intake_clarification",
    )


def _canonical_history_consolidation_lane() -> dict[str, Any]:
    return _lane(
        lane_id="canonical_history_consolidation",
        input_sources=[
            "meal_logs",
            "body_observations",
            "budget_summaries",
            "calibration_diagnostics",
        ],
        candidate_types=[
            "food_preference",
            "golden_order",
            "logging_adherence_pattern",
            "pattern",
        ],
        product_capability_value="recommendation_and_calibration",
    )


def _correction_lineage_lane() -> dict[str, Any]:
    return _lane(
        lane_id="correction_lineage",
        input_sources=["intake_estimation_events", "review_actions"],
        candidate_types=[
            "intake_estimation_bias",
            "missed_item_pattern",
            "correction_tendency",
        ],
        product_capability_value="calibration_bias_and_intake_clarification",
    )


def _recommendation_feedback_lane() -> dict[str, Any]:
    return _lane(
        lane_id="recommendation_feedback",
        input_sources=["candidate_pool", "menu_scan_context", "review_actions"],
        candidate_types=[
            "menu_highlight_context",
            "store_familiarity",
            "negative_preference",
        ],
        product_capability_value="recommendation_ranking_and_explanation",
    )


def _proactive_suppression_feedback_lane() -> dict[str, Any]:
    lane = _lane(
        lane_id="proactive_suppression_feedback",
        input_sources=["app_usage_events", "interaction_events"],
        candidate_types=[
            "app_usage_style",
            "interaction_preference",
            "suppression_summary",
        ],
        product_capability_value="proactive_less_annoying_more_timely",
    )
    lane["write_to_scheduler"] = False
    return lane


def _conversation_summary_recall_lane() -> dict[str, Any]:
    lane = _lane(
        lane_id="conversation_summary_recall",
        input_sources=["conversation_history_summaries"],
        candidate_types=["conversation_recall_context"],
        product_capability_value="manager_future_context_ingress",
    )
    lane["manager_tool_registered"] = False
    return lane


def _lane(
    *,
    lane_id: str,
    input_sources: list[str],
    candidate_types: list[str],
    product_capability_value: str,
) -> dict[str, Any]:
    return {
        "lane_id": lane_id,
        "input_sources": input_sources,
        "candidate_types": candidate_types,
        "product_capability_value": product_capability_value,
        "deterministic_allowed_now": True,
        "llm_allowed_now": False,
        "runtime_memory_write_allowed": False,
    }


__all__ = ["memory_extraction_lanes"]
