from __future__ import annotations

from typing import Any


def build_product_lab_simulated_turns() -> list[dict[str, Any]]:
    return [
        {
            "turn_id": "t1-offer",
            "lab_now_minute": 10,
            "post_turn_control_events": [
                {
                    "event_id": "dismiss-rec",
                    "action": "dismiss",
                    "target_candidate_id": "recommendation_prompt:0",
                    "trigger_type": "recommendation_prompt",
                    "scope": "candidate_instance",
                    "dismiss_reason": "too_frequent",
                    "next_signal_required": "new_app_open_with_qualified_pool",
                }
            ],
            "post_turn_chat_actions": [
                {
                    "event_id": "log-recommendation",
                    "target_candidate_id": "recommendation_prompt:0",
                    "action": "log_this",
                },
                {
                    "event_id": "accept-rescue",
                    "target_candidate_id": "rescue_nudge:1",
                    "action": "accept_rescue_plan",
                },
            ],
            "post_turn_memory_signal_events": [
                {
                    "signal_id": "golden-breakfast-oatmeal",
                    "signal_type": "golden_order",
                    "summary": "Morning Bar oatmeal is a reliable breakfast option.",
                    "source_object_refs": ["turn:t1-offer:user"],
                    "store_name": "Morning Bar",
                    "item_names": ["oatmeal"],
                    "estimated_kcal": 420,
                    "intended_consumers": [
                        "recommendation",
                        "rescue",
                        "proactive",
                    ],
                },
                {
                    "signal_id": "negative-cilantro",
                    "signal_type": "negative_preference",
                    "summary": "Avoid cilantro in recommendations.",
                    "source_object_refs": ["turn:t1-offer:user"],
                    "blocks_candidate_types": ["recommendation_candidate"],
                    "intended_consumers": ["recommendation"],
                },
            ],
            "post_turn_memory_review_decisions": [
                {
                    "candidate_id": "golden-breakfast-oatmeal",
                    "decision": "promote",
                    "confirmed": True,
                    "reviewer": "lab-human",
                    "reason": "confirmed_for_simulated_dogfood",
                },
                {
                    "candidate_id": "negative-cilantro",
                    "decision": "promote",
                    "confirmed": True,
                    "reviewer": "lab-human",
                    "reason": "confirmed_for_simulated_dogfood",
                },
            ],
        },
        {
            "turn_id": "t2-after-dismiss",
            "lab_now_minute": 20,
            "post_turn_chat_actions": [
                {
                    "event_id": "confirm-pending-intake",
                    "target_candidate_id": "pending_intake_followup:3",
                    "action": "confirm_pending_intake",
                }
            ],
        },
        {
            "turn_id": "t3-material-signal",
            "lab_now_minute": 30,
            "observed_material_signals": ["new_app_open_with_qualified_pool"],
            "post_turn_control_events": [
                {
                    "event_id": "snooze-rescue",
                    "action": "snooze",
                    "target_candidate_id": "rescue_nudge:1",
                    "trigger_type": "rescue_nudge",
                    "scope": "candidate_instance",
                    "snooze_minutes": 60,
                    "release_signal": "material_budget_change_or_user_reopens_rescue",
                }
            ],
        },
        {"turn_id": "t4-before-snooze-release", "lab_now_minute": 70},
    ]


__all__ = ["build_product_lab_simulated_turns"]
