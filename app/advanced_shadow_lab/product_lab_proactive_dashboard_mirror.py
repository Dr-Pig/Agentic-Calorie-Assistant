from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS


def build_product_lab_proactive_dashboard_mirror(
    *,
    product_proactive: Mapping[str, Any],
    lab_chat_surface: Mapping[str, Any],
) -> dict[str, Any]:
    blockers = [
        *_source_blockers("product_proactive", product_proactive),
        *_source_blockers("lab_chat_surface", lab_chat_surface),
    ]
    active_cards = [] if blockers else [
        _active_card(message)
        for message in lab_chat_surface.get("messages") or []
        if isinstance(message, Mapping)
    ]
    suppressed_cards = [] if blockers else [
        _suppressed_card(trace)
        for trace in product_proactive.get("omission_traces") or []
        if isinstance(trace, Mapping)
    ]
    return {
        "artifact_type": "advanced_product_lab_proactive_dashboard_mirror_read_model",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "owner": "app/advanced_shadow_lab/product_lab_proactive_dashboard_mirror.py",
        "source_artifact_refs": [
            str(product_proactive.get("artifact_type") or ""),
            str(lab_chat_surface.get("artifact_type") or ""),
        ],
        "read_model_only": True,
        "ui_owns_truth": False,
        "active_card_count": len(active_cards),
        "active_card_ids": [
            str(card.get("candidate_id") or "") for card in active_cards
        ],
        "active_cards": active_cards,
        "suppressed_card_count": len(suppressed_cards),
        "suppressed_cards": suppressed_cards,
        "raw_trace_exposed_to_ui": False,
        "served_to_mainline_user": False,
        "scheduler_delivery_allowed": False,
        "notification_delivery_allowed": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "blockers": blockers,
        **dict(FALSE_FLAGS),
    }


def _source_blockers(prefix: str, artifact: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if artifact.get("status") != "pass":
        blockers.append(f"{prefix}.status_{artifact.get('status') or 'missing'}")
    if artifact.get("served_to_mainline_user") is True:
        blockers.append(f"{prefix}.served_to_mainline_user")
    if artifact.get("scheduler_delivery_allowed") is True:
        blockers.append(f"{prefix}.scheduler_delivery_allowed")
    if artifact.get("notification_delivery_allowed") is True:
        blockers.append(f"{prefix}.notification_delivery_allowed")
    if artifact.get("canonical_product_mutation_allowed") is True:
        blockers.append(f"{prefix}.canonical_product_mutation_allowed")
    return blockers


def _active_card(message: Mapping[str, Any]) -> dict[str, Any]:
    candidate_id = str(message.get("candidate_id") or "")
    return {
        "candidate_id": candidate_id,
        "trigger_type": str(message.get("trigger_type") or ""),
        "workflow_family": str(message.get("workflow_family") or ""),
        "surface": "dashboard_mirror",
        "copy": str(message.get("copy") or ""),
        "controls_visible": message.get("controls_visible") is True,
        "action_ids": [
            _dashboard_action_id(candidate_id, action)
            for action in message.get("actions") or []
            if isinstance(action, Mapping)
        ],
        "source_refs": [
            str(item) for item in message.get("product_runtime_output_refs") or []
        ],
        "ui_can_mutate_truth": False,
    }


def _suppressed_card(trace: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "trigger_type": str(trace.get("trigger_type") or ""),
        "omission_reason": str(trace.get("omission_reason") or ""),
        "suppression_reasons": [
            str(item) for item in trace.get("suppression_reasons") or []
        ],
        "review_decision": dict(_mapping(trace.get("review_decision"))),
        "active_control_event_id": str(trace.get("active_control_event_id") or ""),
        "actions": [],
        "ui_can_mutate_truth": False,
    }


def _dashboard_action_id(candidate_id: str, action: Mapping[str, Any]) -> str:
    action_name = str(action.get("action") or "")
    if action_name == "undo":
        action_name = "reopen_or_modify"
    return f"{action_name}:{candidate_id}"


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["build_product_lab_proactive_dashboard_mirror"]
