from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract("advanced_shadow_lab.rescue_copy_live_diagnostic")
ARTIFACT_TYPE = "advanced_shadow_rescue_copy_live_diagnostic_artifact"
STAGE = "advanced_shadow_rescue_copy_live_diagnostic"
SUPPORTED_INPUT = "rescue_proposal_shaping_input_shadow_packet"
SYSTEM_PROMPT = (
    "Return JSON for rescue proposal copy diagnostics only. Do not claim the plan "
    "was shown, sent, saved, committed, scheduled, or applied. Required fields: "
    "proposal_headline, proposal_summary, coaching_frame, recommended_days, "
    "daily_kcal_adjustment, cap_mode, special_posture, claim_scope, "
    "action_request, delivery_request, mutation_request, reason_codes."
)
DETERMINISTIC_FIELDS = ("recommended_days", "daily_kcal_adjustment", "cap_mode", "special_posture")
FALSE_FLAG_NAMES = (
    "mainline_runtime_connected", "mainline_route_or_api_mount_allowed",
    "production_scheduler_delivery_allowed", "production_db_migration_allowed",
    "canonical_product_mutation_allowed", "delivery_attempted", "proactive_sent",
    "scheduler_enabled", "live_delivery_allowed", "push_or_line_delivery_connected",
    "manager_context_packet_changed", "manager_context_injected",
    "recommendation_served", "rescue_committed", "proposal_committed",
    "day_budget_mutated", "body_plan_mutated", "meal_thread_mutated",
    "durable_product_memory_written", "durable_memory_written", "mutation_changed",
    "user_facing_behavior_changed", "product_readiness_claimed",
)
FALSE_FLAGS = dict.fromkeys(FALSE_FLAG_NAMES, False)
CLAIM_FLAGS = (*FALSE_FLAG_NAMES, "runtime_effect_allowed", "canonical_mutation_changed", "ledger_entry_created")
NON_CLAIMS = [
    "not_runtime_activation_evidence", "not_product_readiness_evidence",
    "not_user_facing_activation", "not_scheduler_delivery",
    "not_canonical_mutation_authority", "not_rescue_proposal_commit",
]
OUTPUT_TEXT_FIELDS = ("proposal_headline", "proposal_summary", "coaching_frame")
DELIVERY_TOKENS = ("sent", "delivered", "notify", "notification", "push", "line message")
MUTATION_TOKENS = ("committed", "saved it", "applied", "updated your budget")


