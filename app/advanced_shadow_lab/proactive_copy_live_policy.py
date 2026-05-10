from __future__ import annotations

from typing import Any, Mapping


ARTIFACT_TYPE = "advanced_shadow_proactive_copy_live_diagnostic_artifact"
STAGE = "advanced_shadow_proactive_copy_live_diagnostic"
SUPPORTED_INPUT = "proactive_no_send_review_sink_artifact"
SYSTEM_PROMPT = (
    "Return JSON for proactive chat-copy diagnostics only. Do not claim the "
    "message was shown, sent, notified, scheduled, saved, committed, or applied. "
    "draft_chat_message is a hypothetical non-served chat draft for review only, "
    "not a delivered message. It must be non-empty and must not say it was sent, "
    "shown, notified, scheduled, saved, committed, or applied. Required fields: "
    "draft_chat_message, reason_summary, "
    "false_positive_silence_case, next_signal, claim_scope, action_request, "
    "delivery_request, mutation_request, scheduler_request, notification_request, "
    "reason_codes."
)
FALSE_FLAG_NAMES = (
    "mainline_runtime_connected", "mainline_route_or_api_mount_allowed",
    "production_scheduler_delivery_allowed", "production_db_migration_allowed",
    "canonical_product_mutation_allowed", "delivery_attempted", "proactive_sent",
    "scheduler_enabled", "scheduler_enqueued", "live_delivery_allowed",
    "push_or_line_delivery_connected", "manager_context_packet_changed",
    "manager_context_injected", "recommendation_served", "rescue_committed",
    "proposal_committed", "durable_product_memory_written", "durable_memory_written",
    "durable_snooze_written", "mutation_changed", "user_facing_behavior_changed",
    "product_readiness_claimed",
)
FALSE_FLAGS = dict.fromkeys(FALSE_FLAG_NAMES, False)
CLAIM_FLAGS = (
    *FALSE_FLAG_NAMES, "runtime_effect_allowed", "canonical_mutation_changed",
    "day_budget_mutated", "body_plan_mutated", "meal_thread_mutated",
    "user_facing_visible",
)
NON_CLAIMS = [
    "not_runtime_activation_evidence", "not_product_readiness_evidence",
    "not_user_facing_activation", "not_scheduler_delivery",
    "not_notification_delivery", "not_canonical_mutation_authority",
    "not_durable_control_state", "not_proactive_send",
]
OUTPUT_TEXT_FIELDS = (
    "draft_chat_message", "reason_summary", "false_positive_silence_case",
    "next_signal",
)
REQUEST_FIELDS = (
    ("action_request", "model_output.action_request_not_allowed"),
    ("delivery_request", "model_output.delivery_request_not_allowed"),
    ("mutation_request", "model_output.mutation_request_not_allowed"),
    ("scheduler_request", "model_output.scheduler_request_not_allowed"),
    ("notification_request", "model_output.notification_request_not_allowed"),
)
DELIVERY_TOKENS = ("sent", "delivered", "notify", "notification", "push", "line message")
SCHEDULER_TOKENS = ("scheduled", "queued", "reminder fired")
MUTATION_TOKENS = ("committed", "saved it", "applied", "updated your budget")


def input_blockers(sink: Mapping[str, Any], records: list[Mapping[str, Any]]) -> list[str]:
    blockers: list[str] = []
    if sink.get("artifact_type") != SUPPORTED_INPUT:
        blockers.append("no_send_review_sink.unsupported_artifact_type")
    if sink.get("status") != "pass":
        blockers.append("no_send_review_sink.status_not_pass")
    if not records:
        blockers.append("no_send_review_sink.records_missing")
    for flag in dict.fromkeys(CLAIM_FLAGS):
        if sink.get(flag) is True:
            blockers.append(f"no_send_review_sink.{flag}")
    blockers.extend(_control_blockers(mapping(sink.get("control_path_evidence"))))
    return blockers


