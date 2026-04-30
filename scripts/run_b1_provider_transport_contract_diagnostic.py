from __future__ import annotations

import argparse
import asyncio
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.providers.builderspace_adapter import BuilderSpaceAdapter, BuilderSpaceResponseError
from app.providers.builderspace_runtime_contract import manager_loop_schema, response_schema_for_stage
from app.providers.builderspace_transport import (
    DECISION_TRANSPORT_TOOL_NAME,
    decision_transport_request_for_stage,
    response_format_request_for_stage,
)
from app.runtime.agent.manager_branch_contract import manager_pass1_decision_tool_arguments_schema_for_constraints
from app.runtime.contracts.trace import MANAGER_LOOP_STAGE
from app.shared.contracts.readiness_claim import build_readiness_claim
from scripts.run_wave1_phase_b_minimal_tool_loop_smoke import (
    AVAILABLE_READ_TOOLS,
    CORE_SMOKE_CASE_MAP,
    FORCED_MODE,
    SINGLE_MANAGER_SYSTEM_PROMPT,
    _phase_b1_case_family_for_message,
    _pass_1_task_payload,
)


ARTIFACT_PATH = ROOT / "artifacts" / "b1_provider_transport_contract_diagnostic.json"
CANARY_CASE_IDS = ("B1-001", "B1-002", "B1-004")
DEFAULT_TRANSPORTS = ("json_schema", "tool_choice", "json_object")
DEFAULT_PROFILES = ("builderspace-deepseek-default", "builderspace-grok-4-fast-b1-transport-probe")
CANONICAL_READ_TOOLS = tuple(AVAILABLE_READ_TOOLS)


@dataclass(frozen=True)
class ProviderProfile:
    profile_id: str
    model: str
    provider: str = "builderspace"
    role: str = "transport_contract_probe"
    production_selected: bool = False


PROFILES: dict[str, ProviderProfile] = {
    "builderspace-deepseek-default": ProviderProfile(
        profile_id="builderspace-deepseek-default",
        model="deepseek",
        role="default_build_loop_transport_probe",
    ),
    "builderspace-grok-4-fast-b1-transport-probe": ProviderProfile(
        profile_id="builderspace-grok-4-fast-b1-transport-probe",
        model="grok-4-fast",
        role="low_cost_transport_probe",
    ),
}


class _TransportDiagnosticAdapter(BuilderSpaceAdapter):
    def __init__(self, *, transport_mode: str, manager_model_override: str) -> None:
        super().__init__(manager_model_override=manager_model_override)
        self.transport_mode = transport_mode

    def _response_format_request_for_stage(
        self,
        stage: str,
        constraints: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if self.transport_mode == "json_schema":
            return response_format_request_for_stage(
                stage,
                constraints=constraints,
                schema=response_schema_for_stage(stage, constraints),
            )
        return (
            {"type": "json_object"},
            {
                "structured_output_transport_attempted": False,
                "structured_output_transport_mode": "json_object",
                "structured_output_transport_accepted": False,
                "structured_output_transport_fallback": None,
                "fallback_reason": None,
                "structured_output_transport_constraint_snapshot": _constraint_snapshot(constraints),
            },
        )

    def _decision_transport_request_for_stage(
        self,
        stage: str,
        constraints: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        if self.transport_mode != "tool_choice":
            return _no_decision_transport_meta(constraints)
        if stage != MANAGER_LOOP_STAGE:
            return _no_decision_transport_meta(constraints)
        schema = manager_pass1_decision_tool_arguments_schema_for_constraints(
            manager_loop_schema(constraints),
            constraints,
        )
        return (
            {
                "mode": "tool_call_decision_transport",
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": DECISION_TRANSPORT_TOOL_NAME,
                            "description": "Return the manager call-tools decision as structured arguments.",
                            "parameters": schema,
                        },
                    }
                ],
                "tool_choice": {
                    "type": "function",
                    "function": {"name": DECISION_TRANSPORT_TOOL_NAME},
                },
            },
            {
                "decision_transport_attempted": True,
                "decision_transport_mode": "tool_call_decision_transport",
                "decision_transport_accepted": False,
                "decision_transport_fallback": None,
                "decision_transport_fallback_reason": None,
                "decision_transport_contract_breach": False,
                "decision_transport_constraint_snapshot": _constraint_snapshot(constraints),
            },
        )


