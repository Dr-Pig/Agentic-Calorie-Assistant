from __future__ import annotations

import inspect
import json
from typing import Any, Awaitable


def json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def compact_resolved_state_prompt_payload(value: Any) -> dict[str, Any]:
    raw = _object_mapping(value)
    injected_context = raw.get("injected_context") if isinstance(raw.get("injected_context"), dict) else {}
    summary: dict[str, Any] = {}
    for key in ("onboarding_ready", "user_id", "user_external_id", "local_date"):
        if key in raw and _safe_summary_value(raw[key]):
            summary[key] = raw[key]
    summary["injected_context_presence"] = {
        "active_meal": _has_payload(injected_context.get("ACTIVE_MEAL")),
        "pending_followup": _pending_followup_open(injected_context.get("PENDING_FOLLOWUP")),
        "target_reference": _has_payload(injected_context.get("TARGET_MEAL_REFERENCE")),
        "current_budget": _has_payload(injected_context.get("CURRENT_BUDGET")),
        "active_body_plan": _has_payload(injected_context.get("ACTIVE_BODY_PLAN")),
        "recent_committed_meal_count": _list_count(injected_context.get("RECENT_COMMITTED_MEALS_SUMMARY")),
        "recent_chat_turn_count": _list_count(injected_context.get("RECENT_CHAT_TURNS")),
    }
    return {
        "prompt_payload_kind": "resolved_state_compact_summary",
        "source_role": "compatibility_legacy",
        "available": value is not None,
        "observed_type": observed_type_name(json_safe(raw if raw else value)),
        "summary": summary,
        "omitted_injected_context_keys": sorted(str(key) for key in injected_context),
        "full_state_omitted_from_prompt": True,
        "primary_context_source": "manager_context_packet_v1",
        "deterministic_semantic_authority": False,
    }


