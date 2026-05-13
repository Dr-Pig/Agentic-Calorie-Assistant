from __future__ import annotations

from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn
from tests.test_advanced_product_lab_runtime import _fixture_inputs, _turn


def test_product_lab_proactive_gate_suppresses_rescue_inside_trigger_cooldown() -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn={
            **_turn("lab-turn-rescue-cooldown"),
            "lab_now_minute": 35,
            "proactive_gate_context": {
                "last_sent_minute_by_trigger": {"rescue_nudge": 10},
                "cooldown_minutes_by_trigger": {"rescue_nudge": 60},
            },
        },
        fixture_inputs=_fixture_inputs(),
    )

    proactive = artifact["product_lab_proactive_artifact"]
    assert proactive["status"] == "pass"
    assert [candidate["trigger_type"] for candidate in proactive["candidates"]] == [
        "recommendation_prompt"
    ]
    [trace] = proactive["omission_traces"]
    assert trace["trigger_type"] == "rescue_nudge"
    assert trace["omission_reason"] == "cooldown_active"
    assert trace["review_decision"]["status"] == "suppressed_context_or_data"
    assert artifact["lab_chat_surface"]["messages"][0]["candidate_id"] == (
        "recommendation_prompt:0"
    )
    assert proactive["scheduler_delivery_allowed"] is False


def test_product_lab_proactive_gate_allows_rescue_after_trigger_cooldown() -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn={
            **_turn("lab-turn-rescue-cooldown-released"),
            "lab_now_minute": 75,
            "proactive_gate_context": {
                "last_sent_minute_by_trigger": {"rescue_nudge": 10},
                "cooldown_minutes_by_trigger": {"rescue_nudge": 60},
            },
        },
        fixture_inputs=_fixture_inputs(),
    )

    proactive = artifact["product_lab_proactive_artifact"]
    assert proactive["status"] == "pass"
    assert [candidate["trigger_type"] for candidate in proactive["candidates"]] == [
        "recommendation_prompt",
        "rescue_nudge",
    ]
    assert proactive["omission_traces"] == []