def classify_transport_case_result(raw_result: dict[str, Any]) -> dict[str, Any]:
    result = dict(raw_result)
    trace = result.get("trace") if isinstance(result.get("trace"), dict) else {}
    parsed = result.get("parsed_object") if isinstance(result.get("parsed_object"), dict) else trace.get("parsed_object")
    if not isinstance(parsed, dict):
        parsed = {}
    tool_names = _tool_names(parsed)
    unsupported_tool_names = [name for name in tool_names if name not in CANONICAL_READ_TOOLS]
    transport_mode = str(result.get("transport_mode") or "")
    failure_family = result.get("failure_family") or _transport_failure_family(
        status=str(result.get("status") or ""),
        transport_mode=transport_mode,
        trace=trace,
        unsupported_tool_names=unsupported_tool_names,
    )
    request_payload = trace.get("request_payload") if isinstance(trace.get("request_payload"), dict) else {}
    response_format = request_payload.get("response_format") if isinstance(request_payload.get("response_format"), dict) else {}
    result.update(
        {
            "failure_family": failure_family,
            "provider_accepted_transport": _provider_accepted_transport(transport_mode=transport_mode, trace=trace, status=result.get("status")),
            "canonical_tool_enum_enforced": not unsupported_tool_names,
            "unsupported_tool_names": unsupported_tool_names,
            "parsed_tool_names": tool_names,
            "alias_normalized": False,
            "raw_response_excerpt": trace.get("raw_response_excerpt"),
            "response_status": trace.get("response_status"),
            "requested_response_format_type": response_format.get("type"),
            "schema_name": (response_format.get("json_schema") or {}).get("name") if isinstance(response_format.get("json_schema"), dict) else None,
            "requested_tool_choice": request_payload.get("tool_choice"),
            "trace": _compact_trace(trace),
        }
    )
    return _json_safe(result)


def build_transport_contract_artifact(
    *,
    results: list[dict[str, Any]],
    generated_at_utc: str,
) -> dict[str, Any]:
    classified_results = [classify_transport_case_result(result) for result in results]
    failure_families = sorted({str(result.get("failure_family")) for result in classified_results if result.get("failure_family")})
    artifact = {
        "artifact_type": "b1_provider_transport_contract_diagnostic",
        "generated_at_utc": generated_at_utc,
        "current_mainline": "Wave 1 Manager-style Agent B1/B2 re-entry",
        "scope": "b1_provider_transport_contract_diagnostic",
        "provider": "builderspace",
        "live_llm_invoked": True,
        "tavily_live_invoked": False,
        "readiness_claimed": False,
        "not_b1_readiness_evidence": True,
        "semantic_owner": "manager_llm_structured_output",
        "deterministic_role": "validation_and_rejection_only",
        "runner_inferred_semantics": False,
        "alias_normalization_allowed": False,
        "best_practice_sources": [
            "https://platform.openai.com/docs/guides/function-calling",
            "https://platform.openai.com/docs/guides/structured-outputs",
        ],
        "cases": classified_results,
        "summary": {
            "case_count": len(classified_results),
            "pass_count": sum(1 for result in classified_results if not result.get("failure_family")),
            "fail_count": sum(1 for result in classified_results if result.get("failure_family")),
            "failure_families": failure_families,
            "viable_transport_profiles": _viable_transport_profiles(classified_results),
        },
        "readiness_claim": build_readiness_claim(
            claim_scope="live_diagnostic",
            activation_stage="live_diagnostic",
            semantic_authority_source="live_manager_structured_output",
            producer_honesty={
                "runner_inferred_semantics": False,
                "fake_provider_simulated_manager": False,
                "final_mapping_fabricated": False,
                "mutation_fabricated": False,
                "readiness_overclaim_prevented": True,
            },
            evidence_lineage={
                "artifacts": ["artifacts/b1_provider_transport_contract_diagnostic.json"],
                "producers": ["scripts/run_b1_provider_transport_contract_diagnostic.py"],
                "not_b1_readiness_evidence": True,
            },
            allowed_next_stage=None,
            forbidden_claims=["b1_ready", "b2_ready", "product_ready", "mutation_ready"],
            readiness_claimed=False,
        ),
    }
    return _json_safe(artifact)


