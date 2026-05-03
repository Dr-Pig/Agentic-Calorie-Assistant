from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.composition.dogfood_trace_policy import (
    build_dogfood_review_record,
    validate_canonical_eval_promotion,
)

REVIEW_QUEUE_TAXONOMY = [
    "unsupported_intent",
    "user_correction",
    "food_kb_gap",
    "manager_context_gap",
    "target_ambiguity",
    "evidence_gap",
    "final_mapping_gap",
    "read_model_mismatch",
    "frontend_display_bug",
]


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _request_text(trace: dict[str, Any]) -> str:
    message = _object_dict(trace.get("user_message"))
    return str(message.get("raw_text") or "")


def _trace_id(trace: dict[str, Any]) -> str:
    return str(trace.get("request_id") or trace.get("trace_id") or "unknown-trace")


def _auto_flags_from_runtime_trace(trace: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    manager_decision = _object_dict(trace.get("manager_decision"))
    dogfood_policy = _object_dict(trace.get("dogfood_trace_policy"))
    unsupported_policy = _object_dict(dogfood_policy.get("unsupported_intent_policy"))
    trace_chain = _object_dict(trace.get("trace_chain"))
    final_mapping = _object_dict(trace.get("final_mapping"))

    if manager_decision.get("unsupported_intent_family") or unsupported_policy.get(
        "unsupported_intent_family"
    ):
        flags.append("unsupported_intent")
    if str(manager_decision.get("target_resolution_posture") or "") == "ambiguous":
        flags.append("target_attachment_ambiguous")
    if trace_chain.get("evidence_required") is True and trace_chain.get(
        "evidence_requirement_satisfied"
    ) is False:
        flags.append("no_accepted_food_packet")
    if final_mapping.get("same_truth_status") == "failed" or trace.get("same_truth_failed") is True:
        flags.append("same_truth_failed")
    if trace.get("read_model_mismatch") is True:
        flags.append("read_model_mismatch")
    return flags


def _raw_trace_review_payload(trace: dict[str, Any]) -> dict[str, Any]:
    return _json_safe(
        {
            "request_id": _trace_id(trace),
            "raw_user_input": _request_text(trace),
            "manager_decision": trace.get("manager_decision"),
            "dogfood_trace_policy": trace.get("dogfood_trace_policy"),
            "trace_chain": trace.get("trace_chain"),
            "final_mapping": trace.get("final_mapping"),
        }
    )


def build_review_candidate_from_runtime_trace(
    trace: dict[str, Any],
    *,
    reviewer_agent_suggestion: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = build_dogfood_review_record(
        trace_id=_trace_id(trace),
        raw_trace=_raw_trace_review_payload(trace),
        auto_flags=_auto_flags_from_runtime_trace(trace),
        reviewer_agent_suggestion=reviewer_agent_suggestion,
    )
    return {
        **record,
        "taxonomy": REVIEW_QUEUE_TAXONOMY,
        "canonical_eval_promotion": validate_canonical_eval_promotion(record),
        "truth_owner": {
            "raw_trace": "system_auto_logger",
            "review_candidate": "deterministic_rules_or_optional_reviewer_agent",
            "human_labeled": "human_reviewer",
            "canonical_eval_case": "human_reviewer",
        },
    }


def build_dogfood_review_queue_artifact(
    *,
    review_candidates: list[dict[str, Any]],
    correction_feedback_events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    correction_events = [_json_safe(event) for event in correction_feedback_events or []]
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_dogfood_review_queue",
        "status": "generated",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "claim_scope": "local_dogfood_review_queue_artifact",
        "local_only": True,
        "contains_personal_diet_logs": True,
        "do_not_commit": True,
        "taxonomy": REVIEW_QUEUE_TAXONOMY,
        "promotion_policy": {
            "raw_trace_can_be_canonical_eval_truth": False,
            "reviewer_agent_can_approve_canonical_eval": False,
            "human_approval_required_for_canonical_eval": True,
            "food_kb_truth_update_from_correction_allowed": False,
        },
        "review_candidate_count": len(review_candidates),
        "correction_feedback_event_count": len(correction_events),
        "review_candidates": [_json_safe(candidate) for candidate in review_candidates],
        "correction_feedback_events": correction_events,
    }


__all__ = [
    "REVIEW_QUEUE_TAXONOMY",
    "build_dogfood_review_queue_artifact",
    "build_review_candidate_from_runtime_trace",
]
