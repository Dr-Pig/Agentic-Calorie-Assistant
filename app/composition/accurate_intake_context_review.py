from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any


FORBIDDEN_CONTEXT_IDS = (
    "debug_artifacts",
    "dogfood_review_artifacts",
    "raw_trace_dump",
    "food_gap_candidates",
    "food_gap_candidates_as_truth",
    "full_day_transcript_by_default",
    "long_term_memory",
    "proactive_context",
    "rescue_context",
    "recommendation_context",
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list_value(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _request_id(trace: dict[str, Any], index: int) -> str:
    return str(trace.get("request_id") or trace.get("trace_id") or f"trace-{index + 1}")


def _forbidden_context_ids(trace: dict[str, Any], packet: dict[str, Any]) -> list[str]:
    detected: list[str] = []
    for context_id in FORBIDDEN_CONTEXT_IDS:
        if trace.get(context_id) is not None or packet.get(context_id) is not None:
            detected.append(context_id)
    return detected


def _context_status(
    *,
    policy_version: Any,
    loaded_summary: dict[str, Any],
    omitted_summary: dict[str, Any],
    packet: dict[str, Any],
) -> str:
    if policy_version or loaded_summary or omitted_summary or packet:
        return "present"
    return "not_available"


def _trace_review(trace: dict[str, Any], index: int) -> dict[str, Any]:
    packet = _object_dict(trace.get("manager_context_packet_v1"))
    hard_pins = _object_dict(packet.get("hard_pins"))
    target_candidates = _object_dict(packet.get("target_candidates"))
    correction_targets = _list_value(target_candidates.get("for_correction_or_removal"))
    loaded_summary = _object_dict(trace.get("loaded_context_summary"))
    omitted_summary = _object_dict(trace.get("omitted_context_summary"))
    policy_version = trace.get("context_policy_version")
    forbidden = _forbidden_context_ids(trace, packet)
    pending_followup_present = bool(_object_dict(hard_pins.get("pending_followup")))
    pending_draft_present = bool(_object_dict(hard_pins.get("pending_draft")))

    if not pending_followup_present and "pending_followup_present" in loaded_summary:
        pending_followup_present = loaded_summary.get("pending_followup_present") is True
    if not pending_draft_present and "pending_draft_present" in loaded_summary:
        pending_draft_present = loaded_summary.get("pending_draft_present") is True

    target_candidate_count = len(correction_targets)
    if target_candidate_count == 0:
        try:
            target_candidate_count = int(loaded_summary.get("target_candidate_count") or 0)
        except (TypeError, ValueError):
            target_candidate_count = 0

    return {
        "trace_id": _request_id(trace, index),
        "status": _context_status(
            policy_version=policy_version,
            loaded_summary=loaded_summary,
            omitted_summary=omitted_summary,
            packet=packet,
        ),
        "context_policy_version": str(policy_version or "not_available"),
        "loaded_context_summary_present": bool(loaded_summary),
        "omitted_context_summary_present": bool(omitted_summary),
        "loaded_context_summary": _json_safe(loaded_summary),
        "omitted_context_summary": _json_safe(omitted_summary),
        "pending_followup_present": pending_followup_present,
        "pending_draft_present": pending_draft_present,
        "target_candidate_count": target_candidate_count,
        "forbidden_context_detected": bool(forbidden),
        "forbidden_context_ids": forbidden,
        "context_engineering_fault_claimed": False,
        "manager_context_packet_schema_changed": False,
    }


def build_context_review_artifact(*, traces: list[dict[str, Any]]) -> dict[str, Any]:
    trace_reviews = [
        _trace_review(dict(trace), index)
        for index, trace in enumerate(list(traces or []))
        if isinstance(trace, dict)
    ]
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_review_artifact",
            "status": "generated",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "claim_scope": "local_context_review_diagnostic",
            "local_only": True,
            "diagnostic_only": True,
            "contains_personal_diet_logs": True,
            "do_not_commit": True,
            "context_engineering_fault_claimed": False,
            "manager_context_packet_schema_changed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "web_readiness_claimed": False,
            "summary": {
                "trace_count": len(trace_reviews),
                "present_context_trace_count": sum(
                    1 for review in trace_reviews if review["status"] == "present"
                ),
                "missing_context_trace_count": sum(
                    1 for review in trace_reviews if review["status"] != "present"
                ),
                "forbidden_context_trace_count": sum(
                    1 for review in trace_reviews if review["forbidden_context_detected"]
                ),
            },
            "trace_reviews": trace_reviews,
        }
    )


__all__ = ["FORBIDDEN_CONTEXT_IDS", "build_context_review_artifact"]
