from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_memory import (
    apply_product_lab_memory_review_decisions,
    build_product_lab_memory_review_queue,
    extract_product_lab_memory_candidates,
)
from app.advanced_shadow_lab.product_lab_memory_action_signals import (
    build_memory_signals_from_action_events,
)


def run_product_lab_turn_memory_pipeline(
    *,
    store: Any,
    session_id: str,
    turn_id: str,
    turn_spec: Mapping[str, Any],
    turn_artifact: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    action_signals = build_memory_signals_from_action_events(
        session_id=session_id,
        turn_id=turn_id,
        turn_artifact=turn_artifact,
        action_events=mappings(turn_spec.get("post_turn_memory_action_events")),
    )
    signal_events = [
        *mappings(turn_spec.get("post_turn_memory_signal_events")),
        *mappings(action_signals.get("memory_signal_events")),
    ]
    if action_signals.get("status") == "blocked":
        return pipeline_artifact(
            pipeline_path="blocked_memory_action_signal",
            memory_write=empty_memory_write(),
            action_signal_artifact=action_signals,
        )
    if signal_events:
        return candidate_review_pipeline(
            store=store,
            session_id=session_id,
            turn_id=turn_id,
            signal_events=signal_events,
            review_decisions=mappings(
                turn_spec.get("post_turn_memory_review_decisions")
            ),
            action_signal_artifact=action_signals,
        )
    memory_write = store.write_memory_events(
        session_id=session_id,
        turn_id=turn_id,
        events=mappings(turn_spec.get("post_turn_memory_events")),
    )
    return pipeline_artifact(
        pipeline_path="direct_memory_event_write",
        memory_write=memory_write,
        action_signal_artifact=action_signals,
    )


def candidate_review_pipeline(
    *,
    store: Any,
    session_id: str,
    turn_id: str,
    signal_events: list[Mapping[str, Any]],
    review_decisions: list[Mapping[str, Any]],
    action_signal_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    extraction = extract_product_lab_memory_candidates(
        session_id=session_id,
        turn_id=turn_id,
        memory_signal_events=signal_events,
    )
    review_queue = build_product_lab_memory_review_queue(
        session_id=session_id,
        turn_id=turn_id,
        extraction_artifact=extraction,
    )
    promotion = apply_product_lab_memory_review_decisions(
        store=store,
        session_id=session_id,
        turn_id=turn_id,
        review_queue=review_queue,
        review_decisions=review_decisions,
    )
    return pipeline_artifact(
        pipeline_path="candidate_review_promotion",
        memory_write=dict(promotion.get("memory_write_artifact") or {}),
        extraction=extraction,
        review_queue=review_queue,
        promotion=promotion,
        action_signal_artifact=action_signal_artifact,
    )


def pipeline_artifact(
    *,
    pipeline_path: str,
    memory_write: Mapping[str, Any],
    extraction: Mapping[str, Any] | None = None,
    review_queue: Mapping[str, Any] | None = None,
    promotion: Mapping[str, Any] | None = None,
    action_signal_artifact: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    blockers = [
        str(blocker)
        for artifact in (
            memory_write,
            extraction,
            review_queue,
            promotion,
            action_signal_artifact,
        )
        for blocker in (artifact or {}).get("blockers") or []
    ]
    return {
        "artifact_type": "advanced_product_lab_turn_memory_pipeline",
        "status": "blocked" if blockers else "pass",
        "pipeline_path": pipeline_path,
        "memory_write_artifact": dict(memory_write),
        "action_signal_artifact": dict(
            action_signal_artifact or empty_action_signal_artifact()
        ),
        "extraction_artifact": dict(extraction or {}),
        "review_queue": dict(review_queue or {}),
        "promotion_artifact": dict(promotion or {}),
        "written_record_ids": list(memory_write.get("written_record_ids") or []),
        "lab_memory_store_written": memory_write.get("lab_memory_store_written") is True,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "manager_context_packet_changed": False,
        "blockers": blockers,
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


def empty_action_signal_artifact() -> dict[str, Any]:
    return {
        "artifact_type": "advanced_product_lab_memory_action_signal_artifact",
        "status": "pass",
        "action_event_count": 0,
        "derived_signal_count": 0,
        "memory_signal_events": [],
        "raw_user_text_semantic_inference_performed": False,
        "semantic_inference_used": False,
        "no_raw_keyword_semantic_oracle": True,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "manager_context_packet_changed": False,
        "blockers": [],
    }


def mappings(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in value or [] if isinstance(item, Mapping)]


__all__ = ["run_product_lab_turn_memory_pipeline"]
