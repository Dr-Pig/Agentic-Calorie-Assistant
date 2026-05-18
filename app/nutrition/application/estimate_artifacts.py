from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.composition.request_runtime_context import load_request_runtime_context
from app.nutrition.application.estimate_artifact_types import EstimatedNutritionArtifact
from app.nutrition.application.fooddb_macro_contract import (
    APPROVED_PACKET_READY_SCHEMA_VERSION,
    APPROVED_PACKET_READY_SOURCE_QUALITY,
    MACRO_CONTRACT,
)
from app.nutrition.application.user_provided_kcal_artifacts import build_user_provided_kcal_artifact  # noqa: F401
from ...shared.contracts.common import EstimateRequest
from ...shared.contracts.intake import ComponentEstimate, EstimatePayload


def build_evidence_unavailable_artifact(
    db: Session,
    *,
    user_external_id: str,
    raw_user_input: str,
    local_date: str,
) -> EstimatedNutritionArtifact:
    request = EstimateRequest(
        text=raw_user_input,
        allow_search=False,
        user_id=user_external_id,
    )
    runtime_context = load_request_runtime_context(
        request=request,
        db=db,
        provider=type("EvidenceUnavailableProvider", (), {"readiness": lambda self: {"configured": True}})(),
    )
    payload = EstimatePayload(
        request_id="intake_execution-evidence-unavailable",
        meal_title=raw_user_input.strip() or "meal",
        components=[],
        component_estimates=[],
        estimated_kcal=0,
        protein_g=0,
        carb_g=0,
        fat_g=0,
        reply_text="",
        action_taken="clarify_before_estimate",
        route_target="clarify_user_private",
        source_decision="ask_user",
        answer_mode=None,
        best_answer_source="evidence_unavailable",
        trace_contract={
            "local_date": local_date,
            "occurred_at": f"{local_date}T12:00:00+08:00",
            "timezone": "Asia/Taipei",
            "route_family": "food_logging",
            "evidence_unavailable": True,
            "shadow_stub": False,
            "db_hit_type": "none",
            "response_mode_hint": "clarify_first",
            "reason_not_direct_answer": "nutrition_evidence_unavailable",
            "unresolved_info": ["composition_or_approved_evidence"],
            "missing_slots": ["composition_or_approved_evidence"],
            "blocking_slots": ["nutrition_evidence"],
            "canonical_write_decision": {
                "can_write_canonical": False,
                "source": "evidence_unavailable",
                "failure_family": "nutrition_evidence_unavailable",
                "blockers": ["no_approved_runtime_evidence"],
            },
            "macro_display_authorized": False,
            "macro_visibility_status": "hidden_missing_source",
            "macro_guard_reason": "no_macro_data",
            "grounding_summary": {
                "exact_truth_present": False,
                "retrieved_knowledge_count": 0,
                "evidence_roles": [],
            },
            "reasoning_state": {
                "exact_lane_count": 0,
                "search_attempt_count": 0,
            },
            "search_attempt_count": 0,
            "search_query": None,
            "websearch_evidence_used": False,
        },
    )
    return EstimatedNutritionArtifact(
        request=request,
        runtime_context=runtime_context,
        payload=payload,
    )


