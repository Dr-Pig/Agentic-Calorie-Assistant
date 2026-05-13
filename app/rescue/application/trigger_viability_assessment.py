from __future__ import annotations

from typing import Any, Mapping

from app.rescue.application.read_model_input_packet import FORBIDDEN_INPUT_SOURCES
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.trigger_viability_assessment"
)
READ_MODEL_PACKET_ARTIFACT = "rescue_read_model_input_packet"
GUARDRAIL_MATH_ARTIFACT = "rescue_guardrail_math_packet"
ALLOWED_TRIGGER_SOURCES = {"reactive_chat", "proactive_budget_alert"}
FALSE_INPUT_FLAGS = (
    "runtime_effect_allowed",
    "canonical_mutation_changed",
    "production_scheduler_delivery_allowed",
    "mainline_activation_enabled",
    "mainline_runtime_connected",
)


def build_rescue_trigger_viability_assessment(
    *,
    read_model_input_packet: Mapping[str, Any],
    guardrail_math_packet: Mapping[str, Any],
    trigger_request: Mapping[str, Any],
) -> dict[str, Any]:
    input_blockers = _input_blockers(
        read_model_input_packet,
        guardrail_math_packet,
        trigger_request,
    )
    if input_blockers:
        return _assessment(
            status="blocked",
            triggered=False,
            trigger_type="none",
            recovery_viability="blocked",
            blockers=input_blockers,
            proactive_eligibility=_proactive_eligibility(read_model_input_packet),
            guardrail_math_packet=guardrail_math_packet,
            read_model_input_packet=read_model_input_packet,
        )

    trigger_source = str(trigger_request.get("trigger_source") or "")
    proactive = _proactive_eligibility(read_model_input_packet)
    allowed, blockers = _trigger_decision_blockers(
        trigger_source=trigger_source,
        explicit_rescue_request=trigger_request.get("explicit_rescue_request") is True,
        proactive_eligibility=proactive,
        overshoot_kcal=_overshoot(guardrail_math_packet),
    )
    triggered = not blockers
    return _assessment(
        status="pass",
        triggered=triggered,
        trigger_type=_trigger_type(trigger_source, triggered),
        recovery_viability=str(guardrail_math_packet.get("recovery_viability"))
        if allowed
        else "not_assessed",
        blockers=blockers,
        proactive_eligibility=proactive,
        guardrail_math_packet=guardrail_math_packet,
        read_model_input_packet=read_model_input_packet,
    )


def _assessment(
    *,
    status: str,
    triggered: bool,
    trigger_type: str,
    recovery_viability: str,
    blockers: list[str],
    proactive_eligibility: Mapping[str, Any],
    guardrail_math_packet: Mapping[str, Any],
    read_model_input_packet: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_type": "rescue_trigger_viability_assessment",
        "status": status,
        "owner": "app/rescue",
        "consumer": "rescue_option_generation_node",
        "decision_mode": "deterministic",
        "triggered": triggered,
        "trigger_type": trigger_type,
        "trigger_severity": _trigger_severity(guardrail_math_packet),
        "trigger_object_ref": _trigger_object_ref(read_model_input_packet),
        "overshoot_summary": dict(guardrail_math_packet.get("overshoot_summary") or {}),
        "recovery_viability": recovery_viability,
        "proactive_eligibility": dict(proactive_eligibility),
        "blockers": blockers,
        "forbidden_input_sources": list(FORBIDDEN_INPUT_SOURCES),
        "option_generated": False,
        "proposal_committed": False,
        "ledger_entry_created": False,
        "runtime_effect_allowed": False,
        "canonical_mutation_changed": False,
        "production_scheduler_delivery_allowed": False,
        "manager_context_packet_changed_in_mainline": False,
        "durable_product_memory_written_in_mainline": False,
    }


def _input_blockers(
    read_model_input_packet: Mapping[str, Any],
    guardrail_math_packet: Mapping[str, Any],
    trigger_request: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if read_model_input_packet.get("artifact_type") != READ_MODEL_PACKET_ARTIFACT:
        blockers.append("read_model_input_packet.unsupported_artifact_type")
    if read_model_input_packet.get("status") == "blocked":
        blockers.append("read_model_input_packet.status_blocked")
    if guardrail_math_packet.get("artifact_type") != GUARDRAIL_MATH_ARTIFACT:
        blockers.append("guardrail_math_packet.unsupported_artifact_type")
    if guardrail_math_packet.get("status") == "blocked":
        blockers.append("guardrail_math_packet.status_blocked")
    for flag in FALSE_INPUT_FLAGS:
        if read_model_input_packet.get(flag) is True:
            blockers.append(f"read_model_input_packet.{flag}")
        if guardrail_math_packet.get(flag) is True:
            blockers.append(f"guardrail_math_packet.{flag}")
    trigger_source = str(trigger_request.get("trigger_source") or "")
    if trigger_source not in ALLOWED_TRIGGER_SOURCES:
        blockers.append(f"unsupported_trigger_source:{trigger_source}")
    return blockers


def _trigger_decision_blockers(
    *,
    trigger_source: str,
    explicit_rescue_request: bool,
    proactive_eligibility: Mapping[str, Any],
    overshoot_kcal: int,
) -> tuple[bool, list[str]]:
    if trigger_source == "reactive_chat" and not explicit_rescue_request:
        return False, ["reactive_trigger_missing_explicit_request"]
    if trigger_source == "proactive_budget_alert" and not proactive_eligibility["eligible"]:
        return False, list(proactive_eligibility["reasons"])
    if overshoot_kcal <= 0:
        return False, ["no_overshoot"]
    return True, []


def _proactive_eligibility(read_model_input_packet: Mapping[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    open_proposals = _mapping(read_model_input_packet.get("open_proposals_view"))
    proactive = _mapping(read_model_input_packet.get("proactive_status_view"))
    if _int(open_proposals.get("open_rescue_proposal_count")) > 0:
        reasons.append("open_rescue_proposal")
    if proactive.get("budget_alert_cooldown_active") is True:
        reasons.append("budget_alert_cooldown_active")
    suppressed = [str(item) for item in proactive.get("suppressed_trigger_types") or []]
    if "budget_alert_check" in suppressed:
        reasons.append("suppressed_trigger_type:budget_alert_check")
    return {"eligible": not reasons, "reasons": reasons}


def _trigger_type(trigger_source: str, triggered: bool) -> str:
    if not triggered:
        return "none"
    if trigger_source == "proactive_budget_alert":
        return "proactive_same_day_overshoot"
    return "reactive_same_day_overshoot"


def _trigger_severity(guardrail_math_packet: Mapping[str, Any]) -> str:
    summary = _mapping(guardrail_math_packet.get("overshoot_summary"))
    overshoot_kcal = _int(summary.get("overshoot_kcal"))
    effective_budget = _int(summary.get("effective_budget_kcal"))
    if overshoot_kcal <= 0 or effective_budget <= 0:
        return "none"
    return "high" if overshoot_kcal >= effective_budget * 0.25 else "moderate"


def _trigger_object_ref(read_model_input_packet: Mapping[str, Any]) -> dict[str, str]:
    budget = _mapping(read_model_input_packet.get("current_budget_view"))
    return {
        "source_type": "CurrentBudgetView",
        "local_date": str(budget.get("local_date") or ""),
    }


def _overshoot(guardrail_math_packet: Mapping[str, Any]) -> int:
    return _int(_mapping(guardrail_math_packet.get("overshoot_summary")).get("overshoot_kcal"))


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


__all__ = [
    "ALLOWED_TRIGGER_SOURCES",
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_rescue_trigger_viability_assessment",
]
