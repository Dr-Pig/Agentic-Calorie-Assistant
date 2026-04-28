from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from ...nutrition.application.evidence_eligibility import classify_query_family, is_high_variance_family
from ...nutrition.application.estimate_artifacts import (
    EstimatedNutritionArtifact,
    build_exact_item_artifact,
    build_shadow_stub_artifact,
    shadow_stub_estimate_enabled,
)
from ...nutrition.agent.exact_item_packets import build_exact_item_lane_packet
from ...shared.contracts.intake import EstimatePayload
from ...shared.time_labels import resolve_local_attribution
from .intake_tool_runtime import looks_like_multi_item_input, normalize_live_payload


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
    search_adapter: Any | None = None,
    allow_search: bool = True,
    force_new_meal_context: bool = False,
    contextualized_query: str | None = None,
) -> EstimatedNutritionArtifact:
    del request_id, search_adapter, allow_search, contextualized_query
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
        return artifact

    if shadow_stub_estimate_enabled(provider=active_provider):
        return build_shadow_stub_artifact(
            db,
            user_external_id=user_external_id,
            raw_user_input=raw_user_input,
            local_date=local_date or datetime.now().date().isoformat(),
        )

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
    return artifact
