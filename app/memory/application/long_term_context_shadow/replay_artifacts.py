from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.contracts import _base_artifact
from app.memory.application.long_term_context_shadow.extraction_engine_artifact import (
    _menu_scan_shadow_context,
)
from app.memory.application.long_term_context_shadow.reviewed_product_replay import (
    reviewed_memory_product_loop_replay,
)
from app.memory.domain.long_term_context_candidates import LongTermContextCandidate


def _shadow_replay_evaluators_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    recommendation = _recommendation_shadow_replay(fixture, candidates)
    intake = _intake_clarification_shadow_replay(candidates)
    calibration = _calibration_bias_shadow_replay(candidates)
    conversation = _conversation_recall_shadow_replay(candidates)
    reviewed_product = reviewed_memory_product_loop_replay(fixture, candidates)
    return _base_artifact(
        artifact_type="shadow_replay_evaluators",
        fixture=fixture,
        extra={
            "recommendation_served": False,
            "intake_commit_requested": False,
            "calibration_math_changed": False,
            "manager_context_packet_written": False,
            "replays": {
                "recommendation_shadow_replay": recommendation,
                "intake_clarification_shadow_replay": intake,
                "calibration_bias_shadow_replay": calibration,
                "conversation_recall_shadow_replay": conversation,
                "reviewed_memory_product_loop_replay": reviewed_product,
            },
            "replay_count": 5,
        },
    )


def _recommendation_shadow_replay(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    used = [
        candidate
        for candidate in candidates
        if candidate.candidate_type
        in {
            "golden_order",
            "food_preference",
            "negative_preference",
            "temporary_preference",
        }
    ]
    used_ids = {candidate.candidate_id for candidate in used}
    menu_context = _menu_scan_shadow_context(fixture)
    return {
        "replay_id": "recommendation_shadow_replay",
        "expected_user_value": "better_candidate_ranking_review",
        "used_candidate_ids": sorted(used_ids),
        "ignored_candidates": _ignored_candidates(candidates, used_ids),
        "menu_scan_context_used_as_candidate_source": bool(
            menu_context.get("available")
        ),
        "runtime_recommendation_mode_started": False,
        "ranking_basis": [
            "preference_profile_summary_shadow",
            "golden_order_shadow",
            "negative_preference_guardrail_shadow",
        ],
        "risk_if_wrong": "Could bias ranking before user-confirmed memory exists.",
        "recommendation_served": False,
        "runtime_effect_allowed": False,
    }


def _conversation_recall_shadow_replay(
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    used = [
        candidate
        for candidate in candidates
        if candidate.candidate_type == "conversation_recall_context"
    ]
    used_ids = {candidate.candidate_id for candidate in used}
    return {
        "replay_id": "conversation_recall_shadow_replay",
        "expected_user_value": "better_cross_session_context_review",
        "used_candidate_ids": sorted(used_ids),
        "ignored_candidates": _ignored_candidates(candidates, used_ids),
        "routing_basis": [
            "summary_first_conversation_archive",
            "source_scope_required",
            "raw_transcript_fallback_disabled",
        ],
        "manager_tool_call_allowed": False,
        "raw_transcript_injected": False,
        "manager_context_packet_written": False,
        "risk_if_wrong": "Could retrieve stale conversation context into a future turn.",
        "runtime_effect_allowed": False,
    }


def _intake_clarification_shadow_replay(
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    used = [
        candidate
        for candidate in candidates
        if candidate.candidate_type
        in {"user_language_pattern", "intake_estimation_bias", "negative_preference"}
    ]
    used_ids = {candidate.candidate_id for candidate in used}
    low_confidence_phrase = any(
        candidate.candidate_type == "user_language_pattern"
        and candidate.confidence < 0.7
        for candidate in used
    )
    return {
        "replay_id": "intake_clarification_shadow_replay",
        "expected_user_value": "fewer_but_better_followups_review",
        "used_candidate_ids": sorted(used_ids),
        "ignored_candidates": _ignored_candidates(candidates, used_ids),
        "clarification_policy": (
            "ask_targeted_followup"
            if low_confidence_phrase
            else "use_phrase_pattern_with_caution"
        ),
        "risk_if_wrong": "Could over-assume meaning of a user phrase.",
        "intake_commit_requested": False,
        "runtime_effect_allowed": False,
    }


def _calibration_bias_shadow_replay(
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    used = [
        candidate
        for candidate in candidates
        if candidate.candidate_type
        in {"intake_estimation_bias", "logging_adherence_pattern", "pattern"}
        and (
            "calibration" in candidate.intended_consumers
            or "intake_risk_tagging" in candidate.intended_consumers
        )
    ]
    used_ids = {candidate.candidate_id for candidate in used}
    return {
        "replay_id": "calibration_bias_shadow_replay",
        "expected_user_value": "better_bias_attribution_review",
        "used_candidate_ids": sorted(used_ids),
        "ignored_candidates": _ignored_candidates(candidates, used_ids),
        "does_not_change_calibration_math": True,
        "bias_attribution": _bias_attribution(used),
        "risk_if_wrong": "Could misattribute mismatch without changing the math.",
        "calibration_math_changed": False,
        "body_plan_mutated": False,
        "day_budget_mutated": False,
        "runtime_effect_allowed": False,
    }


def _bias_attribution(
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    likely_underestimate: list[str] = []
    likely_overestimate: list[str] = []
    logging_quality: list[str] = []
    for candidate in candidates:
        direction = str(candidate.payload.get("bias_direction") or "")
        if direction == "likely_underestimate":
            likely_underestimate.append(candidate.candidate_id)
        elif direction == "likely_overestimate":
            likely_overestimate.append(candidate.candidate_id)
        elif candidate.candidate_type == "logging_adherence_pattern":
            logging_quality.append(candidate.candidate_id)
    return {
        "likely_underestimate_candidate_ids": sorted(likely_underestimate),
        "likely_overestimate_candidate_ids": sorted(likely_overestimate),
        "logging_quality_candidate_ids": sorted(logging_quality),
        "math_adjustment_allowed": False,
        "runtime_effect_allowed": False,
    }


def _ignored_candidates(
    candidates: list[LongTermContextCandidate],
    used_ids: set[str],
) -> list[dict[str, str]]:
    return [
        {
            "candidate_id": candidate.candidate_id,
            "candidate_type": candidate.candidate_type,
            "ignored_reason": "not_relevant_to_this_replay_consumer",
        }
        for candidate in candidates
        if candidate.candidate_id not in used_ids
    ]
