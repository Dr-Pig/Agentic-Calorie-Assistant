from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAG_NAMES as LAB_FALSE_FLAG_NAMES
from app.advanced_shadow_lab.journey_chat_packet_projection import build_journey_chat_packets
from app.advanced_shadow_lab.journey_chat_packet_summary import journey_chat_packet_blockers
from app.advanced_shadow_lab.chat_ux_copy_alignment import (
    build_copy_diagnostic_metadata,
    copy_alignment_summary,
    copy_diagnostic_blockers,
    copy_for_workflow,
    copy_status,
    lab_only_copy_preview,
    public_copy_metadata,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.chat_ux_packet"
)
ARTIFACT_TYPE = "advanced_shadow_chat_ux_packet_artifact"
SOURCE_TYPE = "advanced_shadow_e2e_fixture_chain_artifact"
SINK_TYPE = "proactive_no_send_review_sink_artifact"
FALSE_FLAG_NAMES = LAB_FALSE_FLAG_NAMES
FALSE_FLAGS = dict.fromkeys(FALSE_FLAG_NAMES, False)
NON_CLAIMS = [
    "not_runtime_activation_evidence",
    "not_product_readiness_evidence",
    "not_user_facing_activation",
    "not_scheduler_delivery",
    "not_notification_delivery",
    "not_canonical_mutation_authority",
    "not_durable_control_state",
    "not_chat_delivery",
]


