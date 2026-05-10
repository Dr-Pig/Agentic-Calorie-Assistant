from __future__ import annotations

from typing import Any, Mapping


def build_recommendation_ux_packet(
    *,
    primary_candidate: Mapping[str, Any],
    backup_candidates: list[Mapping[str, Any]],
    explanation: str,
) -> dict[str, Any]:
    backup_ids = [str(candidate.get("candidate_id") or "") for candidate in backup_candidates]
    primary_id = str(primary_candidate.get("candidate_id") or "")
    return {
        "surface": "chat",
        "chat_first": True,
        "serve_allowed_in_lab": True,
        "served_to_mainline_user": False,
        "primary_candidate_id": primary_id,
        "backup_candidate_ids": backup_ids,
        "primary_candidate": dict(primary_candidate),
        "backup_candidates": [dict(candidate) for candidate in backup_candidates],
        "explanation": explanation,
        "actions": [
            {
                "action": "log_this",
                "requires_explicit_user_intake_action": True,
                "canonical_commit_requested": False,
            },
            {
                "action": "show_backups",
                "requires_explicit_user_intake_action": False,
            },
            {
                "action": "dismiss",
                "requires_explicit_user_intake_action": False,
            },
        ],
        "non_serve_flags": {
            "served_to_mainline_user": False,
            "scheduler_enqueued": False,
            "canonical_mutation_requested": False,
        },
    }


__all__ = ["build_recommendation_ux_packet"]
