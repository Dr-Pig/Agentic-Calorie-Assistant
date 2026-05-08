from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.v2_routes import _compute_latency_bucket  # noqa: E402
from app.intake.application.intake_turn_support import intake_turn_latency_tracking  # noqa: E402
from app.runtime.agent.manager_prompt_registry import build_manager_prompt_registry  # noqa: E402
from app.runtime.agent.manager_prompt_layer_contract import build_manager_prompt_layer_contract  # noqa: E402
from app.runtime.agent.manager_react_trace import build_manager_react_trace  # noqa: E402
from app.runtime.agent.manager_system_prompt import single_manager_system_prompt_for_scope  # noqa: E402
from app.runtime.application.request_trace_artifacts import build_internal_trace_refs, build_trace_refs  # noqa: E402
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_rt13_observability_pack.json"


class _FakeProvider:
    def readiness(self) -> dict[str, Any]:
        return {
            "provider": "fake_provider",
            "stage_models": {"intake_manager_round": "fake-model"},
        }


def _status(blockers: list[str]) -> str:
    return "pass" if not blockers else "fail"


def _evaluate_prompt_registry_case() -> dict[str, Any]:
    blockers: list[str] = []
    registry = build_manager_prompt_registry(
        provider=_FakeProvider(),
        constraints={
            "manager_contract_schema_version": "v1",
            "manager_contract_provider_profile_id": "builderspace-grok-4-fast-founder-live-contract",
            "manager_contract_provider_profile_transport_mode": "structured_outputs",
        },
    )
    required_keys = (
        "registry_version",
        "system_prompt_id",
        "system_prompt_version",
        "model_prompt_contract_id",
        "model_prompt_contract_version",
        "tool_surface_version",
        "output_schema_name",
        "output_schema_version",
        "provider",
        "manager_model",
        "model_profile_overlay_id",
        "model_profile_overlay_transport_mode",
    )
    for key in required_keys:
        if not registry.get(key):
            blockers.append(f"missing_prompt_registry_key:{key}")
    if registry.get("system_prompt_version") == registry.get("model_profile_overlay_id"):
        blockers.append("system_prompt_and_model_overlay_not_split")
    return {
        "case_id": "prompt_registry_versions_and_overlay_split",
        "status": _status(blockers),
        "blockers": blockers,
        "observed": registry,
    }


def _evaluate_react_trace_case() -> dict[str, Any]:
    blockers: list[str] = []
    registry = build_manager_prompt_registry(
        provider=_FakeProvider(),
        constraints={
            "manager_contract_schema_version": "v1",
            "manager_contract_provider_profile_id": "builderspace-grok-4-fast-founder-live-contract",
            "manager_contract_provider_profile_transport_mode": "structured_outputs",
        },
    )
    prompt_layer_contract = build_manager_prompt_layer_contract(
        manager_loop_scope="intake_execution",
        system_prompt=single_manager_system_prompt_for_scope("intake_execution"),
        user_payload={
            "raw_user_input": "fixture",
            "available_tools": ["estimate_nutrition", "compare_against_budget"],
            "tool_results": [],
        },
    )
    trace = build_manager_react_trace(
        manager_rounds=[
            {
                "round_index": 1,
                "stage": "pass_1",
                "decision": {
                    "manager_action": "call_tools",
                    "workflow_effect": "commit_with_followup",
                    "tool_calls": [{"name": "estimate_nutrition"}, {"name": "compare_against_budget"}],
                },
                "trace": {"provider": "fake_provider", "model": "fake-model"},
                "prompt_registry": registry,
                "prompt_layer_contract": prompt_layer_contract,
            },
            {
                "round_index": 2,
                "stage": "pass_2",
                "decision": {
                    "manager_action": "final",
                    "final_action": "commit_with_followup",
                    "workflow_effect": "commit_with_followup",
                    "tool_calls": [],
                },
                "trace": {"provider": "fake_provider", "model": "fake-model"},
                "prompt_registry": registry,
                "prompt_layer_contract": prompt_layer_contract,
            },
        ],
        tool_results=[
            {"tool_name": "estimate_nutrition"},
            {"tool_name": "compare_against_budget"},
        ],
        guard_outcome={"verdict": "pass"},
        failure_family=None,
    )
    if trace.get("trace_schema_version") != "manager_react_trace.v1":
        blockers.append("trace_schema_version_missing")
    if trace.get("manager_pass_count") != 2:
        blockers.append("manager_pass_count_incorrect")
    if trace.get("requested_tools") != ["estimate_nutrition", "compare_against_budget"]:
        blockers.append("requested_tools_incorrect")
    if trace.get("executed_tools") != ["estimate_nutrition", "compare_against_budget"]:
        blockers.append("executed_tools_incorrect")
    if not isinstance(trace.get("manager_pass_1"), dict):
        blockers.append("manager_pass_1_missing")
    if not isinstance(trace.get("manager_pass_final"), dict):
        blockers.append("manager_pass_final_missing")
    return {
        "case_id": "react_trace_contains_passes_and_tool_lineage",
        "status": _status(blockers),
        "blockers": blockers,
        "observed": trace,
    }


