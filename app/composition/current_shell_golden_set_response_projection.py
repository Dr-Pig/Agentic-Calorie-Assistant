from __future__ import annotations

from typing import Any

from app.composition.current_shell_golden_set_request_trace_sources import trace_id


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def response_from_request_trace(request_trace: dict[str, Any]) -> dict[str, Any]:
    explicit = _dict(request_trace.get("response"))
    if explicit:
        return _with_visible_response_text(explicit, request_trace)
    response_grade = _dict(request_trace.get("response_grade"))
    if response_grade:
        return _with_visible_response_text(response_grade, request_trace)
    return _with_visible_response_text(_dict(_dict(request_trace.get("sidecar_output")).get("response")), request_trace)


def dogfood_trace_from_request_trace(request_trace: dict[str, Any]) -> dict[str, Any]:
    trace = _dict(request_trace.get("dogfood_trace"))
    trace_refs = _dict(request_trace.get("trace_refs"))
    resolved_trace_id = trace_id(request_trace)
    if resolved_trace_id:
        trace.setdefault("trace_id", resolved_trace_id)
    if trace_refs.get("request_id"):
        trace.setdefault("request_id", trace_refs.get("request_id"))
    feedback = _dict(request_trace.get("feedback_linkage"))
    if feedback:
        trace.setdefault("feedback_linkage", feedback)
        if feedback.get("feedback_links_to_trace") is not None:
            trace.setdefault("feedback_links_to_trace", bool(feedback.get("feedback_links_to_trace")))
            trace.setdefault("feedback_linkage_source", "request_trace_feedback_linkage")
    elif resolved_trace_id:
        trace.setdefault("feedback_links_to_trace", True)
        trace.setdefault("feedback_linkage_source", "trace_id_linkable_only")
    return trace


def _with_visible_response_text(response: dict[str, Any], request_trace: dict[str, Any]) -> dict[str, Any]:
    visible_text = str(response.get("visible_text") or "").strip()
    if not visible_text:
        visible_text = _visible_response_text(request_trace)
    if visible_text:
        response.setdefault("visible_text", visible_text)
        response.setdefault("assistant_message", visible_text)
    return response


def _visible_response_text(request_trace: dict[str, Any]) -> str:
    renderer_output = _dict(request_trace.get("renderer_output"))
    text = str(renderer_output.get("assistant_message") or renderer_output.get("message") or "").strip()
    if text:
        return text
    manager_final = _dict(request_trace.get("manager_final_decision"))
    answer_contract = _dict(manager_final.get("answer_contract"))
    return str(answer_contract.get("reply_text") or answer_contract.get("text") or "").strip()
