from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.consumer_context_packs import (
    _consumer_context_packs,
)
from app.memory.application.long_term_context_shadow.contracts import _base_artifact
from app.memory.domain.long_term_context_candidates import LongTermContextCandidate


def _context_signal_lifecycle_shadow_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    packs = _consumer_context_packs(candidates)
    records = [_lifecycle_record(candidate, packs) for candidate in candidates]
    return _base_artifact(
        artifact_type="context_signal_lifecycle_shadow_eval",
        fixture=fixture,
        extra={
            "runtime_integration_complete": False,
            "shadow_evaluator_complete": True,
            "durable_memory_written": False,
            "manager_context_injected": False,
            "lifecycle_stages": _lifecycle_stages(),
            "source_signal_routes": _source_signal_routes(fixture),
            "candidate_lifecycle_records": records,
            "completion_summary": _completion_summary(records),
            "deferred_runtime_dependencies": [
                "durable_memory_store",
                "memory_correction_and_deletion_surface",
                "manager_context_retrieval_tool",
                "ManagerContextPacket integration",
                "runtime_context_pack_injection_policy",
            ],
        },
    )


def _lifecycle_record(
    candidate: LongTermContextCandidate,
    packs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    selected_pack_ids = _selected_context_pack_ids(candidate, packs)
    return {
        "candidate_id": candidate.candidate_id,
        "candidate_type": candidate.candidate_type,
        "source_trace_ids": candidate.source_trace_ids,
        "source_object_refs": candidate.source_object_refs,
        "source_object_refs_required": True,
        "source_truth_layer": "l1_typed_history_observation",
        "derived_layer": _derived_layer(candidate),
        "review_artifact_key": "context_value_review_queue",
        "selected_context_pack_ids": selected_pack_ids,
        "deferred_reason": (
            ""
            if selected_pack_ids
            else "not_selected_by_current_shadow_pack_rules_keep_review_only"
        ),
        "shadow_replay_ids": _shadow_replay_ids(candidate),
        "context_ingress_mode": _context_ingress_mode(candidate),
        "canonical_truth_owner": _canonical_truth_owner(candidate),
        "promotion_blockers": [
            "human_review_required",
            "runtime_contract_not_approved",
            "durable_memory_write_service_absent",
            "manager_context_injection_forbidden",
        ],
        "runtime_effect_allowed": False,
    }


def _selected_context_pack_ids(
    candidate: LongTermContextCandidate,
    packs: dict[str, dict[str, Any]],
) -> list[str]:
    return [
        pack_id
        for pack_id, pack in sorted(packs.items())
        if candidate.candidate_id in set(pack.get("selected_candidate_ids") or [])
    ]


def _shadow_replay_ids(candidate: LongTermContextCandidate) -> list[str]:
    replay_ids: list[str] = []
    if candidate.candidate_type in {
        "food_preference",
        "golden_order",
        "negative_preference",
        "temporary_preference",
    }:
        replay_ids.append("recommendation_shadow_replay")
    if candidate.candidate_type in {
        "intake_estimation_bias",
        "negative_preference",
        "user_language_pattern",
    }:
        replay_ids.append("intake_clarification_shadow_replay")
    if candidate.candidate_type in {
        "intake_estimation_bias",
        "logging_adherence_pattern",
        "pattern",
    }:
        replay_ids.append("calibration_bias_shadow_replay")
    if candidate.candidate_type == "conversation_recall_context":
        replay_ids.append("conversation_recall_shadow_replay")
    return replay_ids or ["review_queue_only"]


def _source_signal_routes(fixture: dict[str, Any]) -> list[dict[str, Any]]:
    menu_scan = fixture.get("menu_scan_context")
    menu_available = isinstance(menu_scan, dict) and bool(menu_scan)
    return [
        _source_route(
            "meal_logs",
            ["food_preference", "golden_order", "pattern"],
            ["recommendation", "intake_clarification"],
        ),
        _source_route(
            "language_observations",
            ["user_language_pattern"],
            ["intake_clarification", "chat_context"],
        ),
        _source_route(
            "intake_estimation_events",
            ["intake_estimation_bias"],
            ["calibration", "intake_clarification"],
        ),
        _source_route(
            "conversation_history_summaries",
            ["conversation_recall_context"],
            ["chat_context", "future_manager_context_retrieval"],
        ),
        {
            **_source_route(
                "menu_scan_context",
                ["menu_scan_shadow_context"],
                ["recommendation"],
            ),
            "runtime_source_used": False,
            "fixture_source_available": menu_available,
        },
        {
            **_source_route(
                "weekly_highlight_shadow_candidates",
                ["derived_summary_highlight"],
                ["chat_context", "nightly_insight"],
            ),
            "narrative_generated": False,
        },
    ]


def _source_route(
    source_signal_id: str,
    candidate_types: list[str],
    consumers: list[str],
) -> dict[str, Any]:
    return {
        "source_signal_id": source_signal_id,
        "candidate_types": candidate_types,
        "intended_consumers": consumers,
        "runtime_effect_allowed": False,
        "canonical_truth_replaced_by_memory": False,
    }


def _lifecycle_stages() -> list[dict[str, Any]]:
    return [
        {"stage_id": "source_observation", "owner": "canonical_typed_history"},
        {"stage_id": "candidate_extraction", "owner": "shadow_deterministic_engine"},
        {"stage_id": "context_value_scoring", "owner": "shadow_evaluator"},
        {"stage_id": "human_review", "owner": "future_product_owner"},
        {"stage_id": "context_pack_shadow", "owner": "shadow_context_pack_builder"},
        {"stage_id": "shadow_replay", "owner": "shadow_replay_evaluator"},
        {"stage_id": "future_promotion_gate", "owner": "human_approved_runtime_slice"},
    ]


def _completion_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "candidate_count": len(records),
        "candidates_with_source_refs_count": sum(
            1 for record in records if record["source_trace_ids"]
        ),
        "candidates_with_context_pack_count": sum(
            1 for record in records if record["selected_context_pack_ids"]
        ),
        "candidates_with_replay_count": sum(
            1 for record in records if record["shadow_replay_ids"]
        ),
        "candidates_blocked_from_runtime_count": len(records),
        "all_candidates_have_lifecycle_records": True,
        "all_candidates_have_pack_or_deferred_reason": all(
            record["selected_context_pack_ids"] or record["deferred_reason"]
            for record in records
        ),
    }


def _derived_layer(candidate: LongTermContextCandidate) -> str:
    if candidate.candidate_type in {"pattern", "logging_adherence_pattern"}:
        return "l2a_deterministic_statistical_pattern"
    return "l2_candidate_or_review_signal"


def _context_ingress_mode(candidate: LongTermContextCandidate) -> str:
    if candidate.candidate_type == "conversation_recall_context":
        return "future_tool_mediated_recall"
    return "summary_first_context_pack"


def _canonical_truth_owner(candidate: LongTermContextCandidate) -> str:
    if candidate.candidate_type in {"food_preference", "golden_order"}:
        return "MealThread_and_FoodDB_remain_canonical"
    if candidate.candidate_type in {"intake_estimation_bias", "pattern"}:
        return "DayBudgetLedger_and_calibration_diagnostics_remain_canonical"
    if candidate.candidate_type == "logging_adherence_pattern":
        return "MealThread_BodyObservation_and_DayBudgetLedger_remain_canonical"
    return "source_trace_history_remains_canonical"


__all__ = ["_context_signal_lifecycle_shadow_artifact"]
