from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
from app.advanced_shadow_lab.model_profiles import advanced_lab_model_profile_policy
from app.advanced_shadow_lab.product_lab_live_payload import (
    product_lab_live_provider_payload,
)
from app.advanced_shadow_lab.product_lab_live_output_guard import (
    product_lab_live_output_guard,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.product_lab_live_diagnostic"
)
ARTIFACT_TYPE = "advanced_product_lab_live_diagnostic_artifact"
SUPPORTED_SUMMARY = "advanced_product_lab_simulated_dogfood_summary"
STAGE = "advanced_product_lab_live_diagnostic"
SYSTEM_PROMPT = (
    "Return JSON for an advanced product-lab diagnostic only. You may discuss "
    "messages served inside the isolated lab, but do not claim any outside-lab "
    "delivery, save, commit, schedule, or production application. Required fields: "
    "diagnostic_notes, risk_notes, claim_scope, action_request, delivery_request, "
    "mutation_request, reason_codes."
)
NON_CLAIMS = [
    "not_user_facing_activation",
    "not_mainline_runtime_activation",
    "not_scheduler_delivery",
    "not_durable_product_memory",
    "not_canonical_mutation",
    "not_product_readiness_evidence",
]


def run_product_lab_live_diagnostic(
    *,
    summary_artifact: Mapping[str, Any],
    provider: Any,
    provider_mode: str,
    live_invoked: bool,
    output_path: Path | None = None,
) -> dict[str, Any]:
    input_blockers = _summary_blockers(summary_artifact)
    provider_result: dict[str, Any] = {}
    provider_trace: dict[str, Any] = {}
    provider_invoked = False
    provider_error: dict[str, Any] = {}
    if not input_blockers:
        provider_invoked = True
        try:
            provider_result, provider_trace = asyncio.run(
                _invoke_provider(provider, summary_artifact)
            )
        except Exception as exc:  # live diagnostics must leave an artifact.
            provider_error = {"type": type(exc).__name__, "message": str(exc)[:300]}
    output_guard = (
        {"status": "not_run", "blockers": []}
        if input_blockers or provider_error
        else product_lab_live_output_guard(provider_result)
    )
    blockers = [*input_blockers, *output_guard["blockers"]]
    status = "provider_error" if provider_error else "blocked" if blockers else "pass"
    artifact = {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": status,
        **dict(FALSE_FLAGS),
        "owner": "app/advanced_shadow_lab/product_lab_live_diagnostic.py",
        "consumer": "advanced_product_lab_operator_review",
        "retirement_trigger": "approved_advanced_product_lab_live_activation_plan",
        "source_summary_artifact_type": summary_artifact.get("artifact_type"),
        "source_session_id": str(summary_artifact.get("session_id") or ""),
        "source_turn_count": int(summary_artifact.get("turn_count") or 0),
        "lab_user_facing_behavior_changed": bool(summary_artifact.get("lab_user_facing_behavior_changed")),
        "lab_memory_store_written": bool(summary_artifact.get("lab_memory_store_written")),
        "memory_context_injected": bool(summary_artifact.get("memory_context_injected")),
        "model_input_policy": _model_input_policy(),
        "model_profile_policy": advanced_lab_model_profile_policy(),
        "provider_mode": str(provider_mode),
        "live_invoked": bool(live_invoked),
        "live_provider_used": bool(live_invoked and provider_invoked),
        "provider_invoked": provider_invoked,
        "provider_readiness": _mapping(provider.readiness()) if hasattr(provider, "readiness") else {},
        "provider_trace_summary": _trace_summary(provider_trace),
        "provider_error": provider_error,
        "model_output_summary": _model_output_summary(provider_result),
        "output_guard": output_guard,
        "blockers": blockers,
        "non_claims": list(NON_CLAIMS),
    }
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return artifact


async def _invoke_provider(
    provider: Any,
    summary_artifact: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    payload, trace = await provider.complete_with_trace(
        system_prompt=SYSTEM_PROMPT,
        user_payload=product_lab_live_provider_payload(
            summary_artifact,
            constraints=_model_input_policy(),
        ),
        stage=STAGE,
        max_tokens=700,
    )
    return _mapping(payload), _mapping(trace)


def _model_input_policy() -> dict[str, Any]:
    return {
        "claim_scope_required": "diagnostic_only",
        "lab_user_facing_output_allowed": True,
        "outside_lab_delivery_allowed": False,
        "mutation_or_commit_allowed": False,
    }


def _summary_blockers(summary: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if summary.get("artifact_type") != SUPPORTED_SUMMARY:
        blockers.append("summary.unsupported_artifact_type")
    if summary.get("status") != "pass":
        blockers.append("summary.status_not_pass")
    for flag in (
        "live_provider_invoked",
        "user_facing_behavior_changed",
        "mainline_runtime_connected",
        "production_db_migration_allowed",
        "durable_product_memory_written",
        "canonical_product_mutation_allowed",
        "manager_context_packet_changed",
    ):
        if summary.get(flag) is True:
            blockers.append(f"summary.{flag}")
    return blockers


def _model_output_summary(output: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "diagnostic_notes_present": bool(
            str(output.get("diagnostic_notes") or "").strip()
        ),
        "risk_notes_present": bool(str(output.get("risk_notes") or "").strip()),
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


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "run_product_lab_live_diagnostic"]