def build_advanced_shadow_chat_ux_packet(
    *,
    fixture_chain_artifact: Mapping[str, Any],
    copy_diagnostic_artifacts: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    sink = _mapping(fixture_chain_artifact.get("terminal_review_sink"))
    records = _records(sink)
    copy_metadata = build_copy_diagnostic_metadata(list(copy_diagnostic_artifacts or []))
    journey_packets, journey_summary = build_journey_chat_packets(
        fixture_chain_artifact.get("journey_terminal_evidence")
    )
    blockers = [
        *_source_blockers(fixture_chain_artifact, sink),
        *copy_diagnostic_blockers(copy_metadata),
        *_packet_blockers(records),
        *journey_chat_packet_blockers(journey_summary),
    ]
    chat_packets = [] if blockers else [
        _packet(record, index, copy_metadata) for index, record in enumerate(records)
    ]
    return {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "owner": "app/advanced_shadow_lab/chat_ux_packet.py",
        "consumer": "future_advanced_shadow_lab_live_bundle_or_manual_review",
        "retirement_trigger": "approved_advanced_runtime_activation_plan",
        "packet_mode": "lab_only_non_served_projection",
        "source_artifact_type": str(fixture_chain_artifact.get("artifact_type") or ""),
        "source_status": str(fixture_chain_artifact.get("status") or ""),
        "terminal_sink_status": str(sink.get("status") or ""),
        "control_path_summary": _control_path_summary(sink),
        "copy_alignment_summary": copy_alignment_summary(copy_metadata),
        "copy_diagnostic_metadata": copy_metadata,
        "packet_count": len(chat_packets),
        "chat_packets": chat_packets,
        "journey_chat_packet_summary": journey_summary,
        "journey_chat_packets": journey_packets,
        "blockers": blockers,
        "runtime_connected": False,
        "served_to_user": False,
        "scheduler_enqueued": False,
        "non_claims": list(NON_CLAIMS),
        **dict(FALSE_FLAGS),
    }


def _source_blockers(source: Mapping[str, Any], sink: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if source.get("artifact_type") != SOURCE_TYPE:
        blockers.append(
            f"fixture_chain.unsupported_artifact_type:{source.get('artifact_type') or 'missing'}"
        )
    if source.get("status") != "pass":
        blockers.append(f"fixture_chain.status_{source.get('status') or 'missing'}")
    if sink.get("artifact_type") != SINK_TYPE:
        blockers.append(
            f"terminal_review_sink.unsupported_artifact_type:{sink.get('artifact_type') or 'missing'}"
        )
    if sink.get("status") != "pass":
        blockers.append(f"terminal_review_sink.status_{sink.get('status') or 'missing'}")
    blockers.extend(_claim_blockers("fixture_chain", source))
    blockers.extend(_claim_blockers("terminal_review_sink", sink))
    return blockers


def _claim_blockers(prefix: str, artifact: Mapping[str, Any]) -> list[str]:
    return [f"{prefix}.{flag}" for flag in FALSE_FLAG_NAMES if artifact.get(flag) is True]


def _packet_blockers(records: list[Mapping[str, Any]]) -> list[str]:
    if not records:
        return ["terminal_review_sink.records_missing"]
    blockers: list[str] = []
    for index, record in enumerate(records):
        prefix = f"chat_packet[{index}]"
        if not str(record.get("trigger_type") or "").strip():
            blockers.append(f"{prefix}.trigger_type_missing")
        if record.get("dismiss_reason_choices_present") is not True:
            blockers.append(f"{prefix}.dismiss_reason_choices_missing")
        if record.get("snooze_window_present") is not True:
            blockers.append(f"{prefix}.snooze_window_missing")
        if not str(record.get("undo_scope") or "").strip():
            blockers.append(f"{prefix}.undo_scope_missing")
        if not str(record.get("next_signal_required") or "").strip():
            blockers.append(f"{prefix}.next_signal_missing")
    return blockers


def _packet(
    record: Mapping[str, Any],
    index: int,
    copy_metadata: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    trigger = str(record.get("trigger_type") or "")
    copy = copy_for_workflow(_workflow_family(trigger), copy_metadata)
    return {
        "packet_id": f"{trigger}:{index}",
        "surface": "chat",
        "chat_first": True,
        "packet_kind": "no_send_nudge_candidate",
        "workflow_family": _workflow_family(trigger),
        "trigger_type": trigger,
        "candidate_kind": str(record.get("candidate_kind") or ""),
        "source_domains": _source_domains(trigger),
        "source_artifact_refs": [SOURCE_TYPE, SINK_TYPE],
        "copy_status": copy_status(copy),
        "copy_source_metadata": public_copy_metadata(copy),
        "lab_only_copy_preview": lab_only_copy_preview(copy),
        "controls": {
            "dismiss_reason_required": record.get("dismiss_reason_choices_present") is True,
            "snooze_window_present": record.get("snooze_window_present") is True,
            "undo_scope": str(record.get("undo_scope") or ""),
        },
        "next_signal_required": str(record.get("next_signal_required") or ""),
        "served_to_user": False,
        "delivery_attempted": False,
        "scheduler_enqueued": False,
        "canonical_mutation_requested": False,
    }


def _workflow_family(trigger_type: str) -> str:
    return {
        "recommendation_prompt": "recommendation",
        "recommendation_nudge_meal_time": "recommendation",
        "recommendation_nudge_nearby": "recommendation",
        "swap_suggestion": "recommendation",
        "rescue_nudge": "rescue",
    }.get(trigger_type, "general_chat")


def _source_domains(trigger_type: str) -> list[str]:
    if _workflow_family(trigger_type) == "recommendation":
        return ["memory", "recommendation", "proactive"]
    if _workflow_family(trigger_type) == "rescue":
        return ["memory", "rescue", "proactive"]
    return ["proactive"]


def _control_path_summary(sink: Mapping[str, Any]) -> dict[str, Any]:
    control = _mapping(sink.get("control_path_evidence"))
    return {
        "status": str(control.get("status") or ""),
        "configured_paths": dict(_mapping(control.get("configured_paths"))),
        "interaction_actions_observed": [
            str(item) for item in control.get("interaction_actions_observed") or []
        ],
        "next_signal_required_present": control.get("next_signal_required_present") is True,
    }


def _records(sink: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [item for item in sink.get("records") or [] if isinstance(item, Mapping)]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "build_advanced_shadow_chat_ux_packet"]