def run_rescue_copy_live_diagnostic(
    *,
    rescue_shaping_input_packet: Mapping[str, Any],
    provider: Any,
    provider_mode: str,
    live_invoked: bool,
    output_path: Path | None = None,
) -> dict[str, Any]:
    input_blockers = _input_blockers(rescue_shaping_input_packet)
    deterministic_option = _deterministic_option(rescue_shaping_input_packet)
    if not deterministic_option:
        input_blockers.append("rescue_shaping_input_packet.missing_deterministic_option")

    provider_result: dict[str, Any] = {}
    provider_trace: dict[str, Any] = {}
    provider_invoked = False
    if not input_blockers:
        provider_invoked = True
        provider_result, provider_trace = asyncio.run(_invoke_provider(provider, rescue_shaping_input_packet, deterministic_option))

    output_guard = (
        {"status": "not_run", "blockers": []}
        if input_blockers
        else _output_guard(provider_result, deterministic_option)
    )
    blockers = [*input_blockers, *output_guard["blockers"]]
    artifact = {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "owner": "app/advanced_shadow_lab",
        "consumer": "future_advanced_shadow_comparison_or_proactive_quality_review",
        "retirement_trigger": "approved_advanced_runtime_activation_plan",
        "target_surface": "rescue_proposal_copy_posture",
        "source_rescue_artifact_type": rescue_shaping_input_packet.get("artifact_type"),
        "deterministic_option_summary": deterministic_option,
        "provider_mode": str(provider_mode),
        "live_invoked": bool(live_invoked),
        "live_provider_used": bool(live_invoked and provider_invoked),
        "provider_invoked": provider_invoked,
        "provider_readiness": _mapping(provider.readiness()) if hasattr(provider, "readiness") else {},
        "provider_trace_summary": _trace_summary(provider_trace),
        "model_output_summary": _model_output_summary(provider_result),
        "output_guard": output_guard,
        "blockers": blockers,
        "runtime_connected": False,
        "runtime_truth_changed": False,
        "non_claims": list(NON_CLAIMS),
        **dict(FALSE_FLAGS),
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    return artifact


async def _invoke_provider(provider: Any, packet: Mapping[str, Any], deterministic_option: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    payload, trace = await provider.complete_with_trace(
        system_prompt=SYSTEM_PROMPT,
        user_payload=_provider_payload(packet, deterministic_option),
        stage=STAGE,
        max_tokens=600,
    )
    return _mapping(payload), _mapping(trace)


def _input_blockers(packet: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if packet.get("artifact_type") != SUPPORTED_INPUT:
        blockers.append("rescue_shaping_input_packet.unsupported_artifact_type")
    if packet.get("status") != "pass":
        blockers.append("rescue_shaping_input_packet.status_not_pass")
    for flag in dict.fromkeys(CLAIM_FLAGS):
        if packet.get(flag) is True:
            blockers.append(f"rescue_shaping_input_packet.{flag}")
    return blockers


def _provider_payload(packet: Mapping[str, Any], deterministic_option: Mapping[str, Any]) -> dict[str, Any]:
    envelope = _mapping(packet.get("shaping_input_envelope"))
    review_context = _mapping(envelope.get("review_context"))
    return {
        "target_surface": "rescue_proposal_copy_posture",
        "deterministic_option": dict(deterministic_option),
        "review_context": {
            "budget_context": _allowed(_mapping(review_context.get("budget_context")), {"current_date", "overshoot_kcal", "remaining_budget_kcal"}),
            "body_plan_context": _allowed(_mapping(review_context.get("body_plan_context")), {"safety_floor_kcal", "target_days_count", "sex"}),
        },
        "constraints": {
            "claim_scope_required": "diagnostic_copy_only",
            "user_facing_output_allowed": False,
            "delivery_or_notification_allowed": False,
            "mutation_or_commit_allowed": False,
        },
    }


def _output_guard(output: Mapping[str, Any], deterministic_option: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if output.get("claim_scope") != "diagnostic_copy_only":
        blockers.append("model_output.claim_scope_not_diagnostic")
    for key, blocker in (
        ("action_request", "model_output.action_request_not_allowed"),
        ("delivery_request", "model_output.delivery_request_not_allowed"),
        ("mutation_request", "model_output.mutation_request_not_allowed"),
    ):
        if output.get(key) is True:
            blockers.append(blocker)
    for field in DETERMINISTIC_FIELDS:
        if field in output and output.get(field) != deterministic_option.get(field):
            blockers.append(f"model_output.{field}_override")
    text = _joined_output_text(output)
    if any(token in text for token in DELIVERY_TOKENS):
        blockers.append("model_output.delivery_language_present")
    if any(token in text for token in MUTATION_TOKENS):
        blockers.append("model_output.mutation_language_present")
    return {"status": "blocked" if blockers else "pass", "blockers": blockers}


def _model_output_summary(output: Mapping[str, Any]) -> dict[str, Any]:
    return {f"{field}_present": bool(str(output.get(field) or "").strip()) for field in OUTPUT_TEXT_FIELDS} | {
        "claim_scope": str(output.get("claim_scope") or ""),
        "reason_codes": [str(item) for item in output.get("reason_codes") or []],
    }


def _deterministic_option(packet: Mapping[str, Any]) -> dict[str, Any]:
    envelope = _mapping(packet.get("shaping_input_envelope"))
    option = _mapping(envelope.get("deterministic_option"))
    return {field: option.get(field) for field in DETERMINISTIC_FIELDS if field in option}


def _trace_summary(trace: Mapping[str, Any]) -> dict[str, Any]:
    return {"stage": str(trace.get("stage") or ""), "provider": str(trace.get("provider") or ""), "usage_present": isinstance(trace.get("usage"), Mapping)}


def _joined_output_text(output: Mapping[str, Any]) -> str:
    return " ".join(str(output.get(field) or "") for field in OUTPUT_TEXT_FIELDS).lower()


def _allowed(value: Mapping[str, Any], keys: set[str]) -> dict[str, Any]:
    return {key: value[key] for key in keys if key in value}


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "run_rescue_copy_live_diagnostic"]
