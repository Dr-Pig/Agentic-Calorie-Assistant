from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.chat_ux_packet"
)
FLOW_ARTIFACT = "reactive_rescue_independent_message_flow"
OPTION_ARTIFACT = "rescue_option_generation_result"
PRIMARY_ACTIONS = ["accept_rescue_plan", "dismiss_rescue_plan"]
DETERMINISTIC_OPTION_FIELDS = (
    "recommended_days",
    "daily_kcal_adjustment",
    "cap_mode",
)
COPY_FIELDS = ("headline", "summary", "explanation")
FORBIDDEN_TONE_TOKENS = ("failed", "punish", "guilt", "guarantee", "must")
FALSE_INPUT_FLAGS = (
    "runtime_effect_allowed",
    "canonical_mutation_changed",
    "production_scheduler_delivery_allowed",
    "ledger_entry_created",
    "proposal_committed",
)


def build_rescue_chat_ux_packet(
    *,
    independent_message_flow: Mapping[str, Any],
    option_generation_result: Mapping[str, Any],
    copy_candidate: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    input_blockers = _input_blockers(
        independent_message_flow,
        option_generation_result,
    )
    if input_blockers:
        return _packet(status="blocked", blockers=input_blockers)

    deterministic_option = _deterministic_option(option_generation_result)
    copy = dict(copy_candidate or _default_copy(deterministic_option))
    copy_blockers = _copy_blockers(copy, deterministic_option)
    if copy_blockers:
        return _packet(status="fail", blockers=copy_blockers)

    return _packet(
        status="pass",
        copy_guard_passed=True,
        ux_packet=_ux_packet(
            independent_message_flow=independent_message_flow,
            deterministic_option=deterministic_option,
            copy=copy,
        ),
    )


def _packet(
    *,
    status: str,
    blockers: list[str] | None = None,
    copy_guard_passed: bool = False,
    ux_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "artifact_type": "rescue_chat_ux_packet",
        "status": status,
        "owner": "app/rescue",
        "consumer": "rescue_response_presentation",
        "decision_mode": "hybrid_copy_guard",
        "chat_first": True,
        "copy_guard_passed": copy_guard_passed,
        "blockers": blockers or [],
        "ux_packet": ux_packet,
        "lab_user_facing_surface_allowed": status == "pass",
        "mainline_activation_enabled": False,
        "proposal_committed": False,
        "ledger_entry_created": False,
        "runtime_effect_allowed": False,
        "canonical_mutation_changed": False,
        "production_scheduler_delivery_allowed": False,
        "manager_context_packet_changed_in_mainline": False,
        "durable_product_memory_written_in_mainline": False,
    }


def _ux_packet(
    *,
    independent_message_flow: Mapping[str, Any],
    deterministic_option: Mapping[str, Any],
    copy: Mapping[str, Any],
) -> dict[str, Any]:
    message = _mapping(independent_message_flow.get("independent_message"))
    return {
        "message_id": str(message.get("message_id") or ""),
        "surface": "chat",
        "headline": str(copy.get("headline") or ""),
        "summary": str(copy.get("summary") or ""),
        "explanation": str(copy.get("explanation") or ""),
        "primary_actions": list(PRIMARY_ACTIONS),
        "secondary_affordance": "ask_to_adjust",
        "deterministic_option": dict(deterministic_option),
        "rubric": {
            "future_oriented": True,
            "no_shame": True,
            "math_not_overridden": True,
        },
    }


def _input_blockers(
    independent_message_flow: Mapping[str, Any],
    option_generation_result: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if independent_message_flow.get("artifact_type") != FLOW_ARTIFACT:
        blockers.append("independent_message_flow.unsupported_artifact_type")
    if independent_message_flow.get("status") == "blocked":
        blockers.append("independent_message_flow.status_blocked")
    if independent_message_flow.get("rescue_message_created") is not True:
        blockers.append("independent_message_flow.message_not_created")
    if option_generation_result.get("artifact_type") != OPTION_ARTIFACT:
        blockers.append("option_generation_result.unsupported_artifact_type")
    if option_generation_result.get("status") == "blocked":
        blockers.append("option_generation_result.status_blocked")
    if not _mapping(option_generation_result.get("selected_option")):
        blockers.append("option_generation_result.missing_selected_option")
    for flag in FALSE_INPUT_FLAGS:
        if independent_message_flow.get(flag) is True:
            blockers.append(f"independent_message_flow.{flag}")
        if option_generation_result.get(flag) is True:
            blockers.append(f"option_generation_result.{flag}")
    return blockers


def _copy_blockers(
    copy: Mapping[str, Any],
    deterministic_option: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    for field in COPY_FIELDS:
        blockers.extend(_tone_blockers(field, str(copy.get(field) or "")))
    for field in DETERMINISTIC_OPTION_FIELDS:
        if field in copy and copy.get(field) != deterministic_option.get(field):
            blockers.append(f"copy.{field}_override")
    return blockers


def _tone_blockers(field: str, text: str) -> list[str]:
    lowered = text.lower()
    return [
        f"copy.{field}.forbidden_tone_token:{token}"
        for token in FORBIDDEN_TONE_TOKENS
        if token in lowered
    ]


def _default_copy(deterministic_option: Mapping[str, Any]) -> dict[str, str]:
    days = deterministic_option.get("recommended_days")
    daily = abs(int(deterministic_option.get("daily_kcal_adjustment") or 0))
    return {
        "headline": "Recovery plan ready",
        "summary": f"Spread the recovery over {days} days at about {daily} kcal per day.",
        "explanation": "This is a proposal only. You can accept it or ask to adjust it.",
    }


def _deterministic_option(option_generation_result: Mapping[str, Any]) -> dict[str, Any]:
    selected = _mapping(option_generation_result.get("selected_option"))
    return {field: selected.get(field) for field in DETERMINISTIC_OPTION_FIELDS}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "PRIMARY_ACTIONS",
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_rescue_chat_ux_packet",
]
