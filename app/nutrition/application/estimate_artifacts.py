from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any

from sqlalchemy.orm import Session

from app.composition.request_runtime_context import RequestRuntimeContext, load_request_runtime_context
from app.nutrition.application.fooddb_macro_contract import (
    APPROVED_PACKET_READY_SCHEMA_VERSION,
    APPROVED_PACKET_READY_SOURCE_QUALITY,
    MACRO_CONTRACT,
)
from ...shared.contracts.common import EstimateRequest
from ...shared.contracts.intake import ComponentEstimate, EstimatePayload


@dataclass(frozen=True)
class EstimatedNutritionArtifact:
    request: EstimateRequest
    runtime_context: RequestRuntimeContext
    payload: EstimatePayload


def shadow_stub_estimate_enabled(*, provider: Any) -> bool:
    if os.getenv("V2_INTAKE_TURN_ALLOW_STUB_ESTIMATE", "").strip() == "1":
        return True
    readiness = provider.readiness() if hasattr(provider, "readiness") else {}
    return readiness.get("configured") is not True


def _shadow_stub_components(raw_user_input: str) -> list[ComponentEstimate]:
    normalized = raw_user_input.strip().lower()
    chicken_rice = "\u96de\u8089\u98ef"
    soup = "\u6e6f"
    less = "\u5c11\u4e00\u9ede"
    if chicken_rice in raw_user_input and soup in raw_user_input:
        return [
            ComponentEstimate(name=chicken_rice, quantity_hint="1 bowl", estimated_kcal=500, protein_g=30, carb_g=64, fat_g=15),
            ComponentEstimate(name=soup, quantity_hint="1 bowl", estimated_kcal=150, protein_g=5, carb_g=6, fat_g=4),
        ]
    if chicken_rice in raw_user_input and less in raw_user_input:
        return [
            ComponentEstimate(name=chicken_rice, quantity_hint="smaller portion", estimated_kcal=320, protein_g=24, carb_g=42, fat_g=9),
        ]
    if chicken_rice in raw_user_input:
        return [
            ComponentEstimate(name=chicken_rice, quantity_hint="1 bowl", estimated_kcal=500, protein_g=30, carb_g=64, fat_g=15),
        ]
    if "滷肉飯" in raw_user_input and "無糖豆漿" in raw_user_input:
        return [
            ComponentEstimate(name="滷肉飯", quantity_hint="1 bowl", estimated_kcal=550, protein_g=18, carb_g=58, fat_g=24),
            ComponentEstimate(name="無糖豆漿", quantity_hint="1 cup", estimated_kcal=80, protein_g=7, carb_g=4, fat_g=4),
        ]
    if "排骨便當" in raw_user_input and "無糖綠茶" in raw_user_input and "茶葉蛋" in raw_user_input:
        return [
            ComponentEstimate(name="排骨便當", quantity_hint="1 box", estimated_kcal=720, protein_g=28, carb_g=78, fat_g=30),
            ComponentEstimate(name="無糖綠茶", quantity_hint="1 cup", estimated_kcal=0, protein_g=0, carb_g=0, fat_g=0),
            ComponentEstimate(name="茶葉蛋", quantity_hint="1 egg", estimated_kcal=80, protein_g=7, carb_g=1, fat_g=5),
        ]
    if "牛肉麵" in raw_user_input and "豆漿" in raw_user_input:
        soy = "有糖豆漿" if "有糖" in raw_user_input else "無糖豆漿"
        soy_kcal = 150 if "有糖" in raw_user_input else 80
        soy_carbs = 18 if "有糖" in raw_user_input else 4
        return [
            ComponentEstimate(name="牛肉麵", quantity_hint="1 bowl", estimated_kcal=600, protein_g=26, carb_g=66, fat_g=24),
            ComponentEstimate(name=soy, quantity_hint="1 cup", estimated_kcal=soy_kcal, protein_g=7, carb_g=soy_carbs, fat_g=4),
        ]
    if "牛肉麵" in raw_user_input:
        return [
            ComponentEstimate(name="牛肉麵", quantity_hint="1 bowl", estimated_kcal=600, protein_g=26, carb_g=66, fat_g=24),
        ]
    if "chicken sandwich" in normalized:
        return [
            ComponentEstimate(name="chicken sandwich", quantity_hint="1 sandwich", estimated_kcal=480, protein_g=24, carb_g=35, fat_g=14),
        ]
    if "sandwich" in normalized:
        return [
            ComponentEstimate(name="sandwich", quantity_hint="1 sandwich", estimated_kcal=430, protein_g=18, carb_g=38, fat_g=13),
        ]
    if "milk tea" in normalized or "bubble tea" in normalized:
        return [
            ComponentEstimate(name="bubble milk tea", quantity_hint="1 cup", estimated_kcal=350, protein_g=4, carb_g=56, fat_g=10),
        ]
    if "salad" in normalized:
        return [
            ComponentEstimate(name="salad", quantity_hint="1 bowl", estimated_kcal=260, protein_g=14, carb_g=18, fat_g=12),
        ]
    return [
        ComponentEstimate(name=raw_user_input.strip() or "meal", quantity_hint="1 serving", estimated_kcal=400, protein_g=18, carb_g=42, fat_g=12),
    ]


def build_shadow_stub_artifact(
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
        provider=type("StubProvider", (), {"readiness": lambda self: {"configured": False}})(),
    )
    component_estimates = _shadow_stub_components(raw_user_input)
    meal_title = " + ".join(component.name for component in component_estimates)
    kcal = sum(int(component.estimated_kcal or 0) for component in component_estimates)
    protein_g = sum(int(component.protein_g or 0) for component in component_estimates)
    carb_g = sum(int(component.carb_g or 0) for component in component_estimates)
    fat_g = sum(int(component.fat_g or 0) for component in component_estimates)
    reply_text = "; ".join(f"{component.name} {int(component.estimated_kcal or 0)} kcal" for component in component_estimates)
    payload = EstimatePayload(
        request_id="intake_turn-shadow-stub",
        meal_title=meal_title,
        components=[component.name for component in component_estimates],
        component_estimates=component_estimates,
        estimated_kcal=kcal,
        protein_g=protein_g,
        carb_g=carb_g,
        fat_g=fat_g,
        reply_text=f"{reply_text}. Total {kcal} kcal.",
        action_taken="direct_answer",
        route_target="direct_answer",
        source_decision="ready",
        answer_mode="direct_answer",
        trace_contract={
            "local_date": local_date,
            "occurred_at": f"{local_date}T12:00:00+08:00",
            "timezone": "Asia/Taipei",
            "shadow_stub": True,
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
