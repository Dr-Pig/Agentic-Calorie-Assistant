from __future__ import annotations

from typing import Any, Mapping


def explanation_card(
    *,
    primary_candidate: Mapping[str, Any],
    explanation: str,
    backup_count: int,
) -> dict[str, Any]:
    return {
        "primary_candidate_id": str(primary_candidate.get("candidate_id") or ""),
        "why_this": explanation,
        "backup_count": backup_count,
        "source_refs": [str(ref) for ref in primary_candidate.get("source_refs") or []],
    }


def backup_options(backups: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {**dict(candidate), "presentation_role": "backup"}
        for candidate in backups
    ]


def recommendation_control_model() -> dict[str, Any]:
    return {
        "dismiss_reason_choices": [
            "not_relevant_now",
            "already_handled",
            "too_frequent",
        ],
        "snooze_window": {"kind": "duration", "minutes": 180},
        "undo_scope": "current_recommendation_offer_only",
        "next_signal_required": "new_app_open_with_qualified_pool",
    }


__all__ = [
    "backup_options",
    "explanation_card",
    "recommendation_control_model",
]
