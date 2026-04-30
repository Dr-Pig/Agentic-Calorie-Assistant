from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.intake.application.intake_tool_runtime import looks_like_multi_item_input, normalize_live_payload
from app.nutrition.agent.exact_item_packets import build_exact_item_lane_packet
from app.nutrition.application.estimate_artifacts import (
    EstimatedNutritionArtifact,
    build_exact_item_artifact,
    build_shadow_stub_artifact,
    shadow_stub_estimate_enabled,
)
from app.nutrition.application.evidence_eligibility import classify_query_family, is_high_variance_family
from app.nutrition.application.exact_brand_web_canary import LANE_ID as WEB_CANARY_LANE_ID
from app.nutrition.application.exact_brand_web_canary import run_exact_brand_web_canary
from app.nutrition.application.web_extract_port import WebExtractPort
from app.nutrition.application.web_search_port import WebSearchPort
from app.shared.contracts.intake import EstimatePayload
from app.shared.time_labels import resolve_local_attribution


def _fill_missing_trace_dates(payload: EstimatePayload) -> None:
    trace_contract = dict(payload.trace_contract or {})
    if str(trace_contract.get("local_date") or "").strip():
        payload.trace_contract = trace_contract
        return
    attribution = resolve_local_attribution(
        trace_contract.get("occurred_at"),
        timezone_name=str(trace_contract.get("timezone") or "") or None,
    )
    if attribution.get("occurred_at") is not None:
        trace_contract["occurred_at"] = attribution["occurred_at"]
    if str(attribution.get("occurred_at_utc") or "").strip():
        trace_contract["occurred_at_utc"] = attribution["occurred_at_utc"]
    if str(attribution.get("occurred_at_local") or "").strip():
        trace_contract["occurred_at_local"] = attribution["occurred_at_local"]
    if str(attribution.get("local_date") or "").strip():
        trace_contract["local_date"] = attribution["local_date"]
    if str(attribution.get("timezone") or "").strip():
        trace_contract["timezone"] = attribution["timezone"]
    trace_contract.setdefault("search_attempt_count", 0)
    trace_contract.setdefault("grounding_summary", {"exact_truth_present": False, "retrieved_knowledge_count": 0, "evidence_roles": []})
    trace_contract.setdefault("reasoning_state", {"exact_lane_count": 0, "search_attempt_count": 0})
    payload.trace_contract = trace_contract


async def estimate_nutrition_tool(
    db: Session,
    *,
    user_external_id: str,
    raw_user_input: str,
    request_id: str,
    local_date: str,
    manager_provider: Any | None = None,
    provider: Any | None = None,
    search_port: WebSearchPort | None = None,
    extract_port: WebExtractPort | None = None,
    allow_search: bool = True,
    force_new_meal_context: bool = False,
    contextualized_query: str | None = None,
) -> EstimatedNutritionArtifact:
    del request_id
    active_provider = manager_provider or provider
    exact_packet = build_exact_item_lane_packet(raw_user_input, limit=3)
    top_exact_candidate = exact_packet.get("top_exact_candidate")
    if isinstance(top_exact_candidate, dict) and not looks_like_multi_item_input(raw_user_input):
        artifact = build_exact_item_artifact(
            db,
            user_external_id=user_external_id,
            raw_user_input=raw_user_input,
            local_date=local_date or datetime.now().date().isoformat(),
            exact_candidate=top_exact_candidate,
        )
        normalize_live_payload(artifact.payload, raw_user_input=raw_user_input)
        _attach_web_runtime_trace(
            artifact.payload,
            {
                **_default_web_runtime_trace(),
                "skip_reason": "exact_db_hit",
            },
        )
        return artifact

    canary_outcome = await run_exact_brand_web_canary(
        raw_user_input=raw_user_input,
        search_port=search_port,
        extract_port=extract_port,
        allow_search=allow_search,
        contextualized_query=contextualized_query,
    )

    if shadow_stub_estimate_enabled(provider=active_provider):
        artifact = build_shadow_stub_artifact(
            db,
            user_external_id=user_external_id,
            raw_user_input=raw_user_input,
            local_date=local_date or datetime.now().date().isoformat(),
        )
        _attach_web_runtime_trace(artifact.payload, canary_outcome.trace)
        return artifact

    artifact = build_shadow_stub_artifact(
        db,
        user_external_id=user_external_id,
        raw_user_input=raw_user_input,
        local_date=local_date or datetime.now().date().isoformat(),
    )
    if force_new_meal_context:
        if hasattr(artifact.runtime_context, "latest_log"):
            artifact.runtime_context.latest_log = None
        if hasattr(artifact.runtime_context, "conversation_state"):
            conversation_state = getattr(artifact.runtime_context, "conversation_state")
            if conversation_state is not None and hasattr(conversation_state, "pending_followup_state"):
                pending_state = getattr(conversation_state, "pending_followup_state")
                if pending_state is not None and hasattr(pending_state, "is_open"):
                    pending_state.is_open = False
    _fill_missing_trace_dates(artifact.payload)
    normalize_live_payload(
        artifact.payload,
        raw_user_input=raw_user_input,
        family_rule=classify_query_family(raw_user_input),
        high_variance=is_high_variance_family(raw_user_input),
    )
    _attach_web_runtime_trace(artifact.payload, canary_outcome.trace)
    return artifact


def _default_web_runtime_trace() -> dict[str, Any]:
    return {
        "lane_id": WEB_CANARY_LANE_ID,
        "attempted": False,
        "skip_reason": None,
        "failure_reason": None,
        "search_query": None,
        "selected_search_packet_id": None,
        "accepted_extract_packet_id": None,
        "selected_url": None,
        "search_attempt_count": 0,
        "extract_attempt_count": 0,
        "search_latency_ms": 0,
        "extract_latency_ms": 0,
        "total_latency_ms": 0,
        "cost": None,
        "packetized_candidate_present": False,
        "manager_pass_2_saw_search_packet": False,
        "extract_attempted": False,
        "retrieval_goal": None,
        "exact_db_miss_confirmed": False,
    }


def _attach_web_runtime_trace(payload: EstimatePayload, trace: dict[str, Any]) -> None:
    trace_contract = dict(payload.trace_contract or {})
    trace_contract["web_runtime_trace"] = dict(trace)
    trace_contract["search_attempt_count"] = int(trace.get("search_attempt_count") or 0)
    trace_contract["search_query"] = trace.get("search_query")
    reasoning_state = dict(trace_contract.get("reasoning_state") or {})
    reasoning_state["search_attempt_count"] = int(trace.get("search_attempt_count") or 0)
    trace_contract["reasoning_state"] = reasoning_state
    payload.trace_contract = trace_contract
