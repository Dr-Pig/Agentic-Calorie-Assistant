from __future__ import annotations

import re
from typing import Any


ROOT_CAUSE_BUCKETS = (
    "schema_drift",
    "encoding_corruption",
    "context_contamination",
    "tool_routing_gap",
    "fallback_pollution",
    "persistence_pollution",
)

ROOT_CAUSE_OWNERS: dict[str, list[str]] = {
    "schema_drift": [
        "app/agent/task_meal_link_llm.py",
        "app/agent/decision_llm.py",
        "app/agent/nutrition_resolution_llm.py",
        "app/application/pass_runner.py",
    ],
    "encoding_corruption": [
        "app/usecases/text_meal.py",
        "app/agent/final_response_llm.py",
        "app/observability/payload_builders.py",
    ],
    "context_contamination": [
        "app/application/context_assembly.py",
        "app/application/state_transition.py",
    ],
    "tool_routing_gap": [
        "app/usecases/text_meal.py",
        "app/application/evidence_assembly.py",
        "app/agent/decision_llm.py",
    ],
    "fallback_pollution": [
        "app/agent/final_response_llm.py",
        "app/observability/payload_builders.py",
    ],
    "persistence_pollution": [
        "app/infrastructure/meal_log_persistence.py",
        "app/usecases/text_meal.py",
    ],
}


def _payload(trace: dict[str, Any]) -> dict[str, Any]:
    return dict(trace.get("payload") or {})


def _llm_traces(trace: dict[str, Any]) -> list[dict[str, Any]]:
    traces = trace.get("llm_traces")
    if isinstance(traces, list):
        return [dict(item) for item in traces if isinstance(item, dict)]
    payload_traces = _payload(trace).get("llm_traces")
    if isinstance(payload_traces, list):
        return [dict(item) for item in payload_traces if isinstance(item, dict)]
    return []


def _debug_steps(trace: dict[str, Any]) -> list[dict[str, Any]]:
    steps = trace.get("debug_steps")
    if isinstance(steps, list):
        return [dict(item) for item in steps if isinstance(item, dict)]
    payload_steps = _payload(trace).get("debug_steps")
    if isinstance(payload_steps, list):
        return [dict(item) for item in payload_steps if isinstance(item, dict)]
    return []


def _trace_contract(trace: dict[str, Any]) -> dict[str, Any]:
    payload_contract = _payload(trace).get("trace_contract")
    if isinstance(payload_contract, dict):
        return dict(payload_contract)
    contract = trace.get("trace_contract")
    if isinstance(contract, dict):
        return dict(contract)
    return {}


def _diagnosis(trace: dict[str, Any]) -> dict[str, Any]:
    diagnosis = trace.get("diagnosis")
    if isinstance(diagnosis, dict):
        return dict(diagnosis)
    payload_diagnosis = _payload(trace).get("diagnosis")
    if isinstance(payload_diagnosis, dict):
        return dict(payload_diagnosis)
    return {}


def _request_text(trace: dict[str, Any]) -> str:
    request = trace.get("request")
    if isinstance(request, dict):
        return str(request.get("text") or "")
    return ""


def _reply_text(trace: dict[str, Any]) -> str:
    return str(_payload(trace).get("reply_text") or trace.get("reply_text") or "")


def _generic_clarify_reply(reply_text: str) -> bool:
    reply = reply_text.strip()
    return reply in {
        "請再描述更具體的食物名稱、份量或配料。",
        "請再描述更具體的內容與份量。",
    }


def _looks_mojibake(text: str) -> bool:
    if not text:
        return False
    if "\ufffd" in text:
        return True
    punct_noise = len(re.findall(r"\?[^\s]", text)) + len(re.findall(r"[^\s]\?", text))
    suspicious_tokens = sum(
        1
        for token in ("嚗", "鈭", "憭", "銝", "撖", "隢", "蝝", "雿", "鞈", "瘞", "摨", "踹")
        if token in text
    )
    return punct_noise >= 6 or (punct_noise >= 3 and suspicious_tokens >= 2)


