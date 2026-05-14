from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract("advanced_shadow_lab.chat_first_journey_rows")
SCENARIO_IDS = [
    "memory_guided_recommendation_chat_offer",
    "rescue_proactive_no_send_chat_candidate",
    "dismiss_snooze_reopen_modify_shadow_controls",
]
GOLDEN_MEMORY_ID = "golden-order-morning-bar-oatmeal-latte"
GOLDEN_MEMORY_REF = f"memory_candidate:{GOLDEN_MEMORY_ID}"


def build_chat_first_journey_rows(
    *,
    context_pack: Mapping[str, Any],
    memory_projection: Mapping[str, Any],
    fixture_chain: Mapping[str, Any],
    terminal_sink: Mapping[str, Any],
    chat_packet: Mapping[str, Any],
) -> list[dict[str, Any]]:
    return [
        _memory_guided_recommendation(context_pack, memory_projection, fixture_chain, chat_packet),
        _rescue_proactive_no_send(terminal_sink, chat_packet),
        _dismiss_snooze_reopen_modify_controls(terminal_sink),
    ]


def scenario_row_blockers(rows: list[Mapping[str, Any]]) -> list[str]:
    return [
        f"{row.get('scenario_id')}.{blocker}"
        for row in rows
        for blocker in row.get("blockers") or []
    ]


def _memory_guided_recommendation(
    context_pack: Mapping[str, Any],
    memory_projection: Mapping[str, Any],
    fixture_chain: Mapping[str, Any],
    chat_packet: Mapping[str, Any],
) -> dict[str, Any]:
    recommendation = _stage(fixture_chain, "recommendation_three_node_shadow_artifact")
    offer = _mapping(recommendation.get("shadow_offer_packet"))
    lineage_ids = [
        candidate_id
        for candidate_id in [GOLDEN_MEMORY_ID]
        if candidate_id in context_pack.get("selected_candidate_ids", [])
    ]
    packets = _journey_packets(chat_packet, {"L", "M"})
    blockers = []
    if GOLDEN_MEMORY_ID not in lineage_ids:
        blockers.append("golden_memory_not_selected")
    if not _golden_order_projected(memory_projection):
        blockers.append("golden_order_not_projected")
    if GOLDEN_MEMORY_REF not in offer.get("source_refs", []):
        blockers.append("recommendation_missing_memory_source_ref")
    if len(packets) != 2:
        blockers.append("recommendation_journey_packets_missing")
    return {
        **_scenario_base("memory_guided_recommendation_chat_offer"),
        "status": "pass" if not blockers else "blocked",
        "lineage_candidate_ids": lineage_ids,
        "recommendation_source_refs": list(offer.get("source_refs") or []),
        "terminal_packet_refs": [str(packet.get("packet_id") or "") for packet in packets],
        "blockers": blockers,
    }


def _rescue_proactive_no_send(
    terminal_sink: Mapping[str, Any],
    chat_packet: Mapping[str, Any],
) -> dict[str, Any]:
    records = _records(terminal_sink)
    packets = _chat_packets(chat_packet)
    record_refs = [
        f"{record.get('trigger_type')}:{record.get('interaction_action')}"
        for record in records
    ]
    domains = {
        str(packet.get("packet_id") or ""): list(packet.get("source_domains") or [])
        for packet in packets
    }
    blockers = []
    if record_refs != ["recommendation_prompt:dismiss", "rescue_nudge:snooze"]:
        blockers.append("terminal_record_actions_mismatch")
    if sorted(domains) != ["recommendation_prompt:0", "rescue_nudge:1"]:
        blockers.append("chat_packet_refs_mismatch")
    return {
        **_scenario_base("rescue_proactive_no_send_chat_candidate"),
        "status": "pass" if not blockers else "blocked",
        "terminal_record_refs": record_refs,
        "source_domains_by_packet": domains,
        "blockers": blockers,
    }


def _dismiss_snooze_reopen_modify_controls(terminal_sink: Mapping[str, Any]) -> dict[str, Any]:
    control = _mapping(terminal_sink.get("control_path_evidence"))
    configured = _mapping(control.get("configured_paths"))
    actions = set(control.get("interaction_actions_observed") or [])
    undo_scope = _first_undo_scope(terminal_sink)
    blockers = []
    if configured != {"dismiss": True, "snooze": True, "undo": True}:
        blockers.append("configured_controls_incomplete")
    if not {"dismiss", "snooze"}.issubset(actions):
        blockers.append("dismiss_snooze_actions_missing")
    if undo_scope != "current_no_send_candidate_only":
        blockers.append("undo_scope_not_shadow_only")
    return {
        **_scenario_base("dismiss_snooze_reopen_modify_shadow_controls"),
        "status": "pass" if not blockers else "blocked",
        "control_semantics": {
            "dismiss": {
                "observed": "dismiss" in actions,
                "durable_suppression_written": False,
                "semantic_effect": "hide_current_shadow_candidate_only",
            },
            "snooze": {
                "observed": "snooze" in actions,
                "durable_snooze_written": False,
                "semantic_effect": "wait_for_next_signal_without_scheduler_delivery",
            },
            "reopen_or_modify": {
                "configured": configured.get("undo") is True,
                "legacy_internal_alias": "undo",
                "canonical_rollback_requested": False,
                "semantic_effect": undo_scope,
            },
        },
        "blockers": blockers,
    }


def _scenario_base(scenario_id: str) -> dict[str, Any]:
    return {
        "scenario_id": scenario_id,
        "surface": "chat",
        "chat_first": True,
        "served_to_user": False,
        "delivery_attempted": False,
        "scheduler_enqueued": False,
        "canonical_mutation_requested": False,
        "semantic_decision_inferred_by_runner": False,
    }


def _stage(fixture_chain: Mapping[str, Any], artifact_type: str) -> Mapping[str, Any]:
    return next(
        (
            _mapping(stage)
            for stage in fixture_chain.get("stage_artifacts") or []
            if _mapping(stage).get("artifact_type") == artifact_type
        ),
        {},
    )


def _golden_order_projected(memory_projection: Mapping[str, Any]) -> bool:
    summary = _mapping(memory_projection.get("golden_order_summary"))
    return any(
        _mapping(order).get("candidate_id") == GOLDEN_MEMORY_ID
        for order in summary.get("orders") or []
    )


def _journey_packets(
    chat_packet: Mapping[str, Any],
    journey_ids: set[str],
) -> list[Mapping[str, Any]]:
    return [
        _mapping(packet)
        for packet in chat_packet.get("journey_chat_packets") or []
        if _mapping(packet).get("journey_id") in journey_ids
    ]


def _chat_packets(chat_packet: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [_mapping(packet) for packet in chat_packet.get("chat_packets") or []]


def _records(terminal_sink: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [_mapping(record) for record in terminal_sink.get("records") or []]


def _first_undo_scope(terminal_sink: Mapping[str, Any]) -> str:
    records = _records(terminal_sink)
    return str(records[0].get("undo_scope") or "") if records else ""


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["SCENARIO_IDS", "SIDECAR_ACTIVATION_CONTRACT", "build_chat_first_journey_rows", "scenario_row_blockers"]