def provider_payload(sink: Mapping[str, Any], records: list[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "target_surface": "proactive_chat_copy_posture",
        "autonomy_tier": "draft_only",
        "review_records": [_record_payload(record) for record in records[:3]],
        "control_path_evidence": control_summary(sink),
        "constraints": {
            "claim_scope_required": "diagnostic_copy_only",
            "chat_copy_only": True,
            "user_facing_output_allowed": False,
            "draft_chat_message_required": True,
            "draft_chat_message_is_non_served_diagnostic_copy": True,
            "draft_chat_message_must_not_claim_delivery": True,
            "delivery_or_notification_allowed": False,
            "scheduler_allowed": False,
            "mutation_or_commit_allowed": False,
            "must_include_false_positive_silence_case": True,
            "must_include_next_signal": True,
        },
    }


def output_guard(output: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if output.get("claim_scope") != "diagnostic_copy_only":
        blockers.append("model_output.claim_scope_not_diagnostic")
    for key, blocker in REQUEST_FIELDS:
        if output.get(key) is True:
            blockers.append(blocker)
    for field in OUTPUT_TEXT_FIELDS:
        if not str(output.get(field) or "").strip():
            blockers.append(f"model_output.{field}_missing")
    draft_text = str(output.get("draft_chat_message") or "").lower()
    all_text = " ".join(str(output.get(field) or "") for field in OUTPUT_TEXT_FIELDS).lower()
    if any(token in draft_text for token in DELIVERY_TOKENS):
        blockers.append("model_output.delivery_language_present")
    if any(token in all_text for token in SCHEDULER_TOKENS):
        blockers.append("model_output.scheduler_language_present")
    if any(token in all_text for token in MUTATION_TOKENS):
        blockers.append("model_output.mutation_language_present")
    return {"status": "blocked" if blockers else "pass", "blockers": blockers}


def model_output_summary(output: Mapping[str, Any]) -> dict[str, Any]:
    return {
        f"{field}_present": bool(str(output.get(field) or "").strip())
        for field in OUTPUT_TEXT_FIELDS
    } | {
        "claim_scope": str(output.get("claim_scope") or ""),
        "reason_codes": [str(item) for item in output.get("reason_codes") or []],
    }


def control_summary(sink: Mapping[str, Any]) -> dict[str, Any]:
    control = mapping(sink.get("control_path_evidence"))
    return {
        "status": str(control.get("status") or ""),
        "configured_paths": dict(mapping(control.get("configured_paths"))),
        "interaction_actions_observed": [
            str(item) for item in control.get("interaction_actions_observed") or []
        ],
        "next_signal_required_present": control.get("next_signal_required_present") is True,
    }


def records(sink: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [item for item in sink.get("records") or [] if isinstance(item, Mapping)]


def trace_summary(trace: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "stage": str(trace.get("stage") or ""),
        "provider": str(trace.get("provider") or ""),
        "usage_present": isinstance(trace.get("usage"), Mapping),
    }


def mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _control_blockers(control: Mapping[str, Any]) -> list[str]:
    configured = mapping(control.get("configured_paths"))
    blockers: list[str] = []
    if control.get("status") != "pass":
        blockers.append("control_path_evidence.status_not_pass")
    for path in ("dismiss", "snooze", "undo"):
        if configured.get(path) is not True:
            blockers.append(f"control_path_evidence.{path}_not_configured")
    if control.get("next_signal_required_present") is not True:
        blockers.append("control_path_evidence.next_signal_missing")
    return blockers


def _record_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "trigger_type": str(record.get("trigger_type") or ""),
        "candidate_kind": str(record.get("candidate_kind") or ""),
        "interaction_action": str(record.get("interaction_action") or ""),
        "next_signal_required": str(record.get("next_signal_required") or ""),
        "dismiss_reason_choices_present": record.get("dismiss_reason_choices_present") is True,
        "snooze_window_present": record.get("snooze_window_present") is True,
        "undo_scope_present": bool(str(record.get("undo_scope") or "").strip()),
    }
