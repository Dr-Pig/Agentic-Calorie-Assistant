from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass, replace
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import run_wave1_phase_b_minimal_tool_loop_smoke as smoke


DEFAULT_OUTPUT_DIR = ROOT / "artifacts"
LATEST_REPORT = DEFAULT_OUTPUT_DIR / "manager_candidate_eval.json"
MANAGER_CANDIDATE_EVAL_SCOPE = "manager_candidate_eval"
MANAGER_CANDIDATE_EVAL_DIMENSIONS = [
    "tool_call_decision_obedience",
    "pass1_pass2_boundary_obedience",
    "multi_context_state_handling",
    "memory_summarization_posture",
    "no_fake_semantic_green",
]
ALLOWED_CANDIDATE_PROFILES = {
    "builderspace-kimi-k2.5-candidate",
    "builderspace-gemini-3-flash-preview-candidate",
}


@dataclass(frozen=True)
class _ManagerCandidateEvalCase:
    case_id: str
    input_message: str
    dimension: str
    expected_item_results: int
    clarification_only: bool = False
    notes: str = ""


MANAGER_CANDIDATE_EVAL_CASES: dict[str, _ManagerCandidateEvalCase] = {
    "MC-001": _ManagerCandidateEvalCase(
        case_id="MC-001",
        input_message=str(smoke.CORE_SMOKE_CASE_MAP["B1-003"]),
        dimension="tool_call_decision_obedience",
        expected_item_results=1,
        notes="B1-003-style common commercial meal probe for synthetic tool-call decision obedience.",
    ),
    "MC-002": _ManagerCandidateEvalCase(
        case_id="MC-002",
        input_message=str(smoke.CORE_SMOKE_CASE_MAP["B1-001"]),
        dimension="pass1_pass2_boundary_obedience",
        expected_item_results=1,
        notes="Simple common food case for Pass 1 tool request and Pass 2 synthesis boundary integrity.",
    ),
    "MC-003": _ManagerCandidateEvalCase(
        case_id="MC-003",
        input_message=str(smoke.CORE_SMOKE_CASE_MAP["B1-005"]),
        dimension="multi_context_state_handling",
        expected_item_results=3,
        notes="Listed-ingredient proxy for compact multi-item evidence state handling.",
    ),
    "MC-004": _ManagerCandidateEvalCase(
        case_id="MC-004",
        input_message=str(smoke.CORE_SMOKE_CASE_MAP["B1-004"]),
        dimension="memory_summarization_posture",
        expected_item_results=0,
        clarification_only=True,
        notes="Insufficient-composition honesty proxy; must not fake a green estimate or mutation.",
    ),
}


def _resolve_eval_case_ids(case_ids: list[str] | None) -> list[str]:
    if not case_ids:
        return list(MANAGER_CANDIDATE_EVAL_CASES)
    resolved = []
    seen: set[str] = set()
    for raw in case_ids:
        case_id = str(raw).upper()
        if case_id not in MANAGER_CANDIDATE_EVAL_CASES:
            supported = ", ".join(MANAGER_CANDIDATE_EVAL_CASES)
            raise ValueError(f"Unsupported manager candidate eval case_id: {case_id}. Supported: {supported}")
        if case_id not in seen:
            seen.add(case_id)
            resolved.append(case_id)
    return resolved


def _candidate_profile(profile_id: str) -> smoke._PhaseB1ProviderProfile:
    if profile_id not in ALLOWED_CANDIDATE_PROFILES:
        supported = ", ".join(sorted(ALLOWED_CANDIDATE_PROFILES))
        raise ValueError(f"Unsupported manager candidate profile: {profile_id}. Supported: {supported}")
    profile = smoke._phase_b1_provider_profile(profile_id)
    return replace(profile, branch_scope=None, manager_role_scope=None)


def _artifact_path(*, output_dir: Path, candidate_model: str, case_ids: list[str]) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    suffix = uuid4().hex[:6]
    model_slug = candidate_model.replace(".", "-")
    case_slug = "-".join(case_ids)
    return output_dir / f"manager_candidate_eval_{timestamp}_{model_slug}_{case_slug}_{suffix}.json"


