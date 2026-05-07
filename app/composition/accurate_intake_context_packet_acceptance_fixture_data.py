from __future__ import annotations


DEFAULT_CURRENT_BUDGET = {
    "local_date": "2026-05-07",
    "budget_kcal": 1600,
    "consumed_kcal": 420,
    "remaining_kcal": 1180,
    "active_meal_count": 1,
    "has_active_plan": True,
    "has_day_budget_ledger": True,
    "overshoot_status": "within_budget",
    "freshness_status": "current_turn",
}


SCENARIO_INPUTS = (
    {
        "scenario_id": "half_sugar_no_context",
        "raw_user_input": "\u6539\u534a\u7cd6",
        "injected_context": {
            "PENDING_FOLLOWUP": {"is_open": False},
            "TARGET_MEAL_REFERENCE": {},
            "RECENT_COMMITTED_MEALS_SUMMARY": [],
            "SESSION_SUMMARY": {"latest_assistant_turns": []},
        },
    },
    {
        "scenario_id": "half_sugar_resolved_target",
        "raw_user_input": "\u6539\u534a\u7cd6",
        "injected_context": {
            "PENDING_FOLLOWUP": {"is_open": False},
            "TARGET_MEAL_REFERENCE": {
                "meal_thread_id": 77,
                "meal_version_id": 88,
                "target_resolution_source": "manager_structured_target",
                "correction_confidence": "high",
            },
            "RECENT_COMMITTED_MEALS_SUMMARY": [],
            "SESSION_SUMMARY": {"latest_assistant_turns": []},
        },
    },
    {
        "scenario_id": "pending_followup_answer",
        "raw_user_input": "\u8c46\u5e72\u3001\u6d77\u5e36\u3001\u8ca2\u4e38",
        "injected_context": {
            "PENDING_FOLLOWUP": {
                "is_open": True,
                "meal_thread_id": 77,
                "pending_question": "\u9019\u4efd\u6ef7\u5473\u88e1\u6709\u54ea\u4e9b\u6771\u897f\uff1f",
            },
            "TARGET_MEAL_REFERENCE": {
                "meal_thread_id": 77,
                "meal_version_id": 88,
                "target_resolution_source": "pending_followup_state",
                "correction_confidence": "high",
            },
            "RECENT_COMMITTED_MEALS_SUMMARY": [],
            "SESSION_SUMMARY": {"latest_assistant_turns": ["\u9019\u4efd\u6ef7\u5473\u88e1\u6709\u54ea\u4e9b\u6771\u897f\uff1f"]},
        },
    },
    {
        "scenario_id": "ui_explicit_target_action",
        "raw_user_input": "",
        "injected_context": {
            "PENDING_FOLLOWUP": {"is_open": False},
            "TARGET_MEAL_REFERENCE": {},
            "RECENT_COMMITTED_MEALS_SUMMARY": [],
            "SESSION_SUMMARY": {"latest_assistant_turns": []},
        },
        "interaction_event": {
            "source": "ui",
            "target_object_type": "meal_thread",
            "target_object_id": "77",
        },
    },
)
