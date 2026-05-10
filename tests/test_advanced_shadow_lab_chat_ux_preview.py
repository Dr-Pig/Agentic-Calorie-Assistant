from __future__ import annotations

import json

from app.advanced_shadow_lab.chat_ux_packet import (
    build_advanced_shadow_chat_ux_packet,
)
from test_advanced_shadow_lab_chat_ux_packet import (
    _fixture_chain,
    _proactive_copy,
    _recommendation_copy,
    _rescue_copy,
)


def test_chat_ux_packet_projects_lab_only_sanitized_copy_previews() -> None:
    packet = build_advanced_shadow_chat_ux_packet(
        fixture_chain_artifact=_fixture_chain(),
        copy_diagnostic_artifacts=[
            _recommendation_copy(),
            _rescue_copy(),
            _proactive_copy(),
        ],
    )
    serialized = json.dumps(packet, ensure_ascii=False)

    assert packet["status"] == "pass"
    assert packet["chat_packets"][0]["lab_only_copy_preview"] == {
        "preview_text": "Consider the FamilyMart option",
        "lab_only": True,
        "served_to_user": False,
        "delivery_attempted": False,
        "source_field": "model_output_summary.diagnostic_copy_preview",
        "source_surface": "recommendation_prompt_reason_copy",
    }
    assert packet["chat_packets"][1]["lab_only_copy_preview"] == {
        "preview_text": "Recover the rest of the week",
        "lab_only": True,
        "served_to_user": False,
        "delivery_attempted": False,
        "source_field": "model_output_summary.diagnostic_copy_preview",
        "source_surface": "rescue_proposal_copy_posture",
    }
    assert packet["copy_diagnostic_metadata"]["proactive_chat_copy_posture"][
        "alignment_status"
    ] == "not_applicable_to_existing_packet"
    assert "review-only prompt" not in serialized
    assert "draft_prompt" not in serialized
    assert "proposal_headline" not in serialized
    assert packet["served_to_user"] is False
    assert packet["delivery_attempted"] is False
    assert packet["scheduler_enqueued"] is False
    assert packet["user_facing_behavior_changed"] is False


def test_chat_ux_packet_omits_preview_when_copy_is_not_aligned() -> None:
    drift = _recommendation_copy()
    drift["output_guard"] = {"status": "blocked"}

    packet = build_advanced_shadow_chat_ux_packet(
        fixture_chain_artifact=_fixture_chain(),
        copy_diagnostic_artifacts=[drift],
    )

    assert packet["status"] == "pass"
    assert packet["chat_packets"][0]["copy_status"] == "copy_diagnostic_blocked"
    assert packet["chat_packets"][0]["lab_only_copy_preview"] is None