def _usage_summary(trace: dict[str, Any]) -> dict[str, int | None]:
    def _extract_usage(pass_name: str) -> dict[str, int | None] | None:
        payload = trace.get(pass_name)
        if not isinstance(payload, dict):
            return None
        usage = payload.get("usage")
        if not isinstance(usage, dict):
            return None
        return {
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
        }

    pass1 = _extract_usage("manager_pass_1")
    pass2 = _extract_usage("manager_pass_2")
    if pass1 or pass2:
        prompt_tokens = sum(int(item.get("prompt_tokens") or 0) for item in (pass1, pass2) if item)
        completion_tokens = sum(int(item.get("completion_tokens") or 0) for item in (pass1, pass2) if item)
        total_tokens = sum(int(item.get("total_tokens") or 0) for item in (pass1, pass2) if item)
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }
    return {
        "prompt_tokens": None,
        "completion_tokens": None,
        "total_tokens": None,
    }


def _case_failure_family(*, case: _ManagerCandidateEvalCase, case_result: dict[str, Any], trace: dict[str, Any] | None) -> str:
    if case_result.get("case_execution_status") != "completed":
        provider_runtime = case_result.get("provider_runtime")
        if isinstance(provider_runtime, dict) and provider_runtime.get("reason"):
            return str(provider_runtime["reason"])
        runtime_blocker = case_result.get("runtime_blocker")
        if isinstance(runtime_blocker, dict) and runtime_blocker.get("reason"):
            return str(runtime_blocker["reason"])
        provider_trace_blocker = case_result.get("provider_trace_blocker")
        if isinstance(provider_trace_blocker, dict) and provider_trace_blocker.get("reason"):
            return str(provider_trace_blocker["reason"])
        return str(case_result.get("case_execution_status") or "case_execution_failed")
    if not trace:
        return "trace_missing"
    pass1 = trace.get("manager_pass_1") or {}
    pass2 = trace.get("manager_pass_2") or {}
    requested = list(pass1.get("requested_read_tools") or [])
    item_results = list(pass2.get("item_results") or [])
    if case.clarification_only:
        if requested or item_results:
            return "fake_semantic_green"
        if (pass1.get("decision_payload") or {}).get("final_action") != "request_clarification":
            return "clarification_boundary_not_obeyed"
        return "none"
    if "lookup_generic_food" not in requested:
        return "transport_not_obeyed"
    if pass1.get("payload_shape_valid") is False or pass2.get("payload_shape_valid") is False:
        return "schema_invalid"
    if pass1.get("forbidden_final_truth_fields_present") or pass2.get("forbidden_mutation_fields_present"):
        return "boundary_not_obeyed"
    if len(item_results) != case.expected_item_results:
        return "item_results_shape_mismatch"
    if case.case_id == "MC-003" and bool(trace.get("runner_derived_item_results")):
        return "runner_derived_item_results"
    return "none"


