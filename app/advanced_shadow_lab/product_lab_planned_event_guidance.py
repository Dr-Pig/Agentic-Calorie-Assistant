from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.product_lab_planned_event_guidance"
)
ARTIFACT_TYPE = "advanced_product_lab_planned_event_guidance_artifact"


def run_product_lab_planned_event_guidance(
    *, fixture_inputs: Mapping[str, Any], enabled: bool
) -> dict[str, Any]:
    if not enabled:
        return _not_applicable()
    context = _mapping(fixture_inputs.get("planned_event_guidance_context"))
    blockers = _blockers(context)
    guidance = {} if blockers else _guidance_card(context)
    return {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "chat_first": True,
        "guidance_card": guidance,
        "proposal_created": False,
        "planned_event_budget_allocation_proposal_created": False,
        "informational_only": True,
        "served_to_lab_user": not bool(blockers),
        "served_to_mainline_user": False,
        "mainline_activation_enabled": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "blockers": blockers,
        **dict(FALSE_FLAGS),
    }


def _guidance_card(context: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "card_kind": "planned_event_all_day_guidance_lab",
        "event_id": str(context.get("event_id") or ""),
        "event_label": str(context.get("event_label") or ""),
        "event_local_date": str(context.get("event_local_date") or ""),
        "remaining_kcal": _int(context.get("remaining_kcal")),
        "suggested_reserve_kcal": _int(context.get("suggested_reserve_kcal")),
        "lunch_cap_kcal": _int(context.get("lunch_cap_kcal")),
        "informational_only": True,
        "proposal_created": False,
        "source_refs": [str(ref) for ref in context.get("source_refs") or []],
    }


def _not_applicable() -> dict[str, Any]:
    return {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": "not_applicable",
        "proposal_created": False,
        "blockers": [],
        **dict(FALSE_FLAGS),
    }


def _blockers(context: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    for field in ("event_id", "event_label", "event_local_date"):
        if not str(context.get(field) or ""):
            blockers.append(f"planned_event_guidance_context.{field}_missing")
    for field in ("remaining_kcal", "suggested_reserve_kcal", "lunch_cap_kcal"):
        if _int(context.get(field)) <= 0:
            blockers.append(f"planned_event_guidance_context.{field}_missing")
    return blockers


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "run_product_lab_planned_event_guidance"]
