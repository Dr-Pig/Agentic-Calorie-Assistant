from __future__ import annotations

import json
from pathlib import Path

from app.advanced_shadow_lab.product_lab_session_replay import (
    run_advanced_product_lab_dogfood_session,
)
from tests.test_advanced_product_lab_runtime import _fixture_inputs


def test_rescue_proposal_read_model_keeps_pending_proposal_in_active_inbox(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id="rescue-inbox-active-session",
        fixture_inputs=_fixture_inputs(),
        turns=[{"turn_id": "t1-offer"}],
    )

    assert artifact["status"] == "pass"
    assert artifact["lab_rescue_active_inbox_count"] == 1
    assert artifact["lab_rescue_history_count"] == 0

    model = artifact["lab_rescue_proposal_read_model"]
    [active] = model["active_inbox_rows"]
    assert active["candidate_id"] == "rescue_nudge:1"
    assert active["lifecycle_status"] == "pending_user_rescue_commit_confirmation"
    assert active["active_inbox_visible"] is True
    assert active["concise_summary"] == "Smooth today over 2 days."
    assert "150 kcal per day" in active["expandable_user_facing_explanation"]
    assert model["raw_trace_included"] is False
    assert model["sidecar_diagnostic_included"] is False


def test_rescue_proposal_read_model_moves_dismissed_proposal_to_history(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id="rescue-inbox-dismiss-session",
        fixture_inputs=_fixture_inputs(),
        turns=[
            {"turn_id": "t1-offer"},
            {
                "turn_id": "t2-dismiss",
                "post_turn_chat_actions": [
                    {
                        "event_id": "dismiss-rescue",
                        "target_candidate_id": "rescue_nudge:1",
                        "action": "dismiss_rescue_plan",
                    }
                ],
            },
        ],
    )

    assert artifact["status"] == "pass"
    assert artifact["lab_rescue_active_inbox_count"] == 0
    assert artifact["lab_rescue_history_count"] == 1
    assert artifact["lab_rescue_history_statuses"] == ["dismissed"]
    assert artifact["canonical_product_mutation_allowed"] is False

    model = artifact["lab_rescue_proposal_read_model"]
    assert model["active_inbox_rows"] == []
    [history] = model["history_rows"]
    assert history["candidate_id"] == "rescue_nudge:1"
    assert history["lifecycle_status"] == "dismissed"
    assert history["active_inbox_visible"] is False
    assert history["concise_summary"] == "Smooth today over 2 days."
    assert "2 days" in history["expandable_user_facing_explanation"]
    assert history["source_refs"]
    serialized_history = json.dumps(history, ensure_ascii=False)
    assert "raw trace" not in serialized_history.lower()
    assert "sidecar" not in serialized_history.lower()
    assert model["served_to_mainline_user"] is False
    assert model["scheduler_delivery_allowed"] is False
    assert model["durable_product_memory_written"] is False


def test_rescue_proposal_read_model_records_accepted_pending_history(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id="rescue-inbox-accept-session",
        fixture_inputs=_fixture_inputs(),
        turns=[
            {
                "turn_id": "t1-accept",
                "post_turn_chat_actions": [
                    {
                        "event_id": "accept-rescue",
                        "target_candidate_id": "rescue_nudge:1",
                        "action": "accept_rescue_plan",
                    }
                ],
            }
        ],
    )

    assert artifact["status"] == "pass"
    assert artifact["lab_rescue_active_inbox_count"] == 0
    assert artifact["lab_rescue_history_statuses"] == [
        "accepted_pending_commit_confirmation"
    ]
    [history] = artifact["lab_rescue_proposal_read_model"]["history_rows"]
    assert history["active_inbox_visible"] is False
    assert history["canonical_product_mutation_allowed"] is False
    assert "150 kcal per day" in history["expandable_user_facing_explanation"]


def test_rescue_proposal_read_model_keeps_negotiation_in_active_inbox(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id="rescue-inbox-negotiation-session",
        fixture_inputs=_fixture_inputs(),
        turns=[
            {
                "turn_id": "t1-negotiate",
                "post_turn_chat_actions": [
                    {
                        "event_id": "shorter-rescue",
                        "target_candidate_id": "rescue_nudge:1",
                        "action": "request_shorter_plan",
                    },
                    {
                        "event_id": "why-rescue",
                        "target_candidate_id": "rescue_nudge:1",
                        "action": "ask_why_this_plan",
                    },
                ],
            }
        ],
    )

    assert artifact["status"] == "pass"
    assert artifact["lab_rescue_active_inbox_count"] == 1
    assert artifact["lab_rescue_history_statuses"] == [
        "request_shorter_variant",
        "request_explanation",
    ]
    [active] = artifact["lab_rescue_proposal_read_model"]["active_inbox_rows"]
    assert active["candidate_id"] == "rescue_nudge:1"
    assert active["lifecycle_status"] == "pending_user_rescue_commit_confirmation"
    assert active["active_inbox_visible"] is True
    assert artifact["lab_action_state"]["requested_rescue_next_signals"] == [
        "chat_negotiation_requested_shorter_plan",
        "chat_explanation_requested",
    ]
    assert artifact["canonical_product_mutation_allowed"] is False
