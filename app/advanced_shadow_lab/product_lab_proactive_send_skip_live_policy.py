from __future__ import annotations

from typing import Any, Mapping


ARTIFACT_TYPE = "advanced_product_lab_proactive_send_skip_grokfast_live_diagnostic"
STAGE = "advanced_product_lab_proactive_send_skip_grokfast_diagnostic"
SYSTEM_PROMPT = (
    "Return JSON only for a proactive contextual send/skip diagnostic. Decide "
    "send_or_skip for each candidate from the structured trace. Do not request "
    "delivery, notification, scheduler, mutation, durable memory, or canonical "
    "product writes. Required top-level fields: claim_scope=diagnostic_only and "
    "provider_decisions. Each provider_decision needs candidate_id, send_or_skip, "
    "reason_summary, chat_first_copy, skip_reason, reason_codes, delivery_request, "
    "scheduler_request, notification_request, and mutation_request."
)


def provider_payload(pre_delivery_review: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "diagnostic_task": "proactive_contextual_send_skip",
        "candidate_reviews": [
            _candidate_payload(review)
            for review in pre_delivery_review.get("candidate_reviews") or []
            if isinstance(review, Mapping)
        ],
        "constraints": {
            "claim_scope": "diagnostic_only",
            "semantic_owner": "provider_llm",
            "deterministic_role": "validate_reject_or_omit_only",
            "delivery_or_notification_allowed": False,
            "scheduler_allowed": False,
            "mutation_or_commit_allowed": False,
            "durable_memory_write_allowed": False,
        },
    }


def model_output_summary(output: Mapping[str, Any]) -> dict[str, Any]:
    decisions = [
        mapping(item)
        for item in output.get("provider_decisions") or output.get("decisions") or []
        if isinstance(item, Mapping)
    ]
    return {
        "claim_scope": str(output.get("claim_scope") or ""),
        "decision_count": len(decisions),
        "candidate_ids": [str(item.get("candidate_id") or "") for item in decisions],
    }


def trace_summary(trace: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "stage": str(trace.get("stage") or ""),
        "provider": str(trace.get("provider") or ""),
        "usage_present": isinstance(trace.get("usage"), Mapping),
    }


def mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _candidate_payload(review: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": str(review.get("candidate_id") or ""),
        "trigger_type": str(review.get("trigger_type") or ""),
        "review_decision": dict(mapping(review.get("review_decision"))),
        "deterministic_gate_result": dict(mapping(review.get("deterministic_gate_result"))),
        "source_refs": [str(item) for item in review.get("source_refs") or []],
        "permission_posture": str(review.get("permission_posture") or ""),
    }


__all__ = [
    "ARTIFACT_TYPE",
    "STAGE",
    "SYSTEM_PROMPT",
    "mapping",
    "model_output_summary",
    "provider_payload",
    "trace_summary",
]
