from __future__ import annotations

from .. import SCHEMA_SIGNATURE
from ..application.answer_support import evaluate_answer as _evaluate_answer
from ..application.context_assembly import (
    normalize_text as _normalize_text,
    normalize_user_input_for_estimation as _normalize_user_input_for_estimation,
    normalized_input_from_debug_steps as _normalized_input_from_debug_steps,
)
from ..logging import append_audit_event, now_iso, write_request_trace_artifact
from ..observability.payload_builders import build_payload as _build_payload, unicode_escape as _unicode_escape
from ..schemas import AuditEvent, EstimatePayload, EstimateRequest


def build_api_fallback_payload(
    *,
    effective_request: EstimateRequest,
    request_id: str,
    request_text: str,
    risk_packet: dict,
    debug_steps: list[dict],
    llm_traces: list[dict],
) -> EstimatePayload:
    parsed = {
        "decision": "ASK_USER",
        "title": effective_request.text,
        "components": [],
        "protein_g": 0,
        "carb_g": 0,
        "fat_g": 0,
        "estimated_kcal": 0,
        "uncertainty_factors": ["insufficient meal detail"],
        "followup_question": "Please share the food details and portion size so I can estimate it more reliably.",
        "follow_up_needed": True,
        "follow_up_reasoning": "",
        "unresolved_info": ["meal_description", "portion_size"],
        "response_mode_hint": "clarify_first",
        "state_transition_hint": "draft_unresolved",
        "action_taken": "clarify_before_estimate",
        "tool_request": "none",
        "tool_request_reason": "",
        "answer_payload": {},
    }
    return _build_payload(
        effective_request,
        request_id=request_id,
        parsed=parsed,
        risk_packet=risk_packet,
        action_taken="api_fallback",
        route_target="best_effort_answer",
        route_reason="api_error",
        debug_steps=debug_steps,
        llm_traces=llm_traces,
        quality_signals=_evaluate_answer(parsed, risk_packet, None),
        private_only=True,
    )


def record_success(
    request: EstimateRequest,
    payload: EstimatePayload,
    *,
    source_page_version: str | None = None,
    normalized_user_input: str | None = None,
) -> None:
    raw_user_input = _normalize_text(request.text)
    normalized_input = _normalize_text(
        normalized_user_input
        or _normalized_input_from_debug_steps(payload.debug_steps)
        or _normalize_user_input_for_estimation(request.text)["normalized_text"]
    )
    event = AuditEvent(
        request_id=payload.request_id,
        timestamp=now_iso(),
        text=request.text,
        raw_user_input=raw_user_input,
        normalized_user_input=normalized_input,
        user_input_unicode_escape=_unicode_escape(request.text),
        source_page_version=source_page_version,
        allow_search=request.allow_search,
        status="ok",
        route_target=payload.route_target,
        action_taken=payload.action_taken,
        debug_steps=payload.debug_steps,
        llm_traces=payload.llm_traces,
        payload=payload.model_dump(mode="json"),
    )
    payload.trace_meta["source_page_version"] = source_page_version
    trace_path = write_request_trace_artifact(
        payload.request_id,
        {
            "request_id": payload.request_id,
            "timestamp": now_iso(),
            "request": {
                "user_id": getattr(request, "user_id", "anonymous"),
                "text": request.text,
                "allow_search": request.allow_search,
            },
            "raw_user_input": request.text,
            "normalized_user_input": normalized_input,
            "source_page_version": source_page_version,
            "trace_meta": payload.trace_meta or {},
            "span_timeline": payload.span_timeline or [],
            "decision_journal": payload.decision_journal or {},
            "evidence_journal": payload.evidence_journal or {},
            "diagnosis": payload.diagnosis or {},
            "multi_turn_context": payload.multi_turn_context or {},
            "token_usage": getattr(payload, "token_usage", {}) or {},
            "north_star_evaluation": payload.north_star_evaluation or {},
            "planner_result": (payload.trace_contract or {}).get("planner_output", {}),
            "trace_contract": payload.trace_contract or {},
            "payload": payload.model_dump(mode="json"),
            "debug_steps": payload.debug_steps,
            "llm_traces": payload.llm_traces,
        },
    )
    event.trace_artifact_path = str(trace_path)
    append_audit_event(event)


def record_error(
    request: EstimateRequest,
    error: str,
    *,
    request_id: str,
    source_page_version: str | None = None,
    normalized_user_input: str | None = None,
) -> None:
    raw_user_input = _normalize_text(request.text)
    normalized_input = _normalize_text(normalized_user_input or _normalize_user_input_for_estimation(request.text)["normalized_text"])
    event = AuditEvent(
        request_id=request_id,
        timestamp=now_iso(),
        text=request.text,
        raw_user_input=raw_user_input,
        normalized_user_input=normalized_input,
        user_input_unicode_escape=_unicode_escape(request.text),
        source_page_version=source_page_version,
        allow_search=request.allow_search,
        status="error",
        error=error,
    )
    trace_path = write_request_trace_artifact(
        request_id,
        {
            "request_id": request_id,
            "timestamp": now_iso(),
            "request": {
                "user_id": getattr(request, "user_id", "anonymous"),
                "text": request.text,
                "allow_search": request.allow_search,
            },
            "raw_user_input": request.text,
            "normalized_user_input": normalized_input,
            "source_page_version": source_page_version,
            "trace_meta": {
                "request_id": request_id,
                "user_id": getattr(request, "user_id", "anonymous"),
                "timestamp": now_iso(),
                "provider": None,
                "schema_signature": SCHEMA_SIGNATURE,
                "source_page_version": source_page_version,
            },
            "span_timeline": [],
            "decision_journal": {},
            "evidence_journal": {},
            "diagnosis": {
                "failed_layer": "repair_rescue",
                "why": error,
                "repairability": "high",
                "suggested_next_action": "inspect_request_trace",
                "trace_health": "degraded",
            },
            "error": error,
            "status": "error",
        },
    )
    event.trace_artifact_path = str(trace_path)
    append_audit_event(event)
