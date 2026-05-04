from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.contracts import _base_artifact
from app.memory.domain.long_term_context_candidates import LongTermContextCandidate


def _capability_scenario_fixture_pack_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    available_types = {candidate.candidate_type for candidate in candidates}
    scenarios = _capability_scenario_fixtures()
    return _base_artifact(
        artifact_type="capability_scenario_fixture_pack",
        fixture=fixture,
        extra={
            "fixture_only": True,
            "runtime_scenarios_executed": False,
            "scenario_count": len(scenarios),
            "available_candidate_types": sorted(available_types),
            "scenarios": scenarios,
        },
    )


def _capability_scenario_fixtures() -> list[dict[str, Any]]:
    return (
        _recommendation_and_chat_scenarios()
        + _calibration_proactive_rescue_scenarios()
        + _conversation_recall_scenarios()
    )


def _recommendation_and_chat_scenarios() -> list[dict[str, Any]]:
    return [
        _capability_scenario(
            scenario_id="recommendation_with_preferences",
            consumer_id="recommendation",
            expected_artifact_ids=[
                "long_term_memory_candidate_review",
                "recommendation_shadow_eval",
                "long_term_context_pack_shadow_eval",
            ],
            candidate_types=["food_preference", "negative_preference", "golden_order"],
        ),
        _capability_scenario(
            scenario_id="intake_clarification_with_user_language",
            consumer_id="intake_clarification",
            expected_artifact_ids=[
                "long_term_memory_candidate_review",
                "context_value_review_queue",
            ],
            candidate_types=["user_language_pattern", "intake_estimation_bias"],
        ),
        _capability_scenario(
            scenario_id="chat_context_style_shadow",
            consumer_id="chat_context",
            expected_artifact_ids=[
                "long_term_context_pack_shadow_eval",
                "conversation_recall_shadow_eval",
            ],
            candidate_types=["app_usage_style", "interaction_preference"],
        ),
    ]


def _calibration_proactive_rescue_scenarios() -> list[dict[str, Any]]:
    return [
        _capability_scenario(
            scenario_id="calibration_bias_attribution_shadow",
            consumer_id="calibration",
            expected_artifact_ids=[
                "context_quality_contradiction_review_queue",
                "long_term_context_pack_shadow_eval",
            ],
            candidate_types=["intake_estimation_bias", "logging_adherence_pattern"],
        ),
        _capability_scenario(
            scenario_id="proactive_no_send_timing_shadow",
            consumer_id="proactive",
            expected_artifact_ids=[
                "proactive_no_send_simulation",
                "long_term_context_pack_shadow_eval",
            ],
            candidate_types=["app_usage_style", "logging_adherence_pattern"],
        ),
        _capability_scenario(
            scenario_id="rescue_later_viability_shadow",
            consumer_id="rescue_later",
            expected_artifact_ids=[
                "rescue_shadow_candidates",
                "long_term_context_pack_shadow_eval",
            ],
            candidate_types=["logging_adherence_pattern", "intake_estimation_bias"],
        ),
    ]


def _conversation_recall_scenarios() -> list[dict[str, Any]]:
    return [
        _capability_scenario(
            scenario_id="conversation_recall_tool_shadow",
            consumer_id="conversation_recall",
            expected_artifact_ids=[
                "conversation_recall_tool_shadow_plan",
                "conversation_recall_retrieval_shadow_eval",
            ],
            candidate_types=["conversation_recall_context"],
        ),
    ]


def _capability_scenario(
    *,
    scenario_id: str,
    consumer_id: str,
    expected_artifact_ids: list[str],
    candidate_types: list[str],
) -> dict[str, Any]:
    return {
        "scenario_id": scenario_id,
        "consumer_id": consumer_id,
        "candidate_types": candidate_types,
        "expected_artifact_ids": expected_artifact_ids,
        "runtime_effect_allowed": False,
        "forbidden_runtime_effects": [
            "manager_context_injection",
            "durable_memory_write",
            "db_mutation",
            "live_provider_call",
            "proactive_send",
            "recommendation_served",
            "rescue_commit",
        ],
        "acceptance_focus": "review_artifact_shape_only",
    }
