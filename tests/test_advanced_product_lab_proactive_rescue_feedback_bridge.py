from __future__ import annotations

from pathlib import Path

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_memory import (
    ProductLabMemoryStore,
    build_product_lab_memory_context_pack,
)
from app.advanced_shadow_lab.product_lab_recommendation import (
    run_product_lab_recommendation,
)
from app.advanced_shadow_lab.product_lab_rescue import run_product_lab_rescue


def test_proactive_omits_rescue_nudge_from_pending_dismiss_feedback(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_proactive import run_product_lab_proactive

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
        rescue_feedback_memory_projection=_feedback_projection("dismiss", "dismiss"),
    )

    assert artifact["status"] == "pass"
    assert [candidate["trigger_type"] for candidate in artifact["candidates"]] == [
        "recommendation_prompt"
    ]
    [trace] = artifact["omission_traces"]
    assert trace["trigger_type"] == "rescue_nudge"
    assert trace["omission_reason"] == "rescue_feedback_dismissal_pending_review"
    assert trace["human_review_required"] is True
    assert trace["memory_truth_claimed"] is False
    assert trace["scheduler_delivery_allowed"] is False
    assert artifact["delivery_packet"]["candidate_ids"] == ["recommendation_prompt"]
    assert artifact["durable_product_memory_written"] is False


def test_proactive_does_not_omit_rescue_nudge_from_accept_feedback(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_proactive import run_product_lab_proactive

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
        rescue_feedback_memory_projection=_feedback_projection("confirm", "accept"),
    )

    assert artifact["status"] == "pass"
    assert [candidate["trigger_type"] for candidate in artifact["candidates"]] == [
        "recommendation_prompt",
        "rescue_nudge",
    ]
    assert artifact["omission_traces"] == []


def _feedback_projection(action: str, feedback_kind: str) -> dict[str, object]:
    from app.rescue.application.feedback_memory_projection import (
        build_rescue_feedback_memory_projection,
    )

    scope = {
        "user_id": "user-a",
        "workspace_id": "workspace-a",
        "project_id": "advanced-product-lab",
        "surface": "rescue_lab",
    }
    return build_rescue_feedback_memory_projection(
        feedback_event={
            "target_type": "rescue_plan",
            "target_id": "rescue-proposal-1",
            "action": action,
            "reason": "not today",
            "source_turn_id": "turn-rescue-1",
            "scope_keys": scope,
        },
        rescue_feedback_target={
            "target_type": "rescue_plan",
            "target_id": "rescue-proposal-1",
            "feedback_kind": feedback_kind,
            "scope_keys": scope,
            "source_turn_ids": ["turn-rescue-1"],
            "source_refs": ["rescue_plan:rescue-proposal-1"],
        },
    )


def _memory_pack(tmp_path: Path) -> dict[str, object]:
    store = ProductLabMemoryStore(tmp_path)
    store.write_memory_events(
        session_id="proactive-feedback-session",
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
        session_id="proactive-feedback-session",
        turn_id="t2",
        consumers=["recommendation", "proactive"],
        token_budget=120,
    )


def _turn() -> dict[str, object]:
    return {
        "session_id": "proactive-feedback-session",
        "turn_id": "t2",
        "semantic_intent_fixture": "next_meal_recommendation",
        "surface": "chat",
    }