def _evaluate_case(
    *,
    case: _ManagerCandidateEvalCase,
    case_result: dict[str, Any],
    trace: dict[str, Any] | None,
) -> dict[str, Any]:
    trace_payload = trace if isinstance(trace, dict) else {}
    pass1 = trace_payload.get("manager_pass_1")
    pass2 = trace_payload.get("manager_pass_2")
    pass1 = pass1 if isinstance(pass1, dict) else {}
    pass2 = pass2 if isinstance(pass2, dict) else {}
    mutation_payload = trace_payload.get("mutation")
    mutation_payload = mutation_payload if isinstance(mutation_payload, dict) else {}
    requested = list(pass1.get("requested_read_tools") or [])
    item_results = list(pass2.get("item_results") or [])
    clarification_payload = (pass1.get("decision_payload") or {}) if isinstance(pass1.get("decision_payload"), dict) else {}

    transport_obeyed = False
    if case.clarification_only:
        transport_obeyed = clarification_payload.get("final_action") == "request_clarification" and not requested
    else:
        transport_obeyed = case_result.get("case_execution_status") == "completed" and "lookup_generic_food" in requested

    schema_valid = bool(pass1.get("payload_shape_valid") is not False and pass2.get("payload_shape_valid") is not False)
    boundary_obeyed = not bool(pass1.get("forbidden_final_truth_fields_present") or pass2.get("forbidden_mutation_fields_present"))
    if case.clarification_only:
        boundary_obeyed = boundary_obeyed and clarification_payload.get("final_action") == "request_clarification"

    context_stable: bool | None = None
    if case.case_id == "MC-003":
        context_stable = len(item_results) == case.expected_item_results and not bool(trace_payload.get("runner_derived_item_results")) and all(
            bool(item.get("evidence_used")) for item in item_results if isinstance(item, dict)
        )

    memory_posture_acceptable: bool | None = None
    if case.case_id == "MC-004":
        memory_posture_acceptable = not requested and not item_results and clarification_payload.get("final_action") == "request_clarification"

    fake_green_detected = False
    if case.clarification_only:
        fake_green_detected = bool(requested or item_results or mutation_payload.get("mutation_attempted"))
    elif mutation_payload.get("mutation_attempted") and not item_results:
        fake_green_detected = True

    semantic_honesty_preserved = not fake_green_detected
    failure_family = _case_failure_family(case=case, case_result=case_result, trace=trace)

    provider_runtime = case_result.get("provider_runtime") if isinstance(case_result.get("provider_runtime"), dict) else {}
    raw_excerpt = (
        provider_runtime.get("raw_content_excerpt")
        or provider_runtime.get("raw_response_excerpt")
        or provider_runtime.get("value_excerpt")
    )
    trace_pointer = None if trace is None else f"tool_loop_traces[{case_result.get('trace_index', 0)}]"

    return {
        "case_id": case.case_id,
        "dimension": case.dimension,
        "input_message": case.input_message,
        "notes": case.notes,
        "case_execution_status": case_result.get("case_execution_status"),
        "transport_obeyed": transport_obeyed,
        "schema_valid": schema_valid,
        "boundary_obeyed": boundary_obeyed,
        "context_stable": context_stable,
        "memory_posture_acceptable": memory_posture_acceptable,
        "semantic_honesty_preserved": semantic_honesty_preserved,
        "fake_green_detected": fake_green_detected,
        "failure_family": failure_family,
        "raw_excerpt": raw_excerpt,
        "trace_pointer": trace_pointer,
        "usage": _usage_summary(trace or {}),
        "latency_ms": case_result.get("case_latency_ms"),
    }


def _summary_from_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    failure_counts: dict[str, int] = {}
    for case in cases:
        failure = str(case.get("failure_family") or "none")
        failure_counts[failure] = failure_counts.get(failure, 0) + 1
    return {
        "selection_status": "not_decided",
        "transport_obeyed_count": sum(1 for case in cases if case.get("transport_obeyed") is True),
        "schema_valid_count": sum(1 for case in cases if case.get("schema_valid") is True),
        "boundary_obeyed_count": sum(1 for case in cases if case.get("boundary_obeyed") is True),
        "context_stable_count": sum(1 for case in cases if case.get("context_stable") is True),
        "memory_posture_acceptable_count": sum(1 for case in cases if case.get("memory_posture_acceptable") is True),
        "semantic_honesty_preserved_count": sum(1 for case in cases if case.get("semantic_honesty_preserved") is True),
        "fake_green_detected_count": sum(1 for case in cases if case.get("fake_green_detected") is True),
        "failure_family_counts": failure_counts,
    }


def _aggregate_usage(cases: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "prompt_tokens": sum(int((case.get("usage") or {}).get("prompt_tokens") or 0) for case in cases),
        "completion_tokens": sum(int((case.get("usage") or {}).get("completion_tokens") or 0) for case in cases),
        "total_tokens": sum(int((case.get("usage") or {}).get("total_tokens") or 0) for case in cases),
    }


