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
from app.shared.contracts.common import EstimateRequest
from app.shared.contracts.intake import ComponentEstimate, EstimatePayload


def fooddb_request_context(
    db: Session,
    *,
    user_external_id: str,
    raw_user_input: str,
) -> tuple[EstimateRequest, Any]:
    request = EstimateRequest(text=raw_user_input, allow_search=False, user_id=user_external_id)
    runtime_context = load_request_runtime_context(
        request=request,
        db=db,
        provider=type(
            "FoodDBPacketProvider",
            (),
            {"readiness": lambda self: {"configured": False, "provider": "approved_fooddb_packet"}},
        )(),
    )
    return request, runtime_context


def source_lane(candidates: list[dict[str, Any]]) -> str:
    if candidates and all(str(item.get("runtime_usage_boundary") or "").startswith("listed_component") for item in candidates):
        return "listed_component"
    return "generic_common_serving"


def approved_fooddb_trace(
    *,
    source_lane_value: str,
    retrieval_boundary: str,
    evidence_ids: list[str],
    macro_visible: bool,
    runtime_truth_allowed: bool,
    disambiguation_required: bool = False,
    kcal_range: list[int] | None = None,
) -> dict[str, Any]:
    trace = {
        "source_lane": source_lane_value,
        "schema_version": APPROVED_PACKET_READY_SCHEMA_VERSION,
        "source_quality": APPROVED_PACKET_READY_SOURCE_QUALITY,
        "runtime_truth_allowed": runtime_truth_allowed,
        "retrieval_boundary": retrieval_boundary,
        "evidence_ids": evidence_ids,
        "macro_truth_owner": MACRO_CONTRACT["macro_truth_owner"],
        "missing_macro_policy": MACRO_CONTRACT["missing_macro_policy"],
        "packet_fields": list(MACRO_CONTRACT["packet_fields"]),
        "macro_visibility_status": "visible" if macro_visible else "hidden_missing_source",
        "macro_source_basis": "approved_fooddb_packet" if macro_visible else "unknown",
        "macro_confidence": "medium" if macro_visible else "unknown",
        "live_llm_invoked": False,
        "websearch_evidence_used": False,
        "fooddb_truth_updated": False,
        "packet_is_not_mutation_authority": True,
        "disambiguation_required": disambiguation_required,
    }
    if kcal_range:
        trace["kcal_range"] = list(kcal_range)
    return trace


