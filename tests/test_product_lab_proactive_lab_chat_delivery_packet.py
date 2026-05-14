from __future__ import annotations

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_proactive import run_product_lab_proactive
from app.advanced_shadow_lab.product_lab_proactive_send_skip import (
    run_product_lab_proactive_send_skip_fixture,
)
from tests.test_product_lab_proactive_send_skip_fixture import _proactive_artifact
from tests.test_product_lab_proactive_wake_sources import (
    _memory_pack,
    _recommendation_artifact,
    _rescue_artifact,
)


def test_lab_chat_delivery_packet_applies_contextual_send_skip_decision() -> None:
    baseline = _proactive_artifact()
    send_skip = run_product_lab_proactive_send_skip_fixture(
        pre_delivery_review=baseline["pre_delivery_review"],
        provider_decisions=[
            {
                "candidate_id": "recommendation_prompt:0",
                "send_or_skip": "send",
                "reason_summary": "Relevant app-open meal help.",
                "chat_first_copy": "要不要我幫你挑一個現在可行的選項？",
                "skip_reason": "",
                "reason_codes": ["app_open"],
                "delivery_request": False,
                "scheduler_request": False,
                "notification_request": False,
                "mutation_request": False,
            },
            {
                "candidate_id": "rescue_nudge:1",
                "send_or_skip": "skip",
                "reason_summary": "Interrupt cost is too high.",
                "chat_first_copy": "",
                "skip_reason": "interrupt_cost_too_high",
                "reason_codes": ["high_interrupt_cost"],
                "delivery_request": False,
                "scheduler_request": False,
                "notification_request": False,
                "mutation_request": False,
            },
        ],
    )

    artifact = run_product_lab_proactive(
        turn={"session_id": "s1", "turn_id": "t1", "surface": "chat"},
        fixture_inputs=build_product_lab_fixture_inputs(),
        memory_context_pack=_memory_pack(),
        recommendation_artifact=_recommendation_artifact(),
        rescue_artifact=_rescue_artifact(),
        contextual_send_skip_artifact=send_skip,
    )

    assert artifact["status"] == "pass"
    assert artifact["candidate_count"] == 1
    assert [candidate["candidate_id"] for candidate in artifact["candidates"]] == [
        "recommendation_prompt:0"
    ]
    assert artifact["omission_traces"][-1]["omission_reason"] == (
        "contextual_send_skip:interrupt_cost_too_high"
    )
    delivery = artifact["delivery_packet"]
    assert delivery["artifact_type"] == "advanced_product_lab_proactive_delivery_packet"
    assert delivery["delivery_surface"] == "chat"
    assert delivery["contextual_send_skip_applied"] is True
    assert delivery["send_candidate_ids"] == ["recommendation_prompt:0"]
    assert delivery["skipped_candidate_ids"] == ["rescue_nudge:1"]
    assert delivery["chat_first_delivery_records"] == [
        {
            "candidate_id": "recommendation_prompt:0",
            "trigger_type": "recommendation_prompt",
            "chat_first_copy": "要不要我幫你挑一個現在可行的選項？",
            "delivery_surface": "chat",
            "served_to_mainline_user": False,
            "notification_delivery_allowed": False,
            "scheduler_delivery_allowed": False,
        }
    ]
    assert delivery["notification_delivery_attempted"] is False
    assert delivery["scheduler_delivery_attempted"] is False
    assert artifact["source_outputs_read"][-1] == (
        "advanced_product_lab_proactive_contextual_send_skip_fixture"
    )
