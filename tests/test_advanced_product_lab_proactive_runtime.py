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
from app.advanced_shadow_lab.product_lab_recommendation import (
    run_product_lab_recommendation,
)
from app.advanced_shadow_lab.product_lab_rescue import run_product_lab_rescue


def test_product_lab_proactive_reads_outputs_and_builds_chat_candidates(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_proactive import run_product_lab_proactive

    fixture_inputs = build_product_lab_fixture_inputs()
    memory_pack = _memory_pack(tmp_path)
    recommendation = run_product_lab_recommendation(
        turn=_turn(),
        fixture_inputs=fixture_inputs,
        memory_context_pack=memory_pack,
    )
    rescue = run_product_lab_rescue(fixture_inputs=fixture_inputs)

    artifact = run_product_lab_proactive(
        turn=_turn(),
        fixture_inputs=fixture_inputs,
        memory_context_pack=memory_pack,
        recommendation_artifact=recommendation,
        rescue_artifact=rescue,
    )
    serialized = json.dumps(artifact, ensure_ascii=False)

    assert artifact["artifact_type"] == "advanced_product_lab_proactive_runtime_artifact"
    assert artifact["status"] == "pass"
    assert artifact["candidate_count"] == 2
    assert [candidate["trigger_type"] for candidate in artifact["candidates"]] == [
        "recommendation_prompt",
        "rescue_nudge",
    ]
    assert artifact["candidates"][0]["source_output_refs"] == [
        "advanced_product_lab_recommendation_runtime_artifact",
        "candidate:memory-oatmeal",
    ]
    assert artifact["candidates"][1]["source_output_refs"] == [
        "advanced_product_lab_rescue_runtime_artifact",
        "proposal:same_day_rescue_lab",
    ]
    assert artifact["memory_context_refs"] == ["memory-oatmeal"]
    assert artifact["omission_traces"] == []
    assert artifact["chat_first"] is True
    assert artifact["lab_chat_delivery_allowed"] is True
    assert artifact["scheduler_delivery_allowed"] is False
    assert artifact["notification_delivery_allowed"] is False
    for candidate in artifact["candidates"]:
        assert candidate["dismiss_reason_choices"]
        assert candidate["snooze_window"]["minutes"] > 0
        assert candidate["undo_scope"] == "candidate_instance"
        assert candidate["next_signal_required"]
        assert candidate["served_to_lab_chat"] is True
        assert candidate["served_to_mainline_user"] is False
    assert "no_send" not in serialized


def test_product_lab_proactive_blocks_candidates_without_control_path(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_proactive import run_product_lab_proactive

    fixture_inputs = build_product_lab_fixture_inputs()
    fixture_inputs["user_control_models"]["rescue_nudge"].pop("snooze_window")
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

    assert artifact["status"] == "blocked"
    assert "rescue_nudge.snooze_window_missing" in artifact["blockers"]
    assert artifact["lab_chat_delivery_allowed"] is False


def test_product_lab_proactive_uses_action_state_for_pending_intake_followup(
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
        action_state={
            "artifact_type": "advanced_product_lab_action_state",
            "active_pending_intake_draft_ids": ["memory-oatmeal"],
            "active_pending_intake_source_refs": ["pending:memory-oatmeal"],
        },
    )

    assert artifact["status"] == "pass"
    assert [candidate["trigger_type"] for candidate in artifact["candidates"]] == [
        "recommendation_prompt",
        "pending_intake_followup",
        "rescue_nudge",
    ]
    followup = artifact["candidates"][1]
    assert followup["candidate_kind"] == "pending_intake_confirmation_followup"
    assert followup["next_signal_required"] == (
        "user_confirms_or_cancels_pending_intake"
    )
    assert artifact["action_state_refs"] == ["pending:memory-oatmeal"]
    assert artifact["scheduler_delivery_allowed"] is False


def test_product_lab_proactive_omits_dismissed_rescue_nudge(
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
        action_state={
            "artifact_type": "advanced_product_lab_action_state",
            "dismissed_rescue_instance_count": 1,
            "dismissed_rescue_source_refs": ["rescue:source"],
        },
    )

    assert artifact["status"] == "pass"
    assert [candidate["trigger_type"] for candidate in artifact["candidates"]] == [
        "recommendation_prompt"
    ]
    assert artifact["omission_traces"] == [
        {
            "trigger_type": "rescue_nudge",
            "omission_reason": "dismissed_rescue_instance_active",
            "source_refs": ["rescue:source"],
            "user_facing_behavior_changed": False,
            "scheduler_delivery_allowed": False,
            "canonical_product_mutation_allowed": False,
        }
    ]
    assert artifact["lab_chat_delivery_allowed"] is True
    assert artifact["notification_delivery_allowed"] is False


def test_product_lab_turn_exposes_product_proactive_artifact(tmp_path: Path) -> None:
    from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn
    from tests.test_advanced_product_lab_runtime import _turn

    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn("proactive-turn"),
        fixture_inputs=build_product_lab_fixture_inputs(),
        lab_memory_context_pack=_memory_pack(tmp_path),
    )

    proactive = artifact["product_lab_proactive_artifact"]
    assert proactive["status"] == "pass"
    assert proactive["candidate_count"] == 2
    assert proactive["lab_chat_delivery_allowed"] is True
    assert proactive["scheduler_delivery_allowed"] is False


def _memory_pack(tmp_path: Path) -> dict[str, object]:
    store = ProductLabMemoryStore(tmp_path)
    store.write_memory_events(
        session_id="proactive-session",
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
        session_id="proactive-session",
        turn_id="t2",
        consumers=["recommendation", "proactive"],
        token_budget=120,
    )


def _turn() -> dict[str, object]:
    return {
        "session_id": "proactive-session",
        "turn_id": "t2",
        "semantic_intent_fixture": "next_meal_recommendation",
        "surface": "chat",
    }