def optional_refinement_metadata(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    targets = _optional_refinement_targets(candidates)
    if not targets:
        return {}
    return {
        "optional_refinement_allowed": True,
        "optional_refinement_targets": targets,
        "optional_refinement_question": (
            "\u8981\u88dc\u4e00\u4e0b\u7cd6\u5ea6\u548c\u676f\u578b\u55ce\uff1f"
            "\u6211\u53ef\u4ee5\u518d\u5e6b\u4f60\u66f4\u65b0\u4f30\u7b97\u3002"
        ),
        "optional_refinement_source": "fooddb_candidate_modifier_hints",
        "deterministic_final_action": False,
    }


def _optional_refinement_targets(candidates: list[dict[str, Any]]) -> list[str]:
    targets: list[str] = []
    for candidate in candidates:
        if "refinement" not in str(candidate.get("runtime_usage_boundary") or ""):
            continue
        modifier_names = [
            str(modifier.get("name") or "").strip()
            for modifier in candidate.get("major_modifiers") or []
            if isinstance(modifier, dict) and str(modifier.get("name") or "").strip()
        ]
        if not modifier_names:
            modifier_names = [
                _target_from_followup_hint(hint)
                for hint in candidate.get("followup_hints") or []
            ]
        for target in modifier_names:
            if target and target not in targets:
                targets.append(target)
    return targets


def _target_from_followup_hint(hint: object) -> str:
    text = str(hint or "").strip()
    if text == "ask_sugar_level":
        return "sugar_level"
    if text in {"ask_cup_size", "ask_size"}:
        return "cup_size"
    return text


def build_fooddb_followup_artifact(
    db: Session,
    *,
    user_external_id: str,
    raw_user_input: str,
    local_date: str,
    retrieval_result: dict[str, Any],
    source_lane_value: str = "basket_family_alias_modifier",
    evidence_ids: list[str] | None = None,
    followup_reasoning: str = "fooddb_bare_basket_requires_components",
    disambiguation_required: bool = False,
) -> EstimatedNutritionArtifact:
    request, runtime_context = fooddb_request_context(
        db,
        user_external_id=user_external_id,
        raw_user_input=raw_user_input,
    )
    retrieval_boundary = str(retrieval_result.get("retrieval_boundary") or "")
    approved_trace = approved_fooddb_trace(
        source_lane_value=source_lane_value,
        retrieval_boundary=retrieval_boundary,
        evidence_ids=evidence_ids or [],
        macro_visible=False,
        runtime_truth_allowed=False,
        disambiguation_required=disambiguation_required,
    )
    followup_question = "Which items and portions should I estimate?"
    payload = EstimatePayload(
        request_id="intake_execution-approved-fooddb-followup",
        meal_title=raw_user_input.strip() or "pending meal",
        estimated_kcal=0,
        source_decision="ask_user",
        answer_mode=None,
        action_taken="clarify_before_estimate",
        route_target="clarify_user_private",
        followup_question=followup_question,
        follow_up_needed=True,
        follow_up_reasoning=followup_reasoning,
        reply_text=followup_question,
        trace_contract={
            "local_date": local_date,
            "occurred_at": f"{local_date}T12:00:00+08:00",
            "timezone": "Asia/Taipei",
            "route_family": "component_driven_meal",
            "response_mode_hint": "clarify_first",
            "followup_question": followup_question,
            "missing_slots": ["composition_details"],
            "blocking_slots": ["composition_details"],
            "unresolved_info": ["composition_details"],
            "canonical_write_decision": {
                "can_write_canonical": False,
                "source": "approved_fooddb_bare_basket_boundary",
            },
            "db_hit_type": "approved_fooddb_packet",
            "approved_fooddb_evidence_trace": approved_trace,
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
            "shadow_stub": False,
        },
        quality_signals={"estimate_mode": "ask_followup_only"},
    )
    return EstimatedNutritionArtifact(request=request, runtime_context=runtime_context, payload=payload)


def candidate_component(candidate: dict[str, Any], *, source_lane_value: str) -> ComponentEstimate:
    return ComponentEstimate(
        name=str(candidate.get("canonical_name") or candidate.get("anchor_id") or "fooddb item"),
        quantity_hint=str(candidate.get("serving_basis") or "common_serving"),
        source="lookup",
        evidence_role="ingredient_anchor" if source_lane_value == "listed_component" else "meal_pattern_prior",
        estimate_basis="anchored",
        confidence_tier="medium",
        estimated_kcal=int(candidate.get("kcal_point") or 0),
        protein_g=0,
        carb_g=0,
        fat_g=0,
        evidence_ids=[str(candidate.get("anchor_id") or "")],
    )


def component_breakdown_item(
    component: ComponentEstimate,
    *,
    candidate: dict[str, Any],
    source_lane_value: str,
) -> dict[str, Any]:
    return {
        "name": component.name,
        "title": component.name,
        "quantity_hint": component.quantity_hint,
        "estimated_kcal": component.estimated_kcal,
        "kcal_range": list(candidate.get("kcal_range") or []),
        "protein_g": component.protein_g,
        "carb_g": component.carb_g,
        "fat_g": component.fat_g,
        "source_lane": source_lane_value,
        "source_class": "base_nutrition_db",
        "identity_confidence": "low",
        "query_alignment": "exact" if not candidate.get("requires_manager_disambiguation") else "partial",
        "serving_basis": str(candidate.get("serving_basis") or "common_serving"),
    }


__all__ = [
    "approved_fooddb_trace",
    "build_fooddb_followup_artifact",
    "candidate_component",
    "component_breakdown_item",
    "fooddb_request_context",
    "optional_refinement_metadata",
    "source_lane",
]
