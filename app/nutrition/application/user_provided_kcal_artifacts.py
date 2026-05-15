from __future__ import annotations

from sqlalchemy.orm import Session

from app.composition.request_runtime_context import load_request_runtime_context
from app.nutrition.application.estimate_artifact_types import EstimatedNutritionArtifact
from app.shared.contracts.common import EstimateRequest
from app.shared.contracts.intake import ComponentEstimate, EstimatePayload


def build_user_provided_kcal_artifact(
    db: Session,
    *,
    user_external_id: str,
    raw_user_input: str,
    local_date: str,
    user_provided_kcal: int,
) -> EstimatedNutritionArtifact:
    if isinstance(user_provided_kcal, bool) or user_provided_kcal <= 0 or user_provided_kcal > 10000:
        raise ValueError("user_provided_kcal must be an integer between 1 and 10000")
    request = EstimateRequest(text=raw_user_input, allow_search=False, user_id=user_external_id)
    runtime_context = load_request_runtime_context(
        request=request,
        db=db,
        provider=type("UserProvidedKcalProvider", (), {"readiness": lambda self: {"configured": True}})(),
    )
    title = raw_user_input.strip() or "user-provided kcal entry"
    optional_question = (
        "\u5982\u679c\u4f60\u60f3\u88dc\u98df\u7269\u5167\u5bb9\uff0c"
        "\u6211\u53ef\u4ee5\u518d\u5e6b\u4f60\u66f4\u65b0\u3002"
    )
    payload = EstimatePayload(
        request_id="intake_execution-user-provided-kcal",
        meal_title=title,
        components=[title],
        component_estimates=[
            ComponentEstimate(
                name=title,
                source="user",
                evidence_role="user_provided",
                estimate_basis="user_provided",
                confidence_tier="high",
                estimated_kcal=user_provided_kcal,
            )
        ],
        estimated_kcal=user_provided_kcal,
        protein_g=0,
        carb_g=0,
        fat_g=0,
        reply_text=(
            f"\u5df2\u8a18\u9304 {user_provided_kcal} kcal\u3002"
            f"\u4e09\u5927\u71df\u990a\u7d20\u8cc7\u6599\u4e0d\u8db3\uff1b{optional_question}"
        ),
        action_taken="direct_answer",
        route_target="direct_answer",
        source_decision="ready",
        answer_mode="direct_answer",
        best_answer_source="user_provided_kcal",
        best_estimate_mode="user_provided",
        estimate_confidence_tier="high",
        trace_contract={
            "local_date": local_date,
            "occurred_at": f"{local_date}T12:00:00+08:00",
            "timezone": "Asia/Taipei",
            "route_family": "food_logging",
            "source_basis": "user_provided_kcal",
            "user_provided_kcal": user_provided_kcal,
            "response_mode_hint": "rough_estimate_ok",
            "db_hit_type": "user_provided_kcal",
            "shadow_stub": False,
            "canonical_write_decision": {
                "can_write_canonical": True,
                "source": "manager_user_provided_kcal",
                "semantic_authority": "manager_llm",
                "mutation_intent_candidate": "canonical_write",
            },
            "approved_user_provided_kcal_trace": {
                "runtime_truth_allowed": True,
                "source": "manager_semantic_decision.user_provided_kcal",
                "raw_user_input_used": False,
                "deterministic_text_extraction_used": False,
                "macro_truth_allowed": False,
            },
            "macro_display_authorized": False,
            "macro_visibility_status": "hidden_missing_source",
            "macro_guard_reason": "no_macro_data",
            "optional_refinement_allowed": True,
            "optional_refinement_question": optional_question,
            "grounding_summary": {
                "exact_truth_present": False,
                "retrieved_knowledge_count": 0,
                "evidence_roles": ["user_provided_kcal"],
            },
            "reasoning_state": {"exact_lane_count": 0, "search_attempt_count": 0},
            "search_attempt_count": 0,
            "search_query": None,
            "websearch_evidence_used": False,
        },
    )
    return EstimatedNutritionArtifact(request=request, runtime_context=runtime_context, payload=payload)
