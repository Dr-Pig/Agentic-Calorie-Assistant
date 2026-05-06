from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from app.composition.accurate_intake_context_live_provider_input_preflight import (
    build_context_live_provider_input_preflight_artifact,
)
from app.composition.accurate_intake_context_live_response_contract_dry_run import (
    build_context_live_response_contract_dry_run_artifact,
)
from app.shared.contracts.readiness_claim import build_readiness_claim


DEFAULT_CONTEXT_LIVE_PROVIDER_PROFILE_ID = (
    "builderspace-grok-4-fast-accurate-intake-context-live-diagnostic"
)
DEFAULT_CONTEXT_LIVE_MODEL = "grok-4-fast"
DEFAULT_BASE_URL = "https://space.ai-builders.com/backend/v1"

_FORBIDDEN_CLAIMS = (
    "product_ready",
    "self_use_ready",
    "private_self_use_approved",
    "live_ready",
    "user_facing_ready",
    "mutation_ready",
    "production_ready",
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _case_id(row: dict[str, Any]) -> str:
    return str(row.get("case_id") or "")


def provider_profile(
    provider_profile_id: str = DEFAULT_CONTEXT_LIVE_PROVIDER_PROFILE_ID,
) -> dict[str, Any]:
    if provider_profile_id != DEFAULT_CONTEXT_LIVE_PROVIDER_PROFILE_ID:
        raise ValueError(
            "Unsupported context live diagnostic provider profile: "
            f"{provider_profile_id}. Supported: {DEFAULT_CONTEXT_LIVE_PROVIDER_PROFILE_ID}"
        )
    return {
        "provider_profile_id": provider_profile_id,
        "provider": "builderspace",
        "model": DEFAULT_CONTEXT_LIVE_MODEL,
        "provider_profile_role": "accurate_intake_context_live_diagnostic",
        "cost_tier": "low",
        "production_selected": False,
        "not_production_selection": True,
        "readiness_owner": False,
        "temperature": 0.0,
        "max_tokens": 900,
        "schema_mode": "json_object",
    }


def build_missing_token_report(
    *,
    context_live_provider_input_preflight: dict[str, Any] | None = None,
    provider_profile_id: str = DEFAULT_CONTEXT_LIVE_PROVIDER_PROFILE_ID,
) -> dict[str, Any]:
    preflight = _dict(
        context_live_provider_input_preflight
        or build_context_live_provider_input_preflight_artifact()
    )
    profile = provider_profile(provider_profile_id)
    return _report_shell(
        profile=profile,
        provider_mode="not_invoked",
        live_invoked=False,
        provider_inputs=_list(preflight.get("provider_inputs")),
        provider_outputs=[],
        provider_traces=[],
        response_contract={},
        blockers=["missing_provider_token"],
        failure_family="missing_provider_token",
    )


def build_provider_request_payload(provider_input: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "diagnostic_scope": "pl_ce_context_only_live_intent_probe",
        "case_id": provider_input.get("case_id"),
        "messages": provider_input.get("messages"),
        "manager_context_sidecar": provider_input.get("manager_context_sidecar"),
        "expected_semantic_contract": provider_input.get("expected_semantic_contract"),
        "response_schema": provider_input.get("response_schema"),
        "tool_policy": provider_input.get("tool_policy"),
        "trace_requirements": provider_input.get("trace_requirements"),
        "authority": {
            "semantic_owner": "live_manager_provider",
            "deterministic_layer_may_validate": True,
            "deterministic_layer_may_select_intent": False,
            "frontend_may_select_target": False,
            "mutation_authority": False,
            "fooddb_truth_authority": False,
        },
        "non_claims": {
            "fooddb_used": False,
            "web_tavily_used": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        },
    }
    return _json_safe(payload)


def build_context_live_diagnostic_canary_report(
    *,
    context_live_provider_input_preflight: dict[str, Any],
    provider_outputs: list[dict[str, Any]],
    provider_traces: list[dict[str, Any]] | None = None,
    provider_profile_id: str = DEFAULT_CONTEXT_LIVE_PROVIDER_PROFILE_ID,
    live_invoked: bool,
) -> dict[str, Any]:
    preflight = _dict(context_live_provider_input_preflight)
    profile = provider_profile(provider_profile_id)
    response_contract = build_context_live_response_contract_dry_run_artifact(
        context_live_provider_input_preflight=preflight,
        fixture_responses=provider_outputs,
        require_full_matrix=False,
    )
    blockers = []
    if preflight.get("status") != "pass":
        blockers.append("provider_input_preflight_not_pass")
    if response_contract.get("status") != "pass":
        blockers.append("provider_response_contract_not_pass")
    for output in provider_outputs:
        case_id = _case_id(_dict(output)) or "unknown_case"
        mutation_request = _dict(_dict(output).get("mutation_request"))
        if mutation_request.get("requested") is True:
            blockers.append(f"{case_id}.mutation_requested")
        for flag in (
            "fooddb_used",
            "web_tavily_used",
            "runtime_truth_changed",
            "mutation_changed",
            "manager_context_packet_schema_changed",
            "product_readiness_claimed",
            "private_self_use_approved",
        ):
            if _dict(output).get(flag) is True:
                blockers.append(f"{case_id}.{flag}")
    blockers.extend(str(item) for item in _list(response_contract.get("blockers")))
    blockers = list(dict.fromkeys(blockers))
    return _report_shell(
        profile=profile,
        provider_mode="live" if live_invoked else "fixture",
        live_invoked=live_invoked,
        provider_inputs=_list(preflight.get("provider_inputs")),
        provider_outputs=provider_outputs,
        provider_traces=provider_traces or [],
        response_contract=response_contract,
        blockers=blockers,
        failure_family=None if not blockers else "context_live_response_contract_blocked",
    )


def _report_shell(
    *,
    profile: dict[str, Any],
    provider_mode: str,
    live_invoked: bool,
    provider_inputs: list[Any],
    provider_outputs: list[dict[str, Any]],
    provider_traces: list[dict[str, Any]],
    response_contract: dict[str, Any],
    blockers: list[str],
    failure_family: str | None,
) -> dict[str, Any]:
    status = "live_diagnostic_pass" if live_invoked and not blockers else "blocked"
    if provider_mode == "not_invoked":
        status = "not_invoked"
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_live_diagnostic_canary",
            "status": status,
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "claim_scope": "pl_ce_context_only_live_diagnostic",
            "diagnostic_only": True,
            "provider_mode": provider_mode,
            "live_invoked": live_invoked,
            "live_llm_invoked": live_invoked,
            "live_provider_invoked": live_invoked,
            "provider_profile_id": profile["provider_profile_id"],
            "provider_profile_model": profile["model"],
            "provider_profile_role": profile["provider_profile_role"],
            "provider_schema_mode": profile["schema_mode"],
            "semantic_owner": "live_manager_provider" if live_invoked else "not_invoked",
            "deterministic_role": "validate_provider_response_contract_not_select_intent",
            "deterministic_selected_intent": False,
            "deterministic_selected_target": False,
            "raw_text_intent_router_used": False,
            "fooddb_used": False,
            "web_tavily_used": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "shared_contract_changed": False,
            "production_db_used": False,
            "user_facing_rollout": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "production_selected": False,
            "not_production_selection": True,
            "readiness_claimed": False,
            "readiness_claim": build_readiness_claim(
                claim_scope="live_diagnostic" if live_invoked else "unit_contract",
                activation_stage="live_diagnostic" if live_invoked else "contract",
                semantic_authority_source=(
                    "live_manager_structured_output" if live_invoked else "none"
                ),
                producer_honesty={
                    "runner_inferred_semantics": False,
                    "fake_provider_simulated_manager": not live_invoked,
                    "final_mapping_fabricated": False,
                    "mutation_fabricated": False,
                },
                evidence_lineage={
                    "artifacts": [],
                    "producers": [
                        "scripts/run_accurate_intake_context_live_diagnostic_canary.py"
                    ],
                    "live_invoked": live_invoked,
                    "legacy_oracle_used": False,
                },
                allowed_next_stage=None,
                forbidden_claims=_FORBIDDEN_CLAIMS,
                readiness_claimed=False,
            ),
            "blockers": blockers,
            "failure_family": failure_family,
            "summary": {
                "provider_input_count": len(provider_inputs),
                "provider_output_count": len(provider_outputs),
                "provider_trace_count": len(provider_traces),
                "validated_response_count": _dict(response_contract.get("summary")).get(
                    "validated_response_count", 0
                ),
                "blocked_response_count": _dict(response_contract.get("summary")).get(
                    "blocked_response_count", 0
                ),
                "target_candidate_response_count": _dict(response_contract.get("summary")).get(
                    "target_candidate_response_count", 0
                ),
                "ambiguity_preserved_response_count": _dict(response_contract.get("summary")).get(
                    "ambiguity_preserved_response_count", 0
                ),
            },
            "response_contract_status": response_contract.get("status", "not_available"),
            "response_contract_blockers": _list(response_contract.get("blockers")),
            "provider_traces": provider_traces,
            "provider_outputs": provider_outputs,
        }
    )


__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_CONTEXT_LIVE_MODEL",
    "DEFAULT_CONTEXT_LIVE_PROVIDER_PROFILE_ID",
    "build_context_live_diagnostic_canary_report",
    "build_missing_token_report",
    "build_provider_request_payload",
    "provider_profile",
]