def build_exact_item_artifact(
    db: Session,
    *,
    user_external_id: str,
    raw_user_input: str,
    local_date: str,
    exact_candidate: dict[str, Any],
) -> EstimatedNutritionArtifact:
    request = EstimateRequest(
        text=raw_user_input,
        allow_search=False,
        user_id=user_external_id,
    )
    runtime_context = load_request_runtime_context(
        request=request,
        db=db,
        provider=type("ExactProvider", (), {"readiness": lambda self: {"configured": False, "provider": "exact_item_db"}})(),
    )
    title = str(exact_candidate.get("title") or raw_user_input).strip() or raw_user_input
    kcal = int(round(float(exact_candidate.get("label_kcal") or exact_candidate.get("kcal") or 0)))
    label_macros = dict(exact_candidate.get("label_macros") or {})
    protein_g = int(round(float(label_macros.get("protein_g") or exact_candidate.get("protein_g") or 0)))
    carb_g = int(round(float(label_macros.get("carb_g") or exact_candidate.get("carb_g") or 0)))
    fat_g = int(round(float(label_macros.get("fat_g") or exact_candidate.get("fat_g") or 0)))
    display_macro_breakdown = {}
    if any(value > 0 for value in (protein_g, carb_g, fat_g)):
        display_macro_breakdown = {
            "protein_g": protein_g,
            "carb_g": carb_g,
            "fat_g": fat_g,
            "macro_source": "exact_item_db",
            "macro_confidence": "high",
            "macro_status": "available",
        }
    approved_exact_macro_trace = _approved_exact_macro_trace(
        exact_candidate=exact_candidate,
        display_macro_breakdown=display_macro_breakdown,
    )
    serving_basis = str(exact_candidate.get("serving_basis") or "").strip() or None
    component = ComponentEstimate(
        name=title,
        quantity_hint=serving_basis or "1 serving",
        source="lookup",
        evidence_role="exact_truth",
        estimate_basis="exact",
        confidence_tier="high",
        estimated_kcal=kcal,
        protein_g=protein_g,
        carb_g=carb_g,
        fat_g=fat_g,
        evidence_ids=[str(exact_candidate.get("item_id") or "")] if exact_candidate.get("item_id") else [],
    )
    payload = EstimatePayload(
        request_id="intake_execution-exact-item",
        meal_title=title,
        components=[title],
        component_estimates=[component],
        estimated_kcal=kcal,
        protein_g=protein_g,
        carb_g=carb_g,
        fat_g=fat_g,
        macro_breakdown=display_macro_breakdown,
        raw_macro_breakdown=display_macro_breakdown,
        display_macro_breakdown=display_macro_breakdown,
        evidence_ids_used=[str(exact_candidate.get("item_id") or "")] if exact_candidate.get("item_id") else [],
        reply_text=f"{title} {kcal} kcal.",
        action_taken="direct_answer",
        route_target="direct_answer",
        source_decision="ready",
        answer_mode="direct_answer",
        best_estimate_mode="exact_item",
        estimate_confidence_tier="high",
        trace_contract={
            "local_date": local_date,
            "occurred_at": f"{local_date}T12:00:00+08:00",
            "timezone": "Asia/Taipei",
            "db_hit_type": "exact_truth",
            "macro_display_authorized": bool(display_macro_breakdown),
            "approved_exact_macro_trace": approved_exact_macro_trace,
            "search_attempt_count": 0,
            "why_not_exact": [],
            "grounding_summary": {
                "exact_truth_present": True,
                "retrieved_knowledge_count": 1,
                "evidence_roles": ["exact_truth"],
            },
            "reasoning_state": {
                "exact_lane_count": 1,
                "search_attempt_count": 0,
            },
        },
        retrieved_evidence_summary=[
            {
                "title": title,
                "source_class": "exact_item_db",
                "evidence_role": "exact_truth",
                "identity_confidence": str(exact_candidate.get("identity_confidence") or "high"),
                "query_alignment": str(exact_candidate.get("query_alignment") or "exact_title"),
            }
        ],
        sources=[
            {
                "source_class": "exact_item_db",
                "source_type": str(exact_candidate.get("source_type") or "exact_item_card"),
                "title": title,
                "url": str((exact_candidate.get("provenance") or {}).get("source_url") or ""),
            }
        ],
    )
    return EstimatedNutritionArtifact(
        request=request,
        runtime_context=runtime_context,
        payload=payload,
    )


def _approved_exact_macro_trace(
    *,
    exact_candidate: dict[str, Any],
    display_macro_breakdown: dict[str, Any],
) -> dict[str, Any]:
    macro_visible = bool(display_macro_breakdown)
    return {
        "source_lane": "exact_item_card",
        "runtime_role": "exact_item_card",
        "runtime_truth_allowed": True,
        "source_quality": APPROVED_PACKET_READY_SOURCE_QUALITY,
        "approved_packet_schema_version": APPROVED_PACKET_READY_SCHEMA_VERSION,
        "item_id": str(exact_candidate.get("item_id") or ""),
        "macro_truth_owner": MACRO_CONTRACT["macro_truth_owner"],
        "missing_macro_policy": MACRO_CONTRACT["missing_macro_policy"],
        "packet_fields": list(MACRO_CONTRACT["packet_fields"]),
        "macro_visibility_status": "visible" if macro_visible else "hidden_missing_source",
        "macro_source_basis": "exact_item_seed_label" if macro_visible else "unavailable",
        "macro_confidence": str(display_macro_breakdown.get("macro_confidence") or "unknown"),
        "live_llm_invoked": False,
        "websearch_evidence_used": False,
        "fooddb_truth_updated": False,
    }