async def run_manager_candidate_eval(
    *,
    provider: Any,
    candidate_profile_id: str,
    case_ids: list[str] | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    write_latest: bool = True,
    provider_timeout_ms: int = smoke.DEFAULT_PROVIDER_TIMEOUT_MS,
) -> dict[str, Any]:
    started_perf = smoke.time.perf_counter()
    selected_case_ids = _resolve_eval_case_ids(case_ids)
    profile = _candidate_profile(candidate_profile_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = _artifact_path(output_dir=output_dir, candidate_model=profile.model, case_ids=selected_case_ids)
    phase_b_provider = smoke._PhaseB1ManagerProvider(
        provider,
        pass1_mode=smoke.NATURAL_MODE,
        provider_timeout_ms=provider_timeout_ms,
        provider_profile=profile,
        case_set="targeted",
        requested_profile_id=candidate_profile_id,
    )
    readiness = phase_b_provider.readiness()
    traces: list[dict[str, Any]] = []
    case_reports: list[dict[str, Any]] = []

    for index, case_id in enumerate(selected_case_ids):
        case = MANAGER_CANDIDATE_EVAL_CASES[case_id]
        case_result = await smoke._run_targeted_case_with_retries(
            case_id=case.case_id,
            message=case.input_message,
            provider=phase_b_provider,
            pass1_mode=smoke.NATURAL_MODE,
            provider_timeout_ms=provider_timeout_ms,
            readiness=dict(readiness),
            max_attempts=1,
            retry_backoff_seconds=0.0,
            sleep_func=asyncio.sleep,
            jitter_func=lambda: 0.0,
        )
        trace = None
        if case_result.get("trace_present"):
            trace = smoke._json_safe(case_result["trace"])
            traces.append(trace)
            case_result["trace_index"] = len(traces) - 1
        else:
            case_result["trace_index"] = index
        case_reports.append(_evaluate_case(case=case, case_result=case_result, trace=trace))

    summary = _summary_from_cases(case_reports)
    report = {
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "scope": MANAGER_CANDIDATE_EVAL_SCOPE,
        "not_b1_readiness_evidence": True,
        "provider": readiness.get("provider") or "builderspace",
        "candidate_model": profile.model,
        "provider_profile_id": profile.profile_id,
        "provider_profile_role": profile.provider_profile_role,
        "manager_candidate_status": profile.manager_candidate_status,
        "production_selected": False,
        "selection_status": summary["selection_status"],
        "evaluation_dimensions": list(MANAGER_CANDIDATE_EVAL_DIMENSIONS),
        "cases": smoke._json_safe(case_reports),
        "summary": summary,
        "usage": _aggregate_usage(case_reports),
        "latency_ms": smoke._elapsed_ms(started_perf),
        "tool_loop_traces": smoke._json_safe(traces),
        "artifact_path": str(artifact_path),
    }
    artifact_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if write_latest:
        LATEST_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return smoke._json_safe(report)


async def _async_main() -> int:
    parser = argparse.ArgumentParser(description="Run BuilderSpace-only manager candidate eval lane.")
    parser.add_argument("--candidate-profile-id", required=True)
    parser.add_argument("--cases", default=None)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--provider-timeout-ms", type=int, default=smoke.DEFAULT_PROVIDER_TIMEOUT_MS)
    args = parser.parse_args()

    from app.runtime.interface.provider_runtime import manager_provider

    selected_case_ids = None
    if args.cases:
        selected_case_ids = [part.strip() for part in str(args.cases).split(",") if part.strip()]

    report = await run_manager_candidate_eval(
        provider=manager_provider,
        candidate_profile_id=args.candidate_profile_id,
        case_ids=selected_case_ids,
        output_dir=Path(args.output_dir),
        provider_timeout_ms=args.provider_timeout_ms,
    )
    print(
        json.dumps(
            {
                "scope": report.get("scope"),
                "candidate_model": report.get("candidate_model"),
                "artifact_path": report.get("artifact_path"),
                "case_count": len(report.get("cases") or []),
                "summary": report.get("summary"),
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
