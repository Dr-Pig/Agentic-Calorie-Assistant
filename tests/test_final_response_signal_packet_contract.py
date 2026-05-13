from __future__ import annotations

from app.shared.contracts.final_response_signal_packet import (
    build_final_response_signal_packet,
    build_final_response_signal_packet_contract,
)


def test_final_response_signal_packet_contract_declares_capability_signals() -> None:
    artifact = build_final_response_signal_packet_contract()

    assert artifact["artifact_type"] == "shared_final_response_signal_packet_contract"
    assert artifact["status"] == "pass"
    assert artifact["response_mode_default"] == "chat_first"
    assert artifact["capability_signal_ids"]["rescue"] == "rescue_plan_ready"
    assert artifact["default_action_affordances"]["proactive"] == [
        "dismiss_nudge",
        "snooze_nudge",
        "undo_nudge",
    ]


def test_final_response_signal_packet_derives_user_visible_capabilities_from_tool_results() -> None:
    artifact = build_final_response_signal_packet(
        final_response={
            "source_tool_call_ids": ["memory-1", "recommendation-1", "rescue-1"],
        },
        prior_results={
            "memory-1": {
                "normalized_result_envelope": {
                    "capability_id": "memory",
                }
            },
            "recommendation-1": {
                "normalized_result_envelope": {
                    "capability_id": "recommendation",
                }
            },
            "rescue-1": {
                "normalized_result_envelope": {
                    "capability_id": "rescue",
                }
            },
        },
    )

    assert artifact["status"] == "pass"
    plan = artifact["response_plan"]
    assert plan["user_visible_capabilities"] == [
        "memory",
        "recommendation",
        "rescue",
    ]
    assert "view_recommendation_offer" in plan["action_affordances"]
    assert "accept_rescue_plan" in plan["action_affordances"]
    assert artifact["capability_signals"] == [
        {"capability_id": "memory", "signal_id": "used_saved_preferences"},
        {"capability_id": "recommendation", "signal_id": "recommendation_ready"},
        {"capability_id": "rescue", "signal_id": "rescue_plan_ready"},
    ]


def test_final_response_signal_packet_respects_explicit_action_affordances_override() -> None:
    artifact = build_final_response_signal_packet(
        final_response={
            "source_tool_call_ids": ["proactive-1"],
            "action_affordances": ["dismiss_nudge"],
        },
        prior_results={
            "proactive-1": {
                "normalized_result_envelope": {
                    "capability_id": "proactive",
                }
            }
        },
    )

    assert artifact["response_plan"]["action_affordances"] == ["dismiss_nudge"]
