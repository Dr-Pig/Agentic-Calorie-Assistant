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

from app.runtime.application import manager_service  # noqa: E402
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_rt1b_stable_prefix_dynamic_suffix_contract.json"


class _FakeLoopProvider:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def readiness(self) -> dict[str, Any]:
        return {
            "configured": True,
            "provider": "fake_provider",
            "manager_model": "fake-model",
            "stage_models": {"intake_manager_round": "fake-model"},
        }

    async def complete_with_trace(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        self.calls.append(dict(kwargs))
        payload = self.responses.pop(0)
        return payload, {"provider": "fake_provider", "model": "fake-model"}


def _status(blockers: list[str]) -> str:
    return "pass" if not blockers else "fail"


async def _inspect_single_turn_call() -> dict[str, Any]:
    provider = _FakeLoopProvider(
        [
            {
                "manager_action": "final",
                "intent": "general_chat",
                "intent_type": "general_chat",
                "final_action": "answer_only",
                "workflow_effect": "answer_only",
                "target_attachment": {"mode": "none"},
                "exactness": "unknown",
                "confidence": "low",
                "evidence_posture": "none",
                "repair_ack": False,
                "answer_contract": {"reply_text": "ok"},
            }
        ]
    )
    result = await manager_service.run_intake_manager(
        provider=provider,
        raw_user_input="today",
        resolved_state=SimpleNamespace(onboarding_ready=True),
        available_tools=("body.get_latest_observation", "budget.get_today_summary", "budget.get_today_summary"),
        constraints={
            "manager_contract_schema_version": "v1",
            "manager_contract_provider_profile_id": "builderspace-grok-4-fast-founder-live-contract",
            "manager_contract_provider_profile_transport_mode": "structured_outputs",
        },
    )
    return {
        "provider_call": provider.calls[0],
        "manager_trace": result.trace,
    }


def _evaluate_system_prompt_and_dynamic_payload(case: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    provider_call = dict(case.get("provider_call") or {})
    system_prompt = str(provider_call.get("system_prompt") or "")
    user_payload = dict(provider_call.get("user_payload") or {})
    if "bounded ReAct loop" not in system_prompt:
        blockers.append("system_prompt_missing_static_contract_text")
    if "raw_user_input" not in user_payload:
        blockers.append("user_payload_missing_raw_user_input")
    if "available_tools" not in user_payload:
        blockers.append("user_payload_missing_available_tools")
    if "tool_results" not in user_payload:
        blockers.append("user_payload_missing_tool_results")
    if "manager_prompt_registry" in user_payload:
        blockers.append("prompt_registry_leaked_into_dynamic_payload")
    if system_prompt == str(user_payload):
        blockers.append("system_prompt_not_separate_from_dynamic_payload")
    return {
        "case_id": "system_prompt_stays_static_and_dynamic_payload_carries_runtime_state",
        "status": _status(blockers),
        "blockers": blockers,
        "observed": {
            "system_prompt_prefix": system_prompt[:160],
            "user_payload_keys": sorted(user_payload),
        },
    }


def _evaluate_tool_order(case: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    provider_call = dict(case.get("provider_call") or {})
    available_tools = list((provider_call.get("user_payload") or {}).get("available_tools") or [])
    if available_tools != ["body.get_latest_observation", "budget.get_today_summary"]:
        blockers.append("available_tools_not_stably_normalized")
    return {
        "case_id": "available_tools_are_stably_normalized_for_prefix_reuse",
        "status": _status(blockers),
        "blockers": blockers,
        "observed": {"available_tools": available_tools},
    }


def _evaluate_trace_only_registry(case: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    manager_trace = dict(case.get("manager_trace") or {})
    prompt_registry = dict(manager_trace.get("prompt_registry") or {})
    if prompt_registry.get("provider") != "fake_provider":
        blockers.append("provider_trace_missing")
    if prompt_registry.get("manager_model") != "fake-model":
        blockers.append("model_trace_missing")
    return {
        "case_id": "provider_trace_stays_trace_side_and_not_prompt_side",
        "status": _status(blockers),
        "blockers": blockers,
        "observed": prompt_registry,
    }


def _evaluate_prompt_layer_contract(case: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    provider_call = dict(case.get("provider_call") or {})
    user_payload = dict(provider_call.get("user_payload") or {})
    manager_trace = dict(case.get("manager_trace") or {})
    manager_rounds = list(manager_trace.get("manager_rounds") or [])
    first_round = dict(manager_rounds[0]) if manager_rounds and isinstance(manager_rounds[0], dict) else {}
    layer = dict(first_round.get("prompt_layer_contract") or {})
    if layer.get("system_prompt_layer") != "static_prefix":
        blockers.append("system_prompt_layer_not_static_prefix")
    if layer.get("runtime_payload_layer") != "dynamic_suffix":
        blockers.append("runtime_payload_layer_not_dynamic_suffix")
    if layer.get("provider_profile_layer") != "transport_overlay_trace_only":
        blockers.append("provider_profile_layer_not_trace_only")
    cache_profile = dict(layer.get("prompt_cache_profile") or {})
    if cache_profile.get("static_prefix_first") is not True:
        blockers.append("cache_profile_static_prefix_first_missing")
    if cache_profile.get("dynamic_context_last") is not True:
        blockers.append("cache_profile_dynamic_context_last_missing")
    if layer.get("dynamic_payload_keys") != sorted(user_payload):
        blockers.append("dynamic_payload_keys_do_not_match_user_payload")
    if "prompt_layer_contract" in user_payload:
        blockers.append("prompt_layer_contract_leaked_into_user_payload")
    return {
        "case_id": "prompt_layer_contract_supports_prefix_cache_and_progressive_disclosure",
        "status": _status(blockers),
        "blockers": blockers,
        "observed": layer,
    }


async def build_rt1b_stable_prefix_dynamic_suffix_contract_artifact(
    *,
    output_path: Path | None = None,
) -> dict[str, Any]:
    first_call = await _inspect_single_turn_call()
    cases = [
        _evaluate_system_prompt_and_dynamic_payload(first_call),
        _evaluate_tool_order(first_call),
        _evaluate_trace_only_registry(first_call),
        _evaluate_prompt_layer_contract(first_call),
    ]
    blockers = [f"{case['case_id']}.{blocker}" for case in cases for blocker in case["blockers"]]
    resolved_output_path = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH
    return {
        "artifact_schema_version": "1.0",
        "artifact_name": resolved_output_path.name,
        "artifact_path": str(resolved_output_path),
        "claim_scope": "stable_prefix_dynamic_suffix_contract_gate",
        "launch_scope": "current_shell_v1",
        "producer_track": "CurrentShell/ManagerRuntime",
        "target_manager_runtime_gate": "rt1b_stable_prefix_dynamic_suffix_contract",
        "pass_type": "contract",
        "runtime_backed": False,
        "live_llm_invoked": False,
        "production_db_used": False,
        "fooddb_truth_updated": False,
        "supports_journeys": ["B", "C", "D", "E", "G", "H", "J", "K"],
        "status": _status(blockers),
        "blockers": blockers,
        "summary": {
            "case_count": len(cases),
            "passed_case_count": sum(1 for case in cases if case["status"] == "pass"),
            "stable_prefix_contracts": [
                "static_system_prompt",
                "dynamic_user_payload_suffix",
                "stable_available_tool_order",
                "trace_only_provider_metadata",
            ],
        },
        "cases": cases,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the RT1b stable-prefix / dynamic-suffix contract artifact."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Where to write the JSON artifact.",
    )
    args = parser.parse_args(argv)
    artifact = __import__("asyncio").run(
        build_rt1b_stable_prefix_dynamic_suffix_contract_artifact(output_path=args.output)
    )
    write_json_artifact(args.output, artifact)
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
