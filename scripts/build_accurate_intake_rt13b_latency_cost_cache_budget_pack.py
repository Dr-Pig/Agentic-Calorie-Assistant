from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.runtime.infrastructure.trace.text_meal_observability import compute_token_usage  # noqa: E402
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402
from scripts.build_accurate_intake_mvp_live_cost_summary import (  # noqa: E402
    build_accurate_intake_live_cost_summary,
)


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_rt13b_latency_cost_cache_budget_pack.json"
FORBIDDEN_TRUE_FLAGS = (
    "readiness_claimed",
    "product_readiness_claimed",
    "private_self_use_approved",
    "production_selected",
    "mutation_rollout_approved",
    "runtime_web_activation_approved",
    "live_provider_used_as_truth",
)


def build_rt13b_latency_cost_cache_budget_pack(
    *,
    live_artifacts: list[dict[str, Any]],
    rt1c_artifact: dict[str, Any],
    rt13_artifact: dict[str, Any],
    rt12b_artifact: dict[str, Any],
    output_path: Path | None = None,
) -> dict[str, Any]:
    dependency_case = _dependency_case(
        rt1c_artifact=rt1c_artifact,
        rt13_artifact=rt13_artifact,
        rt12b_artifact=rt12b_artifact,
    )
    source_case = _source_case(live_artifacts)
    stage_case = _latency_case(live_artifacts)
    cost_case = _token_cost_case(live_artifacts)
    cache_case = _prompt_cache_case(live_artifacts)
    retry_case = _retry_timeout_case(live_artifacts)
    cases = [dependency_case, source_case, stage_case, cost_case, cache_case, retry_case]
    blockers = [f"{case['case_id']}.{blocker}" for case in cases for blocker in case["blockers"]]
    stages = _stages(live_artifacts)
    cost_summary = build_accurate_intake_live_cost_summary(live_artifacts)
    token_usage = _token_usage(live_artifacts)
    retry_dependent_stage_count = sum(1 for stage in stages if _is_retry_dependent(stage))
    timeout_stage_count = sum(1 for stage in stages if _is_timeout_stage(stage))
    resolved_output_path = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH
    reported_cost_usd = cost_summary["summary"]["reported_cost_usd"]
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_name": resolved_output_path.name,
            "artifact_path": str(resolved_output_path),
            "artifact_type": "accurate_intake_rt13b_latency_cost_cache_budget_pack",
            "claim_scope": "latency_cost_cache_budget_visibility",
            "launch_scope": "current_shell_v1",
            "producer_track": "CurrentShell/ManagerRuntime",
            "target_manager_runtime_gate": "rt13b_latency_cost_cache_budget_pack",
            "pass_type": "runtime_backed",
            "runtime_backed": True,
            "live_llm_invoked": _all_live_sources_invoked(live_artifacts),
            "production_db_used": False,
            "fooddb_truth_updated": False,
            "supports_journeys": ["B", "C", "D", "E", "J", "K"],
            "status": _status(blockers),
            "blockers": blockers,
            "summary": {
                "source_artifact_count": len(live_artifacts),
                "stage_count": len(stages),
                "provider_invocation_count": int(cost_summary["summary"]["provider_invocation_count"]),
                "total_latency_ms": sum(_int(stage.get("latency_ms")) for stage in stages),
                "max_stage_latency_ms": max((_int(stage.get("latency_ms")) for stage in stages), default=0),
                "timeout_stage_count": timeout_stage_count,
                "retry_dependent_stage_count": retry_dependent_stage_count,
                "usage_record_count": int(cost_summary["summary"]["usage_record_count"]),
                "total_tokens": int(cost_summary["summary"]["total_tokens"]),
                "cached_prompt_tokens": int(token_usage["total_cached_prompt_tokens"]),
                "cache_reporting_call_count": int(token_usage["cache_reporting_call_count"]),
                "cache_hit_call_count": int(token_usage["cache_hit_call_count"]),
                "reported_cost_usd": reported_cost_usd,
                "cost_budget_enforceable": reported_cost_usd is not None,
            },
            "budget_policy": {
                "latency_truth_source": "live_stage_artifact_latency_ms",
                "token_truth_source": "provider_usage_fields",
                "cost_truth_source": "provider_reported_artifact_fields_only",
                "token_counts_are_not_billing_truth": True,
                "pricing_table_applied": False,
                "cache_reporting_required_for_green": True,
                "cache_hit_not_required_for_green": True,
                "retry_dependent_evidence_blocks_green": True,
                "timeout_evidence_blocks_green": True,
            },
            "dependencies": {
                "rt1c_cache_metrics_observability": _dependency_status(rt1c_artifact),
                "rt13_observability_pack": _dependency_status(rt13_artifact),
                "rt12b_live_trace_grading_extension": _dependency_status(rt12b_artifact),
            },
            "cases": cases,
            "cost_summary": {
                "summary": cost_summary["summary"],
                "cost_policy": cost_summary["cost_policy"],
                "input_integrity": cost_summary["input_integrity"],
            },
            "non_claims": {
                "product_readiness_claimed": False,
                "private_self_use_approved": False,
                "whole_product_mvp_ready": False,
                "production_selected": False,
                "mutation_rollout_approved": False,
            },
        }
    )


