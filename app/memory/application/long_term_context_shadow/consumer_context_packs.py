from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.lab_active_view import (
    reviewed_context_pack_fields,
)
from app.memory.application.long_term_context_shadow.utils import (
    _context_candidate_summary,
    _token_estimate,
)
from app.memory.domain.long_term_context_candidates import LongTermContextCandidate


def _consumer_context_packs(
    candidates: list[LongTermContextCandidate],
    reviewed_view: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    return {
        **_recommendation_and_intake_packs(candidates, reviewed_view),
        **_calibration_and_proactive_packs(candidates, reviewed_view),
        **_rescue_and_cross_surface_packs(candidates, reviewed_view),
    }


def _recommendation_and_intake_packs(
    candidates: list[LongTermContextCandidate],
    reviewed_view: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    return {
        "recommendation": _context_pack(
            pack_id="recommendation",
            candidates=candidates,
            reviewed_view=reviewed_view,
            allowed_consumers={"recommendation", "recommendation_presentation"},
            allowed_candidate_types={
                "food_preference",
                "golden_order",
                "negative_preference",
                "temporary_preference",
                "user_language_pattern",
                "conversation_recall_context",
            },
        ),
        "intake_chat_context": _context_pack(
            pack_id="intake_chat_context",
            candidates=candidates,
            reviewed_view=reviewed_view,
            allowed_consumers={
                "chat_context",
                "intake_clarification",
                "response_context",
                "response_generation",
                "nutrition_clarify_priority",
            },
            allowed_candidate_types={
                "app_usage_style",
                "conversation_recall_context",
                "food_preference",
                "golden_order",
                "intake_estimation_bias",
                "interaction_preference",
                "negative_preference",
                "pattern",
                "temporary_preference",
                "user_language_pattern",
            },
        ),
    }


def _calibration_and_proactive_packs(
    candidates: list[LongTermContextCandidate],
    reviewed_view: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    return {
        "calibration_context": _context_pack(
            pack_id="calibration_context",
            candidates=candidates,
            reviewed_view=reviewed_view,
            allowed_consumers={
                "calibration",
                "intake_risk_tagging",
                "nutrition_clarify_priority",
            },
            allowed_candidate_types={
                "conversation_recall_context",
                "intake_estimation_bias",
                "logging_adherence_pattern",
                "pattern",
            },
        ),
        "proactive_context": _context_pack(
            pack_id="proactive_context",
            candidates=candidates,
            reviewed_view=reviewed_view,
            allowed_consumers={
                "proactive",
                "proactive_message_style",
                "recommendation",
                "rescue_later",
            },
            allowed_candidate_types={
                "app_usage_style",
                "food_preference",
                "golden_order",
                "interaction_preference",
                "logging_adherence_pattern",
                "negative_preference",
                "pattern",
                "temporary_preference",
            },
        ),
    }


def _rescue_and_cross_surface_packs(
    candidates: list[LongTermContextCandidate],
    reviewed_view: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    return {
        "rescue_context": _context_pack(
            pack_id="rescue_context",
            candidates=candidates,
            reviewed_view=reviewed_view,
            allowed_consumers={"rescue_later", "calibration", "proactive"},
            allowed_candidate_types={
                "intake_estimation_bias",
                "interaction_preference",
                "logging_adherence_pattern",
                "pattern",
            },
        ),
        "cross_surface_context": _context_pack(
            pack_id="cross_surface_context",
            candidates=candidates,
            reviewed_view=reviewed_view,
            allowed_consumers={
                "chat_context",
                "intake_clarification",
                "proactive",
                "response_generation",
                "ux",
            },
            allowed_candidate_types={
                "app_usage_style",
                "conversation_recall_context",
                "interaction_preference",
                "user_language_pattern",
            },
        ),
    }


def _context_pack(
    *,
    pack_id: str,
    candidates: list[LongTermContextCandidate],
    reviewed_view: dict[str, Any] | None,
    allowed_consumers: set[str],
    allowed_candidate_types: set[str],
) -> dict[str, Any]:
    selected = [
        candidate
        for candidate in candidates
        if candidate.candidate_type in allowed_candidate_types
        and allowed_consumers.intersection(candidate.intended_consumers)
    ]
    selected.sort(
        key=lambda candidate: (
            _context_pack_rank(pack_id, candidate),
            -candidate.confidence,
            candidate.candidate_id,
        )
    )
    selected_text = " ".join(
        str(candidate.proposed_memory_text or "") for candidate in selected
    )
    return {
        "pack_id": pack_id,
        "summary_first": True,
        "structured_state_first": True,
        "raw_full_history_dumped": False,
        "runtime_effect_allowed": False,
        "manager_context_injection_allowed": False,
        "selected_candidate_ids": [candidate.candidate_id for candidate in selected],
        "selected_candidate_summaries": [
            _context_candidate_summary(candidate) for candidate in selected
        ],
        **reviewed_context_pack_fields(pack_id, reviewed_view),
        "token_estimate": _token_estimate(selected_text),
        "omission_trace": {
            "raw_transcript_omitted": True,
            "full_history_dump_omitted": True,
            "unselected_candidates_omitted": max(
                0,
                len(candidates) - len(selected),
            ),
        },
    }


def _context_pack_rank(
    pack_id: str,
    candidate: LongTermContextCandidate,
) -> int:
    ranking = {
        "recommendation": {
            "golden_order": 0,
            "food_preference": 1,
            "negative_preference": 2,
            "temporary_preference": 3,
            "user_language_pattern": 4,
            "conversation_recall_context": 5,
        },
        "intake_chat_context": {
            "user_language_pattern": 0,
            "interaction_preference": 1,
            "app_usage_style": 2,
            "intake_estimation_bias": 3,
            "negative_preference": 4,
            "temporary_preference": 5,
            "conversation_recall_context": 6,
            "golden_order": 7,
            "food_preference": 8,
            "pattern": 9,
        },
        "calibration_context": {
            "intake_estimation_bias": 0,
            "logging_adherence_pattern": 1,
            "pattern": 2,
            "conversation_recall_context": 3,
        },
        "proactive_context": {
            "app_usage_style": 0,
            "interaction_preference": 1,
            "logging_adherence_pattern": 2,
            "negative_preference": 3,
            "temporary_preference": 4,
            "food_preference": 5,
            "golden_order": 6,
            "pattern": 7,
        },
        "rescue_context": {
            "logging_adherence_pattern": 0,
            "intake_estimation_bias": 1,
            "pattern": 2,
            "interaction_preference": 3,
        },
        "cross_surface_context": {
            "app_usage_style": 0,
            "interaction_preference": 1,
            "conversation_recall_context": 2,
            "user_language_pattern": 3,
        },
    }
    return ranking.get(pack_id, {}).get(candidate.candidate_type, 99)