def _evaluate_trace_ref_case() -> dict[str, Any]:
    blockers: list[str] = []
    public_refs = build_trace_refs(request_id="rt13-request")
    internal_refs = build_internal_trace_refs(request_id="rt13-request")
    if public_refs != {"request_id": "rt13-request"}:
        blockers.append("public_trace_refs_incorrect")
    if internal_refs.get("request_id") != "rt13-request":
        blockers.append("internal_trace_refs_missing_request_id")
    if internal_refs.get("admin_trace_url") != "/admin/trace/rt13-request":
        blockers.append("admin_trace_url_incorrect")
    for key in ("request_trace_path", "stage_trace_path", "request_trace_exists", "stage_trace_exists"):
        if key not in internal_refs:
            blockers.append(f"internal_trace_refs_missing:{key}")
    return {
        "case_id": "trace_refs_include_public_and_internal_request_linkage",
        "status": _status(blockers),
        "blockers": blockers,
        "observed": {
            "public_refs": public_refs,
            "internal_refs": internal_refs,
        },
    }


def _evaluate_latency_case() -> dict[str, Any]:
    blockers: list[str] = []
    latency = intake_turn_latency_tracking(
        manager_decision=SimpleNamespace(
            intent_type="log_meal",
            tool_calls=[{"tool_name": "estimate_nutrition"}, {"tool_name": "compare_against_budget"}],
        ),
        stage_timings=[
            {"stage": "manager_pass_1", "duration_ms": 180},
            {"stage": "tool_batch", "duration_ms": 420},
            {"stage": "manager_pass_2", "duration_ms": 260},
        ],
    )
    if latency.get("total_duration_ms") != 860:
        blockers.append("total_duration_ms_incorrect")
    if latency.get("slowest_step_ms") != 420:
        blockers.append("slowest_step_ms_incorrect")
    if latency.get("slowest_step_name") != "tool_batch":
        blockers.append("slowest_step_name_incorrect")
    if latency.get("tools_used") != ["estimate_nutrition", "compare_against_budget"]:
        blockers.append("tools_used_incorrect")
    return {
        "case_id": "latency_tracking_summarizes_passes_and_tools",
        "status": _status(blockers),
        "blockers": blockers,
        "observed": latency,
    }


def _evaluate_latency_bucket_case() -> dict[str, Any]:
    blockers: list[str] = []
    expected = {
        1999: "<2s",
        2000: "2-4s",
        3999: "2-4s",
        4000: "4-8s",
        7999: "4-8s",
        8000: ">8s",
    }
    observed = {str(total_ms): _compute_latency_bucket(total_ms) for total_ms in expected}
    for total_ms, bucket in expected.items():
        if observed[str(total_ms)] != bucket:
            blockers.append(f"latency_bucket_incorrect:{total_ms}")
    return {
        "case_id": "route_latency_bucket_thresholds_are_stable",
        "status": _status(blockers),
        "blockers": blockers,
        "observed": observed,
    }


def build_rt13_observability_pack_artifact(
    *,
    output_path: Path | None = None,
) -> dict[str, Any]:
    cases = [
        _evaluate_prompt_registry_case(),
        _evaluate_react_trace_case(),
        _evaluate_trace_ref_case(),
        _evaluate_latency_case(),
        _evaluate_latency_bucket_case(),
    ]
    blockers = [f"{case['case_id']}.{blocker}" for case in cases for blocker in case["blockers"]]
    resolved_output_path = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH
    return {
        "artifact_schema_version": "1.0",
        "artifact_name": resolved_output_path.name,
        "artifact_path": str(resolved_output_path),
        "claim_scope": "runtime_observability_contract_gate",
        "launch_scope": "current_shell_v1",
        "producer_track": "CurrentShell/ManagerRuntime",
        "target_manager_runtime_gate": "rt13_observability_pack",
        "pass_type": "contract",
        "runtime_backed": False,
        "live_llm_invoked": False,
        "production_db_used": False,
        "fooddb_truth_updated": False,
        "supports_journeys": ["B", "C", "D", "E", "J", "K"],
        "status": _status(blockers),
        "blockers": blockers,
        "summary": {
            "case_count": len(cases),
            "passed_case_count": sum(1 for case in cases if case["status"] == "pass"),
            "observability_contracts": [
                "prompt_registry_version_ids",
                "react_trace_schema",
                "request_trace_linkage",
                "latency_tracking_summary",
                "route_latency_bucket",
            ],
        },
        "cases": cases,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the RT13 runtime observability pack artifact."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Where to write the JSON artifact.",
    )
    args = parser.parse_args(argv)
    artifact = build_rt13_observability_pack_artifact(output_path=args.output)
    write_json_artifact(args.output, artifact)
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