def _dependency_case(
    *,
    rt1c_artifact: dict[str, Any],
    rt13_artifact: dict[str, Any],
    rt12b_artifact: dict[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    blockers.extend(_required_dependency_blockers(rt1c_artifact, "rt1c_cache_metrics_observability"))
    blockers.extend(_required_dependency_blockers(rt13_artifact, "rt13_observability_pack"))
    blockers.extend(_required_dependency_blockers(rt12b_artifact, "rt12b_live_trace_grading_extension"))
    return _case(
        "dependencies",
        blockers,
        {
            "rt1c": _dependency_status(rt1c_artifact),
            "rt13": _dependency_status(rt13_artifact),
            "rt12b": _dependency_status(rt12b_artifact),
        },
    )


def _source_case(live_artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    blockers: list[str] = []
    if not live_artifacts:
        blockers.append("live_artifacts_missing")
    for index, artifact in enumerate(live_artifacts):
        if artifact.get("artifact_type") != "accurate_intake_mvp_live_diagnostic":
            blockers.append(f"source_{index}_artifact_type_invalid")
        if artifact.get("live_invoked") is not True or artifact.get("live_llm_invoked") is not True:
            blockers.append(f"source_{index}_live_llm_not_invoked")
        for flag in FORBIDDEN_TRUE_FLAGS:
            if artifact.get(flag) is True:
                blockers.append(f"source_{index}_{flag}")
    return _case(
        "live_source_integrity",
        blockers,
        {
            "source_artifact_count": len(live_artifacts),
            "live_llm_invoked": _all_live_sources_invoked(live_artifacts),
        },
    )


def _latency_case(live_artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    blockers: list[str] = []
    stages = _stages(live_artifacts)
    if not stages:
        blockers.append("stages_missing")
    for stage in stages:
        stage_id = str(stage.get("stage_id") or "unknown_stage")
        if "latency_ms" not in stage:
            blockers.append(f"latency_missing:{stage_id}")
        if "timeout_budget_ms" not in stage or _int(stage.get("timeout_budget_ms")) <= 0:
            blockers.append(f"timeout_budget_missing:{stage_id}")
        if _int(stage.get("timeout_budget_ms")) > 0 and _int(stage.get("latency_ms")) > _int(
            stage.get("timeout_budget_ms")
        ):
            blockers.append(f"stage_exceeded_timeout_budget:{stage_id}")
    total_latency_ms = sum(_int(stage.get("latency_ms")) for stage in stages)
    if stages and total_latency_ms <= 0:
        blockers.append("total_latency_not_observed")
    return _case(
        "latency_budget",
        blockers,
        {
            "stage_count": len(stages),
            "total_latency_ms": total_latency_ms,
            "max_stage_latency_ms": max((_int(stage.get("latency_ms")) for stage in stages), default=0),
        },
    )


def _token_cost_case(live_artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    blockers: list[str] = []
    cost_summary = build_accurate_intake_live_cost_summary(live_artifacts)
    input_integrity = _dict(cost_summary.get("input_integrity"))
    if input_integrity.get("passed") is not True:
        blockers.extend(f"cost_summary.{blocker}" for blocker in _list(input_integrity.get("blockers")))
    summary = _dict(cost_summary.get("summary"))
    if _int(summary.get("provider_invocation_count")) <= 0:
        blockers.append("provider_invocations_missing")
    if _int(summary.get("usage_record_count")) <= 0 or _int(summary.get("total_tokens")) <= 0:
        blockers.append("usage_not_observed")
    return _case(
        "token_cost_visibility",
        blockers,
        {
            "usage_record_count": _int(summary.get("usage_record_count")),
            "total_tokens": _int(summary.get("total_tokens")),
            "reported_cost_usd": summary.get("reported_cost_usd"),
            "cost_budget_enforceable": summary.get("reported_cost_usd") is not None,
            "cost_unavailable_without_pricing": bool(summary.get("cost_unavailable_without_pricing")),
        },
    )


def _prompt_cache_case(live_artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    blockers: list[str] = []
    token_usage = _token_usage(live_artifacts)
    if token_usage.get("prompt_cache_reporting_observed") is not True:
        blockers.append("cache_reporting_not_observed")
    return _case(
        "prompt_cache_visibility",
        blockers,
        {
            "cache_reporting_call_count": token_usage.get("cache_reporting_call_count"),
            "cache_hit_call_count": token_usage.get("cache_hit_call_count"),
            "cached_prompt_tokens": token_usage.get("total_cached_prompt_tokens"),
            "prompt_cache_hit_observed": token_usage.get("prompt_cache_hit_observed"),
        },
    )


def _retry_timeout_case(live_artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    blockers: list[str] = []
    stages = _stages(live_artifacts)
    retry_dependent_stage_count = sum(1 for stage in stages if _is_retry_dependent(stage))
    timeout_stage_count = sum(1 for stage in stages if _is_timeout_stage(stage))
    if retry_dependent_stage_count:
        blockers.append("retry_dependent_stage_present")
    if timeout_stage_count:
        blockers.append("timeout_stage_present")
    return _case(
        "retry_timeout_budget",
        blockers,
        {
            "retry_dependent_stage_count": retry_dependent_stage_count,
            "timeout_stage_count": timeout_stage_count,
        },
    )


def _required_dependency_blockers(artifact: dict[str, Any], gate_id: str) -> list[str]:
    blockers: list[str] = []
    if artifact.get("target_manager_runtime_gate") != gate_id:
        blockers.append(f"{gate_id}_unexpected_gate")
    if artifact.get("status") != "pass":
        blockers.append(f"{gate_id}_not_pass")
    return blockers


def _dependency_status(artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_manager_runtime_gate": artifact.get("target_manager_runtime_gate"),
        "status": artifact.get("status"),
    }


def _case(case_id: str, blockers: list[str], observed: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "status": _status(blockers),
        "blockers": blockers,
        "observed": observed,
    }


def _stages(live_artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stages: list[dict[str, Any]] = []
    for artifact in live_artifacts:
        stages.extend(_dict(stage) for stage in _list(artifact.get("stages")))
    return stages


def _token_usage(live_artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    return compute_token_usage([{"usage": usage} for usage in _usage_dicts(live_artifacts)])


def _usage_dicts(value: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if isinstance(value, dict):
        usage = value.get("usage")
        if isinstance(usage, dict):
            records.append(dict(usage))
        for key, item in value.items():
            if key == "usage":
                continue
            records.extend(_usage_dicts(item))
    elif isinstance(value, list):
        for item in value:
            records.extend(_usage_dicts(item))
    return records


def _is_retry_dependent(stage: dict[str, Any]) -> bool:
    return bool(stage.get("retry_policy_applied")) or str(stage.get("result_kind") or "") == "pass_after_retry"


def _is_timeout_stage(stage: dict[str, Any]) -> bool:
    status = str(stage.get("status") or "")
    result_kind = str(stage.get("result_kind") or "")
    return status == "timeout" or result_kind.startswith("timeout")


def _all_live_sources_invoked(live_artifacts: list[dict[str, Any]]) -> bool:
    return bool(live_artifacts) and all(
        artifact.get("live_invoked") is True and artifact.get("live_llm_invoked") is True
        for artifact in live_artifacts
    )


def _status(blockers: list[str]) -> str:
    return "pass" if not blockers else "fail"


def _int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return 0
    return 0


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the RT13b latency/cost/cache budget pack.")
    parser.add_argument("--live-artifact", action="append", dest="live_artifacts", required=True)
    parser.add_argument("--rt1c-artifact", type=Path, required=True)
    parser.add_argument("--rt13-artifact", type=Path, required=True)
    parser.add_argument("--rt12b-artifact", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args(argv)
    artifact = build_rt13b_latency_cost_cache_budget_pack(
        live_artifacts=[read_json_artifact(Path(path)) for path in args.live_artifacts],
        rt1c_artifact=read_json_artifact(args.rt1c_artifact),
        rt13_artifact=read_json_artifact(args.rt13_artifact),
        rt12b_artifact=read_json_artifact(args.rt12b_artifact),
        output_path=args.output,
    )
    write_json_artifact(args.output, artifact)
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
