from __future__ import annotations

from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn
from tests.test_advanced_shadow_lab_e2e_fixture_chain import (
    _body_plan_view,
    _budget_view,
    _controls,
    _derived_views,
    _memory_projection,
    _proposal_candidate_output,
    _recommendation_payload,
)


def test_product_lab_turn_runs_complete_fixture_loop_on_isolated_surface() -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn={
            "session_id": "lab-session-1",
            "turn_id": "lab-turn-1",
            "surface": "chat",
            "user_utterance": "晚餐幫我抓一個穩一點的選項",
            "semantic_intent_fixture": "advanced_recommendation_rescue_proactive_loop",
        },
        fixture_inputs=_fixture_inputs(),
    )

    assert artifact["artifact_type"] == "advanced_product_lab_turn_artifact"
    assert artifact["status"] == "pass"
    assert artifact["lab_mode"] == "isolated_advanced_product_lab"
    assert artifact["session_id"] == "lab-session-1"
    assert artifact["turn_id"] == "lab-turn-1"
    assert artifact["surface"] == "chat"
    assert artifact["chat_first_surface"] is True
    assert artifact["full_product_lab_runtime_enabled"] is True
    assert artifact["raw_user_text_semantic_inference_performed"] is False
    assert artifact["product_capabilities_exercised"] == [
        "long_term_memory",
        "recommendation",
        "rescue",
        "proactive",
        "chat_first_controls",
    ]
    assert artifact["e2e_chain_artifact"]["status"] == "pass"
    assert artifact["lab_chat_response_packet"]["status"] == "pass"
    assert artifact["lab_chat_response_packet"]["packet_mode"] == (
        "lab_served_product_chat_packet"
    )
    assert artifact["lab_chat_response_packet"]["packet_count"] == 2
    assert artifact["lab_chat_response_packet"]["served_to_lab_surface"] is True
    assert artifact["lab_chat_response_packet"]["served_to_mainline_user"] is False
    assert artifact["lab_chat_surface"]["artifact_type"] == (
        "advanced_product_lab_chat_surface_artifact"
    )
    assert artifact["lab_chat_surface"]["status"] == "pass"
    assert artifact["lab_chat_surface"]["surface_mode"] == "lab_served_chat"
    assert artifact["lab_chat_surface"]["served_to_lab_user"] is True
    assert artifact["lab_chat_surface"]["served_to_mainline_user"] is False
    assert artifact["lab_chat_surface"]["visible_message_count"] == 2
    assert [message["workflow_family"] for message in artifact["lab_chat_surface"]["messages"]] == [
        "recommendation",
        "rescue",
    ]
    assert artifact["lab_chat_surface"]["messages"][0]["actions"] == [
        {
            "action_id": "lab-session-1:lab-turn-1:recommendation_prompt:0:dismiss",
            "action": "dismiss",
            "scope": "candidate_instance",
        },
        {
            "action_id": "lab-session-1:lab-turn-1:recommendation_prompt:0:snooze",
            "action": "snooze",
            "scope": "candidate_instance",
        },
        {
            "action_id": "lab-session-1:lab-turn-1:recommendation_prompt:0:undo",
            "action": "undo",
            "scope": "candidate_instance",
        },
    ]
    assert artifact["lab_chat_surface"]["production_scheduler_delivery_allowed"] is False
    assert artifact["lab_chat_surface"]["production_db_migration_allowed"] is False
    assert artifact["lab_chat_surface"]["canonical_product_mutation_allowed"] is False
    assert artifact["merge_back_activation_wall"] == {
        "mainline_activation_requires_separate_pr": True,
        "self_use_v1_route_or_startup_changed": False,
        "mainline_runtime_connected": False,
        "mainline_route_or_api_mount_allowed": False,
        "production_scheduler_delivery_allowed": False,
        "production_db_migration_allowed": False,
        "canonical_product_mutation_allowed": False,
        "manager_context_packet_changed": False,
    }
    assert artifact["lab_user_facing_behavior_changed"] is True
    assert artifact["user_facing_behavior_changed"] is False
    assert artifact["mainline_runtime_connected"] is False
    assert artifact["production_scheduler_delivery_allowed"] is False
    assert artifact["canonical_product_mutation_allowed"] is False
    assert artifact["manager_context_packet_changed"] is False
    assert artifact["durable_product_memory_written"] is False


