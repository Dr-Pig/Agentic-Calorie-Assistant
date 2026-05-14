from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.composition.request_runtime_context import load_request_runtime_context
from app.nutrition.application.estimate_artifacts import EstimatedNutritionArtifact
from app.nutrition.application.fooddb_macro_contract import (
    APPROVED_PACKET_READY_SCHEMA_VERSION,
    APPROVED_PACKET_READY_SOURCE_QUALITY,
    MACRO_CONTRACT,
)
from app.nutrition.application.local_component_stub_catalog import (
    component_estimates_from_manager_listed_items,
)
from app.shared.contracts.common import EstimateRequest
from app.shared.contracts.intake import EstimatePayload


def build_manager_listed_component_anchor_artifact(
    db: Session,
    *,
    user_external_id: str,
    raw_user_input: str,
    local_date: str,
    manager_semantic_decision: Any | None,
) -> EstimatedNutritionArtifact | None:
    listed_items = list(getattr(manager_semantic_decision, "listed_items", None) or [])
    component_estimates = component_estimates_from_manager_listed_items(listed_items)
    if not listed_items or not component_estimates or len(component_estimates) != len(listed_items):
        return None

    request = EstimateRequest(text=raw_user_input, allow_search=False, user_id=user_external_id)
    runtime_context = load_request_runtime_context(
        request=request,
        db=db,
        provider=type(
            "ComponentAnchorProvider",
            (),
            {"readiness": lambda self: {"configured": True, "provider": "manager_listed_component_anchor"}},
        )(),
    )
    meal_title = " + ".join(component.name for component in component_estimates)
    kcal = sum(int(component.estimated_kcal or 0) for component in component_estimates)
    protein_g = sum(int(component.protein_g or 0) for component in component_estimates)
    carb_g = sum(int(component.carb_g or 0) for component in component_estimates)
    fat_g = sum(int(component.fat_g or 0) for component in component_estimates)
    evidence_ids = [item for component in component_estimates for item in component.evidence_ids if item]
    approved_trace = {
        "source_lane": "listed_component",
        "runtime_role": "component_anchor",
        "runtime_truth_allowed": True,
        "source_quality": APPROVED_PACKET_READY_SOURCE_QUALITY,
        "approved_packet_schema_version": APPROVED_PACKET_READY_SCHEMA_VERSION,
        "evidence_ids": evidence_ids,
        "macro_truth_owner": MACRO_CONTRACT["macro_truth_owner"],
        "missing_macro_policy": MACRO_CONTRACT["missing_macro_policy"],
        "packet_fields": list(MACRO_CONTRACT["packet_fields"]),
        "macro_visibility_status": "hidden_missing_source",
        "macro_source_basis": "internal_component_anchor_not_label",
        "macro_confidence": "unknown",
        "live_llm_invoked": False,
        "websearch_evidence_used": False,
        "fooddb_truth_updated": False,
    }
    payload = EstimatePayload(
        request_id="intake_execution-manager-listed-component-anchor",
        meal_title=meal_title,
        components=[component.name for component in component_estimates],
        component_estimates=component_estimates,
        component_breakdown=[
            {
                "name": component.name,
                "estimated_kcal": int(component.estimated_kcal or 0),
                "source_lane": "listed_component",
                "evidence_role": component.evidence_role,
                "evidence_ids": list(component.evidence_ids or []),
            }
            for component in component_estimates
        ],
        estimated_kcal=kcal,
        protein_g=protein_g,
        carb_g=carb_g,
        fat_g=fat_g,
        evidence_ids_used=evidence_ids,
        source_decision="ready",
        answer_mode="direct_answer",
        action_taken="direct_answer",
        route_target="direct_answer",
        reply_text=f"{meal_title} about {kcal} kcal.",
        best_answer_source="approved_fooddb_packet",
        best_estimate_mode="anchored_component",
        estimate_confidence_tier="medium",
        retrieved_evidence_summary=[
            {
                "title": component.name,
                "source_class": "approved_fooddb_packet",
                "source_lane": "listed_component",
                "evidence_role": component.evidence_role,
            }
            for component in component_estimates
        ],
        sources=[
            {
                "source_class": "approved_fooddb_packet",
                "source_type": "listed_component",
                "title": meal_title,
            }
        ],
        trace_contract={
            "local_date": local_date,
            "occurred_at": f"{local_date}T12:00:00+08:00",
            "timezone": "Asia/Taipei",
            "route_family": "food_logging",
            "db_hit_type": "approved_fooddb_packet",
            "approved_fooddb_evidence_trace": approved_trace,
            "macro_display_authorized": False,
            "macro_visibility_status": "hidden_missing_source",
            "macro_guard_reason": "no_macro_data",
            "grounding_summary": {
                "exact_truth_present": False,
                "retrieved_knowledge_count": len(component_estimates),
                "evidence_roles": ["ingredient_anchor"],
            },
            "reasoning_state": {
                "exact_lane_count": 0,
                "search_attempt_count": 0,
            },
            "search_attempt_count": 0,
            "search_query": None,
            "websearch_evidence_used": False,
            "shadow_stub": False,
        },
    )
    return EstimatedNutritionArtifact(request=request, runtime_context=runtime_context, payload=payload)


__all__ = ["build_manager_listed_component_anchor_artifact"]
