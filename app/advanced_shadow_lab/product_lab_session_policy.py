from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_session_store import unsafe_segment_blocker
from app.advanced_shadow_lab.product_lab_turn_policy import observed_material_signals


LAB_MODE = "isolated_advanced_product_lab"
INTENT_FIXTURE = "advanced_recommendation_rescue_proactive_loop"


def session_blockers(
    *,
    session_id: str,
    turns: list[Mapping[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    session_blocker = unsafe_segment_blocker("session_id", session_id)
    if session_blocker:
        blockers.append(session_blocker)
    for turn in turns:
        turn_blocker = unsafe_segment_blocker("turn_id", str(turn.get("turn_id") or ""))
        if turn_blocker:
            blockers.append(turn_blocker)
    if not turns:
        blockers.append("turns.empty")
    return blockers


def turn_input(*, session_id: str, turn_spec: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "turn_id": str(turn_spec.get("turn_id") or ""),
        "surface": "chat",
        "user_utterance": "simulated dogfood text is not a semantic oracle",
        "semantic_intent_fixture": INTENT_FIXTURE,
        "lab_now_minute": lab_now_minute(turn_spec),
        "observed_material_signals": observed_material_signals(turn_spec),
        "planned_event_rescue_enabled": (
            turn_spec.get("planned_event_rescue_enabled") is True
        ),
    }


def lab_now_minute(turn_spec: Mapping[str, Any]) -> int:
    value = turn_spec.get("lab_now_minute")
    return value if isinstance(value, int) else 0


__all__ = ["LAB_MODE", "session_blockers", "turn_input", "lab_now_minute"]