def test_product_lab_turn_blocks_without_isolated_lab_mode() -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="",
        turn={
            "session_id": "lab-session-1",
            "turn_id": "lab-turn-1",
            "surface": "chat",
            "semantic_intent_fixture": "advanced_recommendation_rescue_proactive_loop",
        },
        fixture_inputs=_fixture_inputs(),
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == ["lab_mode.not_isolated_advanced_product_lab"]
    assert artifact["e2e_chain_artifact"] is None
    assert artifact["lab_chat_surface"] is None
    assert artifact["lab_user_facing_behavior_changed"] is False
    assert artifact["user_facing_behavior_changed"] is False
    assert artifact["mainline_runtime_connected"] is False


def test_product_lab_turn_requires_explicit_fixture_semantics_not_raw_text() -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn={
            "session_id": "lab-session-1",
            "turn_id": "lab-turn-1",
            "surface": "chat",
            "user_utterance": "這句話不能被 deterministic runner 當 intent oracle",
        },
        fixture_inputs=_fixture_inputs(),
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == ["turn.semantic_intent_fixture_missing"]
    assert artifact["raw_user_text_semantic_inference_performed"] is False
    assert artifact["e2e_chain_artifact"] is None
    assert artifact["lab_chat_surface"] is None


def test_product_lab_dismiss_control_suppresses_candidate_until_material_signal() -> None:
    dismissed = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn("lab-turn-dismiss", lab_now_minute=10),
        fixture_inputs=_fixture_inputs(),
        control_events=[
            {
                "event_id": "dismiss-1",
                "action": "dismiss",
                "target_candidate_id": "recommendation_prompt:0",
                "trigger_type": "recommendation_prompt",
                "scope": "candidate_instance",
                "dismiss_reason": "too_frequent",
                "next_signal_required": "new_app_open_with_qualified_pool",
            }
        ],
    )

    suppressed = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn("lab-turn-after-dismiss", lab_now_minute=20),
        fixture_inputs=_fixture_inputs(),
        prior_control_journal=dismissed["control_state"]["journal_entries"],
    )
    released = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn(
            "lab-turn-material-signal",
            lab_now_minute=30,
            observed_material_signals=["new_app_open_with_qualified_pool"],
        ),
        fixture_inputs=_fixture_inputs(),
        prior_control_journal=dismissed["control_state"]["journal_entries"],
    )

    assert dismissed["control_state"]["status"] == "pass"
    assert dismissed["control_state"]["journal_entry_count"] == 1
    assert _candidate_state(suppressed, "recommendation_prompt:0") == {
        "candidate_id": "recommendation_prompt:0",
        "trigger_type": "recommendation_prompt",
        "visible_in_lab": False,
        "suppression_reason": "dismissed_until_material_signal",
        "active_control_event_id": "dismiss-1",
    }
    assert _candidate_state(released, "recommendation_prompt:0")["visible_in_lab"] is True
    assert _candidate_state(released, "recommendation_prompt:0")[
        "suppression_reason"
    ] == "released_by_material_signal"
    assert suppressed["raw_user_text_semantic_inference_performed"] is False
    assert [
        message["candidate_id"] for message in suppressed["lab_chat_surface"]["messages"]
    ] == ["rescue_nudge:1"]
    assert suppressed["user_facing_behavior_changed"] is False
    assert suppressed["merge_back_activation_wall"]["self_use_v1_route_or_startup_changed"] is False


def test_product_lab_snooze_control_releases_after_window_or_signal() -> None:
    snoozed = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn("lab-turn-snooze", lab_now_minute=100),
        fixture_inputs=_fixture_inputs(),
        control_events=[
            {
                "event_id": "snooze-1",
                "action": "snooze",
                "target_candidate_id": "rescue_nudge:1",
                "trigger_type": "rescue_nudge",
                "scope": "candidate_instance",
                "snooze_minutes": 120,
                "release_signal": "material_budget_change_or_user_reopens_rescue",
            }
        ],
    )

    still_suppressed = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn("lab-turn-before-snooze-release", lab_now_minute=180),
        fixture_inputs=_fixture_inputs(),
        prior_control_journal=snoozed["control_state"]["journal_entries"],
    )
    time_released = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn("lab-turn-after-snooze-release", lab_now_minute=221),
        fixture_inputs=_fixture_inputs(),
        prior_control_journal=snoozed["control_state"]["journal_entries"],
    )
    signal_released = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn(
            "lab-turn-signal-snooze-release",
            lab_now_minute=150,
            observed_material_signals=["material_budget_change_or_user_reopens_rescue"],
        ),
        fixture_inputs=_fixture_inputs(),
        prior_control_journal=snoozed["control_state"]["journal_entries"],
    )

    assert _candidate_state(still_suppressed, "rescue_nudge:1")[
        "suppression_reason"
    ] == "snoozed_until_release"
    assert _candidate_state(time_released, "rescue_nudge:1")["visible_in_lab"] is True
    assert _candidate_state(time_released, "rescue_nudge:1")[
        "suppression_reason"
    ] == "released_by_snooze_window"
    assert _candidate_state(signal_released, "rescue_nudge:1")["visible_in_lab"] is True
    assert _candidate_state(signal_released, "rescue_nudge:1")[
        "suppression_reason"
    ] == "released_by_material_signal"


