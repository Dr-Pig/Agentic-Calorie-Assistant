from __future__ import annotations

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_memory import (
    empty_product_lab_memory_context_pack,
)


def test_product_lab_recommendation_graph_contract_keeps_three_node_boundary() -> None:
    from app.advanced_shadow_lab.product_lab_recommendation import (
        run_product_lab_recommendation,
    )

    artifact = run_product_lab_recommendation(
        turn={
            "session_id": "rec-contract-session",
            "turn_id": "t1",
            "semantic_intent_fixture": "next_meal_recommendation",
        },
        fixture_inputs=build_product_lab_fixture_inputs(),
        memory_context_pack=empty_product_lab_memory_context_pack(
            session_id="rec-contract-session",
            turn_id="t1",
        ),
    )

    contract = artifact["graph_contract"]

    assert contract["artifact_type"] == (
        "advanced_product_lab_recommendation_graph_contract"
    )
    assert contract["physical_node_count"] == 3
    assert contract["physical_node_order"] == [
        "recommendation_planning",
        "candidate_retrieval_guard_scoring",
        "offer_synthesis",
    ]
    assert contract["conceptual_step_count"] == 5
    assert contract["ownership_boundaries"] == [
        "llm_planning_to_deterministic_guard",
        "deterministic_guard_to_llm_offer_synthesis",
    ]
    assert contract["node_contracts"][1] == {
        "node": "candidate_retrieval_guard_scoring",
        "owner": "deterministic",
        "llm_semantic_authority": False,
        "may_filter_candidates": True,
        "may_create_user_intent": False,
        "may_mutate_canonical_state": False,
    }
    assert contract["anti_overengineering_guard"] == {
        "five_node_pass_chain_rejected": True,
        "node_split_requires_new_ownership_boundary": True,
        "generic_workflow_engine_required": False,
    }
    assert artifact["blockers"] == []
