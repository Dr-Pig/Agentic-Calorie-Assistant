from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_memory_records import segment_blockers


def build_product_lab_memory_review_queue(
    *,
    session_id: str,
    turn_id: str,
    extraction_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    blockers = segment_blockers(session_id=session_id, turn_id=turn_id)
    if extraction_artifact.get("status") == "blocked":
        blockers.append("extraction_artifact.blocked")

    review_items: list[dict[str, Any]] = []
    for candidate in extraction_artifact.get("memory_candidates") or []:
        candidate_map = candidate if isinstance(candidate, Mapping) else {}
        candidate_id = str(candidate_map.get("candidate_id") or "missing")
        candidate_blockers = review_candidate_blockers(
            candidate_map,
            candidate_id=candidate_id,
            session_id=session_id,
            turn_id=turn_id,
        )
        blockers.extend(candidate_blockers)
        if candidate_blockers:
            continue
        review_items.append(review_item(candidate_map, candidate_id=candidate_id))

    if blockers:
        review_items = []
    return {
        "artifact_type": "advanced_product_lab_memory_review_queue",
        "status": "blocked" if blockers else "pass",
        "session_id": session_id,
        "turn_id": turn_id,
        "queue_status": "blocked" if blockers else "pending_human_review",
        "review_item_count": len(review_items),
        "review_items": review_items,
        "blockers": blockers,
        "memory_write_allowed": False,
        "lab_memory_store_written": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "manager_context_packet_changed": False,
        "user_facing_behavior_changed": False,
        "mainline_activation_enabled": False,
    }


def review_candidate_blockers(
    candidate: Mapping[str, Any],
    *,
    candidate_id: str,
    session_id: str,
    turn_id: str,
) -> list[str]:
    scope = candidate.get("scope_keys")
    scope_map = scope if isinstance(scope, Mapping) else {}
    checks = [
        None if candidate_id != "missing" else "candidate_id.missing",
        None if str(candidate.get("summary") or "").strip() else "summary.missing",
        None if candidate.get("source_object_refs") else "source_object_refs.missing",
        None
        if str(scope_map.get("session_id") or "") == session_id
        else "scope_keys.session_mismatch",
        None
        if str(candidate.get("turn_id") or "") == turn_id
        else "turn_id.mismatch",
    ]
    return [
        f"candidate.{candidate_id}.{blocker}"
        for blocker in checks
        if blocker
    ]


def review_item(candidate: Mapping[str, Any], *, candidate_id: str) -> dict[str, Any]:
    review_action = str(candidate.get("review_action") or "promote_with_confirmation")
    return {
        "review_item_id": f"review-{candidate_id}",
        "candidate_id": candidate_id,
        "candidate_type": str(candidate.get("candidate_type") or ""),
        "memory_type": str(candidate.get("memory_type") or ""),
        "summary": str(candidate.get("summary") or ""),
        "source_object_refs": list(candidate.get("source_object_refs") or []),
        "scope_keys": dict(candidate.get("scope_keys") or {}),
        "intended_consumers": list(candidate.get("intended_consumers") or []),
        "valid_until_minute": candidate.get("valid_until_minute"),
        "payload": dict(candidate.get("payload") or {}),
        "queue_status": "pending_human_review",
        "allowed_review_actions": [review_action, "reject", "edit_summary"],
        "promotion_requires_confirmation": True,
    }


__all__ = ["build_product_lab_memory_review_queue"]
