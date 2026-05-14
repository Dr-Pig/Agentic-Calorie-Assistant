from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_proactive_delivery import (
    build_product_lab_proactive_delivery_packet,
)
from app.advanced_shadow_lab.product_lab_proactive_action_state import action_state_source_refs, rescue_omission_trace
from app.advanced_shadow_lab.product_lab_proactive_candidate import (
    product_lab_proactive_candidate,
    product_lab_proactive_candidate_blockers,
)
from app.advanced_shadow_lab.product_lab_proactive_gate import (
    review_product_lab_proactive_candidates,
)
from app.advanced_shadow_lab import product_lab_proactive_rescue_feedback as rf
from app.advanced_shadow_lab.product_lab_proactive_wake_sources import (
    build_product_lab_proactive_wake_sources,
)


def run_product_lab_proactive(
    *,
    turn: Mapping[str, Any],
    fixture_inputs: Mapping[str, Any],
    memory_context_pack: Mapping[str, Any],
    recommendation_artifact: Mapping[str, Any],
    rescue_artifact: Mapping[str, Any],
    weekly_insight_artifact: Mapping[str, Any] | None = None,
    action_state: Mapping[str, Any] | None = None,
    prior_control_journal: list[Mapping[str, Any]] | None = None,
    rescue_feedback_memory_projection: Mapping[str, Any] | None = None,
    contextual_send_skip_artifact: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    current_action_state = action_state or {}
    feedback_projection = rescue_feedback_memory_projection or {}
    rescue_omission = (
        rescue_omission_trace(current_action_state)
        or rf.rescue_feedback_omission_trace(feedback_projection)
    )
    wake_source_adapter = build_product_lab_proactive_wake_sources(
        fixture_inputs=fixture_inputs,
        memory_context_pack=memory_context_pack,
        recommendation_artifact=recommendation_artifact,
        rescue_artifact=rescue_artifact,
        weekly_insight_artifact=weekly_insight_artifact,
        action_state=current_action_state,
        rescue_omission_active=rescue_omission is not None,
    )
    prepared_candidates = [
        product_lab_proactive_candidate(
            trigger_type=str(spec.get("trigger_type") or ""),
            candidate_kind=str(spec.get("candidate_kind") or ""),
            source_output_refs=[str(item) for item in spec.get("source_output_refs") or []],
            source_status=str(spec.get("source_status") or ""),
            control_model=_mapping(spec.get("control_model")),
            next_signal_fallback=str(spec.get("next_signal_fallback") or ""),
            wake_source_trace=_mapping(spec.get("wake_source_trace")),
        )
        for spec in wake_source_adapter.get("candidate_specs") or []
        if isinstance(spec, Mapping)
    ]
    bridge_blockers = [
        f"wake_source_adapter.{blocker}"
        for blocker in wake_source_adapter.get("blockers") or []
        if wake_source_adapter.get("status") == "blocked"
    ]
    blockers = [
        *bridge_blockers,
        *[
            blocker
            for candidate in prepared_candidates
            for blocker in product_lab_proactive_candidate_blockers(candidate)
        ],
    ]
    review = review_product_lab_proactive_candidates(
        turn=turn,
        candidates=[] if blockers else prepared_candidates,
        memory_context_pack=memory_context_pack,
        prior_control_journal=prior_control_journal,
    )
    review_passed = [] if blockers else [
        candidate
        for candidate in prepared_candidates
        if str(candidate.get("trigger_type") or "") in review["allowed_trigger_types"]
    ]
    passed, send_skip_omissions, send_skip_blockers = _apply_contextual_send_skip(
        candidates=review_passed,
        contextual_send_skip_artifact=contextual_send_skip_artifact,
    )
    blockers.extend(send_skip_blockers)
    delivery = build_product_lab_proactive_delivery_packet(
        candidates=passed,
        blocked=bool(blockers),
        contextual_send_skip_artifact=contextual_send_skip_artifact,
    )
    return {
        "artifact_type": "advanced_product_lab_proactive_runtime_artifact",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "session_id": str(turn.get("session_id") or ""),
        "turn_id": str(turn.get("turn_id") or ""),
        "chat_first": True,
        "candidate_count": len(passed),
        "candidates": passed,
        "wake_source_adapter": wake_source_adapter,
        "recommendation_proactive_candidate_bridge": dict(
            wake_source_adapter.get("recommendation_proactive_candidate_bridge") or {}
        ),
        "delivery_packet": delivery,
        "pre_delivery_review": review,
        "pre_delivery_review_summary": dict(review.get("summary") or {}),
        "memory_context_refs": [
            str(item) for item in memory_context_pack.get("selected_record_ids") or []
        ],
        "action_state_refs": action_state_source_refs(current_action_state),
        "omission_traces": [
            *([] if rescue_omission is None else [rescue_omission]),
            *list(review.get("omission_traces") or []),
            *send_skip_omissions,
        ],
        "source_outputs_read": [
            str(recommendation_artifact.get("artifact_type") or ""),
            str(rescue_artifact.get("artifact_type") or ""),
            str((weekly_insight_artifact or {}).get("artifact_type") or ""),
            str(current_action_state.get("artifact_type") or ""),
            str(feedback_projection.get("artifact_type") or ""),
            str(wake_source_adapter.get("artifact_type") or ""),
            str((contextual_send_skip_artifact or {}).get("artifact_type") or ""),
        ],
        "lab_chat_delivery_allowed": not bool(blockers),
        "scheduler_delivery_allowed": False,
        "notification_delivery_allowed": False,
        "push_or_line_delivery_connected": False,
        "served_to_mainline_user": False,
        "mainline_activation_enabled": False,
        "self_use_v1_affected": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "blockers": blockers,
    }


def _apply_contextual_send_skip(
    *,
    candidates: list[Mapping[str, Any]],
    contextual_send_skip_artifact: Mapping[str, Any] | None,
) -> tuple[list[Mapping[str, Any]], list[dict[str, Any]], list[str]]:
    if not contextual_send_skip_artifact:
        return candidates, [], []
    if contextual_send_skip_artifact.get("status") != "pass":
        return [], [], ["contextual_send_skip.status_not_pass"]
    send_ids = {str(item) for item in contextual_send_skip_artifact.get("send_candidate_ids") or []}
    return (
        [candidate for candidate in candidates if str(candidate.get("candidate_id") or "") in send_ids],
        [dict(item) for item in contextual_send_skip_artifact.get("omission_traces") or []],
        [],
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["run_product_lab_proactive"]
