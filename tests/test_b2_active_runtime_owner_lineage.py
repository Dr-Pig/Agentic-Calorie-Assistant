from __future__ import annotations

from app.nutrition.application.owner_lineage_trace import attach_owner_lineage_trace
from app.shared.contracts.intake import EstimatePayload


def _payload(*, estimated_kcal: int = 400, trace_contract: dict | None = None) -> EstimatePayload:
    return EstimatePayload(
        request_id="test-request",
        meal_title="test meal",
        components=["test meal"],
        estimated_kcal=estimated_kcal,
        protein_g=10,
        carb_g=40,
        fat_g=12,
        action_taken="direct_answer",
        route_target="direct_answer",
        trace_contract=trace_contract or {},
    )


def test_owner_lineage_trace_exposes_manager_owned_retrieval_and_source_selection() -> None:
    payload = _payload(trace_contract={"canonical_write_decision": {"can_write_canonical": True}})

    attach_owner_lineage_trace(
        payload=payload,
        manager_semantic_decision={
            "semantic_authority": "deterministic_fake_provider",
            "workflow_effect": "estimate_with_followup",
            "followup_question": "size?",
        },
        manager_final_action="commit",
    )

    trace = payload.trace_contract
    assert trace["retrieval_intent_source"] == "manager_semantic_decision"
    assert trace["source_selection"]["decides_logged_or_draft"] is False
    assert trace["source_selection"]["source_path"] == "generic_anchor"
    assert trace["packet_consumption_trace"]["trace_role"] == "observability_only"
    assert trace["nutrition_final_mapping"]["final_mapping_owner"] == "nutrition_final_mapping"
    assert trace["nutrition_final_mapping"]["external_outcome"] == "logged"
    assert trace["nutrition_owner_lineage_role"] == "trace_only_no_runtime_authority_change"


def test_owner_lineage_trace_keeps_query_only_as_no_mutation_mapping() -> None:
    payload = _payload(trace_contract={"canonical_write_decision": {"can_write_canonical": True}})

    attach_owner_lineage_trace(
        payload=payload,
        manager_semantic_decision={
            "semantic_authority": "deterministic_fake_provider",
            "workflow_effect": "answer_only",
        },
        manager_final_action="answer_only",
    )

    trace = payload.trace_contract
    assert trace["source_selection"]["read_only"] is True
    assert trace["nutrition_final_mapping"]["external_outcome"] == "no_mutation_query"
    assert trace["nutrition_final_mapping"]["mutation_allowed"] is False