async def run_transport_contract_diagnostic(
    *,
    case_ids: list[str],
    transport_modes: list[str],
    profile_ids: list[str],
    output_path: Path,
    write_latest: bool = True,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for case_id in case_ids:
        for profile_id in profile_ids:
            for transport_mode in transport_modes:
                results.append(
                    await _run_single_probe(
                        case_id=case_id,
                        profile=PROFILES[profile_id],
                        transport_mode=transport_mode,
                    )
                )
    artifact = build_transport_contract_artifact(
        results=results,
        generated_at_utc=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    specific_path = _specific_artifact_path(output_path)
    specific_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    artifact["artifact_path"] = _project_relative(specific_path)
    specific_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    if write_latest:
        output_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    return artifact


async def _run_single_probe(
    *,
    case_id: str,
    profile: ProviderProfile,
    transport_mode: str,
) -> dict[str, Any]:
    message = str(CORE_SMOKE_CASE_MAP[case_id])
    case_family = _phase_b1_case_family_for_message(message)
    task_payload_id, task_payload = _pass_1_task_payload(FORCED_MODE, case_family=case_family)
    constraints = {
        "phase_b1_manager_role": "pass_1_tool_request",
        "phase_b1_pass1_mode": FORCED_MODE,
        "phase_b1_case_family": case_family,
        "phase_b1_case_id": case_id,
        "phase_b1_task_payload_id": task_payload_id,
    }
    adapter = _TransportDiagnosticAdapter(
        transport_mode=transport_mode,
        manager_model_override=profile.model,
    )
    raw_result: dict[str, Any] = {
        "case_id": case_id,
        "input_message": message,
        "case_family": case_family,
        "transport_mode": transport_mode,
        "profile_id": profile.profile_id,
        "profile_role": profile.role,
        "provider": profile.provider,
        "model": profile.model,
        "production_selected": profile.production_selected,
        "status": "not_run",
    }
    try:
        parsed, trace = await adapter.complete_with_trace(
            system_prompt=f"{task_payload}\n\n{SINGLE_MANAGER_SYSTEM_PROMPT}",
            user_payload={
                "raw_user_input": message,
                "round_index": 0,
                "available_read_tools": list(CANONICAL_READ_TOOLS),
                "constraints": constraints,
                "transport_contract_diagnostic": True,
            },
            stage=MANAGER_LOOP_STAGE,
            max_tokens=900,
        )
        raw_result.update({"status": "success", "parsed_object": parsed, "trace": trace})
    except BuilderSpaceResponseError as exc:
        raw_result.update({"status": "error", "error": str(exc), "trace": dict(exc.trace or {})})
    except Exception as exc:
        raw_result.update(
            {
                "status": "error",
                "error": str(exc),
                "trace": {
                    "failure_family": "provider_runtime_error",
                    "error_type": type(exc).__name__,
                    "raw_response_excerpt": getattr(exc, "raw_response_excerpt", None),
                },
            }
        )
    return classify_transport_case_result(raw_result)


def _transport_failure_family(
    *,
    status: str,
    transport_mode: str,
    trace: dict[str, Any],
    unsupported_tool_names: list[str],
) -> str | None:
    trace_family = trace.get("failure_family") or trace.get("request_failure_family")
    if trace_family == "schema_transport_rejected":
        return "schema_transport_rejected"
    if trace_family == "tool_choice_rejected":
        return "tool_choice_rejected"
    if trace_family == "tool_call_transport_contract_breach":
        return "tool_choice_not_obeyed"
    if trace.get("structured_output_transport_fallback") == "json_object":
        return "schema_transport_rejected"
    if trace.get("decision_transport_fallback"):
        return "tool_choice_rejected"
    if unsupported_tool_names:
        if transport_mode == "json_schema":
            return "schema_not_enforced"
        if transport_mode == "tool_choice":
            return "tool_choice_not_obeyed"
        return "model_contract_non_adherence"
    if trace_family == "manager_output_contract_violation":
        return "model_contract_non_adherence"
    if status == "error":
        return str(trace_family or "provider_runtime_error")
    return None


def _provider_accepted_transport(*, transport_mode: str, trace: dict[str, Any], status: Any) -> bool:
    if transport_mode == "json_schema":
        return bool(trace.get("structured_output_transport_accepted")) and status == "success"
    if transport_mode == "tool_choice":
        return bool(trace.get("decision_transport_accepted")) and not trace.get("decision_transport_fallback")
    if transport_mode == "json_object":
        return status == "success"
    return False


def _tool_names(parsed: dict[str, Any]) -> list[str]:
    tool_calls = parsed.get("tool_calls")
    if not isinstance(tool_calls, list):
        return []
    names: list[str] = []
    for item in tool_calls:
        if isinstance(item, dict) and isinstance(item.get("name"), str):
            names.append(str(item["name"]))
    return names


def _viable_transport_profiles(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        grouped[(str(result.get("profile_id")), str(result.get("transport_mode")))].append(result)
    viable: list[dict[str, Any]] = []
    for (profile_id, transport_mode), group in sorted(grouped.items()):
        if group and all(not item.get("failure_family") and item.get("canonical_tool_enum_enforced") is True for item in group):
            viable.append(
                {
                    "profile_id": profile_id,
                    "transport_mode": transport_mode,
                    "case_ids": [str(item.get("case_id")) for item in group],
                }
            )
    return viable


def _constraint_snapshot(constraints: dict[str, Any] | None) -> dict[str, str]:
    return {
        "phase_b1_manager_role": str((constraints or {}).get("phase_b1_manager_role") or ""),
        "phase_b1_pass1_mode": str((constraints or {}).get("phase_b1_pass1_mode") or ""),
        "phase_b1_case_family": str((constraints or {}).get("phase_b1_case_family") or ""),
    }


def _no_decision_transport_meta(constraints: dict[str, Any] | None) -> tuple[None, dict[str, Any]]:
    return (
        None,
        {
            "decision_transport_attempted": False,
            "decision_transport_mode": None,
            "decision_transport_accepted": False,
            "decision_transport_fallback": None,
            "decision_transport_fallback_reason": None,
            "decision_transport_contract_breach": False,
            "decision_transport_constraint_snapshot": _constraint_snapshot(constraints),
        },
    )


def _compact_trace(trace: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "provider",
        "model",
        "response_status",
        "failure_family",
        "request_failure_family",
        "failing_component",
        "structured_output_transport_attempted",
        "structured_output_transport_mode",
        "structured_output_transport_accepted",
        "structured_output_transport_fallback",
        "fallback_reason",
        "effective_response_format_type",
        "decision_transport_attempted",
        "decision_transport_mode",
        "decision_transport_accepted",
        "decision_transport_fallback",
        "decision_transport_fallback_reason",
        "decision_transport_contract_breach",
        "raw_response_excerpt",
        "raw_content_excerpt",
        "transport_attempts",
        "parse_attempts",
        "request_payload",
    )
    return {key: _json_safe(trace.get(key)) for key in keys if key in trace}


def _specific_artifact_path(output_path: Path) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    return output_path.with_name(f"{output_path.stem}_{timestamp}_{uuid4().hex[:6]}{output_path.suffix}")


def _project_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _parse_csv(value: str | None, *, default: tuple[str, ...]) -> list[str]:
    if not value:
        return list(default)
    return [item.strip() for item in value.split(",") if item.strip()]


async def _async_main() -> int:
    parser = argparse.ArgumentParser(description="Run the B1 BuilderSpace provider transport contract diagnostic.")
    parser.add_argument("--cases", default=",".join(CANARY_CASE_IDS), help="Comma-separated B1 case IDs.")
    parser.add_argument("--transports", default=",".join(DEFAULT_TRANSPORTS), help="Comma-separated transport modes.")
    parser.add_argument("--profiles", default=",".join(DEFAULT_PROFILES), help="Comma-separated provider profile IDs.")
    parser.add_argument("--output-path", default=str(ARTIFACT_PATH), help="Latest artifact output path.")
    parser.add_argument("--no-latest", action="store_true", help="Only write the timestamped artifact.")
    args = parser.parse_args()

    case_ids = _parse_csv(args.cases, default=CANARY_CASE_IDS)
    transport_modes = _parse_csv(args.transports, default=DEFAULT_TRANSPORTS)
    profile_ids = _parse_csv(args.profiles, default=DEFAULT_PROFILES)
    unknown_cases = [case_id for case_id in case_ids if case_id not in CORE_SMOKE_CASE_MAP]
    unknown_transports = [mode for mode in transport_modes if mode not in DEFAULT_TRANSPORTS]
    unknown_profiles = [profile_id for profile_id in profile_ids if profile_id not in PROFILES]
    if unknown_cases or unknown_transports or unknown_profiles:
        raise SystemExit(
            json.dumps(
                {
                    "unknown_cases": unknown_cases,
                    "unknown_transports": unknown_transports,
                    "unknown_profiles": unknown_profiles,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    artifact = await run_transport_contract_diagnostic(
        case_ids=case_ids,
        transport_modes=transport_modes,
        profile_ids=profile_ids,
        output_path=Path(args.output_path),
        write_latest=not args.no_latest,
    )
    print(
        json.dumps(
            {
                "artifact_path": artifact.get("artifact_path"),
                "case_count": artifact["summary"]["case_count"],
                "failure_families": artifact["summary"]["failure_families"],
                "viable_transport_profiles": artifact["summary"]["viable_transport_profiles"],
                "readiness_claimed": artifact["readiness_claimed"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def main() -> int:
    return asyncio.run(_async_main())


if __name__ == "__main__":
    raise SystemExit(main())
