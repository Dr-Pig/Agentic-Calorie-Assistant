from __future__ import annotations

from pathlib import Path

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_memory import (
    ProductLabMemoryStore,
    build_product_lab_memory_context_pack,
)
from app.advanced_shadow_lab.product_lab_proactive import run_product_lab_proactive
from app.advanced_shadow_lab.product_lab_recommendation import (
    run_product_lab_recommendation,
)
from app.advanced_shadow_lab.product_lab_rescue import run_product_lab_rescue


def test_rescue_output_becomes_proactive_candidate_with_legality_trace(
    tmp_path: Path,
) -> None:
    fixture_inputs = build_product_lab_fixture_inputs()
    memory_pack = _memory_pack(tmp_path)
    artifact = run_product_lab_proactive(
        turn=_turn(),
        fixture_inputs=fixture_inputs,
        memory_context_pack=memory_pack,
        recommendation_artifact=run_product_lab_recommendation(
            turn=_turn(),
            fixture_inputs=fixture_inputs,
            memory_context_pack=memory_pack,
        ),
        rescue_artifact=run_product_lab_rescue(fixture_inputs=fixture_inputs),
    )

    bridge = artifact["wake_source_adapter"]["rescue_proactive_candidate_bridge"]
    rescue = next(
        candidate
        for candidate in artifact["candidates"]
        if candidate["trigger_type"] == "rescue_nudge"
    )
    delivery_trace = artifact["delivery_packet"]["candidate_traces_by_candidate"][
        "rescue_nudge"
    ]

    assert bridge["artifact_type"] == "advanced_product_lab_rescue_proactive_candidate_bridge"
    assert bridge["status"] == "pass"
    assert bridge["candidate_created"] is True
    assert bridge["candidate_spec"]["downstream_workflow_family"] == "rescue"
    assert bridge["candidate_spec"]["source_bridge_trace"] == {
        "downstream_workflow_family": "rescue",
        "proposal_kind": "same_day_rescue_lab",
        "recovery_viability": "viable",
        "recommended_days": 2,
        "daily_kcal_adjustment": -150,
        "pending_commit_handoff_state": "pending_user_rescue_commit_confirmation",
        "requires_explicit_user_rescue_commit": True,
        "rescue_handoff_mode": "chat_first_independent_message",
    }
    assert rescue["source_bridge_trace"]["downstream_workflow_family"] == "rescue"
    assert rescue["source_bridge_trace"]["proposal_kind"] == "same_day_rescue_lab"
    assert delivery_trace["downstream_workflow_family"] == "rescue"
    assert bridge["proposal_committed"] is False
    assert bridge["day_budget_mutated"] is False
    assert bridge["canonical_product_mutation_allowed"] is False
    assert bridge["scheduler_delivery_allowed"] is False
    assert bridge["notification_delivery_allowed"] is False


def test_rescue_bridge_blocks_mutation_bearing_rescue_artifact() -> None:
    from app.advanced_shadow_lab.product_lab_proactive_rescue_bridge import (
        build_rescue_proactive_candidate_bridge,
    )

    rescue_artifact = run_product_lab_rescue(
        fixture_inputs=build_product_lab_fixture_inputs()
    )
    rescue_artifact = {
        **rescue_artifact,
        "proposal_committed": True,
        "day_budget_mutated": True,
        "pending_rescue_commit_packet": {
            **rescue_artifact["pending_rescue_commit_packet"],
            "canonical_commit_requested": True,
        },
    }

    bridge = build_rescue_proactive_candidate_bridge(
        rescue_artifact=rescue_artifact,
        fixture_inputs=build_product_lab_fixture_inputs(),
    )

    assert bridge["status"] == "blocked"
    assert bridge["candidate_created"] is False
    assert bridge["candidate_spec"] is None
    assert bridge["blockers"] == [
        "rescue.proposal_committed_not_allowed",
        "rescue.day_budget_mutated_not_allowed",
        "rescue.pending_commit_requested_not_allowed",
    ]
    assert bridge["scheduler_delivery_allowed"] is False
    assert bridge["notification_delivery_allowed"] is False


def _memory_pack(tmp_path: Path) -> dict[str, object]:
    store = ProductLabMemoryStore(tmp_path)
    store.write_memory_events(
        session_id="rescue-proactive-session",
        turn_id="t1",
        events=[
            {
                "memory_id": "memory-oatmeal",
                "memory_type": "golden_order",
                "summary": "Morning Bar oatmeal is a reliable breakfast option.",
                "review_status": "accepted_lab",
                "source_object_refs": ["turn:t1:user"],
                "store_name": "Morning Bar",
                "item_names": ["oatmeal"],
                "estimated_kcal": 420,
                "intended_consumers": ["recommendation", "proactive"],
            }
        ],
    )
    return build_product_lab_memory_context_pack(
        store=store,
        session_id="rescue-proactive-session",
        turn_id="t2",
        consumers=["recommendation", "proactive"],
        token_budget=120,
    )


def _turn() -> dict[str, object]:
    return {
        "session_id": "rescue-proactive-session",
        "turn_id": "t2",
        "semantic_intent_fixture": "next_meal_recommendation",
        "surface": "chat",
    }
