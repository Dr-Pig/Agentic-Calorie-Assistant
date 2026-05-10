from __future__ import annotations

import json

from app.advanced_shadow_lab.chat_ux_packet import (
    build_advanced_shadow_chat_ux_packet,
)
from app.advanced_shadow_lab.e2e_fixture_chain import (
    run_advanced_shadow_e2e_fixture_chain,
)
from app.advanced_shadow_lab.live_bundle_fixture_inputs import (
    build_live_bundle_chain_payload,
)


def test_chat_ux_packet_projects_fixture_chain_without_serving_or_mutating() -> None:
    packet = build_advanced_shadow_chat_ux_packet(
        fixture_chain_artifact=_fixture_chain()
    )
    serialized = json.dumps(packet, ensure_ascii=False)

    assert packet["artifact_type"] == "advanced_shadow_chat_ux_packet_artifact"
    assert packet["status"] == "pass"
    assert packet["packet_mode"] == "lab_only_non_served_projection"
    assert packet["packet_count"] == 2
    assert [item["workflow_family"] for item in packet["chat_packets"]] == [
        "recommendation",
        "rescue",
    ]
    assert [item["trigger_type"] for item in packet["chat_packets"]] == [
        "recommendation_prompt",
        "rescue_nudge",
    ]
    assert packet["control_path_summary"] == {
        "status": "pass",
        "configured_paths": {"dismiss": True, "snooze": True, "undo": True},
        "interaction_actions_observed": ["dismiss", "snooze"],
        "next_signal_required_present": True,
    }
    for item in packet["chat_packets"]:
        assert item["surface"] == "chat"
        assert item["chat_first"] is True
        assert item["copy_status"] == "copy_diagnostic_not_attached"
        assert item["served_to_user"] is False
        assert item["delivery_attempted"] is False
        assert item["scheduler_enqueued"] is False
        assert item["canonical_mutation_requested"] is False
        assert item["controls"]["dismiss_reason_required"] is True
        assert item["controls"]["snooze_window_present"] is True
        assert item["controls"]["undo_scope"] == "current_no_send_candidate_only"
        assert item["next_signal_required"]
        assert item["source_artifact_refs"] == [
            "advanced_shadow_e2e_fixture_chain_artifact",
            "proactive_no_send_review_sink_artifact",
        ]
    assert packet["mainline_runtime_connected"] is False
    assert packet["user_facing_behavior_changed"] is False
    assert packet["recommendation_served"] is False
    assert packet["rescue_committed"] is False
    assert packet["proactive_sent"] is False
    assert packet["mutation_changed"] is False
    assert "Chicken salad" not in serialized
    assert "Fixture headline" not in serialized


def test_chat_ux_packet_blocks_missing_required_controls() -> None:
    chain = _fixture_chain()
    chain["terminal_review_sink"]["records"][0]["undo_scope"] = ""

    packet = build_advanced_shadow_chat_ux_packet(fixture_chain_artifact=chain)

    assert packet["status"] == "blocked"
    assert packet["blockers"] == ["chat_packet[0].undo_scope_missing"]
    assert packet["chat_packets"] == []
    assert packet["user_facing_behavior_changed"] is False
    assert packet["mutation_changed"] is False


def test_chat_ux_packet_blocks_activation_claim_drift() -> None:
    chain = _fixture_chain()
    chain["recommendation_served"] = True
    chain["terminal_review_sink"]["delivery_attempted"] = True

    packet = build_advanced_shadow_chat_ux_packet(fixture_chain_artifact=chain)

    assert packet["status"] == "blocked"
    assert packet["blockers"] == [
        "fixture_chain.recommendation_served",
        "terminal_review_sink.delivery_attempted",
    ]
    assert packet["recommendation_served"] is False
    assert packet["delivery_attempted"] is False
    assert packet["user_facing_behavior_changed"] is False


def _fixture_chain() -> dict[str, object]:
    payload = build_live_bundle_chain_payload()
    return run_advanced_shadow_e2e_fixture_chain(
        memory_summary_projection=payload["memory_summary_projection"],
        recommendation_payload=payload["recommendation_payload"],
        derived_memory_views=payload["derived_memory_views"],
        current_budget_view=payload["current_budget_view"],
        active_body_plan_view=payload["active_body_plan_view"],
        open_proposals_view=payload["open_proposals_view"],
        proposal_candidate_output=payload["proposal_candidate_output"],
        user_control_models=payload["user_control_models"],
        interaction_plan=payload["interaction_plan"],
    )
