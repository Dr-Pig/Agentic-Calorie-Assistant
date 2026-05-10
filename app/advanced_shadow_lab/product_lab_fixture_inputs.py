from __future__ import annotations

from typing import Any

from app.recommendation.application.three_node_shadow_contract import (
    build_fixture_recommendation_three_node_input,
)


def build_product_lab_fixture_inputs() -> dict[str, Any]:
    return {
        "memory_summary_projection": _memory_projection(),
        "recommendation_payload": _recommendation_payload(),
        "derived_memory_views": _derived_views(),
        "current_budget_view": _budget_view(),
        "active_body_plan_view": _body_plan_view(),
        "open_proposals_view": {"open_rescue_proposal_count": 0},
        "proposal_candidate_output": _proposal_candidate_output(),
        "user_control_models": {
            "recommendation_prompt": _controls("new_app_open_with_qualified_pool"),
            "rescue_nudge": _controls(
                "material_budget_change_or_user_reopens_rescue"
            ),
        },
        "interaction_plan": [
            {"action": "dismiss", "dismiss_reason": "too_frequent"},
            {"action": "snooze", "snooze_minutes": 120},
        ],
    }


def _recommendation_payload() -> dict[str, Any]:
    payload = build_fixture_recommendation_three_node_input()
    golden = _candidate(payload, "golden-1")
    golden.update(
        {
            "estimated_kcal": 520,
            "evidence_posture": "exact",
            "availability_posture": "available",
            "realistic_executable": True,
            "user_accessible": True,
            "store_name": "FamilyMart",
            "source_refs": ["memory_candidate:pref-1", "memory_candidate:golden-1"],
        }
    )
    return payload


def _candidate(payload: dict[str, Any], candidate_id: str) -> dict[str, Any]:
    for item in payload["candidate_source_fixture"]:
        if isinstance(item, dict) and item.get("candidate_id") == candidate_id:
            return item
    raise ValueError(f"candidate_not_found:{candidate_id}")


def _memory_projection() -> dict[str, Any]:
    return {
        "artifact_type": "runtime_lab_memory_consumer_summary_projection",
        "status": "pass",
        "preference_profile_summary": {
            "freshness_posture": "fresh",
            "accepted_shadow_candidate_ids": ["pref-1"],
            "negative_preference_blockers": ["neg-1"],
        },
        "golden_order_summary": {
            "orders": [{"candidate_id": "golden-1", "store_name": "FamilyMart"}]
        },
        "suppression_summary": {
            "suppression_blockers": [
                {"candidate_id": "suppress-1", "trigger_type": "rescue_nudge"}
            ]
        },
    }


def _derived_views() -> dict[str, Any]:
    return {
        "rescue_history_summary": {
            "is_durable_memory_truth": False,
            "rescue_event_count": 1,
        },
        "adherence_summary": {
            "is_durable_memory_truth": False,
            "adherence_posture": "mixed",
        },
    }


def _budget_view() -> dict[str, int]:
    return {
        "base_budget_kcal": 1800,
        "effective_budget_kcal": 1800,
        "meal_consumption_total_kcal": 2100,
    }


def _body_plan_view() -> dict[str, Any]:
    return {
        "safety_floor_kcal": 1200,
        "target_days": [
            {
                "local_date": f"2026-05-{10 + index:02d}",
                "base_budget_kcal": 1800,
                "calibration_adjustment_total_kcal": 0,
            }
            for index in range(5)
        ],
    }


def _proposal_candidate_output() -> dict[str, Any]:
    return {
        "proposal_headline": "Fixture headline, not user-facing",
        "proposal_summary": "Fixture summary, not user-facing",
        "coaching_frame": "Fixture frame, not user-facing",
        "recommended_days": 2,
        "daily_kcal_adjustment": -150,
        "cap_mode": "standard_15_percent",
        "special_posture": "standard_spread",
        "rubric": {
            "future_oriented": True,
            "no_shame": True,
            "not_user_facing": True,
            "fixture_only": True,
        },
    }


def _controls(next_signal: str) -> dict[str, Any]:
    return {
        "dismiss_reason_choices": [
            "not_relevant_now",
            "already_handled",
            "too_frequent",
        ],
        "snooze_window": {"kind": "duration", "minutes": 180},
        "undo_scope": "current_no_send_candidate_only",
        "next_signal_required": next_signal,
    }


__all__ = ["build_product_lab_fixture_inputs"]
