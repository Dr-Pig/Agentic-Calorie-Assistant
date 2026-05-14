from __future__ import annotations

from app.advanced_shadow_lab.product_lab_control_state import (
    build_product_lab_control_state,
)
from app.advanced_shadow_lab.product_lab_proactive_control_store import (
    ProductLabProactiveControlStore,
)


def test_trigger_opt_out_suppresses_future_same_trigger_candidate() -> None:
    first = build_product_lab_control_state(
        session_id="session-opt-out",
        turn_id="t1",
        lab_now_minute=10,
        observed_material_signals=[],
        candidates=[
            {
                "packet_id": "recommendation_prompt:0",
                "trigger_type": "recommendation_prompt",
            }
        ],
        control_events=[
            {
                "event_id": "opt-out-rec",
                "target_candidate_id": "recommendation_prompt:0",
                "trigger_type": "recommendation_prompt",
                "action": "opt_out",
                "scope": "trigger_family",
                "dismiss_reason": "too_frequent",
                "next_signal_required": "user_reopens_recommendation_prompts",
            }
        ],
    )
    assert first["status"] == "pass"

    second = build_product_lab_control_state(
        session_id="session-opt-out",
        turn_id="t2",
        lab_now_minute=20,
        observed_material_signals=[],
        candidates=[
            {
                "packet_id": "recommendation_prompt:1",
                "trigger_type": "recommendation_prompt",
            }
        ],
        prior_control_journal=first["journal_entries"],
    )

    [state] = second["candidate_states"]
    assert state["candidate_id"] == "recommendation_prompt:1"
    assert state["visible_in_lab"] is False
    assert state["suppression_reason"] == "opted_out_trigger"
    assert state["active_control_event_id"] == "opt-out-rec"
    assert second["canonical_product_mutation_allowed"] is False
    assert second["scheduler_enabled"] is False


def test_reopen_or_modify_releases_user_control_without_legacy_undo_copy() -> None:
    opt_out = build_product_lab_control_state(
        session_id="session-reopen",
        turn_id="t1",
        lab_now_minute=10,
        observed_material_signals=[],
        candidates=[
            {"packet_id": "rescue_nudge:1", "trigger_type": "rescue_nudge"}
        ],
        control_events=[
            {
                "event_id": "opt-out-rescue",
                "target_candidate_id": "rescue_nudge:1",
                "trigger_type": "rescue_nudge",
                "action": "opt_out",
                "scope": "trigger_family",
                "next_signal_required": "user_reopens_rescue_nudges",
            }
        ],
    )
    reopened = build_product_lab_control_state(
        session_id="session-reopen",
        turn_id="t2",
        lab_now_minute=20,
        observed_material_signals=[],
        candidates=[
            {"packet_id": "rescue_nudge:2", "trigger_type": "rescue_nudge"}
        ],
        prior_control_journal=opt_out["journal_entries"],
        control_events=[
            {
                "event_id": "reopen-rescue",
                "target_candidate_id": "rescue_nudge:2",
                "trigger_type": "rescue_nudge",
                "action": "reopen_or_modify",
                "scope": "trigger_family",
                "reopen_target_event_id": "opt-out-rescue",
                "source_chat_action_event_id": "chat-reopen-rescue",
            }
        ],
    )

    [state] = reopened["candidate_states"]
    [entry] = [
        item
        for item in reopened["journal_entries"]
        if item["event_id"] == "reopen-rescue"
    ]
    assert state["visible_in_lab"] is True
    assert state["suppression_reason"] == "restored_by_reopen_or_modify"
    assert state["active_control_event_id"] == "reopen-rescue"
    assert entry["user_facing_control_action"] == "reopen_or_modify"
    assert entry["legacy_undo_alias_used"] is False


def test_lab_control_store_persists_journal_by_session_only(tmp_path) -> None:
    store = ProductLabProactiveControlStore(tmp_path)
    entry = {
        "artifact_type": "advanced_product_lab_control_journal_entry",
        "event_id": "dismiss-rec",
        "session_id": "session-a",
        "turn_id": "t1",
        "action": "dismiss",
        "target_candidate_id": "recommendation_prompt:0",
        "trigger_type": "recommendation_prompt",
    }

    artifact = store.write_journal(session_id="session-a", journal_entries=[entry])

    assert artifact["artifact_type"] == "advanced_product_lab_proactive_control_store"
    assert artifact["lab_isolated"] is True
    assert artifact["mainline_activation_enabled"] is False
    assert artifact["canonical_product_mutation_allowed"] is False
    assert artifact["scheduler_delivery_allowed"] is False
    assert artifact["journal_entry_count"] == 1
    assert store.read_journal(session_id="session-a") == [entry]
    assert store.read_journal(session_id="session-b") == []