def test_product_lab_undo_restores_latest_control_for_same_candidate_only() -> None:
    dismissed = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn("lab-turn-dismiss", lab_now_minute=10),
        fixture_inputs=_fixture_inputs(),
        control_events=[
            {
                "event_id": "dismiss-1",
                "action": "dismiss",
                "target_candidate_id": "recommendation_prompt:0",
                "trigger_type": "recommendation_prompt",
                "scope": "candidate_instance",
                "dismiss_reason": "too_frequent",
                "next_signal_required": "new_app_open_with_qualified_pool",
            }
        ],
    )
    undone = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn("lab-turn-undo", lab_now_minute=12),
        fixture_inputs=_fixture_inputs(),
        prior_control_journal=dismissed["control_state"]["journal_entries"],
        control_events=[
            {
                "event_id": "undo-1",
                "action": "undo",
                "target_candidate_id": "recommendation_prompt:0",
                "trigger_type": "recommendation_prompt",
                "scope": "candidate_instance",
                "undo_event_id": "dismiss-1",
            }
        ],
    )
    after_undo = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn("lab-turn-after-undo", lab_now_minute=20),
        fixture_inputs=_fixture_inputs(),
        prior_control_journal=undone["control_state"]["journal_entries"],
    )

    assert undone["control_state"]["journal_entry_count"] == 2
    assert _candidate_state(after_undo, "recommendation_prompt:0") == {
        "candidate_id": "recommendation_prompt:0",
        "trigger_type": "recommendation_prompt",
        "visible_in_lab": True,
        "suppression_reason": "restored_by_undo",
        "active_control_event_id": "undo-1",
    }
    assert _candidate_state(after_undo, "rescue_nudge:1")["visible_in_lab"] is True


def _fixture_inputs() -> dict[str, object]:
    return {
        "memory_summary_projection": _memory_projection(),
        "recommendation_payload": _recommendation_payload(),
        "derived_memory_views": _derived_views(),
        "current_budget_view": _budget_view(),
        "active_body_plan_view": _body_plan_view(),
        "open_proposals_view": {"open_rescue_proposal_count": 0},
        "proposal_candidate_output": _proposal_candidate_output(),
        "user_control_models": {
            "recommendation_prompt": _controls("new_app_open_with_qualified_pool"),
            "rescue_nudge": _controls(
                "material_budget_change_or_user_reopens_rescue"
            ),
        },
        "interaction_plan": [
            {"action": "dismiss", "dismiss_reason": "too_frequent"},
            {"action": "snooze", "snooze_minutes": 120},
        ],
    }


def _turn(
    turn_id: str,
    *,
    lab_now_minute: int = 0,
    observed_material_signals: list[str] | None = None,
) -> dict[str, object]:
    return {
        "session_id": "lab-session-1",
        "turn_id": turn_id,
        "surface": "chat",
        "user_utterance": "fixture text is not a semantic oracle",
        "semantic_intent_fixture": "advanced_recommendation_rescue_proactive_loop",
        "lab_now_minute": lab_now_minute,
        "observed_material_signals": list(observed_material_signals or []),
    }


def _candidate_state(
    artifact: dict[str, object],
    candidate_id: str,
) -> dict[str, object]:
    states = artifact["lab_chat_response_packet"]["candidate_states"]  # type: ignore[index]
    for state in states:
        if state["candidate_id"] == candidate_id:
            return state
    raise AssertionError(f"candidate state not found: {candidate_id}")
