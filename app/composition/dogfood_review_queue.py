from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

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

DESKTOP_FEEDBACK_CATEGORIES = [
    "manager_behavior",
    "nutrition_estimate",
    "macro_gap",
    "fooddb_gap",
    "ui_ux",
    "bug",
    "latency",
    "product_feedback",
]


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _clean_optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _required_text(value: Any, *, field: str) -> str:
    text = _clean_optional_text(value)
    if text is None:
        raise ValueError(f"{field}_required")
    return text


def _normalized_feedback_category(category: Any) -> str:
    value = _required_text(category, field="category")
    if value not in DESKTOP_FEEDBACK_CATEGORIES:
        raise ValueError("unsupported_feedback_category")
    return value


def build_feedback_record_from_desktop_capture(
    *,
    category: str,
    feedback_text: str,
    page: str,
    selected_date: str,
    user_external_id: str,
    trace_id: str | None = None,
    message_id: str | None = None,
    meal_id: str | None = None,
    severity: str = "medium",
    ui_event: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_dogfood_feedback_record",
            "status": "captured",
            "feedback_id": f"feedback-{uuid4()}",
            "captured_at_utc": datetime.now(UTC).isoformat(),
            "claim_scope": "local_dogfood_feedback_triage_record",
            "local_only": True,
            "contains_personal_diet_logs": True,
            "do_not_commit": True,
            "category": _normalized_feedback_category(category),
            "severity": _clean_optional_text(severity) or "medium",
            "feedback_text": _required_text(feedback_text, field="feedback_text"),
            "linked_context": {
                "page": _required_text(page, field="page"),
                "selected_date": _required_text(selected_date, field="selected_date"),
                "user_external_id": _required_text(user_external_id, field="user_external_id"),
                "trace_id": _clean_optional_text(trace_id),
                "message_id": _clean_optional_text(message_id),
                "meal_id": _clean_optional_text(meal_id),
            },
            "ui_event": _object_dict(ui_event),
            "feedback_owner": "human_operator",
            "frontend_semantic_owner": False,
            "mutation_authority": False,
            "manager_context_injection_allowed": False,
            "food_kb_truth_update_allowed": False,
            "canonical_eval_promotion_allowed": False,
            "product_truth_update_allowed": False,
        }
    )


def append_desktop_feedback_record(
    *,
    record: dict[str, Any],
    feedback_dir: Path,
) -> dict[str, Any]:
    feedback_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = feedback_dir / "accurate_intake_dogfood_feedback.jsonl"
    with jsonl_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(_json_safe(record), ensure_ascii=False) + "\n")
    return {**_json_safe(record), "feedback_store_path": str(jsonl_path)}


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


def _flags_from_product_loop_diagnostic(diagnostic: dict[str, Any]) -> list[str]:
    artifact_type = str(diagnostic.get("artifact_type") or "")
    status = str(diagnostic.get("status") or "")
    summary = _object_dict(diagnostic.get("summary"))
    flags: list[str] = []

    if artifact_type == "accurate_intake_context_target_candidate_eval":
        if int(summary.get("ambiguous_scenarios") or 0) > 0:
            flags.append("target_ambiguity")
    elif artifact_type == "accurate_intake_context_review_artifact":
        if int(summary.get("forbidden_context_trace_count") or 0) > 0:
            flags.append("manager_context_gap")
    elif artifact_type == "accurate_intake_context_window_diagnostic":
        if diagnostic.get("long_term_memory_used") is True:
            flags.append("manager_context_gap")
        if diagnostic.get("proactive_or_rescue_used") is True:
            flags.append("manager_context_gap")
    elif artifact_type == "accurate_intake_browser_realistic_web_dogfood_v2":
        if "evidence_gap" in status:
            flags.append("evidence_gap")

    return list(dict.fromkeys(flags or ["manager_context_gap"]))


def build_review_candidate_from_product_loop_diagnostic(
    diagnostic: dict[str, Any],
) -> dict[str, Any]:
    artifact_type = str(diagnostic.get("artifact_type") or "unknown_product_loop_diagnostic")
    record = build_dogfood_review_record(
        trace_id=artifact_type,
        raw_trace={
            "artifact_type": artifact_type,
            "status": diagnostic.get("status"),
            "summary": diagnostic.get("summary"),
            "raw_trace_is_truth": False,
        },
        auto_flags=_flags_from_product_loop_diagnostic(diagnostic),
        reviewer_agent_suggestion={
            "review_candidate": True,
            "likely_failure_family": "product_loop_context_diagnostic",
        },
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
    desktop_feedback_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    correction_events = [_json_safe(event) for event in correction_feedback_events or []]
    desktop_feedback = [_json_safe(record) for record in desktop_feedback_records or []]
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
            "feedback_can_create_product_truth": False,
            "feedback_can_create_fooddb_truth": False,
            "feedback_can_create_eval_truth": False,
        },
        "review_candidate_count": len(review_candidates),
        "correction_feedback_event_count": len(correction_events),
        "feedback_triage_record_count": len(desktop_feedback),
        "review_candidates": [_json_safe(candidate) for candidate in review_candidates],
        "correction_feedback_events": correction_events,
        "desktop_feedback_records": desktop_feedback,
    }


__all__ = [
    "REVIEW_QUEUE_TAXONOMY",
    "DESKTOP_FEEDBACK_CATEGORIES",
    "append_desktop_feedback_record",
    "build_dogfood_review_queue_artifact",
    "build_feedback_record_from_desktop_capture",
    "build_review_candidate_from_product_loop_diagnostic",
    "build_review_candidate_from_runtime_trace",
]