def _has_encoding_corruption(trace: dict[str, Any]) -> bool:
    texts: list[str] = [_request_text(trace), _reply_text(trace)]
    trace_contract = _trace_contract(trace)
    multi_turn = trace.get("multi_turn_context") or _payload(trace).get("multi_turn_context") or trace_contract.get("multi_turn_context") or {}
    if isinstance(multi_turn, dict):
        texts.append(str(multi_turn.get("context_injection_snapshot") or ""))
        active = multi_turn.get("active_meal_summary") or {}
        if isinstance(active, dict):
            texts.append(str(active.get("meal_title") or ""))
    for step in _debug_steps(trace):
        for key in ("raw_user_input", "thin_sanitized_input", "planner_error", "error"):
            texts.append(str(step.get(key) or ""))
    return any(_looks_mojibake(text) for text in texts if text)


def _has_missing_field_error(trace: dict[str, Any], *, stages: tuple[str, ...] | None = None) -> bool:
    for step in _debug_steps(trace):
        stage = str(step.get("stage") or step.get("step") or "")
        if stages and not any(token in stage for token in stages):
            continue
        error = str(step.get("error") or step.get("planner_error") or "")
        if "missing_fields" in error:
            return True
    for llm_trace in _llm_traces(trace):
        stage = str(llm_trace.get("stage") or "")
        if stages and not any(token in stage for token in stages):
            continue
        error = str(llm_trace.get("error") or "")
        if "missing_fields" in error:
            return True
    return False


def _stage_failed(trace: dict[str, Any], stage_prefixes: tuple[str, ...]) -> bool:
    for llm_trace in _llm_traces(trace):
        stage = str(llm_trace.get("stage") or "")
        if any(stage.startswith(prefix) for prefix in stage_prefixes):
            if llm_trace.get("error"):
                return True
    for step in _debug_steps(trace):
        stage = str(step.get("stage") or step.get("step") or "")
        if any(stage.startswith(prefix) or prefix in stage for prefix in stage_prefixes):
            if str(step.get("status") or "") in {"failed", "degraded"} or step.get("error") or step.get("planner_error"):
                return True
    return False


def infer_first_bad_pass(trace: dict[str, Any]) -> str | None:
    diagnosis = _diagnosis(trace)
    failed_layer = str(diagnosis.get("failed_layer") or "").strip()
    bucket = classify_root_cause_bucket(trace)
    if _has_encoding_corruption(trace):
        return "task_meal_link_pass"
    if _stage_failed(trace, ("task_meal_link_pass", "planner_pass")) or failed_layer in {"planner", "normalizer"}:
        return "task_meal_link_pass"
    if bucket == "tool_routing_gap":
        return "decision_pass"
    if _stage_failed(trace, ("decision_pass",)) or failed_layer == "grounding":
        return "decision_pass"
    if _stage_failed(trace, ("nutrition_resolution_pass",)) or failed_layer in {"layer3_primary_llm", "risk_validator"}:
        return "nutrition_resolution_pass"
    if bucket == "fallback_pollution":
        return "final_response_pass"
    if bucket == "persistence_pollution":
        return "persistence_decision"
    if _stage_failed(trace, ("final_response_pass",)) or _generic_clarify_reply(_reply_text(trace)):
        return "final_response_pass"
    persistence = _trace_contract(trace).get("persistence_decision") or {}
    if isinstance(persistence, dict) and persistence:
        if str(persistence.get("status") or "") == "completed_meal":
            unresolved = _trace_contract(trace).get("unresolved_info") or []
            if unresolved:
                return "persistence_decision"
    return None


