from __future__ import annotations

from typing import Any, Mapping

from app.rescue.domain.shadow_status import RESCUE_SHADOW_NON_RUNTIME_FLAGS
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.proposal_shaping_output_validator_shadow"
)
INPUT_ARTIFACT = "rescue_proposal_shaping_input_shadow_packet"
REQUIRED_RUBRIC_FLAGS = (
    "future_oriented",
    "no_shame",
    "not_user_facing",
    "fixture_only",
)
DETERMINISTIC_OPTION_FIELDS = (
    "recommended_days",
    "daily_kcal_adjustment",
    "cap_mode",
    "special_posture",
)
FALSE_INPUT_FLAGS = (
    "runtime_effect_allowed",
    "live_llm_invoked",
    "provider_called",
    "manager_context_injected",
    "rescue_committed",
    "proposal_committed",
    "day_budget_mutated",
    "body_plan_mutated",
    "meal_thread_mutated",
    "durable_memory_written",
    "proactive_sent",
    "recommendation_served",
    "ledger_entry_created",
)
FORBIDDEN_AUTHORITY_FIELDS = (
    "primary_actions",
    "proposal_card",
    "proposal_id",
    "container_id",
    "commit",
    "accept_rescue_plan",
    "dismiss_rescue_plan",
    "route_target",
    "scheduler_trigger",
    "runtime_effect_allowed",
    "rescue_committed",
    "proposal_committed",
    "day_budget_mutated",
    "body_plan_mutated",
    "meal_thread_mutated",
    "ledger_entry_created",
    "durable_memory_written",
    "proactive_sent",
    "recommendation_served",
)


def validate_rescue_proposal_shaping_output_shadow(
    *,
    proposal_shaping_input_shadow_packet: Mapping[str, Any],
    candidate_output: Mapping[str, Any],
) -> dict[str, Any]:
    input_blockers = _input_blockers(proposal_shaping_input_shadow_packet)
    deterministic_option = _deterministic_option(proposal_shaping_input_shadow_packet)
    candidate_blockers = (
        []
        if input_blockers
        else _candidate_blockers(candidate_output, deterministic_option)
    )
    blockers = [*input_blockers, *candidate_blockers]
    status = "blocked" if input_blockers else "fail" if candidate_blockers else "pass"

    return {
        "artifact_type": "rescue_proposal_shaping_output_validation_shadow",
        "artifact_schema_version": "1.0",
        "status": status,
        "owner": "app/rescue",
        "consumer": "future_rescue_proposal_shaping_llm_activation_review",
        "retirement_trigger": "approved_rescue_runtime_activation_plan",
        "deterministic_option": deterministic_option,
        "blockers": blockers,
        "fixture_output_validated": status == "pass",
        "copy_payload_evaluated_semantically": False,
        "raw_candidate_output_included": False,
        "runtime_effect_allowed": False,
        "live_llm_invoked": False,
        "provider_called": False,
        "manager_context_injected": False,
        "rescue_committed": False,
        "proposal_committed": False,
        "ledger_entry_created": False,
        "day_budget_mutated": False,
        "body_plan_mutated": False,
        "meal_thread_mutated": False,
        "durable_memory_written": False,
        "proactive_sent": False,
        "recommendation_served": False,
        **dict(RESCUE_SHADOW_NON_RUNTIME_FLAGS),
    }


def _input_blockers(packet: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if packet.get("artifact_type") != INPUT_ARTIFACT:
        blockers.append("proposal_shaping_input_shadow_packet.unsupported_artifact_type")
    if packet.get("status") == "blocked":
        blockers.append("proposal_shaping_input_shadow_packet.status_blocked")
    if not _deterministic_option(packet):
        blockers.append("proposal_shaping_input_shadow_packet.missing_deterministic_option")
    for flag in FALSE_INPUT_FLAGS:
        if packet.get(flag) is True:
            blockers.append(f"proposal_shaping_input_shadow_packet.{flag}")
    return blockers


def _candidate_blockers(
    candidate_output: Mapping[str, Any],
    deterministic_option: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    for field in DETERMINISTIC_OPTION_FIELDS:
        if (
            field in candidate_output
            and candidate_output.get(field) != deterministic_option.get(field)
        ):
            blockers.append(f"candidate_output.{field}_override")
    for field in FORBIDDEN_AUTHORITY_FIELDS:
        if _has_authority_value(candidate_output.get(field)):
            blockers.append(f"candidate_output.{field}_forbidden")
    blockers.extend(_rubric_blockers(candidate_output.get("rubric")))
    return blockers


def _rubric_blockers(rubric: Any) -> list[str]:
    if not isinstance(rubric, Mapping):
        return [
            f"candidate_output.rubric.{flag}_not_true"
            for flag in REQUIRED_RUBRIC_FLAGS
        ]
    return [
        f"candidate_output.rubric.{flag}_not_true"
        for flag in REQUIRED_RUBRIC_FLAGS
        if rubric.get(flag) is not True
    ]


def _deterministic_option(packet: Mapping[str, Any]) -> dict[str, Any]:
    envelope = packet.get("shaping_input_envelope")
    if not isinstance(envelope, Mapping):
        return {}
    option = envelope.get("deterministic_option")
    if not isinstance(option, Mapping):
        return {}
    return {field: option.get(field) for field in DETERMINISTIC_OPTION_FIELDS}


def _has_authority_value(value: Any) -> bool:
    return value not in (None, False, [], {})


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "validate_rescue_proposal_shaping_output_shadow",
]
