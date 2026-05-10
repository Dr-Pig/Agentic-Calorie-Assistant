from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAG_NAMES
from app.advanced_shadow_lab.llm_node_input import (
    build_recommendation_offer_synthesis_node_input,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract("advanced_shadow_lab.llm_node_contract")
INPUT_TYPE = "advanced_shadow_llm_node_input_artifact"
OUTPUT_TYPE = "advanced_shadow_llm_node_diagnostic_artifact"
STAGE = "advanced_shadow_llm_node_diagnostic"
SCHEMA_ID = "advanced_shadow_llm_node_diagnostic_v1"
CLAIM_SCOPE = "advanced_shadow_llm_node_diagnostic_only"
FALSE_FLAGS = {
    **dict.fromkeys(FALSE_FLAG_NAMES, False),
    "runtime_connected": False,
    "runtime_truth_changed": False,
    "production_selected": False,
}
NON_CLAIMS = [
    "not_runtime_activation_evidence", "not_product_readiness_evidence",
    "not_user_facing_activation", "not_scheduler_delivery",
    "not_canonical_mutation_authority", "not_live_provider_activation",
    "not_kimi_activation",
]
SYSTEM_PROMPT = (
    "Return JSON for an advanced shadow-lab LLM node diagnostic only. Do not claim "
    "the offer was served, delivered, saved, committed, scheduled, or used as truth."
)


def run_advanced_shadow_llm_node(
    *,
    node_input: Mapping[str, Any],
    provider: Any,
    provider_profile: Mapping[str, Any],
    provider_mode: str,
    live_invoked: bool,
    output_path: Path | None = None,
) -> dict[str, Any]:
    blockers = _input_blockers(node_input) + _profile_blockers(provider_profile)
    provider_invoked = False
    output: dict[str, Any] = {}
    trace: dict[str, Any] = {}
    if not blockers:
        provider_invoked = True
        output, trace = asyncio.run(_invoke_provider(provider, node_input))
    guard = {"status": "not_run", "blockers": []} if blockers else _output_guard(output)
    blockers.extend(guard["blockers"])
    artifact = _artifact(
        status="pass" if not blockers else "blocked",
        blockers=blockers,
        node_input=node_input,
        provider_profile=provider_profile,
        provider_mode=provider_mode,
        live_invoked=live_invoked,
        provider_invoked=provider_invoked,
        output=output,
        trace=trace,
        output_guard=guard,
    )
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    return artifact


def blocked_llm_node_artifact(
    *, reason: str, provider_profile_id: str, output_path: Path | None = None
) -> dict[str, Any]:
    artifact = _artifact(
        status="blocked",
        blockers=[reason],
        node_input={},
        provider_profile={"provider_profile_id": provider_profile_id},
        provider_mode="not_invoked",
        live_invoked=False,
        provider_invoked=False,
        output={},
        trace={},
        output_guard={"status": "not_run", "blockers": []},
    )
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    return artifact


async def _invoke_provider(provider: Any, node_input: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    output, trace = await provider.complete_with_trace(
        system_prompt=SYSTEM_PROMPT,
        user_payload=dict(_mapping(node_input.get("provider_payload"))),
        stage=STAGE,
        max_tokens=500,
    )
    return dict(_mapping(output)), dict(_mapping(trace))


def _artifact(**kwargs: Any) -> dict[str, Any]:
    node_input = _mapping(kwargs["node_input"])
    profile = _mapping(kwargs["provider_profile"])
    return {
        "artifact_type": OUTPUT_TYPE,
        "artifact_schema_version": "1.0",
        "status": kwargs["status"],
        "owner": "app/advanced_shadow_lab/llm_node_contract.py",
        "consumer": "future_advanced_shadow_lab_llm_node_live_diagnostic",
        "retirement_trigger": "approved_advanced_runtime_activation_plan",
        "node_id": str(node_input.get("node_id") or ""),
        "node_role": str(node_input.get("node_role") or ""),
        "structured_output_schema_id": SCHEMA_ID,
        "provider_profile_id": str(profile.get("provider_profile_id") or ""),
        "provider_family": str(profile.get("provider_family") or ""),
        "model_id": str(profile.get("model_id") or ""),
        "provider_mode": kwargs["provider_mode"],
        "live_invoked": bool(kwargs["live_invoked"]),
        "provider_invoked": bool(kwargs["provider_invoked"]),
        "live_provider_used": bool(kwargs["live_invoked"] and kwargs["provider_invoked"]),
        "provider_trace_summary": _trace_summary(_mapping(kwargs["trace"])),
        "model_output_summary": _model_output_summary(_mapping(kwargs["output"])),
        "output_guard": kwargs["output_guard"],
        "blockers": kwargs["blockers"],
        "non_claims": list(NON_CLAIMS),
        **dict(FALSE_FLAGS),
    }

def _input_blockers(node_input: Mapping[str, Any]) -> list[str]:
    blockers = []
    if node_input.get("artifact_type") != INPUT_TYPE:
        blockers.append("node_input.unsupported_artifact_type")
    if node_input.get("status") != "pass":
        blockers.append("node_input.status_not_pass")
    return blockers + [f"node_input.{b}" for b in node_input.get("blockers") or []]


def _profile_blockers(profile: Mapping[str, Any]) -> list[str]:
    blockers = []
    for flag in ("production_selected", "provider_specific_product_semantics_allowed", "kimi_live_calls_allowed"):
        if profile.get(flag) is True:
            blockers.append(f"profile.{flag}")
    return blockers


def _output_guard(output: Mapping[str, Any]) -> dict[str, Any]:
    blockers = []
    if output.get("claim_scope") != CLAIM_SCOPE:
        blockers.append("model_output.claim_scope_not_diagnostic")
    for key in ("action_request", "delivery_request", "mutation_request"):
        if output.get(key) is True:
            blockers.append(f"model_output.{key}_not_allowed")
    return {"status": "blocked" if blockers else "pass", "blockers": blockers}


def _model_output_summary(output: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "node_output_id": str(output.get("node_output_id") or ""),
        "selected_candidate_id": str(output.get("selected_candidate_id") or ""),
        "draft_text_present": bool(str(output.get("draft_text") or "").strip()),
        "rationale_present": bool(str(output.get("rationale") or "").strip()),
        "reason_codes": [str(item) for item in output.get("reason_codes") or []],
        "claim_scope": str(output.get("claim_scope") or ""),
    }


def _trace_summary(trace: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "stage": str(trace.get("stage") or ""),
        "provider": str(trace.get("provider") or ""),
        "usage_present": isinstance(trace.get("usage"), Mapping),
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "blocked_llm_node_artifact", "build_recommendation_offer_synthesis_node_input", "run_advanced_shadow_llm_node"]
