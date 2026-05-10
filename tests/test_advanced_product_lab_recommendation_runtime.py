from __future__ import annotations

import json
from pathlib import Path

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_memory import (
    ProductLabMemoryStore,
    build_product_lab_memory_context_pack,
)


def test_product_lab_recommendation_runtime_uses_three_nodes_and_memory_candidate(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_recommendation import (
        run_product_lab_recommendation,
    )

    memory_pack = _memory_pack(tmp_path)

    artifact = run_product_lab_recommendation(
        turn={
            "session_id": "rec-session",
            "turn_id": "t2",
            "semantic_intent_fixture": "next_meal_recommendation",
            "user_utterance": "raw text is not a recommendation oracle",
        },
        fixture_inputs=build_product_lab_fixture_inputs(),
        memory_context_pack=memory_pack,
    )
    serialized = json.dumps(artifact, ensure_ascii=False)

    assert artifact["artifact_type"] == (
        "advanced_product_lab_recommendation_runtime_artifact"
    )
    assert artifact["status"] == "pass"
    assert artifact["physical_node_order"] == [
        "recommendation_planning",
        "candidate_retrieval_guard_scoring",
        "offer_synthesis",
    ]
    assert [row["logical_stage"] for row in artifact["logical_stage_trace"]] == [
        "recommendation_context_result",
        "candidate_spec",
        "candidate_retrieval_guard_scoring",
        "ranking_result",
        "recommendation_response_result",
    ]
    assert artifact["provider_profile"] == {
        "provider_name": "fixture_product_lab_llm",
        "planning_model_profile": "fast_router_model",
        "offer_model_profile": "strict_reasoner_or_response_writer_model",
        "model_dependency_inverted": True,
    }
    assert artifact["planning"]["recommendation_context_result"][
        "user_goal"
    ] == "next_meal_recommendation"
    assert artifact["planning"]["candidate_spec"]["budget_posture"] == {
        "remaining_kcal": 700,
        "max_candidate_kcal": 700,
    }
    assert "memory-oatmeal" in artifact["retrieval_guard_scoring"][
        "source_candidate_ids"
    ]
    assert artifact["retrieval_guard_scoring"]["deterministic_guard_only"] is True
    assert artifact["offer_synthesis"]["selected_primary"]["candidate_id"] == (
        "memory-oatmeal"
    )
    assert artifact["offer_synthesis"]["ux_packet"]["serve_allowed_in_lab"] is True
    assert artifact["offer_synthesis"]["ux_packet"]["served_to_mainline_user"] is False
    assert artifact["intake_handoff_packet"] == {
        "candidate_id": "memory-oatmeal",
        "requires_explicit_user_intake_action": True,
        "canonical_commit_requested": False,
    }
    assert artifact["recommendation_served_to_lab"] is True
    assert artifact["recommendation_intent_state_created"] is True
    assert artifact["canonical_product_mutation_allowed"] is False
    assert artifact["raw_user_text_semantic_inference_performed"] is False
    assert "no_send" not in serialized


def test_product_lab_recommendation_guard_blocks_hard_constraints(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_recommendation import (
        run_product_lab_recommendation,
    )

    artifact = run_product_lab_recommendation(
        turn={
            "session_id": "rec-session",
            "turn_id": "t2",
            "semantic_intent_fixture": "next_meal_recommendation",
        },
        fixture_inputs=build_product_lab_fixture_inputs(),
        memory_context_pack=_memory_pack(tmp_path),
    )

    filtered = {
        item["candidate_id"]: item["reason_codes"]
        for item in artifact["retrieval_guard_scoring"]["filtered_candidates"]
    }
    assert filtered["over-1"] == ["over_budget"]
    assert filtered["cilantro-1"] == ["confirmed_negative_preference"]
    assert filtered["fried-1"] == ["accepted_rescue_conflict"]
    assert filtered["closed-1"] == ["unavailable"]
    assert "memory-oatmeal" in artifact["retrieval_guard_scoring"][
        "allowed_candidate_ids"
    ]


def test_product_lab_turn_exposes_product_recommendation_artifact(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn
    from tests.test_advanced_product_lab_runtime import _turn

    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn("rec-turn"),
        fixture_inputs=build_product_lab_fixture_inputs(),
        lab_memory_context_pack=_memory_pack(tmp_path),
    )

    recommendation = artifact["product_lab_recommendation_artifact"]
    assert recommendation["status"] == "pass"
    assert recommendation["recommendation_served_to_lab"] is True
    assert recommendation["offer_synthesis"]["selected_primary"]["candidate_id"] == (
        "memory-oatmeal"
    )
    assert artifact["lab_chat_response_packet"]["lab_runtime_capabilities"][
        "recommendation_served_to_lab"
    ] is True


def _memory_pack(tmp_path: Path) -> dict[str, object]:
    store = ProductLabMemoryStore(tmp_path)
    store.write_memory_events(
        session_id="rec-session",
        turn_id="t1",
        events=[
            {
                "memory_id": "memory-oatmeal",
                "memory_type": "golden_order",
                "summary": "Morning Bar oatmeal is reliable before meetings.",
                "review_status": "accepted_lab",
                "source_object_refs": ["turn:t1:user"],
                "store_name": "Morning Bar",
                "item_names": ["oatmeal"],
                "estimated_kcal": 420,
                "intended_consumers": ["recommendation"],
            }
        ],
    )
    return build_product_lab_memory_context_pack(
        store=store,
        session_id="rec-session",
        turn_id="t2",
        consumers=["recommendation"],
        token_budget=120,
    )
