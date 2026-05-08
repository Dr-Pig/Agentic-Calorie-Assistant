from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.runtime.infrastructure.trace.text_meal_observability import (  # noqa: E402
    build_trace_envelope,
    compute_token_usage,
)
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_rt1c_cache_metrics_observability.json"


def _status(blockers: list[str]) -> str:
    return "pass" if not blockers else "fail"


def _evaluate_openai_cache_case() -> dict[str, Any]:
    blockers: list[str] = []
    usage = compute_token_usage(
        [
            {
                "usage": {
                    "prompt_tokens": 1200,
                    "completion_tokens": 120,
                    "prompt_tokens_details": {"cached_tokens": 960},
                }
            },
            {
                "usage": {
                    "prompt_tokens": 400,
                    "completion_tokens": 80,
                    "prompt_tokens_details": {"cached_tokens": 0},
                }
            },
        ]
    )
    if usage.get("total_cached_prompt_tokens") != 960:
        blockers.append("cached_prompt_tokens_not_aggregated")
    if usage.get("cache_reporting_call_count") != 2:
        blockers.append("cache_reporting_call_count_incorrect")
    if usage.get("cache_hit_call_count") != 1:
        blockers.append("cache_hit_call_count_incorrect")
    return {
        "case_id": "openai_prompt_cache_usage_is_normalized",
        "status": _status(blockers),
        "blockers": blockers,
        "observed": usage,
    }


def _evaluate_input_output_cache_case() -> dict[str, Any]:
    blockers: list[str] = []
    usage = compute_token_usage(
        [
            {
                "usage": {
                    "input_tokens": 1400,
                    "output_tokens": 200,
                    "input_tokens_details": {"cached_tokens": 1024},
                }
            },
            {"usage": {"input_tokens": 320, "output_tokens": 40}},
        ]
    )
    if usage.get("total_prompt_tokens") != 1720:
        blockers.append("input_tokens_not_mapped_to_prompt_tokens")
    if usage.get("total_completion_tokens") != 240:
        blockers.append("output_tokens_not_mapped_to_completion_tokens")
    if usage.get("total_cached_prompt_tokens") != 1024:
        blockers.append("input_token_cache_not_aggregated")
    return {
        "case_id": "input_output_usage_cache_metrics_are_normalized",
        "status": _status(blockers),
        "blockers": blockers,
        "observed": usage,
    }


def _evaluate_trace_envelope_case() -> dict[str, Any]:
    blockers: list[str] = []
    envelope = build_trace_envelope(
        request_id="rt1c-request",
        user_id="u-1",
        timestamp="2026-05-08T00:00:00Z",
        provider_name="fake_provider",
        schema_signature="schema-v1",
        source_page_version="page-v1",
        trace_contract={
            "route_family": "intake",
            "manager_output": {"intent": "log_meal"},
            "followup_policy_decision": "optional_refinement",
            "followup_decision": "ask_size_then_commit",
            "grounding_summary": {},
            "grounding_attempts": [],
            "persistence_decision": {},
            "retry_reason": None,
        },
        llm_traces=[
            {
                "stage": "manager_pass_1",
                "usage": {
                    "prompt_tokens": 1500,
                    "completion_tokens": 110,
                    "prompt_tokens_details": {"cached_tokens": 1280},
                },
            }
        ],
        debug_steps=[],
        quality_signals={},
        best_answer_source="primary",
        retry_triggered=False,
        multi_turn_context={"is_multi_turn": False},
    )
    token_usage = envelope.token_usage
    if token_usage.get("total_cached_prompt_tokens") != 1280:
        blockers.append("trace_envelope_missing_cached_prompt_tokens")
    if token_usage.get("prompt_cache_reporting_observed") is not True:
        blockers.append("trace_envelope_missing_cache_reporting_flag")
    if envelope.trace_contract.get("token_usage") != token_usage:
        blockers.append("trace_contract_token_usage_not_synced")
    return {
        "case_id": "trace_envelope_carries_cache_metrics_summary",
        "status": _status(blockers),
        "blockers": blockers,
        "observed": {
            "token_usage": token_usage,
            "trace_contract_token_usage": envelope.trace_contract.get("token_usage"),
        },
    }


def build_rt1c_cache_metrics_observability_artifact(
    *,
    output_path: Path | None = None,
) -> dict[str, Any]:
    cases = [
        _evaluate_openai_cache_case(),
        _evaluate_input_output_cache_case(),
        _evaluate_trace_envelope_case(),
    ]
    blockers = [f"{case['case_id']}.{blocker}" for case in cases for blocker in case["blockers"]]
    resolved_output_path = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH
    return {
        "artifact_schema_version": "1.0",
        "artifact_name": resolved_output_path.name,
        "artifact_path": str(resolved_output_path),
        "claim_scope": "prompt_cache_metrics_observability_contract_gate",
        "launch_scope": "current_shell_v1",
        "producer_track": "CurrentShell/ManagerRuntime",
        "target_manager_runtime_gate": "rt1c_cache_metrics_observability",
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
                "openai_cached_tokens_normalization",
                "input_output_token_cache_normalization",
                "trace_envelope_cache_metrics_summary",
            ],
        },
        "cases": cases,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the RT1c prompt cache metrics observability artifact."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Where to write the RT1c artifact JSON.",
    )
    args = parser.parse_args(argv)

    artifact = build_rt1c_cache_metrics_observability_artifact(output_path=args.output)
    write_json_artifact(args.output, artifact)
    print(args.output)
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
