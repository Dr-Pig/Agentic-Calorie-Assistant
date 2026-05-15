from __future__ import annotations

import re
from typing import Any


def approved_nutrition_evidence_present(request_trace: dict[str, Any], manager_final: dict[str, Any]) -> bool:
    for payload in nutrition_payloads(request_trace, manager_final):
        trace_contract = _dict(payload.get("trace_contract"))
        approved = _dict(trace_contract.get("approved_fooddb_evidence_trace"))
        if approved.get("runtime_truth_allowed") is True:
            return True
        if trace_contract.get("db_hit_type") == "approved_fooddb_packet":
            return True
        user_kcal = _dict(trace_contract.get("approved_user_provided_kcal_trace"))
        if user_kcal.get("runtime_truth_allowed") is True:
            return True
    return False


def first_nutrition_trace_contract(request_trace: dict[str, Any], manager_final: dict[str, Any]) -> dict[str, Any]:
    for payload in nutrition_payloads(request_trace, manager_final):
        trace_contract = _dict(payload.get("trace_contract"))
        if trace_contract:
            return trace_contract
    return {}


def generic_range_evidence_present(trace_contract: dict[str, Any]) -> bool:
    approved = _dict(trace_contract.get("approved_fooddb_evidence_trace"))
    if approved.get("source_lane") != "generic_common_serving":
        return False
    if approved.get("runtime_truth_allowed") is not True:
        return False
    kcal_range = approved.get("kcal_range") or trace_contract.get("kcal_range")
    return isinstance(kcal_range, list) and len(kcal_range) >= 2


def visible_range_or_basis_present(request_trace: dict[str, Any]) -> bool:
    text = _visible_response_text(request_trace)
    if not text:
        return False
    if "常見份量" in text or "參考範圍" in text:
        return True
    return bool(re.search(r"\d+\s*-\s*\d+\s*kcal", text, flags=re.IGNORECASE))


def macro_visible(request_trace: dict[str, Any]) -> bool | None:
    for payload in nutrition_payloads(request_trace, {}):
        trace_contract = _dict(payload.get("trace_contract"))
        if trace_contract.get("macro_visibility_status") == "visible":
            return True
        if trace_contract.get("macro_visibility_status") in {"hidden", "hidden_missing_source", "not_available"}:
            return False
    return None


def component_basis_present(request_trace: dict[str, Any]) -> bool | None:
    for payload in nutrition_payloads(request_trace, {}):
        trace_contract = _dict(payload.get("trace_contract"))
        approved = _dict(trace_contract.get("approved_fooddb_evidence_trace"))
        commit_candidate = _dict(trace_contract.get("commit_request_candidate"))
        components = (
            _list(payload.get("components"))
            or _list(payload.get("component_estimates"))
            or _list(commit_candidate.get("items"))
            or _list(commit_candidate.get("components"))
        )
        if approved.get("source_lane") == "listed_component" and components:
            return True
    return None


def nutrition_packet_present(request_trace: dict[str, Any], manager_final: dict[str, Any]) -> bool:
    return bool(nutrition_payloads(request_trace, manager_final))


def nutrition_payloads(request_trace: dict[str, Any], manager_final: dict[str, Any]) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    tool_results = []
    tool_results.extend(_list(_dict(request_trace.get("tool_outputs")).get("tool_results")))
    tool_results.extend(_list(manager_final.get("tool_results")))
    tool_results.extend(_list(request_trace.get("compact_packets")))
    tool_results.extend(_list(_dict(request_trace.get("react_trace")).get("compact_packets")))
    for result in tool_results:
        payload = _dict(_dict(_dict(result).get("evidence")).get("nutrition_payload"))
        if payload:
            payloads.append(payload)
    return payloads


def _visible_response_text(request_trace: dict[str, Any]) -> str:
    renderer_output = _dict(request_trace.get("renderer_output"))
    text = str(renderer_output.get("assistant_message") or renderer_output.get("message") or "").strip()
    if text:
        return text
    manager_final = _dict(request_trace.get("manager_final_decision"))
    answer_contract = _dict(manager_final.get("answer_contract"))
    return str(
        answer_contract.get("reply_text")
        or answer_contract.get("text")
        or manager_final.get("response_summary")
        or ""
    ).strip()


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []
