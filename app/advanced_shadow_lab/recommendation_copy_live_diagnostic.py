from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract("advanced_shadow_lab.recommendation_copy_live_diagnostic")
ARTIFACT_TYPE = "advanced_shadow_recommendation_copy_live_diagnostic_artifact"
STAGE = "advanced_shadow_recommendation_copy_live_diagnostic"
SUPPORTED_SUMMARY = "recommendation_shadow_summary_consumer_quality_report"
SYSTEM_PROMPT = (
    "Return JSON for recommendation copy diagnostics only. Do not claim the recommendation "
    "was sent, shown, saved, committed, or scheduled. Required fields: candidate_id, "
    "draft_prompt, reason_summary, claim_scope, action_request, delivery_request, "
    "mutation_request, reason_codes."
)
FALSE_FLAG_NAMES = (
    "mainline_runtime_connected", "mainline_route_or_api_mount_allowed",
    "production_scheduler_delivery_allowed", "production_db_migration_allowed",
    "canonical_product_mutation_allowed", "delivery_attempted", "proactive_sent",
    "scheduler_enabled", "live_delivery_allowed", "push_or_line_delivery_connected",
    "manager_context_packet_changed", "manager_context_injected", "recommendation_served",
    "rescue_committed", "proposal_committed", "durable_product_memory_written",
    "durable_memory_written", "mutation_changed", "user_facing_behavior_changed",
    "product_readiness_claimed",
)
FALSE_FLAGS = dict.fromkeys(FALSE_FLAG_NAMES, False)
CLAIM_FLAGS = (
    "recommendation_served", "manager_context_packet_changed", *FALSE_FLAG_NAMES,
    "runtime_effect_allowed", "canonical_mutation_changed", "memory_store_written",
    "day_budget_mutated", "body_plan_mutated", "meal_thread_mutated",
    "intake_handoff_created",
)
NON_CLAIMS = [
    "not_runtime_activation_evidence", "not_product_readiness_evidence",
    "not_user_facing_activation", "not_scheduler_delivery",
    "not_canonical_mutation_authority", "not_recommendation_serving",
]


def run_recommendation_copy_live_diagnostic(
    *,
    recommendation_summary_report: Mapping[str, Any],
    provider: Any,
    provider_mode: str,
    live_invoked: bool,
    output_path: Path | None = None,
) -> dict[str, Any]:
    input_blockers = _summary_blockers(recommendation_summary_report)
    candidate = _primary_candidate(recommendation_summary_report)
    if not candidate:
        input_blockers.append("recommendation_summary.primary_candidate_missing")

    provider_result: dict[str, Any] = {}
    provider_trace: dict[str, Any] = {}
    provider_invoked = False
    if not input_blockers:
        provider_invoked = True
        provider_result, provider_trace = asyncio.run(_invoke_provider(provider, candidate))

    output_guard = {"status": "not_run", "blockers": []} if input_blockers else _output_guard(provider_result)
    blockers = [*input_blockers, *output_guard["blockers"]]
    artifact = {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "owner": "app/advanced_shadow_lab",
        "consumer": "future_advanced_shadow_comparison_or_quality_gate",
        "retirement_trigger": "approved_advanced_runtime_activation_plan",
        "target_surface": "recommendation_prompt_reason_copy",
        "source_recommendation_artifact_type": recommendation_summary_report.get("artifact_type"),
        "source_candidate_count": _int(recommendation_summary_report.get("candidate_count")),
        "primary_candidate_id": str(candidate.get("candidate_id") or ""),
        "provider_mode": str(provider_mode),
        "live_invoked": bool(live_invoked),
        "live_provider_used": bool(live_invoked and provider_invoked),
        "provider_invoked": provider_invoked,
        "provider_readiness": _mapping(provider.readiness()) if hasattr(provider, "readiness") else {},
        "provider_trace_summary": _trace_summary(provider_trace),
        "model_output_summary": _model_output_summary(provider_result),
        "output_guard": output_guard,
        "blockers": blockers,
        "non_claims": list(NON_CLAIMS),
        **dict(FALSE_FLAGS),
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    return artifact


async def _invoke_provider(provider: Any, candidate: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    payload, trace = await provider.complete_with_trace(
        system_prompt=SYSTEM_PROMPT,
        user_payload=_provider_payload(candidate),
        stage=STAGE,
        max_tokens=500,
    )
    return _mapping(payload), _mapping(trace)


def _summary_blockers(report: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if report.get("artifact_type") != SUPPORTED_SUMMARY:
        blockers.append("recommendation_summary.unsupported_artifact_type")
    if report.get("status") != "pass":
        blockers.append("recommendation_summary.status_not_pass")
    if isinstance(report.get("blockers"), list):
        blockers += [f"recommendation_summary.{b}" for b in report["blockers"]]
    for flag in dict.fromkeys(CLAIM_FLAGS):
        if report.get(flag) is True:
            blockers.append(f"recommendation_summary.{flag}")
    return blockers


def _primary_candidate(report: Mapping[str, Any]) -> Mapping[str, Any]:
    primary_id = str(report.get("primary_candidate_id") or "")
    if not primary_id:
        ids = report.get("offer_candidate_ids")
        primary_id = str(ids[0]) if isinstance(ids, list) and ids else ""
    for item in report.get("candidate_evaluations") or []:
        candidate = _mapping(item)
        if candidate.get("candidate_id") == primary_id and candidate.get("quality_gate_passed") is True:
            return candidate
    return {}


def _provider_payload(candidate: Mapping[str, Any]) -> dict[str, Any]:
    refs = [str(ref) for ref in candidate.get("source_refs") or [] if str(ref).startswith("memory_candidate:")]
    return {
        "target_surface": "recommendation_prompt_reason_copy",
        "candidate": {
            "candidate_id": str(candidate.get("candidate_id") or ""),
            "title": str(candidate.get("title") or ""),
            "store_name": str(candidate.get("store_name") or ""),
            "estimated_kcal": candidate.get("estimated_kcal"),
            "quality_tier": str(candidate.get("quality_tier") or ""),
            "quality_signals": [str(item) for item in candidate.get("quality_signals") or []],
            "safe_source_refs": refs,
        },
        "constraints": {
            "claim_scope_required": "diagnostic_copy_only",
            "user_facing_output_allowed": False,
            "delivery_or_notification_allowed": False,
            "mutation_or_commit_allowed": False,
        },
    }


def _output_guard(output: Mapping[str, Any]) -> dict[str, Any]:
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
    text = f"{output.get('draft_prompt') or ''} {output.get('reason_summary') or ''}".lower()
    if any(token in text for token in ("sent", "delivered", "notify", "notification", "push", "line message")):
        blockers.append("model_output.delivery_language_present")
    if any(token in text for token in ("committed", "logged it", "saved it", "updated your budget")):
        blockers.append("model_output.mutation_language_present")
    return {"status": "blocked" if blockers else "pass", "blockers": blockers}


def _model_output_summary(output: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": str(output.get("candidate_id") or ""),
        "draft_prompt_present": bool(str(output.get("draft_prompt") or "").strip()),
        "reason_summary_present": bool(str(output.get("reason_summary") or "").strip()),
        "reason_codes": [str(item) for item in output.get("reason_codes") or []],
        "claim_scope": str(output.get("claim_scope") or ""),
    }


def _trace_summary(trace: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "stage": str(trace.get("stage") or ""),
        "provider": str(trace.get("provider") or ""),
        "usage_present": isinstance(trace.get("usage"), Mapping),
    }


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "run_recommendation_copy_live_diagnostic"]
