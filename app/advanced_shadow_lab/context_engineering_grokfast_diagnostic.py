from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.context_engineering_case_loader import (
    load_context_engineering_golden_set,
)
from app.advanced_shadow_lab.model_profiles import ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID
from app.shared.infra.json_artifacts import write_json_artifact


ARTIFACT_TYPE = "advanced_product_lab_ce_grokfast_live_diagnostic"
STAGE = "advanced_product_lab_ce_grokfast_diagnostic"
SYSTEM_PROMPT = (
    "Return JSON only. You are evaluating advanced product-lab Manager planning. "
    "Use the provided case contracts, not raw chat text. For each case choose "
    "selected_capabilities and tool_call_order. Do not request user-facing delivery, "
    "canonical mutation, scheduler delivery, or durable memory activation."
)


def run_context_engineering_grokfast_diagnostic(
    *,
    provider: Any,
    provider_mode: str,
    live_invoked: bool,
    provider_profile_id: str = ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    output_path: Path | None = None,
) -> dict[str, Any]:
    provider_result: dict[str, Any] = {}
    provider_trace: dict[str, Any] = {}
    provider_error: dict[str, Any] = {}
    provider_invoked = True
    try:
        provider_result, provider_trace = asyncio.run(_invoke_provider(provider))
    except Exception as exc:
        provider_error = {"type": type(exc).__name__, "message": str(exc)[:300]}
    output_guard = (
        {"status": "not_run", "blockers": []}
        if provider_error
        else ce_grokfast_output_guard(provider_result)
    )
    blockers = list(output_guard["blockers"])
    status = "provider_error" if provider_error else "blocked" if blockers else "pass"
    artifact = {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": status,
        "provider_mode": provider_mode,
        "provider_profile_id": provider_profile_id,
        "diagnostic_evidence_class": "live_grokfast" if live_invoked else "fake_contract",
        "live_invoked": live_invoked,
        "provider_invoked": provider_invoked,
        "live_provider_used": live_invoked and provider_invoked,
        "live_grokfast_diagnostic_pass": live_invoked and status == "pass",
        "case_count": len(_live_seed_cases()),
        "provider_readiness": _mapping(provider.readiness()) if hasattr(provider, "readiness") else {},
        "provider_trace_summary": {
            "stage": str(provider_trace.get("stage") or ""),
            "provider": str(provider_trace.get("provider") or ""),
            "usage_present": isinstance(provider_trace.get("usage"), Mapping),
        },
        "provider_error": provider_error,
        "model_output_summary": _model_output_summary(provider_result),
        "output_guard": output_guard,
        "mainline_activation_enabled": False,
        "canonical_product_mutation_allowed": False,
        "scheduler_delivery_allowed": False,
        "durable_product_memory_written": False,
        "raw_user_text_semantic_inference_performed": False,
        "blockers": blockers,
    }
    if output_path is not None:
        write_json_artifact(output_path, artifact)
    return artifact


def ce_grokfast_output_guard(output: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if output.get("claim_scope") != "diagnostic_only":
        blockers.append("output.claim_scope_not_diagnostic_only")
    decisions = [_mapping(item) for item in output.get("case_decisions") or []]
    expected = {str(case["case_id"]): case for case in _live_seed_cases()}
    if {str(item.get("case_id") or "") for item in decisions} != set(expected):
        blockers.append("output.case_ids_mismatch")
    for decision in decisions:
        case_id = str(decision.get("case_id") or "")
        case = expected.get(case_id)
        if not case:
            continue
        blockers.extend(_decision_blockers(case, decision))
    return {"status": "blocked" if blockers else "pass", "blockers": blockers}


async def _invoke_provider(provider: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    result, trace = await provider.complete_with_trace(
        system_prompt=SYSTEM_PROMPT,
        user_payload={
            "diagnostic_task": "advanced_product_lab_context_engineering_live_seed_planning",
            "cases": [_case_payload(case) for case in _live_seed_cases()],
            "output_contract": {
                "claim_scope": "diagnostic_only",
                "required_fields": ["claim_scope", "case_decisions"],
                "per_case_fields": [
                    "case_id",
                    "selected_capabilities",
                    "tool_call_order",
                    "action_request",
                    "delivery_request",
                    "mutation_request",
                    "risk_notes",
                ],
            },
        },
        stage=STAGE,
        max_tokens=900,
    )
    return _mapping(result), _mapping(trace)


def _decision_blockers(case: Mapping[str, Any], decision: Mapping[str, Any]) -> list[str]:
    case_id = str(case["case_id"])
    selected = [str(item) for item in decision.get("selected_capabilities") or []]
    required = [str(item) for item in case.get("expected_capabilities") or []]
    forbidden = {str(item) for item in case.get("forbidden_capabilities") or []}
    blockers = [
        f"case:{case_id}.required_capability_missing:{capability}"
        for capability in required
        if capability not in selected
    ]
    blockers.extend(
        f"case:{case_id}.forbidden_capability_invoked:{capability}"
        for capability in selected
        if capability in forbidden
    )
    for field in ("action_request", "delivery_request", "mutation_request"):
        if decision.get(field) is True:
            blockers.append(f"case:{case_id}.{field}")
    return blockers


def _live_seed_cases() -> list[Mapping[str, Any]]:
    return [
        case
        for case in load_context_engineering_golden_set()["cases"]
        if case.get("split") == "live_diagnostic_seed"
    ]


def _case_payload(case: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "case_id": str(case["case_id"]),
        "expected_primary_workflow": str(case["expected_primary_workflow"]),
        "expected_capabilities": [str(item) for item in case["expected_capabilities"]],
        "forbidden_capabilities": [str(item) for item in case["forbidden_capabilities"]],
        "expected_ordering_constraints": [
            str(item) for item in case["expected_ordering_constraints"]
        ],
        "mutation_posture": str(case["mutation_posture"]),
    }


def _model_output_summary(output: Mapping[str, Any]) -> dict[str, Any]:
    decisions = [_mapping(item) for item in output.get("case_decisions") or []]
    return {
        "claim_scope": str(output.get("claim_scope") or ""),
        "case_decision_count": len(decisions),
        "case_ids": [str(item.get("case_id") or "") for item in decisions],
    }


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


__all__ = [
    "ARTIFACT_TYPE",
    "ce_grokfast_output_guard",
    "run_context_engineering_grokfast_diagnostic",
]
