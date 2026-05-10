from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_memory_records import segment_blockers


SUPPORTED_DECISIONS = {"promote", "reject", "hold"}


def apply_product_lab_memory_review_decisions(
    *,
    store: Any,
    session_id: str,
    turn_id: str,
    review_queue: Mapping[str, Any],
    review_decisions: list[Mapping[str, Any]],
) -> dict[str, Any]:
    blockers = segment_blockers(session_id=session_id, turn_id=turn_id)
    if review_queue.get("status") == "blocked":
        blockers.append("review_queue.blocked")
    items_by_id = review_items_by_candidate_id(review_queue)
    decisions = normalized_decisions(review_decisions, blockers=blockers)

    promoted_events: list[dict[str, Any]] = []
    rejected_ids: list[str] = []
    held_ids: list[str] = []
    for candidate_id, decision in decisions.items():
        review_item = items_by_id.get(candidate_id)
        if review_item is None:
            blockers.append(f"decision.{candidate_id}.candidate_not_in_queue")
            continue
        action = str(decision.get("decision") or "")
        if action not in SUPPORTED_DECISIONS:
            blockers.append(f"decision.{candidate_id}.unsupported_decision")
            continue
        if action == "promote":
            if decision.get("confirmed") is not True:
                blockers.append(f"decision.{candidate_id}.confirmation_required")
                continue
            promoted_events.append(memory_event_from_review_item(review_item))
        elif action == "reject":
            rejected_ids.append(candidate_id)
        elif action == "hold":
            held_ids.append(candidate_id)

    memory_write = empty_memory_write()
    if not blockers and promoted_events:
        memory_write = store.write_memory_events(
            session_id=session_id,
            turn_id=turn_id,
            events=promoted_events,
        )
        blockers.extend(str(item) for item in memory_write.get("blockers") or [])
    if blockers:
        promoted_ids: list[str] = []
        rejected_ids = []
        held_ids = []
    else:
        promoted_ids = [str(item) for item in memory_write.get("written_record_ids") or []]
    return promotion_artifact(
        session_id=session_id,
        turn_id=turn_id,
        blockers=blockers,
        promoted_ids=promoted_ids,
        rejected_ids=rejected_ids,
        held_ids=held_ids,
        memory_write=memory_write,
    )


def review_items_by_candidate_id(
    review_queue: Mapping[str, Any],
) -> dict[str, Mapping[str, Any]]:
    return {
        str(item.get("candidate_id") or ""): item
        for item in review_queue.get("review_items") or []
        if isinstance(item, Mapping)
    }


def normalized_decisions(
    review_decisions: list[Mapping[str, Any]],
    *,
    blockers: list[str],
) -> dict[str, Mapping[str, Any]]:
    decisions: dict[str, Mapping[str, Any]] = {}
    for decision in review_decisions:
        candidate_id = str(decision.get("candidate_id") or "")
        if not candidate_id:
            blockers.append("decision.candidate_id.missing")
            continue
        if candidate_id in decisions:
            blockers.append(f"decision.{candidate_id}.duplicate")
            continue
        decisions[candidate_id] = decision
    return decisions


def memory_event_from_review_item(review_item: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(review_item.get("payload") or {})
    valid_until = review_item.get("valid_until_minute")
    if valid_until is not None:
        payload["valid_until_minute"] = valid_until
    return {
        "memory_id": str(review_item.get("candidate_id") or ""),
        "memory_type": str(review_item.get("memory_type") or ""),
        "summary": str(review_item.get("summary") or ""),
        "review_status": "accepted_lab",
        "source_object_refs": list(review_item.get("source_object_refs") or []),
        "intended_consumers": list(review_item.get("intended_consumers") or []),
        **payload,
    }


def empty_memory_write() -> dict[str, Any]:
    return {
        "artifact_type": "advanced_product_lab_memory_write_artifact",
        "status": "pass",
        "written_record_ids": [],
        "all_record_ids": [],
        "surface_paths": {},
        "lab_memory_store_written": False,
        "isolated_lab_durable_memory_written": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "manager_context_packet_changed": False,
        "blockers": [],
    }


def promotion_artifact(
    *,
    session_id: str,
    turn_id: str,
    blockers: list[str],
    promoted_ids: list[str],
    rejected_ids: list[str],
    held_ids: list[str],
    memory_write: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_type": "advanced_product_lab_memory_promotion_artifact",
        "status": "blocked" if blockers else "pass",
        "session_id": session_id,
        "turn_id": turn_id,
        "promoted_record_ids": promoted_ids,
        "rejected_candidate_ids": rejected_ids,
        "held_candidate_ids": held_ids,
        "memory_write_artifact": dict(memory_write),
        "lab_memory_store_written": not blockers
        and memory_write.get("lab_memory_store_written") is True,
        "isolated_lab_durable_memory_written": not blockers and bool(promoted_ids),
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "manager_context_packet_changed": False,
        "user_facing_behavior_changed": False,
        "mainline_activation_enabled": False,
        "blockers": blockers,
    }


__all__ = ["apply_product_lab_memory_review_decisions"]
