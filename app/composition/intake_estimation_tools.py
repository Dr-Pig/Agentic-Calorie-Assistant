from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.intake.application.intake_tool_runtime import looks_like_multi_item_input, normalize_live_payload
from app.nutrition.agent.exact_item_packets import build_exact_item_lane_packet
from app.nutrition.application.estimate_artifacts import (
    EstimatedNutritionArtifact,
    build_evidence_unavailable_artifact,
    build_exact_item_artifact,
)
from app.nutrition.application.exact_brand_web_canary import LANE_ID as WEB_CANARY_LANE_ID
from app.nutrition.application.exact_brand_web_canary import run_exact_brand_web_canary
from app.nutrition.application.fooddb_retrieval_policy import (
    build_runtime_retrieval_records_from_small_anchor_payload,
    retrieve_fooddb_candidates,
)
from app.nutrition.application.fooddb_retrieval_estimate_artifacts import (
    build_fooddb_retrieval_artifact,
)
from app.nutrition.application.manager_listed_component_anchor_artifact import (
    build_manager_listed_component_anchor_artifact,
)
from app.nutrition.application.listed_component_web_evidence import run_listed_component_web_evidence
from app.nutrition.application.retrieval_semantic_decision import B2ManagerSemanticDecision
from app.nutrition.application.turn_web_evidence_artifacts import (
    build_component_turn_web_evidence_artifact,
    build_exact_turn_web_evidence_artifact,
)
from app.nutrition.application.web_extract_port import WebExtractPort
from app.nutrition.application.web_search_port import WebSearchPort
from app.nutrition.infrastructure.small_anchor_store_loader import load_small_anchor_seed_records
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
    manager_semantic_decision: B2ManagerSemanticDecision | None = None,
) -> EstimatedNutritionArtifact:
    del request_id
    del manager_provider, provider
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

    canary_decision = manager_semantic_decision
    canary_outcome = await run_exact_brand_web_canary(
        raw_user_input=raw_user_input,
        manager_decision=canary_decision,
        search_port=search_port,
        extract_port=extract_port,
        allow_search=allow_search,
        contextualized_query=contextualized_query,
    )
    if canary_outcome.result is not None:
        artifact = build_exact_turn_web_evidence_artifact(
            db,
            user_external_id=user_external_id,
            raw_user_input=raw_user_input,
            local_date=local_date or datetime.now().date().isoformat(),
            lane_result=canary_outcome.result,
            web_trace=canary_outcome.trace,
        )
        normalize_live_payload(artifact.payload, raw_user_input=raw_user_input)
        _attach_web_runtime_trace(artifact.payload, canary_outcome.trace)
        return artifact

    component_web_outcome = await run_listed_component_web_evidence(
        raw_user_input=raw_user_input,
        manager_decision=manager_semantic_decision,
        search_port=search_port,
        extract_port=extract_port,
        allow_search=allow_search,
    )
    if (
        component_web_outcome.results
        and component_web_outcome.trace.get("all_listed_components_have_sources") is True
        and component_web_outcome.trace.get("turn_web_evidence_packet_present") is True
    ):
        artifact = build_component_turn_web_evidence_artifact(
            db,
            user_external_id=user_external_id,
            raw_user_input=raw_user_input,
            local_date=local_date or datetime.now().date().isoformat(),
            lane_results=component_web_outcome.results,
            web_trace=component_web_outcome.trace,
        )
        normalize_live_payload(artifact.payload, raw_user_input=raw_user_input)
        _attach_web_runtime_trace(artifact.payload, component_web_outcome.trace)
        return artifact

    fallback_web_trace = (
        component_web_outcome.trace
        if component_web_outcome.trace.get("attempted") is True
        else canary_outcome.trace
    )
    if canary_outcome.trace.get("attempted") is not True:
        component_anchor_artifact = build_manager_listed_component_anchor_artifact(
            db,
            user_external_id=user_external_id,
            raw_user_input=raw_user_input,
            local_date=local_date or datetime.now().date().isoformat(),
            manager_semantic_decision=manager_semantic_decision,
        )
        if component_anchor_artifact is not None:
            normalize_live_payload(component_anchor_artifact.payload, raw_user_input=raw_user_input)
            _attach_web_runtime_trace(component_anchor_artifact.payload, fallback_web_trace)
            return component_anchor_artifact
        fooddb_artifact = _approved_fooddb_retrieval_artifact(
            db,
            user_external_id=user_external_id,
            raw_user_input=raw_user_input,
            local_date=local_date or datetime.now().date().isoformat(),
            manager_semantic_decision=manager_semantic_decision,
        )
        if fooddb_artifact is not None:
            normalize_live_payload(fooddb_artifact.payload, raw_user_input=raw_user_input)
            _attach_web_runtime_trace(fooddb_artifact.payload, fallback_web_trace)
            return fooddb_artifact

    artifact = build_evidence_unavailable_artifact(
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
    normalize_live_payload(artifact.payload, raw_user_input=raw_user_input)
    _attach_web_runtime_trace(artifact.payload, fallback_web_trace)
    return artifact


def _approved_fooddb_retrieval_artifact(
    db: Session,
    *,
    user_external_id: str,
    raw_user_input: str,
    local_date: str,
    manager_semantic_decision: B2ManagerSemanticDecision | None = None,
) -> EstimatedNutritionArtifact | None:
    anchors = load_small_anchor_seed_records()
    if not anchors:
        return None
    retrieval_records = build_runtime_retrieval_records_from_small_anchor_payload({"anchors": anchors})
    retrieval_query = _manager_owned_retrieval_query(
        manager_semantic_decision,
        raw_user_input=raw_user_input,
    ) or raw_user_input
    retrieval_result = retrieve_fooddb_candidates(
        retrieval_query,
        retrieval_records=retrieval_records,
        limit=8,
        listed_components=_manager_owned_listed_components(manager_semantic_decision),
    )
    return build_fooddb_retrieval_artifact(
        db,
        user_external_id=user_external_id,
        raw_user_input=raw_user_input,
        local_date=local_date,
        retrieval_result=retrieval_result,
    )


def _manager_owned_retrieval_query(
    manager_semantic_decision: B2ManagerSemanticDecision | None,
    *,
    raw_user_input: str | None = None,
) -> str | None:
    if manager_semantic_decision is None:
        return None
    base_dish = str(getattr(manager_semantic_decision, "base_dish", "") or "").strip()
    retrieval_goal = str(getattr(manager_semantic_decision, "retrieval_goal", "") or "").strip()
    if base_dish and retrieval_goal in {"generic_anchor_lookup", "listed_item_lookup"}:
        modifier_text = _manager_owned_modifier_text(manager_semantic_decision, raw_user_input=raw_user_input)
        if modifier_text and modifier_text not in base_dish:
            return f"{base_dish} {modifier_text}"
        return base_dish
    return None


def _manager_owned_modifier_text(
    manager_semantic_decision: B2ManagerSemanticDecision,
    *,
    raw_user_input: str | None,
) -> str:
    del raw_user_input
    hints = [
        str(getattr(manager_semantic_decision, "size_hint", "") or "").strip(),
        *[str(item).strip() for item in getattr(manager_semantic_decision, "modifier_hints", None) or []],
    ]
    return " ".join(item for item in hints if item)


def _manager_owned_listed_components(
    manager_semantic_decision: B2ManagerSemanticDecision | None,
) -> list[str] | None:
    if manager_semantic_decision is None:
        return None
    if str(getattr(manager_semantic_decision, "retrieval_goal", "") or "").strip() != "listed_item_lookup":
        return None
    return list(getattr(manager_semantic_decision, "listed_items", None) or []) or None


def _default_web_runtime_trace() -> dict[str, Any]:
    return {
        "lane_id": WEB_CANARY_LANE_ID,
        "attempted": False, "skip_reason": None, "failure_reason": None, "search_query": None,
        "selected_search_packet_id": None, "accepted_extract_packet_id": None, "selected_url": None,
        "search_attempt_count": 0, "extract_attempt_count": 0, "search_latency_ms": 0, "extract_latency_ms": 0,
        "total_latency_ms": 0, "cost": None, "packetized_candidate_present": False,
        "manager_pass_2_saw_search_packet": False, "extract_attempted": False,
        "retrieval_goal": None, "exact_db_miss_confirmed": False,
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


def manager_semantic_decision_from_tool_arguments(
    arguments: dict[str, Any] | None,
) -> B2ManagerSemanticDecision | None:
    raw = dict((arguments or {}).get("manager_semantic_decision") or {})
    if not raw:
        return None
    return B2ManagerSemanticDecision(
        base_dish=_optional_text(raw.get("base_dish")),
        aliases=_text_list(raw.get("aliases")),
        brand_hint=_optional_text(raw.get("brand_hint")),
        size_hint=_optional_text(raw.get("size_hint")),
        modifier_hints=_text_list(raw.get("modifier_hints")),
        listed_items=_text_list(raw.get("listed_items")),
        retrieval_goal=str(raw.get("retrieval_goal") or "").strip(),
        semantic_authority_source=str(raw.get("semantic_authority_source") or "").strip(),
    )


def _optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [cleaned for item in value if (cleaned := str(item or "").strip())]
