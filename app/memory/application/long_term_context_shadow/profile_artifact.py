from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.contracts import _base_artifact
from app.memory.domain.long_term_context_candidates import LongTermContextCandidate


def _user_context_profile_shadow_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    return _base_artifact(
        artifact_type="user_context_profile_shadow_eval",
        fixture=fixture,
        extra={
            "profile_materialized_to_runtime": False,
            "structured_user_model_written": False,
            "canonical_truth_replaced_by_profile": False,
            "memory_layer_order": [
                "l1_observation_typed_history",
                "l2_inference_shadow_candidates",
                "l3_profile_shadow_review",
            ],
            "profile_sections": [
                _profile_section(
                    "food_preference_profile",
                    candidates,
                    {
                        "food_preference",
                        "golden_order",
                        "negative_preference",
                        "temporary_preference",
                    },
                    ["recommendation", "intake_clarification", "proactive"],
                ),
                _profile_section(
                    "user_language_profile",
                    candidates,
                    {"user_language_pattern"},
                    ["intake_clarification", "chat_context", "recommendation"],
                ),
                _profile_section(
                    "estimation_bias_profile",
                    candidates,
                    {"intake_estimation_bias"},
                    ["calibration", "intake_clarification"],
                ),
                _profile_section(
                    "app_usage_profile",
                    candidates,
                    {"app_usage_style"},
                    ["chat_context", "proactive", "ux"],
                ),
                _profile_section(
                    "interaction_preference_profile",
                    candidates,
                    {"interaction_preference"},
                    ["response_generation", "chat_context"],
                ),
                _profile_section(
                    "adherence_profile",
                    candidates,
                    {"logging_adherence_pattern", "pattern"},
                    ["calibration", "proactive", "rescue_later"],
                ),
                _profile_section(
                    "conversation_recall_profile",
                    candidates,
                    {"conversation_recall_context"},
                    ["chat_context", "future_manager_context_retrieval"],
                ),
            ],
        },
    )


def _profile_section(
    section_id: str,
    candidates: list[LongTermContextCandidate],
    candidate_types: set[str],
    consumers: list[str],
) -> dict[str, Any]:
    source_candidates = [
        candidate
        for candidate in candidates
        if candidate.candidate_type in candidate_types
        and set(candidate.intended_consumers).intersection(consumers)
    ]
    return {
        "profile_section_id": section_id,
        "source_candidate_ids": [
            candidate.candidate_id for candidate in source_candidates
        ],
        "source_trace_ids": sorted(
            {
                trace_id
                for candidate in source_candidates
                for trace_id in candidate.source_trace_ids
            }
        ),
        "intended_consumers": consumers,
        "candidate_types": sorted(candidate_types),
        "profile_write_allowed": False,
        "runtime_effect_allowed": False,
        "risk_if_wrong": _profile_risk(section_id),
        "promotion_path": "human_review_then_profile_slice_later",
    }


def _profile_risk(section_id: str) -> str:
    risks = {
        "food_preference_profile": "Could bias food ranking before confirmed preference.",
        "user_language_profile": "Could over-assume phrase meaning and skip needed clarification.",
        "estimation_bias_profile": "Could misattribute intake mismatch without enough evidence.",
        "app_usage_profile": "Could personalize reminders or UX timing too aggressively.",
        "interaction_preference_profile": "Could adapt response style against current user intent.",
        "adherence_profile": "Could overstate adherence risk or rescue viability.",
        "conversation_recall_profile": "Could retrieve stale prior conversation context.",
    }
    return risks.get(section_id, "Could over-personalize before human review.")


__all__ = ["_user_context_profile_shadow_artifact"]