def compact_manager_product_policy_hints_prompt_payload(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    payload = _object_mapping(value)
    rules = payload.get("rules") if isinstance(payload.get("rules"), list) else []
    policy_ids = [
        str(rule.get("policy_id")).strip()
        for rule in rules
        if isinstance(rule, dict) and str(rule.get("policy_id") or "").strip()
    ]
    return {
        "prompt_payload_kind": "manager_product_policy_hints_compact_summary",
        "policy_source": payload.get("policy_source"),
        "policy_role": payload.get("policy_role"),
        "policy_ids": policy_ids,
        "rule_count": len(rules),
        "static_policy_text_source": "single_manager_system_prompt",
        "full_policy_text_omitted_from_prompt": True,
        "deterministic_semantic_authority": False,
    }


_NUTRITION_PAYLOAD_PROMPT_FIELDS = (
    "meal_title",
    "estimated_kcal",
    "route_target",
    "action_taken",
    "followup_question",
    "reply_text",
    "unresolved_info",
)
_TRACE_CONTRACT_PROMPT_FIELDS = (
    "route_family",
    "db_hit_type",
    "match_confidence",
    "response_mode_hint",
    "reason_not_direct_answer",
    "unresolved_info",
    "missing_slots",
    "blocking_slots",
    "canonical_write_decision",
    "macro_display_authorized",
    "macro_visibility_status",
    "macro_guard_reason",
    "grounding_summary",
    "why_not_exact",
    "search_attempt_count",
    "search_query",
    "correction_target_ref",
    "correction_operation",
    "intake_execution_guard_family",
    "best_estimate_mode",
    "estimate_confidence_tier",
)
_CORRECTION_TARGET_PROMPT_FIELDS = (
    "meal_thread_id",
    "meal_item_id",
    "canonical_name",
    "observed_canonical_name",
    "operation",
    "correction_operation",
    "target_resolution_source",
    "correction_confidence",
    "manager_target_proposal_validation",
)
_BUDGET_SUMMARY_PROMPT_FIELDS = (
    "budget_kcal",
    "consumed_kcal_before",
    "predicted_consumed_kcal_after",
    "predicted_remaining_kcal_after",
    "overshoot_detected",
    "overshoot_kcal",
    "replaced_kcal_before",
)


def compact_tool_results_prompt_payload(tool_results: Any) -> list[dict[str, Any]]:
    if not isinstance(tool_results, list):
        return []
    return [_compact_tool_result_prompt_payload(item) for item in tool_results if isinstance(item, dict)]


def _compact_tool_result_prompt_payload(tool_result: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {
        "prompt_payload_kind": "manager_tool_result_prompt_compact",
        "tool_name": tool_result.get("tool_name") or tool_result.get("name"),
        "confidence": tool_result.get("confidence"),
        "failure_family": tool_result.get("failure_family"),
    }
    if tool_result.get("error_message"):
        compact["error_message"] = tool_result.get("error_message")
    evidence = _object_mapping(tool_result.get("evidence"))
    if evidence:
        compact["evidence"] = _compact_tool_evidence_prompt_payload(evidence)
    provenance = _object_mapping(tool_result.get("provenance"))
    if provenance:
        compact["provenance"] = _compact_tool_provenance_prompt_payload(provenance)
    return {key: value for key, value in compact.items() if value not in (None, "", {}, [])}


def _compact_tool_evidence_prompt_payload(evidence: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    nutrition_payload = _object_mapping(evidence.get("nutrition_payload"))
    if nutrition_payload:
        compact["nutrition_payload"] = _compact_nutrition_payload_prompt_payload(nutrition_payload)
    target_evidence_payload = _object_mapping(evidence.get("target_evidence_payload"))
    if target_evidence_payload:
        compact["target_evidence_payload"] = target_evidence_payload
    return compact


def _compact_nutrition_payload_prompt_payload(payload: dict[str, Any]) -> dict[str, Any]:
    compact = _select_prompt_fields(payload, _NUTRITION_PAYLOAD_PROMPT_FIELDS)
    trace_contract = _object_mapping(payload.get("trace_contract"))
    if trace_contract:
        compact["trace_contract"] = _select_prompt_fields(trace_contract, _TRACE_CONTRACT_PROMPT_FIELDS)
    return compact


def _compact_tool_provenance_prompt_payload(provenance: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key in ("canonical_tool_name", "truth_owner", "tool_kind", "mutation_authority"):
        if key in provenance and provenance.get(key) not in (None, ""):
            compact[key] = json_safe(provenance[key])
    correction_target = _select_prompt_fields(
        _object_mapping(provenance.get("correction_target")),
        _CORRECTION_TARGET_PROMPT_FIELDS,
    )
    if correction_target:
        compact["correction_target"] = correction_target
    budget_summary = _select_prompt_fields(
        _object_mapping(provenance.get("budget_summary")),
        _BUDGET_SUMMARY_PROMPT_FIELDS,
    )
    if budget_summary:
        compact["budget_summary"] = budget_summary
    for key in ("macro_summary", "evidence_summary"):
        value = provenance.get(key)
        if value not in (None, "", {}, []):
            compact[key] = json_safe(value)
    return compact


def _select_prompt_fields(payload: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {key: json_safe(payload[key]) for key in fields if payload.get(key) not in (None, "", {}, [])}


def _object_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "__dict__"):
        return dict(vars(value))
    safe = json_safe(value)
    return dict(safe) if isinstance(safe, dict) else {}


def _safe_summary_value(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _has_payload(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, dict):
        return bool(value)
    if isinstance(value, (list, tuple, set)):
        return bool(value)
    return True


def _pending_followup_open(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if "is_open" in value:
        return bool(value.get("is_open"))
    return bool(value.get("pending_question") or value.get("question"))


def _list_count(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def observed_type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, tuple):
        return "tuple"
    return "unknown"


def value_excerpt(value: Any, *, max_chars: int = 1000) -> tuple[str, bool]:
    rendered = json.dumps(json_safe(value), ensure_ascii=False, default=str)
    if len(rendered) <= max_chars:
        return rendered, False
    return rendered[:max_chars], True


def tool_names(raw_tool_calls: Any) -> tuple[str, ...]:
    names: list[str] = []
    if not isinstance(raw_tool_calls, list):
        return tuple()
    for item in raw_tool_calls:
        if isinstance(item, dict):
            name = str(item.get("name") or item.get("tool_name") or "").strip()
        else:
            name = str(item or "").strip()
        if name:
            names.append(name)
    return tuple(names)


def tool_call_dicts(raw_tool_calls: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_tool_calls, list):
        return []
    result: list[dict[str, Any]] = []
    for item in raw_tool_calls:
        if isinstance(item, dict):
            name = str(item.get("name") or item.get("tool_name") or "").strip()
            arguments = item.get("arguments") if isinstance(item.get("arguments"), dict) else {}
        else:
            name = str(item or "").strip()
            arguments = {}
        if name:
            result.append({"name": name, "arguments": dict(arguments or {})})
    return result


async def maybe_await(value: Awaitable[Any] | Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def stable_available_tools(raw_tools: tuple[str, ...] | list[str] | Any) -> tuple[str, ...]:
    if not isinstance(raw_tools, (tuple, list)):
        return tuple()
    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw_tools:
        name = str(item or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        normalized.append(name)
    return tuple(sorted(normalized))
