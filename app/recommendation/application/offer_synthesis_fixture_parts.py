from __future__ import annotations

from typing import Any, Mapping

from app.recommendation.application.offer_synthesis_chat_first_packet import (
    backup_options,
    explanation_card,
    recommendation_control_model,
)


def empty_ranking() -> dict[str, Any]:
    return {
        "pool_decision": "silent_no_qualified_candidate",
        "ranked_candidate_ids": [],
        "selected_primary": "",
        "backup_candidate_ids": [],
    }


def ranking(
    retrieval: Mapping[str, Any],
    allowed: list[Mapping[str, Any]],
    primary: Mapping[str, Any],
    backups: list[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "pool_decision": str(retrieval.get("pool_decision") or ""),
        "ranked_candidate_ids": [str(item.get("candidate_id") or "") for item in allowed],
        "selected_primary": str(primary.get("candidate_id") or ""),
        "backup_candidate_ids": [str(item.get("candidate_id") or "") for item in backups],
    }


def ux_packet(
    *,
    retrieval_guard_scoring: Mapping[str, Any],
    primary_candidate: Mapping[str, Any],
    public_primary: Mapping[str, Any],
    public_backups: list[Mapping[str, Any]],
    explanation: str,
) -> dict[str, Any]:
    return {
        "surface": "chat",
        "chat_first": True,
        "serve_allowed_in_lab": True,
        "served_to_mainline_user": False,
        "primary_candidate_id": str(public_primary.get("candidate_id") or ""),
        "backup_candidate_ids": [str(item.get("candidate_id") or "") for item in public_backups],
        "primary_candidate": dict(public_primary),
        "backup_candidates": [dict(candidate) for candidate in public_backups],
        "explanation": explanation,
        "explanation_card": explanation_card(
            primary_candidate=public_primary,
            explanation=explanation,
            backup_count=len(public_backups),
        ),
        "backup_options": backup_options(public_backups),
        "control_model": recommendation_control_model(),
        "pre_meal_planning_packet": _premeal_packet(
            primary_candidate=primary_candidate,
            context=_mapping(retrieval_guard_scoring.get("pre_meal_planning_context")),
            remaining_kcal=_remaining_kcal_from_retrieval(retrieval_guard_scoring),
        ),
        "swap_suggestion_packet": _swap_packet(
            context=_mapping(retrieval_guard_scoring.get("swap_suggestion_context")),
        ),
        "actions": [
            {
                "action": "log_this",
                "requires_explicit_user_intake_action": True,
                "canonical_commit_requested": False,
            },
            {"action": "show_backups", "requires_explicit_user_intake_action": False},
            {"action": "dismiss", "requires_explicit_user_intake_action": False},
        ],
        "non_serve_flags": {
            "served_to_mainline_user": False,
            "scheduler_enqueued": False,
            "canonical_mutation_requested": False,
        },
    }


def public_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "title": str(candidate.get("title") or ""),
        "source_type": str(candidate.get("source_type") or ""),
        "estimated_kcal_range": dict(_mapping(candidate.get("estimated_kcal_range"))),
        "quality_score": int(candidate.get("quality_score") or 0),
        "quality_tier": str(candidate.get("quality_tier") or ""),
        "proactive_intensity": str(candidate.get("proactive_intensity") or ""),
        "source_refs": [str(ref) for ref in candidate.get("source_refs") or []],
        "store_name": str(candidate.get("store_name") or ""),
        "location_area": str(candidate.get("location_area") or ""),
        "distance_m": _int_or_none(candidate.get("distance_m")),
    }


def contract_blockers(retrieval: Mapping[str, Any]) -> list[str]:
    trace = _mapping(retrieval.get("allowed_pool_trace"))
    blockers: list[str] = []
    if trace.get("artifact_type") != "recommendation_allowed_pool_trace":
        blockers.append("allowed_pool_trace_missing")
    if trace.get("raw_transcript_included") is True:
        blockers.append("allowed_pool_trace.raw_transcript_included")
    return blockers


def candidate_by_id(
    candidates: list[Mapping[str, Any]],
    candidate_id: str,
) -> dict[str, Any] | None:
    for candidate in candidates:
        if str(candidate.get("candidate_id") or "") == candidate_id:
            return dict(candidate)
    return None


def candidate_explanation(candidate: Mapping[str, Any]) -> str:
    title = str(candidate.get("title") or "this option")
    return f"{title} fits the current budget and remembered preference context."


def _premeal_packet(
    *,
    primary_candidate: Mapping[str, Any],
    context: Mapping[str, Any],
    remaining_kcal: int | None,
) -> dict[str, Any]:
    if context.get("mode") != "pre_meal_planning":
        return {}
    kcal = _mapping(primary_candidate.get("estimated_kcal_range"))
    min_kcal = _int(kcal.get("min"))
    max_kcal = _int(kcal.get("max"))
    return {
        "mode": "pre_meal_planning",
        "selected_place": {
            "candidate_id": str(primary_candidate.get("candidate_id") or ""),
            "store_name": str(primary_candidate.get("store_name") or ""),
            "location_area": str(primary_candidate.get("location_area") or ""),
            "distance_m": _int(primary_candidate.get("distance_m")),
        },
        "suggested_kcal_range": {"min": min_kcal, "max": max_kcal},
        "remaining_kcal_after_primary_range": _remaining_after(
            remaining_kcal,
            min_kcal,
            max_kcal,
        ),
        "location_fallback_reason": str(context.get("location_fallback_reason") or ""),
        "budget_allocation_advice": (
            f"Keep this meal around {min_kcal}-{max_kcal} kcal; "
            f"you should still have {remaining_kcal - max_kcal}-{remaining_kcal - min_kcal} kcal."
        )
        if remaining_kcal is not None
        else "",
        "canonical_commit_requested": False,
    }


def _swap_packet(*, context: Mapping[str, Any]) -> dict[str, Any]:
    if context.get("mode") != "swap_suggestion" or context.get("history_sufficient") is not True:
        return {}
    original_kcal = _int(context.get("original_kcal"))
    suggested_kcal = _int(context.get("suggested_kcal"))
    saving = max(original_kcal - suggested_kcal, 0)
    frequency = _int_or_none(context.get("weekly_frequency_estimate"))
    return {
        "mode": "swap_suggestion",
        "original_item_name": str(context.get("original_item_name") or ""),
        "original_kcal": original_kcal,
        "suggested_item_name": str(context.get("suggested_item_name") or ""),
        "suggested_kcal": suggested_kcal,
        "kcal_saving_per_instance": saving,
        "weekly_saving_estimate": saving * frequency if frequency else None,
        "suggestion_basis": str(context.get("suggestion_basis") or ""),
        "source_refs": [str(ref) for ref in context.get("source_refs") or []],
        "canonical_commit_requested": False,
        "durable_product_memory_written": False,
    }


def _remaining_kcal_from_retrieval(retrieval: Mapping[str, Any]) -> int | None:
    value = _mapping(retrieval.get("budget_posture")).get("remaining_kcal")
    return value if isinstance(value, int) else None


def _remaining_after(
    remaining_kcal: int | None,
    min_kcal: int,
    max_kcal: int,
) -> dict[str, int | None]:
    if remaining_kcal is None:
        return {"min": None, "max": None}
    return {"min": remaining_kcal - max_kcal, "max": remaining_kcal - min_kcal}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) else None


__all__ = [
    "candidate_by_id",
    "candidate_explanation",
    "contract_blockers",
    "empty_ranking",
    "public_candidate",
    "ranking",
    "ux_packet",
]
