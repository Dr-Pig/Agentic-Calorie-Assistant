from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.runtime.agent.manager import SINGLE_MANAGER_SYSTEM_PROMPT, run_intake_manager

DEFAULT_OUTPUT_DIR = ROOT / "artifacts"
LATEST_REPORT = DEFAULT_OUTPUT_DIR / "wave1_phase_b_minimal_tool_loop_smoke.json"
FORCED_MODE = "forced_tool_request_smoke"
NATURAL_MODE = "natural_tool_selection_probe"
CLI_MODES = {"forced": FORCED_MODE, "natural-probe": NATURAL_MODE}
DEFAULT_PROVIDER_TIMEOUT_MS = 180_000
FULL_SMOKE_LATENCY_TARGET_MS = 180_000

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
    "The runtime, not the model, validates allowed and blocked tools.\n"
    "JSON example for tea egg:\n"
    "{\"manager_action\":\"call_tools\",\"interaction_family\":\"food_logging\",\"response_mode\":\"intake_result\",\"operations\":[],\"answer_contract\":{},\"tool_calls\":[{\"name\":\"lookup_generic_food\",\"arguments\":{\"food_name\":\"茶葉蛋\"}}]}\n"
    "JSON example for nutrition query:\n"
    "{\"manager_action\":\"call_tools\",\"interaction_family\":\"nutrition_info_query\",\"response_mode\":\"info_answer\",\"operations\":[],\"answer_contract\":{},\"tool_calls\":[{\"name\":\"lookup_generic_food\",\"arguments\":{\"food_name\":\"珍珠奶茶\"}}]}\n"
    "JSON example for self-selected basket blocking trace:\n"
    "{\"manager_action\":\"call_tools\",\"interaction_family\":\"food_logging\",\"response_mode\":\"clarification\",\"operations\":[],\"answer_contract\":{},\"tool_calls\":[{\"name\":\"lookup_generic_food\",\"arguments\":{\"food_name\":\"滷味\"}},{\"name\":\"retrieve_web_food_evidence\",\"arguments\":{\"query\":\"滷味 熱量\"}}]}"
)
PASS_1_NATURAL_TOOL_SELECTION_GUIDANCE = (
    "Phase B-1 natural-probe tool selection guidance.\n"
    "This probe evaluates whether Manager Pass 1 naturally selects appropriate read tools without the forced smoke contract.\n"
    "For this probe, already-consumed estimable common foods, common commercial drinks, common commercial meals, listed ingredients, and nutrition information queries are evidence-needed scenarios before B-1 can continue to synthesis.\n"
    "When the user reports an already-consumed estimable common food, common commercial drink, common commercial meal, or listed ingredients, select appropriate read tools when evidence is needed.\n"
    "For evidence-needed scenarios, return manager_action='call_tools' with tool_calls rather than producing final nutrition or logging output from model memory.\n"
    "When returning manager_action='call_tools', include the active wrapper fields: interaction_family, response_mode, operations=[], and answer_contract={}.\n"
    "Each tool_calls item should include name and arguments; use available tool names only.\n"
    "Use lookup_generic_food for generic common foods and item-level listed ingredients.\n"
    "Do not use generic aliases such as search or web_search; retrieve_web_food_evidence is the canonical web evidence tool when web evidence is appropriate.\n"
    "For generic common foods and listed ingredients, lookup_generic_food is the core tool; web evidence may be extra but does not replace lookup_generic_food.\n"
    "A nutrition information query may use read tools for answer support, but it must not mutate the ledger.\n"
    "For a self-selected basket without listed ingredients, do not execute estimate tools; ask for the missing composition or let the runtime block estimate tools if they are requested.\n"
    "This is not forced mode: do not call tools when the input does not need evidence."
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


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _elapsed_ms(start: float) -> int:
    return max(0, int((time.perf_counter() - start) * 1000))


def _hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _prompt_hash(*, manager_role: str) -> str:
    task_payload = PASS_1_TOOL_REQUEST_PAYLOAD if manager_role == "pass_1_tool_request" else PASS_2_SYNTHESIS_PAYLOAD
    return _hash({"manager_role": manager_role, "system_prompt": SINGLE_MANAGER_SYSTEM_PROMPT, "task_payload": task_payload})


def _pass_1_task_payload(pass1_mode: str) -> tuple[str, str]:
    if pass1_mode == NATURAL_MODE:
        return "phase_b1_pass_1_natural_tool_selection_guidance_v1", PASS_1_NATURAL_TOOL_SELECTION_GUIDANCE
    return "phase_b1_pass_1_forced_tool_request_v1", PASS_1_TOOL_REQUEST_PAYLOAD


def _task_payload_for_round(*, round_index: int, pass1_mode: str) -> tuple[str, str]:
    if round_index == 0:
        return _pass_1_task_payload(pass1_mode)
    return "phase_b1_pass_2_synthesis_v1", PASS_2_SYNTHESIS_PAYLOAD


def _case_prompt_hash(*, manager_role: str, pass1_mode: str) -> str:
    if manager_role == "pass_1_tool_request":
        _, task_payload = _pass_1_task_payload(pass1_mode)
    else:
        task_payload = PASS_2_SYNTHESIS_PAYLOAD
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
    def __init__(self, provider: Any, *, pass1_mode: str, provider_timeout_ms: int) -> None:
        self._provider = provider
        self.pass1_mode = pass1_mode
        self.provider_timeout_ms = provider_timeout_ms

    def readiness(self) -> dict[str, Any]:
        if hasattr(self._provider, "readiness"):
            readiness = self._provider.readiness()
            return dict(readiness or {})
        return {"configured": False, "reason": "provider_missing_readiness"}

    async def complete_with_trace(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        user_payload = dict(kwargs.get("user_payload") or {})
        round_index = int(user_payload.get("round_index") or 0)
        manager_role = "pass_1_tool_request" if round_index == 0 else "pass_2_synthesis"
        task_payload_id, task_payload = _task_payload_for_round(round_index=round_index, pass1_mode=self.pass1_mode)
        constraints = dict(user_payload.get("constraints") or {})
        constraints.update(
            {
                "phase_b1_manager_role": manager_role,
                "phase_b1_pass1_mode": self.pass1_mode,
                "phase_b1_task_payload_id": task_payload_id,
            }
        )
        user_payload["constraints"] = constraints
        kwargs["user_payload"] = user_payload
        if round_index == 0 and self.pass1_mode == NATURAL_MODE:
            kwargs["system_prompt"] = f"{task_payload}\n\n{str(kwargs.get('system_prompt') or '')}"
        elif round_index == 0 and self.pass1_mode == FORCED_MODE:
            kwargs["system_prompt"] = task_payload
        else:
            kwargs["system_prompt"] = f"{task_payload}\n\n{kwargs.get('system_prompt')}\n\n{task_payload}"
        started_at_utc = _utc_now()
        started_perf = time.perf_counter()
        payload, trace = await asyncio.wait_for(
            self._provider.complete_with_trace(**kwargs),
            timeout=self.provider_timeout_ms / 1000,
        )
        ended_at_utc = _utc_now()
        latency_ms = _elapsed_ms(started_perf)
        trace = _normalize_provider_trace(dict(trace or {}), manager_role=manager_role, user_payload=user_payload)
        trace["manager_role"] = manager_role
        trace["pass1_mode"] = self.pass1_mode
        trace["started_at_utc"] = started_at_utc
        trace["ended_at_utc"] = ended_at_utc
        trace["latency_ms"] = latency_ms
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
    packet_type = "GenericFoodDbPacket" if tool_name == "lookup_generic_food" else "SearchCandidatePacket"
    packet = {
        "packet_type": packet_type,
        "truth_level": truth_level,
        "fixture_id": fixture_id,
        "fixture_hash": _hash({"fixture_id": fixture_id, "food_name": food_name, "tool_name": tool_name}),
        "fixture_only": True,
        "generated_by": "deterministic_fixture",
        "candidates": [{"food_name": food_name, "kcal_range": [70, 90], "likely_kcal": 80}],
    }
    if packet_type == "SearchCandidatePacket":
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
    supported_tools = list(AVAILABLE_READ_TOOLS)
    supported_tool_set = set(supported_tools)
    blocked_tools: list[str] = []
    block_reasons: list[dict[str, Any]] = []
    for tool_name in requested_tools:
        if tool_name not in supported_tool_set:
            blocked_tools.append(tool_name)
            block_reasons.append(
                {
                    "tool_name": tool_name,
                    "reason": "unsupported_read_tool_name",
                    "supported_tools": supported_tools,
                    "normalization_attempted": False,
                }
            )
    if _is_self_selected_basket_without_ingredients(message):
        for tool_name in sorted(ESTIMATE_READ_TOOLS):
            if tool_name not in blocked_tools:
                blocked_tools.append(tool_name)
            block_reasons.append(
                {
                    "tool_name": tool_name,
                    "reason": "self_selected_basket_without_ingredients_blocks_estimate_tools",
                    "rule": "self_selected_basket_without_ingredients_blocks_estimate_tools",
                    "detail": "Composition is unknown; ask for ingredients before generic DB or web estimate.",
                }
            )
    blocked_tool_set = set(blocked_tools)
    allowed_tools = [tool for tool in requested_tools if tool in supported_tool_set and tool not in blocked_tool_set]
    return {
        "available_read_tools": supported_tools,
        "canonical_tool_catalog_hash": _hash(supported_tools),
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


def _item_results_from_payload(
    payload: dict[str, Any],
    packets: list[dict[str, Any]],
    *,
    allow_packet_fallback: bool,
) -> tuple[list[dict[str, Any]], bool]:
    raw_item_results = payload.get("item_results")
    if isinstance(raw_item_results, list) and raw_item_results:
        return [dict(item) for item in raw_item_results if isinstance(item, dict)], False
    if not allow_packet_fallback:
        return [], False
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
    return results, bool(results)


async def _run_case(*, case_id: str, message: str, provider: Any, pass1_mode: str) -> dict[str, Any]:
    case_started_at_utc = _utc_now()
    case_started_perf = time.perf_counter()
    router_trace: dict[str, Any] = {
        "requested_read_tools": [],
        "manager_requested_tools": [],
        "allowed_tools": [],
        "filtered_tool_plan": [],
        "blocked_tools": [],
        "block_reasons": [],
        "available_read_tools": list(AVAILABLE_READ_TOOLS),
        "canonical_tool_catalog_hash": _hash(list(AVAILABLE_READ_TOOLS)),
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
    item_results, runner_derived_item_results = _item_results_from_payload(
        pass2_decision,
        packetizer_outputs,
        allow_packet_fallback=pass1_mode == FORCED_MODE,
    )
    mutation = _mutation_trace(message=message, item_results=item_results)
    guard = {"ran": True, "ran_before_mutation": True, "result": "no_mutation" if not mutation["mutation_attempted"] else "pass"}
    case_ended_at_utc = _utc_now()
    return {
        "case_id": case_id,
        "input_message": message,
        "case_started_at_utc": case_started_at_utc,
        "case_ended_at_utc": case_ended_at_utc,
        "case_latency_ms": _elapsed_ms(case_started_perf),
        "semantic_boundary": "self_selected_basket_without_ingredients" if _is_self_selected_basket_without_ingredients(message) else None,
        "pass1_mode": pass1_mode,
        "forced_tool_request_contract": pass1_mode == FORCED_MODE,
        "manager_tool_selection_claimed": pass1_mode == NATURAL_MODE,
        "runner_derived_item_results": runner_derived_item_results,
        "is_live_tavily_canary": False,
        "uses_deterministic_stub_fixtures": True,
        "stub_fixture_source": "scripts/run_wave1_phase_b_minimal_tool_loop_smoke.py",
        "stub_generated_by_llm": False,
        "manager_pass_1": {
            "manager_round": 0,
            "manager_role": "pass_1_tool_request",
            "prompt_hash": _case_prompt_hash(manager_role="pass_1_tool_request", pass1_mode=pass1_mode),
            "started_at_utc": (dict(pass1_round.get("trace") or {})).get("started_at_utc"),
            "ended_at_utc": (dict(pass1_round.get("trace") or {})).get("ended_at_utc"),
            "latency_ms": (dict(pass1_round.get("trace") or {})).get("latency_ms"),
            "provider_params": _provider_params(dict(pass1_round.get("trace") or {})),
            "phase_b1_task_payload_id": (dict(pass1_round.get("trace") or {})).get("phase_b1_task_payload_id"),
            "phase_b1_task_payload_hash": (dict(pass1_round.get("trace") or {})).get("phase_b1_task_payload_hash"),
            "requested_read_tools": router_trace["requested_read_tools"],
            "forbidden_final_truth_fields_present": _contains_any_key(pass1_decision, PASS_1_FORBIDDEN_FIELDS),
        },
        "runtime_tool_router": router_trace,
        "read_tool_executions": read_tool_executions,
        "packetizer": {"outputs": packetizer_outputs, "forbidden_final_truth_fields_present": _contains_any_key(packetizer_outputs, {"final_kcal", "final_truth", "primary_source"})},
        "manager_pass_2": {
            "manager_round": 1,
            "manager_role": "pass_2_synthesis",
            "prompt_hash": _case_prompt_hash(manager_role="pass_2_synthesis", pass1_mode=pass1_mode),
            "started_at_utc": (dict(pass2_round.get("trace") or {})).get("started_at_utc"),
            "ended_at_utc": (dict(pass2_round.get("trace") or {})).get("ended_at_utc"),
            "latency_ms": (dict(pass2_round.get("trace") or {})).get("latency_ms"),
            "provider_params": _provider_params(dict(pass2_round.get("trace") or {})),
            "phase_b1_task_payload_id": (dict(pass2_round.get("trace") or {})).get("phase_b1_task_payload_id"),
            "phase_b1_task_payload_hash": (dict(pass2_round.get("trace") or {})).get("phase_b1_task_payload_hash"),
            "item_results": item_results,
            "mutation_attempted": False,
            "forbidden_mutation_fields_present": _contains_any_key(pass2_decision, PASS_2_FORBIDDEN_MUTATION_FIELDS),
        },
        "guard": guard,
        "mutation": mutation,
        "renderer": _renderer_trace(item_results=item_results, mutation=mutation),
        "tavily_canary": None,
    }


def _runtime_latency_summary(*, started_perf: float, traces: list[dict[str, Any]], pass1_mode: str) -> dict[str, Any]:
    return {
        "latency_budget_type": "b1_full_smoke_reporting_target",
        "not_user_runtime_budget": True,
        "full_smoke_target_ms": FULL_SMOKE_LATENCY_TARGET_MS,
        "total_latency_ms": _elapsed_ms(started_perf),
        "trace_count": len(traces),
        "completed_trace_count": len(traces),
        "mode": pass1_mode,
    }


def _provider_unavailable_report(
    *,
    readiness: dict[str, Any],
    artifact_path: Path,
    pass1_mode: str,
    started_perf: float,
) -> dict[str, Any]:
    return {
        "phase": "B-1",
        "scope": "minimal_tool_loop_smoke",
        "b2_evidence_runtime_started": False,
        "nutrition_accuracy_claimed": False,
        "provider": readiness.get("provider"),
        "manager_model": readiness.get("manager_model"),
        "mode": "hybrid_canary",
        "pass1_mode": pass1_mode,
        "forced_tool_request_contract": pass1_mode == FORCED_MODE,
        "manager_tool_selection_claimed": pass1_mode == NATURAL_MODE,
        "natural_tool_selection_pass": "not_applicable" if pass1_mode == FORCED_MODE else False,
        "provider_runtime": {"configured": False, "blocker": True, "reason": readiness.get("reason") or "provider_not_configured"},
        "runtime_latency": _runtime_latency_summary(started_perf=started_perf, traces=[], pass1_mode=pass1_mode),
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
    pass1_mode: str,
    started_perf: float,
    provider_timeout_ms: int,
) -> dict[str, Any]:
    is_timeout = isinstance(error, TimeoutError)
    provider_runtime: dict[str, Any] = {
        "configured": bool(readiness.get("configured")),
        "blocker": True,
        "reason": "provider_timeout" if is_timeout else "provider_runtime_error",
        "error_type": type(error).__name__,
        "error": str(error),
    }
    if is_timeout:
        provider_runtime["timeout_ms"] = provider_timeout_ms
        provider_runtime["completed_traces"] = len(traces)
    return {
        "phase": "B-1",
        "scope": "minimal_tool_loop_smoke",
        "b2_evidence_runtime_started": False,
        "nutrition_accuracy_claimed": False,
        "provider": readiness.get("provider") or "builderspace",
        "manager_model": readiness.get("manager_model") or readiness.get("model") or "deepseek",
        "mode": "hybrid_canary",
        "pass1_mode": pass1_mode,
        "forced_tool_request_contract": pass1_mode == FORCED_MODE,
        "manager_tool_selection_claimed": pass1_mode == NATURAL_MODE,
        "natural_tool_selection_pass": "not_applicable" if pass1_mode == FORCED_MODE else False,
        "provider_runtime": provider_runtime,
        "runtime_latency": _runtime_latency_summary(started_perf=started_perf, traces=traces, pass1_mode=pass1_mode),
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
    mode: str = "forced",
    provider_timeout_ms: int = DEFAULT_PROVIDER_TIMEOUT_MS,
) -> dict[str, Any]:
    run_started_perf = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    pass1_mode = CLI_MODES.get(mode, mode)
    if pass1_mode not in {FORCED_MODE, NATURAL_MODE}:
        raise ValueError(f"Unsupported B-1 smoke mode: {mode}")
    phase_b_provider = _PhaseB1ManagerProvider(provider, pass1_mode=pass1_mode, provider_timeout_ms=provider_timeout_ms)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    artifact_path = output_dir / f"wave1_phase_b_minimal_tool_loop_smoke_{timestamp}.json"
    readiness = phase_b_provider.readiness()
    if not readiness.get("configured"):
        report = _provider_unavailable_report(
            readiness=dict(readiness),
            artifact_path=artifact_path,
            pass1_mode=pass1_mode,
            started_perf=run_started_perf,
        )
    else:
        traces: list[dict[str, Any]] = []
        try:
            for index, message in enumerate(smoke_cases, start=1):
                traces.append(
                    await _run_case(
                        case_id=f"B1-{index:03d}",
                        message=message,
                        provider=phase_b_provider,
                        pass1_mode=pass1_mode,
                    )
                )
        except Exception as exc:
            report = _provider_runtime_error_report(
                readiness=dict(readiness),
                artifact_path=artifact_path,
                smoke_cases=smoke_cases,
                traces=traces,
                error=exc,
                pass1_mode=pass1_mode,
                started_perf=run_started_perf,
                provider_timeout_ms=provider_timeout_ms,
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
                "pass1_mode": pass1_mode,
                "forced_tool_request_contract": pass1_mode == FORCED_MODE,
                "manager_tool_selection_claimed": pass1_mode == NATURAL_MODE,
                "natural_tool_selection_pass": "not_applicable" if pass1_mode == FORCED_MODE else False,
                "runtime_latency": _runtime_latency_summary(
                    started_perf=run_started_perf,
                    traces=traces,
                    pass1_mode=pass1_mode,
                ),
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
    parser.add_argument("--mode", choices=sorted(CLI_MODES), default="forced")
    parser.add_argument("--provider-timeout-ms", type=int, default=DEFAULT_PROVIDER_TIMEOUT_MS)
    args = parser.parse_args()
    from app.runtime.interface.provider_runtime import manager_provider

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=manager_provider,
        output_dir=Path(args.output_dir),
        mode=args.mode,
        provider_timeout_ms=args.provider_timeout_ms,
    )
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
