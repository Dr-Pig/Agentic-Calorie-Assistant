from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAG_NAMES
from app.advanced_shadow_lab.journey_terminal_contract import expected_terminal_output
from app.advanced_shadow_lab.ux_acceptance_coverage import REQUIRED_UX_JOURNEY_IDS
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.journey_chat_packet_summary"
)


def compare_journey_chat_packets(
    *,
    fixture_chain: Mapping[str, Any],
    fixture_status: str,
    journey_evidence_summary: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    summary = summarize_journey_chat_packets(
        journey_chat_packets=_mapping(fixture_chain.get("chat_ux_packet")).get(
            "journey_chat_packets"
        ),
        journey_terminal_evidence=fixture_chain.get("journey_terminal_evidence"),
    )
    blockers = journey_chat_packet_blockers_if_comparable(
        fixture_status=fixture_status,
        journey_evidence_status=str(journey_evidence_summary.get("status") or "blocked"),
        summary=summary,
    )
    return summary, journey_chat_packet_row(summary), blockers


def summarize_journey_chat_packets(
    *,
    journey_chat_packets: Any,
    journey_terminal_evidence: Any,
) -> dict[str, Any]:
    packets = _packets(journey_chat_packets)
    evidence_by_id = _by_id(_rows(journey_terminal_evidence))
    packet_by_id = _by_id(packets)
    missing = [jid for jid in REQUIRED_UX_JOURNEY_IDS if jid not in packet_by_id]
    kind_mismatch = _mismatches(packet_by_id, evidence_by_id, "output_kind")
    family_mismatch = _mismatches(packet_by_id, evidence_by_id, "workflow_family")
    control_mismatch = [
        jid for jid in REQUIRED_UX_JOURNEY_IDS if _control_mismatch(jid, packet_by_id, evidence_by_id)
    ]
    activation = _activation_violations(packets)
    semantic_inferred = [
        str(packet.get("journey_id") or "unknown_journey")
        for packet in packets
        if packet.get("semantic_decision_inferred_by_runner") is True
    ]
    blockers = missing or kind_mismatch or family_mismatch or control_mismatch or activation or semantic_inferred
    return {
        "status": "blocked" if blockers else "pass",
        "required_journey_ids": list(REQUIRED_UX_JOURNEY_IDS),
        "observed_journey_ids": [jid for jid in REQUIRED_UX_JOURNEY_IDS if jid in packet_by_id],
        "packet_count": len(packets),
        "missing_journey_ids": missing,
        "output_kind_by_journey": _field_by_journey(packet_by_id, "output_kind"),
        "workflow_family_by_journey": _field_by_journey(packet_by_id, "workflow_family"),
        "output_kind_mismatch_journey_ids": kind_mismatch,
        "workflow_family_mismatch_journey_ids": family_mismatch,
        "control_contract_mismatch_journey_ids": control_mismatch,
        "activation_violations": activation,
        "semantic_decision_inferred_journey_ids": semantic_inferred,
        "new_report_family_created": False,
    }


def journey_chat_packet_blockers(summary: Mapping[str, Any]) -> list[str]:
    fields = (
        ("missing_journey", "missing_journey_ids"),
        ("output_kind_mismatch", "output_kind_mismatch_journey_ids"),
        ("workflow_family_mismatch", "workflow_family_mismatch_journey_ids"),
        ("control_contract_mismatch", "control_contract_mismatch_journey_ids"),
        ("activation", "activation_violations"),
        ("semantic_inferred", "semantic_decision_inferred_journey_ids"),
    )
    return [
        f"journey_chat_packet_projection.{label}:{value}"
        for label, field in fields
        for value in summary.get(field) or []
    ]


def journey_chat_packet_blockers_if_comparable(
    *,
    fixture_status: str,
    journey_evidence_status: str,
    summary: Mapping[str, Any],
) -> list[str]:
    if fixture_status != "pass" or journey_evidence_status != "pass":
        return []
    return journey_chat_packet_blockers(summary)


def journey_chat_packet_row(summary: Mapping[str, Any]) -> dict[str, str]:
    status = str(summary.get("status") or "blocked")
    return {
        "surface": "journey_chat_ux_packet_projection",
        "fixture_status": status,
        "dogfood_status": "not_applicable",
        "live_status": "not_required",
        "finding": "all_required_journeys_have_lab_chat_packets"
        if status == "pass"
        else "journey_chat_packet_projection_blocked",
    }


def _mismatches(
    packet_by_id: Mapping[str, Mapping[str, Any]],
    evidence_by_id: Mapping[str, Mapping[str, Any]],
    field: str,
) -> list[str]:
    return [
        jid
        for jid in REQUIRED_UX_JOURNEY_IDS
        if _field_mismatch(jid, packet_by_id, evidence_by_id, field)
    ]


def _field_mismatch(jid: str, packets: Mapping[str, Mapping[str, Any]], evidence: Mapping[str, Mapping[str, Any]], field: str) -> bool:
    packet = _mapping(packets.get(jid))
    return bool(packet) and packet.get(field) != _expected_output(jid, evidence).get(field)


def _control_mismatch(jid: str, packets: Mapping[str, Mapping[str, Any]], evidence: Mapping[str, Mapping[str, Any]]) -> bool:
    packet = _mapping(packets.get(jid))
    return bool(packet) and packet.get("control_contract") != _expected_output(jid, evidence).get("control_contract")


def _expected_output(journey_id: str, evidence_by_id: Mapping[str, Mapping[str, Any]]) -> Mapping[str, Any]:
    evidence_output = _mapping(_mapping(evidence_by_id.get(journey_id)).get("ux_terminal_output"))
    return evidence_output or expected_terminal_output(journey_id)


def _field_by_journey(packet_by_id: Mapping[str, Mapping[str, Any]], field: str) -> dict[str, str]:
    return {
        jid: str(_mapping(packet_by_id.get(jid)).get(field) or "")
        for jid in REQUIRED_UX_JOURNEY_IDS
        if jid in packet_by_id
    }


def _activation_violations(packets: list[Mapping[str, Any]]) -> list[str]:
    return [
        f"{packet.get('journey_id') or 'unknown_journey'}.{flag}"
        for packet in packets
        for flag in FALSE_FLAG_NAMES
        if packet.get(flag) is True
    ]


def _by_id(items: list[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {str(item.get("journey_id") or ""): item for item in items}


def _rows(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in value or [] if isinstance(item, Mapping)]


def _packets(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in value or [] if isinstance(item, Mapping)]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "compare_journey_chat_packets",
    "journey_chat_packet_blockers",
    "journey_chat_packet_blockers_if_comparable",
    "journey_chat_packet_row",
    "summarize_journey_chat_packets",
]
