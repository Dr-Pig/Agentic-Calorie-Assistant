from __future__ import annotations

from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.composition.request_runtime_context import load_request_runtime_context
from app.nutrition.application.estimate_artifact_types import EstimatedNutritionArtifact
from app.nutrition.application.exact_brand_web_canary import ExactBrandWebLaneResult
from app.shared.contracts.common import EstimateRequest
from app.shared.contracts.intake import ComponentEstimate, EstimatePayload


def build_exact_turn_web_evidence_artifact(
    db: Session,
    *,
    user_external_id: str,
    raw_user_input: str,
    local_date: str,
    lane_result: ExactBrandWebLaneResult,
    web_trace: dict[str, Any],
) -> EstimatedNutritionArtifact:
    packet = _first_accepted_web_extract_packet(lane_result)
    component = _component_from_packet(packet, estimate_basis="exact", evidence_role="exact_truth")
    payload = _base_turn_web_payload(
        user_external_id=user_external_id,
        raw_user_input=raw_user_input,
        local_date=local_date,
        meal_title=component.name,
        components=[component],
        best_estimate_mode="exact_item",
        estimate_confidence_tier="medium",
        trace_role="turn_web_evidence",
        web_trace=web_trace,
    )
    return _artifact(db, user_external_id=user_external_id, raw_user_input=raw_user_input, payload=payload)


def build_component_turn_web_evidence_artifact(
    db: Session,
    *,
    user_external_id: str,
    raw_user_input: str,
    local_date: str,
    lane_results: Iterable[ExactBrandWebLaneResult],
    web_trace: dict[str, Any],
) -> EstimatedNutritionArtifact:
    components = [
        _component_from_packet(
            _first_accepted_web_extract_packet(lane_result),
            estimate_basis="anchored",
            evidence_role="ingredient_anchor",
        )
        for lane_result in lane_results
    ]
    payload = _base_turn_web_payload(
        user_external_id=user_external_id,
        raw_user_input=raw_user_input,
        local_date=local_date,
        meal_title=" + ".join(component.name for component in components) or raw_user_input,
        components=components,
        best_estimate_mode="anchored_component",
        estimate_confidence_tier="medium",
        trace_role="component_turn_web_evidence",
        web_trace=web_trace,
    )
    payload.component_breakdown = [
        {
            "name": component.name,
            "estimated_kcal": int(component.estimated_kcal or 0),
            "source_lane": "turn_web_evidence",
            "evidence_role": component.evidence_role,
            "evidence_ids": list(component.evidence_ids or []),
        }
        for component in components
    ]
    return _artifact(db, user_external_id=user_external_id, raw_user_input=raw_user_input, payload=payload)


def _base_turn_web_payload(
    *,
    user_external_id: str,
    raw_user_input: str,
    local_date: str,
    meal_title: str,
    components: list[ComponentEstimate],
    best_estimate_mode: str,
    estimate_confidence_tier: str,
    trace_role: str,
    web_trace: dict[str, Any],
) -> EstimatePayload:
    del user_external_id
    kcal = sum(int(component.estimated_kcal or 0) for component in components)
    evidence_ids = [item for component in components for item in component.evidence_ids if item]
    retrieved_evidence_summary = [
        {
            "title": component.name,
            "source_class": "turn_web_evidence",
            "source_type": "web_extract",
            "evidence_role": component.evidence_role,
            "truth_role": "turn_scoped",
        }
        for component in components
    ]
    sources = [
        {
            "source_class": "turn_web_evidence",
            "source_type": "web_extract",
            "title": component.name,
            "packet_id": component.evidence_ids[0] if component.evidence_ids else "",
        }
        for component in components
    ]
    return EstimatePayload(
        request_id=f"intake_execution-{trace_role}",
        meal_title=meal_title or raw_user_input,
        components=[component.name for component in components],
        component_estimates=components,
        estimated_kcal=kcal,
        protein_g=0,
        carb_g=0,
        fat_g=0,
        evidence_ids_used=evidence_ids,
        source_decision="ready",
        answer_mode="direct_answer",
        action_taken="direct_answer",
        route_target="direct_answer",
        reply_text=f"{meal_title or raw_user_input} {kcal} kcal.",
        best_answer_source="turn_web_evidence_packet",
        best_estimate_mode=best_estimate_mode,  # type: ignore[arg-type]
        estimate_confidence_tier=estimate_confidence_tier,  # type: ignore[arg-type]
        retrieved_evidence_summary=retrieved_evidence_summary,
        sources=sources,
        used_search=True,
        search_query=str(web_trace.get("search_query") or web_trace.get("web_query") or "") or None,
        retrieval_triggered=True,
        trace_contract={
            "local_date": local_date,
            "occurred_at": f"{local_date}T12:00:00+08:00",
            "timezone": "Asia/Taipei",
            "route_family": "food_logging",
            "db_hit_type": trace_role,
            "shadow_stub": False,
            "websearch_evidence_used": True,
            "macro_display_authorized": False,
            "macro_visibility_status": "hidden_missing_source",
            "macro_guard_reason": "no_macro_data",
            "grounding_summary": {
                "exact_truth_present": False,
                "retrieved_knowledge_count": len(components),
                "evidence_roles": [trace_role],
            },
            "canonical_write_decision": {
                "can_write_canonical": True,
                "source": "turn_web_evidence_packet",
                "failure_family": None,
            },
            "reasoning_state": {
                "exact_lane_count": 0,
                "search_attempt_count": int(web_trace.get("search_attempt_count") or 0),
            },
            "search_attempt_count": int(web_trace.get("search_attempt_count") or 0),
            "search_query": str(web_trace.get("search_query") or web_trace.get("web_query") or "") or None,
        },
    )


def _artifact(
    db: Session,
    *,
    user_external_id: str,
    raw_user_input: str,
    payload: EstimatePayload,
) -> EstimatedNutritionArtifact:
    request = EstimateRequest(text=raw_user_input, allow_search=False, user_id=user_external_id)
    runtime_context = load_request_runtime_context(request=request, db=db, provider=type("TurnWebEvidenceProvider", (), {"readiness": lambda self: {"configured": True}})())
    return EstimatedNutritionArtifact(request=request, runtime_context=runtime_context, payload=payload)


def _component_from_packet(
    packet: dict[str, object],
    *,
    estimate_basis: str,
    evidence_role: str,
) -> ComponentEstimate:
    kcal_value = packet.get("kcal")
    kcal = int(round(float(kcal_value))) if isinstance(kcal_value, (int, float)) else 0
    title = str(packet.get("canonical_name") or packet.get("title") or "web evidence").strip()
    return ComponentEstimate(
        name=title or "web evidence",
        source="retrieval",
        evidence_role=evidence_role,  # type: ignore[arg-type]
        estimate_basis=estimate_basis,  # type: ignore[arg-type]
        confidence_tier="medium",
        quantity_hint=str(packet.get("serving_basis") or "1 serving"),
        reason="turn_scoped_web_extract_packet",
        evidence_ids=[str(packet.get("packet_id") or "").strip()],
        estimated_kcal=kcal,
        protein_g=0,
        carb_g=0,
        fat_g=0,
    )


def _first_accepted_web_extract_packet(lane_result: ExactBrandWebLaneResult) -> dict[str, object]:
    for packet in lane_result.consumption.accepted_packets:
        if str(packet.get("source_type") or "").strip() == "web_extract":
            return dict(packet)
    raise ValueError("turn web evidence artifact requires an accepted web extract packet")


__all__ = ["build_component_turn_web_evidence_artifact", "build_exact_turn_web_evidence_artifact"]
