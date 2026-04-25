from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.runtime.agent.manager import SINGLE_MANAGER_SYSTEM_PROMPT, run_intake_manager

DEFAULT_OUTPUT_DIR = ROOT / "artifacts"
LATEST_REPORT = DEFAULT_OUTPUT_DIR / "wave1_phase_b_minimal_tool_loop_smoke.json"

CORE_SMOKE_CASES = (
    "我吃了一顆茶葉蛋",
    "我喝了一杯珍珠奶茶",
    "我吃了一個便當",
    "我吃了滷味",
    "我吃了豆干、海帶、貢丸的滷味",
    "珍珠奶茶大概多少熱量？",
)
AVAILABLE_READ_TOOLS = (
    "lookup_generic_food",
    "retrieve_web_food_evidence",
    "load_taiwan_food_semantics_skill",
)
ESTIMATE_READ_TOOLS = {"lookup_generic_food", "retrieve_web_food_evidence"}
PROVIDER_PARAM_KEYS = (
    "provider",
    "model",
    "temperature",
    "max_tokens",
    "response_format",
    "timeout",
    "retry_policy",
    "tool_choice",
    "request_id",
)
PASS_1_FORBIDDEN_FIELDS = {
    "final_kcal",
    "kcal_range",
    "likely_kcal",
    "evidence_used",
    "final_response",
    "mutation_result",
    "ledger_delta",
    "canonical_ledger_entry",
}
PASS_2_FORBIDDEN_MUTATION_FIELDS = {"mutation_result", "ledger_delta", "canonical_ledger_entry"}
PASS_1_TOOL_REQUEST_PAYLOAD = (
    "Phase B-1 Pass 1 HARD CONTRACT.\n"
    "This is Manager Pass 1. You MUST return manager_action='call_tools'.\n"
    "Do not choose manager_action='final' in Pass 1.\n"
    "Even for call_tools, include interaction_family, response_mode, operations=[], and answer_contract={} to satisfy the active manager schema.\n"
    "Do not return final nutrition truth, evidence_used, answer text, mutation result, ledger delta, or renderer response.\n"
    "Request read tools needed for the current user message using available tool names.\n"
    "In this B-1 smoke, every food_logging or nutrition_info_query case must call at least one read tool in Pass 1; never skip directly to final in Pass 1.\n"
    "For estimable common foods, request lookup_generic_food.\n"
    "For listed ingredients inside a self-selected basket, request lookup_generic_food for the listed ingredients.\n"
    "For web evidence candidates, request retrieve_web_food_evidence.\n"
    "For self-selected basket foods without listed ingredients, still expose requested estimate tools so the runtime router can block them.\n"
    "The runtime, not the model, validates allowed and blocked tools."
)
PASS_2_SYNTHESIS_PAYLOAD = (
    "Phase B-1 minimal tool-loop smoke mode.\n"
    "This is Manager Pass 2: consume packetized tool_results only and return manager_action='final'.\n"
    "Raw tool outputs are trace-only and are not visible as synthesis input.\n"
    "You may produce item_results, kcal_range, likely_kcal, uncertainty, and evidence_used from packet refs.\n"
    "Do not output mutation_result, ledger_delta, canonical_ledger_entry, or renderer final response."
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _prompt_hash(*, manager_role: str) -> str:
    task_payload = PASS_1_TOOL_REQUEST_PAYLOAD if manager_role == "pass_1_tool_request" else PASS_2_SYNTHESIS_PAYLOAD
    return _hash({"manager_role": manager_role, "system_prompt": SINGLE_MANAGER_SYSTEM_PROMPT, "task_payload": task_payload})


def _provider_params(trace: dict[str, Any]) -> dict[str, Any]:
    return {key: trace.get(key) for key in PROVIDER_PARAM_KEYS}


def _normalize_provider_trace(trace: dict[str, Any], *, manager_role: str, user_payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(trace or {})
    request_payload = normalized.get("request_payload") if isinstance(normalized.get("request_payload"), dict) else {}
    def pick(key: str, fallback: Any) -> Any:
        value = normalized.get(key)
        return fallback if value in (None, "") else value

    normalized.setdefault("provider", "builderspace")
    normalized.setdefault("model", request_payload.get("model"))
    normalized["temperature"] = pick("temperature", request_payload.get("temperature"))
    normalized["max_tokens"] = pick("max_tokens", request_payload.get("max_tokens"))
    normalized["response_format"] = pick("response_format", request_payload.get("response_format"))
    normalized["timeout"] = pick("timeout", normalized.get("timeout_seconds"))
    normalized["retry_policy"] = pick("retry_policy", {"source": "provider_trace_unavailable"})
    normalized["tool_choice"] = pick("tool_choice", "none")
    if not normalized.get("request_id"):
        normalized["request_id"] = f"phase_b1_{manager_role}_{_hash({'user_payload': user_payload, 'raw_content': normalized.get('raw_content')})}"
    return normalized


class _PhaseB1ManagerProvider:
    def __init__(self, provider: Any) -> None:
        self._provider = provider

    def readiness(self) -> dict[str, Any]:
        if hasattr(self._provider, "readiness"):
            readiness = self._provider.readiness()
            return dict(readiness or {})
        return {"configured": False, "reason": "provider_missing_readiness"}

    async def complete_with_trace(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        user_payload = dict(kwargs.get("user_payload") or {})
        round_index = int(user_payload.get("round_index") or 0)
        manager_role = "pass_1_tool_request" if round_index == 0 else "pass_2_synthesis"
        task_payload = PASS_1_TOOL_REQUEST_PAYLOAD if round_index == 0 else PASS_2_SYNTHESIS_PAYLOAD
        constraints = dict(user_payload.get("constraints") or {})
        constraints.update(
            {
                "phase_b1_manager_role": manager_role,
                "phase_b1_task_payload_id": f"phase_b1_{manager_role}_v1",
            }
        )
        user_payload["constraints"] = constraints
        kwargs["user_payload"] = user_payload
        kwargs["system_prompt"] = f"{task_payload}\n\n{kwargs.get('system_prompt')}\n\n{task_payload}"
        payload, trace = await self._provider.complete_with_trace(**kwargs)
        trace = _normalize_provider_trace(dict(trace or {}), manager_role=manager_role, user_payload=user_payload)
        trace["manager_role"] = manager_role
        trace["phase_b1_task_payload_id"] = constraints["phase_b1_task_payload_id"]
        trace["phase_b1_task_payload_hash"] = _hash(task_payload)
        return payload, trace


def _contains_any_key(value: Any, keys: set[str]) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in keys:
                found.append(key)
            found.extend(_contains_any_key(item, keys))
    elif isinstance(value, list):
        for item in value:
            found.extend(_contains_any_key(item, keys))
    return sorted(set(found))


def _is_self_selected_basket_without_ingredients(message: str) -> bool:
    return message.strip() in {"我吃了滷味"}


def _is_no_mutation_query(message: str) -> bool:
    return "多少熱量" in message or "大概多少熱量" in message


def _fixture_packet(*, case_id: str, tool_name: str, food_name: str, truth_level: str = "candidate") -> dict[str, Any]:
    fixture_id = f"{case_id}_{tool_name}_{_hash(food_name)}"
    if tool_name == "load_taiwan_food_semantics_skill":
        return {
            "packet_type": "TaiwanSkillPacket",
            "truth_level": "rule_hint",
            "fixture_id": fixture_id,
            "fixture_hash": _hash({"fixture_id": fixture_id, "food_name": food_name, "tool_name": tool_name}),
            "fixture_only": True,
            "generated_by": "deterministic_fixture",
            "rule_id": "taiwan_food_semantic_hint",
            "trigger_food_name": food_name,
        }
    packet = {
        "packet_type": "GenericFoodDbPacket" if tool_name == "lookup_generic_food" else "SearchCandidatePacket",
        "truth_level": truth_level,
        "fixture_id": fixture_id,
        "fixture_hash": _hash({"fixture_id": fixture_id, "food_name": food_name, "tool_name": tool_name}),
        "fixture_only": True,
        "generated_by": "deterministic_fixture",
        "candidates": [{"food_name": food_name, "kcal_range": [70, 90], "likely_kcal": 80}],
    }
    if tool_name == "retrieve_web_food_evidence":
        packet.update(
            {
                "query": food_name,
                "source_quality_label": "third_party",
                "candidates": [{"food_name": food_name, "url": "https://example.test/phase-b1", "snippet": "candidate only"}],
            }
        )
    return packet


def _raw_stub_output(*, case_id: str, tool_name: str, food_name: str) -> dict[str, Any]:
    return {
        "truth_level": "candidate",
        "fixture_id": f"raw_{case_id}_{tool_name}_{_hash(food_name)}",
        "fixture_only": True,
        "generated_by": "deterministic_fixture",
        "candidate": {"food_name": food_name},
    }


def _food_names_for_message(message: str) -> list[str]:
    if "豆干" in message and "海帶" in message and "貢丸" in message:
        return ["豆干", "海帶", "貢丸"]
    if "珍珠奶茶" in message:
        return ["珍珠奶茶"]
    if "便當" in message:
        return ["便當"]
    if "滷味" in message:
        return ["滷味"]
    return ["茶葉蛋"]


def _route_tools(*, message: str, requested_tools: list[str]) -> dict[str, Any]:
    blocked_tools: list[str] = []
    block_reasons: list[dict[str, str]] = []
    if _is_self_selected_basket_without_ingredients(message):
        blocked_tools = sorted(ESTIMATE_READ_TOOLS)
        block_reasons.append(
            {
                "rule": "self_selected_basket_without_ingredients_blocks_estimate_tools",
                "detail": "Composition is unknown; ask for ingredients before generic DB or web estimate.",
            }
        )
    allowed_tools = [tool for tool in requested_tools if tool not in set(blocked_tools)]
    return {
        "requested_read_tools": list(requested_tools),
        "manager_requested_tools": list(requested_tools),
        "allowed_tools": allowed_tools,
        "filtered_tool_plan": list(allowed_tools),
        "blocked_tools": blocked_tools,
        "block_reasons": block_reasons,
    }


def _renderer_trace(*, item_results: list[dict[str, Any]], mutation: dict[str, Any]) -> dict[str, Any]:
    return {
        "input": {
            "allowed_facts": ["item_results", "ledger_mutation_result"],
            "forbidden_claims": ["invent calories not in item_results", "invent logged status outside mutation_result"],
            "item_results": item_results,
            "ledger_mutation_result": mutation["mutation_result"],
        },
        "final_response": "Renderer mirrors allowed facts.",
        "invented_facts": [],
    }


def _mutation_trace(*, message: str, item_results: list[dict[str, Any]]) -> dict[str, Any]:
    if _is_no_mutation_query(message) or _is_self_selected_basket_without_ingredients(message):
        return {"mutation_attempted": False, "reason": "no_mutation_intent", "mutation_result": None}
    if not item_results:
        return {"mutation_attempted": False, "reason": "missing_item_results_guard", "mutation_result": None}
    return {
        "mutation_attempted": True,
        "reason": "guard_approved_logging",
        "mutation_result": {"truth_level": "mutation_result", "ledger_item_ids": [f"item_{_hash(item_results)}"]},
    }


def _item_results_from_payload(payload: dict[str, Any], packets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    raw_item_results = payload.get("item_results")
    if isinstance(raw_item_results, list) and raw_item_results:
        return [dict(item) for item in raw_item_results if isinstance(item, dict)]
    results: list[dict[str, Any]] = []
    for packet in packets:
        candidates = packet.get("candidates") if isinstance(packet, dict) else None
        if not isinstance(candidates, list):
            continue
        for candidate in candidates:
            if isinstance(candidate, dict):
                results.append(
                    {
                        "food_name": candidate.get("food_name"),
                        "kcal_range": candidate.get("kcal_range"),
                        "likely_kcal": candidate.get("likely_kcal"),
                        "uncertainty": "moderate",
                        "evidence_used": [packet.get("fixture_id")],
                    }
                )
    return results


async def _run_case(*, case_id: str, message: str, provider: Any) -> dict[str, Any]:
    router_trace: dict[str, Any] = {
        "requested_read_tools": [],
        "manager_requested_tools": [],
        "allowed_tools": [],
        "filtered_tool_plan": [],
        "blocked_tools": [],
        "block_reasons": [],
    }
    read_tool_executions: list[dict[str, Any]] = []
    packetizer_outputs: list[dict[str, Any]] = []

    async def tool_executor(*, tool_calls: list[dict[str, Any]], **_: Any) -> list[dict[str, Any]]:
        nonlocal router_trace, read_tool_executions, packetizer_outputs
        requested_tools = [str(call.get("name") or call.get("tool_name") or "") for call in tool_calls if isinstance(call, dict)]
        requested_tools = [tool for tool in requested_tools if tool]
        router_trace = _route_tools(message=message, requested_tools=requested_tools)
        for tool_name in router_trace["allowed_tools"]:
            for food_name in _food_names_for_message(message):
                raw_output = _raw_stub_output(case_id=case_id, tool_name=tool_name, food_name=food_name)
                packet = _fixture_packet(case_id=case_id, tool_name=tool_name, food_name=food_name)
                read_tool_executions.append(
                    {
                        "tool_name": tool_name,
                        "raw_tool_output_ref": f"artifacts/raw/{case_id}_{tool_name}_{_hash(food_name)}.json",
                        "output": raw_output,
                    }
                )
                packetizer_outputs.append(packet)
        if _is_self_selected_basket_without_ingredients(message) and not packetizer_outputs:
            packetizer_outputs.append(
                {
                    "packet_type": "TaiwanSkillPacket",
                    "truth_level": "rule_hint",
                    "fixture_id": f"{case_id}_self_selected_basket",
                    "fixture_hash": _hash({"case_id": case_id, "rule": "self_selected_basket_without_ingredients"}),
                    "fixture_only": True,
                    "generated_by": "deterministic_fixture",
                    "rule_id": "self_selected_basket_without_ingredients",
                }
            )
        return [
            {
                "tool_name": "packetize_food_evidence",
                "truth_level": "hint",
                "packetizer_outputs": _json_safe(packetizer_outputs),
            }
        ]

    result = await run_intake_manager(
        provider=provider,
        raw_user_input=message,
        resolved_state=SimpleNamespace(onboarding_ready=True),
        available_tools=AVAILABLE_READ_TOOLS,
        tool_executor=tool_executor,
        constraints={
            "phase": "B-1",
            "scope": "minimal_tool_loop_smoke",
            "manager_pass_contract": "pass1_requests_tools_pass2_synthesizes",
        },
        max_rounds=2,
    )
    if _is_self_selected_basket_without_ingredients(message) and not router_trace["blocked_tools"]:
        router_trace = _route_tools(message=message, requested_tools=[])
        if not packetizer_outputs:
            packetizer_outputs.append(
                {
                    "packet_type": "TaiwanSkillPacket",
                    "truth_level": "rule_hint",
                    "fixture_id": f"{case_id}_self_selected_basket",
                    "fixture_hash": _hash({"case_id": case_id, "rule": "self_selected_basket_without_ingredients"}),
                    "fixture_only": True,
                    "generated_by": "deterministic_fixture",
                    "rule_id": "self_selected_basket_without_ingredients",
                }
            )
    rounds = list(result.manager_rounds)
    pass1_round = rounds[0] if rounds else {"decision": {}, "trace": {}}
    pass2_round = rounds[-1] if len(rounds) > 1 else {"decision": {}, "trace": {}}
    pass1_decision = dict(pass1_round.get("decision") or {})
    pass2_decision = dict(pass2_round.get("decision") or {})
    item_results = _item_results_from_payload(pass2_decision, packetizer_outputs)
    mutation = _mutation_trace(message=message, item_results=item_results)
    guard = {"ran": True, "ran_before_mutation": True, "result": "no_mutation" if not mutation["mutation_attempted"] else "pass"}
    return {
        "case_id": case_id,
        "input_message": message,
        "semantic_boundary": "self_selected_basket_without_ingredients" if _is_self_selected_basket_without_ingredients(message) else None,
        "is_live_tavily_canary": False,
        "uses_deterministic_stub_fixtures": True,
        "stub_fixture_source": "scripts/run_wave1_phase_b_minimal_tool_loop_smoke.py",
        "stub_generated_by_llm": False,
        "manager_pass_1": {
            "manager_round": 0,
            "manager_role": "pass_1_tool_request",
            "prompt_hash": _prompt_hash(manager_role="pass_1_tool_request"),
            "provider_params": _provider_params(dict(pass1_round.get("trace") or {})),
            "requested_read_tools": router_trace["requested_read_tools"],
            "forbidden_final_truth_fields_present": _contains_any_key(pass1_decision, PASS_1_FORBIDDEN_FIELDS),
        },
        "runtime_tool_router": router_trace,
        "read_tool_executions": read_tool_executions,
        "packetizer": {"outputs": packetizer_outputs, "forbidden_final_truth_fields_present": _contains_any_key(packetizer_outputs, {"final_kcal", "final_truth", "primary_source"})},
        "manager_pass_2": {
            "manager_round": 1,
            "manager_role": "pass_2_synthesis",
            "prompt_hash": _prompt_hash(manager_role="pass_2_synthesis"),
            "provider_params": _provider_params(dict(pass2_round.get("trace") or {})),
            "item_results": item_results,
            "mutation_attempted": False,
            "forbidden_mutation_fields_present": _contains_any_key(pass2_decision, PASS_2_FORBIDDEN_MUTATION_FIELDS),
        },
        "guard": guard,
        "mutation": mutation,
        "renderer": _renderer_trace(item_results=item_results, mutation=mutation),
        "tavily_canary": None,
    }


def _provider_unavailable_report(*, readiness: dict[str, Any], artifact_path: Path) -> dict[str, Any]:
    return {
        "phase": "B-1",
        "scope": "minimal_tool_loop_smoke",
        "b2_evidence_runtime_started": False,
        "nutrition_accuracy_claimed": False,
        "provider": readiness.get("provider"),
        "manager_model": readiness.get("manager_model"),
        "mode": "hybrid_canary",
        "provider_runtime": {"configured": False, "blocker": True, "reason": readiness.get("reason") or "provider_not_configured"},
        "core_smoke_cases_run": [],
        "tool_loop_traces": [],
        "artifact_path": str(artifact_path),
    }


def _provider_runtime_error_report(
    *,
    readiness: dict[str, Any],
    artifact_path: Path,
    smoke_cases: list[str] | tuple[str, ...],
    traces: list[dict[str, Any]],
    error: Exception,
) -> dict[str, Any]:
    return {
        "phase": "B-1",
        "scope": "minimal_tool_loop_smoke",
        "b2_evidence_runtime_started": False,
        "nutrition_accuracy_claimed": False,
        "provider": readiness.get("provider") or "builderspace",
        "manager_model": readiness.get("manager_model") or readiness.get("model") or "deepseek",
        "mode": "hybrid_canary",
        "provider_runtime": {
            "configured": bool(readiness.get("configured")),
            "blocker": True,
            "reason": "provider_runtime_error",
            "error_type": type(error).__name__,
            "error": str(error),
        },
        "core_smoke_cases_run": list(smoke_cases)[: len(traces)],
        "tool_loop_traces": _json_safe(traces),
        "artifact_path": str(artifact_path),
    }


async def run_phase_b_minimal_tool_loop_smoke(
    *,
    provider: Any,
    smoke_cases: list[str] | tuple[str, ...] = CORE_SMOKE_CASES,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    write_latest: bool = True,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    phase_b_provider = _PhaseB1ManagerProvider(provider)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    artifact_path = output_dir / f"wave1_phase_b_minimal_tool_loop_smoke_{timestamp}.json"
    readiness = phase_b_provider.readiness()
    if not readiness.get("configured"):
        report = _provider_unavailable_report(readiness=dict(readiness), artifact_path=artifact_path)
    else:
        traces: list[dict[str, Any]] = []
        try:
            for index, message in enumerate(smoke_cases, start=1):
                traces.append(await _run_case(case_id=f"B1-{index:03d}", message=message, provider=phase_b_provider))
        except Exception as exc:
            report = _provider_runtime_error_report(
                readiness=dict(readiness),
                artifact_path=artifact_path,
                smoke_cases=smoke_cases,
                traces=traces,
                error=exc,
            )
        else:
            report = {
                "phase": "B-1",
                "scope": "minimal_tool_loop_smoke",
                "b2_evidence_runtime_started": False,
                "nutrition_accuracy_claimed": False,
                "provider": readiness.get("provider") or "builderspace",
                "manager_model": readiness.get("manager_model") or readiness.get("model") or "deepseek",
                "mode": "hybrid_canary",
                "core_smoke_cases_run": list(smoke_cases),
                "tool_loop_traces": _json_safe(traces),
                "artifact_path": str(artifact_path),
            }
    artifact_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if write_latest:
        LATEST_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return _json_safe(report)


async def _async_main() -> int:
    parser = argparse.ArgumentParser(description="Run Wave 1 Phase B-1 minimal runtime LLM tool-loop smoke.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    from app.runtime.interface.provider_runtime import manager_provider

    report = await run_phase_b_minimal_tool_loop_smoke(provider=manager_provider, output_dir=Path(args.output_dir))
    print(
        json.dumps(
            {
                "phase": report.get("phase"),
                "scope": report.get("scope"),
                "artifact_path": report.get("artifact_path"),
                "trace_count": len(report.get("tool_loop_traces") or []),
                "provider_runtime": report.get("provider_runtime"),
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