def classify_root_cause_bucket(trace: dict[str, Any]) -> str | None:
    trace_contract = _trace_contract(trace)
    reply_text = _reply_text(trace)
    if _has_encoding_corruption(trace):
        return "encoding_corruption"
    if _has_missing_field_error(trace):
        return "schema_drift"
    boundary = trace_contract.get("boundary_trace") or {}
    if isinstance(boundary, dict):
        if str(boundary.get("meal_boundary") or "") == "start_new_meal" and bool(boundary.get("active_meal_context_allowed")):
            return "context_contamination"
    tool_decision = trace_contract.get("tool_decision_trace") or {}
    if isinstance(tool_decision, dict):
        candidate = tool_decision.get("candidate_tool_calls") or []
        executed = tool_decision.get("executed_tool_calls") or []
        if candidate and not [item for item in executed if str(item.get("status") or "") == "executed"]:
            return "tool_routing_gap"
    if _generic_clarify_reply(reply_text):
        final_answer = trace_contract.get("final_answer_summary") or {}
        if isinstance(final_answer, dict) and int(final_answer.get("estimated_kcal") or 0) > 0:
            return "fallback_pollution"
    if any(token in reply_text for token in ("0 kcal", "0g", "0 大卡")):
        return "fallback_pollution"
    persistence = trace_contract.get("persistence_decision") or {}
    if isinstance(persistence, dict) and persistence:
        persisted_status = str(persistence.get("status") or "")
        unresolved = trace_contract.get("unresolved_info") or []
        if persisted_status == "completed_meal" and unresolved:
            return "persistence_pollution"
    return None


def _find_stage_trace(trace: dict[str, Any], stage_name: str) -> dict[str, Any]:
    for item in _llm_traces(trace):
        stage = str(item.get("stage") or "")
        if stage == stage_name or stage.startswith(stage_name):
            return item
    return {}


def _raw_output_for_pass(trace: dict[str, Any], first_bad_pass: str | None) -> dict[str, Any]:
    if not first_bad_pass:
        return {}
    stage_trace = _find_stage_trace(trace, first_bad_pass)
    return {
        "stage": str(stage_trace.get("stage") or first_bad_pass),
        "parsed_object": stage_trace.get("parsed_object"),
        "raw_content": stage_trace.get("raw_content"),
        "error": stage_trace.get("error"),
    }


def _normalized_output_for_pass(trace: dict[str, Any], first_bad_pass: str | None) -> dict[str, Any]:
    trace_contract = _trace_contract(trace)
    if first_bad_pass == "task_meal_link_pass":
        return dict(trace_contract.get("planner_output") or {})
    if first_bad_pass == "decision_pass":
        return {
            "followup_decision": trace_contract.get("followup_decision"),
            "followup_policy_decision": trace_contract.get("followup_policy_decision"),
            "route_family": trace_contract.get("route_family"),
        }
    if first_bad_pass == "nutrition_resolution_pass":
        return dict(trace_contract.get("final_answer_summary") or {})
    if first_bad_pass == "final_response_pass":
        return {"reply_text": _reply_text(trace)}
    if first_bad_pass == "persistence_decision":
        persistence = trace_contract.get("persistence_decision") or {}
        return dict(persistence) if isinstance(persistence, dict) else {}
    return {}


def _fallback_reason(trace: dict[str, Any], first_bad_pass: str | None) -> str:
    if not first_bad_pass:
        return ""
    for step in _debug_steps(trace):
        stage = str(step.get("stage") or step.get("step") or "")
        if first_bad_pass in stage or (
            first_bad_pass == "task_meal_link_pass" and stage == "planner_pass"
        ):
            return str(step.get("error") or step.get("planner_error") or "")
    diagnosis = _diagnosis(trace)
    return str(diagnosis.get("why") or "")


def build_live_trace_triage(
    trace: dict[str, Any],
    *,
    expected_behavior: str = "",
) -> dict[str, Any]:
    first_bad_pass = infer_first_bad_pass(trace)
    root_cause_bucket = classify_root_cause_bucket(trace)
    return {
        "user_input": _request_text(trace),
        "expected_behavior": expected_behavior,
        "actual_reply": _reply_text(trace),
        "first_bad_pass": first_bad_pass,
        "raw_provider_output": _raw_output_for_pass(trace, first_bad_pass),
        "normalized_output": _normalized_output_for_pass(trace, first_bad_pass),
        "fallback_or_degraded_reason": _fallback_reason(trace, first_bad_pass),
        "suspected_root_cause_bucket": root_cause_bucket,
        "owner_file": ROOT_CAUSE_OWNERS.get(root_cause_bucket or "", []),
    }
