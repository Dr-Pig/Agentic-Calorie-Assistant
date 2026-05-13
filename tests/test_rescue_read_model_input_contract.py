from __future__ import annotations

from app.rescue.application.read_model_input_packet import (
    build_rescue_read_model_input_packet,
)


def _ingress_event() -> dict:
    return {
        "artifact_type": "rescue_ingress_event",
        "event_id": "rescue-ingress-test",
        "request_id": "req-1",
        "scope_keys": {
            "user_id": "user-1",
            "workspace_id": "workspace-1",
            "project_id": "project-1",
            "surface": "advanced_lab",
            "run_id": "run-1",
        },
        "canonical_source_refs": [
            {
                "source_type": "current_budget_view",
                "source_id": "req-1",
                "field_path": "context_snapshot.active_day_state.budget_summary",
            }
        ],
        "raw_user_input_redacted": "今天超標了，幫我想想怎麼補救",
        "current_budget_view": {
            "local_date": "2026-05-13",
            "base_budget_kcal": 1800,
            "effective_budget_kcal": 1800,
            "meal_consumption_total_kcal": 2250,
            "remaining_kcal": -450,
            "source": "context_snapshot.active_day_state.budget_summary",
        },
        "recent_committed_meals_view": {
            "meal_count": 2,
            "meals": [
                {
                    "meal_thread_id": "meal-1",
                    "meal_title": "ramen",
                    "total_kcal": 1050,
                },
                {
                    "meal_thread_id": "meal-2",
                    "meal_title": "beef bowl",
                    "total_kcal": 1200,
                },
            ],
        },
        "active_body_plan_view": {
            "safety_floor_kcal": 1500,
            "target_days": [
                {
                    "local_date": "2026-05-14",
                    "base_budget_kcal": 1800,
                    "calibration_adjustment_total_kcal": 0,
                },
                {
                    "local_date": "2026-05-15",
                    "base_budget_kcal": 1800,
                    "calibration_adjustment_total_kcal": 0,
                },
            ],
            "source": "context_snapshot.active_body_plan",
        },
        "open_proposals_view": {
            "open_rescue_proposal_count": 0,
            "active_proposal_ids": [],
        },
        "sanitized_source_trace": {
            "context_snapshot": {},
            "current_intake_event_context": {"must_not_be_read": True},
            "transcript": "not for rescue input packet",
        },
        "runtime_connected": True,
        "lab_isolated": True,
        "canonical_mutation_changed": False,
        "production_scheduler_delivery_allowed": False,
        "manager_context_packet_changed": False,
    }


def test_read_model_packet_projects_only_structured_rescue_inputs() -> None:
    packet = build_rescue_read_model_input_packet(
        _ingress_event(),
        rescue_history_summary={"recent_rescue_count": 1},
        adherence_summary={"recent_over_budget_days": 2},
        proactive_status_view={
            "budget_alert_cooldown_active": False,
            "suppressed_trigger_types": [],
        },
    )
    payload = packet.model_dump()

    assert payload["artifact_type"] == "rescue_read_model_input_packet"
    assert payload["status"] == "ready"
    assert payload["scope_keys"]["user_id"] == "user-1"
    assert payload["view_source_order"] == [
        "CurrentBudgetView",
        "RecentCommittedMealsView",
        "RescueHistorySummary",
        "AdherenceSummary",
        "OpenProposalsView",
        "ProactiveStatusView",
        "ActiveBodyPlanView",
    ]
    assert payload["current_budget_view"]["overshoot_kcal"] == 450
    assert payload["recent_committed_meals_view"]["meal_count"] == 2
    assert payload["active_body_plan_view"]["target_day_count"] == 2
    assert payload["open_proposals_view"]["open_rescue_proposal_count"] == 0
    assert payload["proactive_status_view"]["budget_alert_cooldown_active"] is False


def test_read_model_packet_blocks_missing_required_budget_without_mutating() -> None:
    event = _ingress_event()
    event["current_budget_view"] = {"local_date": "2026-05-13"}

    packet = build_rescue_read_model_input_packet(event)
    payload = packet.model_dump()

    assert payload["status"] == "blocked"
    assert payload["blockers"] == ["missing_current_budget_view"]
    assert payload["current_budget_view"]["view_available"] is False
    assert payload["runtime_effect_allowed"] is False
    assert payload["canonical_mutation_changed"] is False
    assert payload["production_scheduler_delivery_allowed"] is False


def test_read_model_packet_does_not_expose_raw_trace_or_current_intake_context() -> None:
    packet = build_rescue_read_model_input_packet(_ingress_event())
    payload = packet.model_dump()
    rendered = repr(payload)

    assert "sanitized_source_trace" not in rendered
    assert "raw_user_input_redacted" not in rendered
    assert "must_not_be_read" not in rendered
    assert "not for rescue input packet" not in rendered
    assert payload["forbidden_input_sources"] == [
        "current_intake_event_context",
        "raw_transcript_search",
        "full_session_history",
        "durable_memory_truth",
    ]


def test_read_model_packet_keeps_mainline_and_runtime_activation_walled_off() -> None:
    payload = build_rescue_read_model_input_packet(_ingress_event()).model_dump()

    assert payload["lab_enabled"] is True
    assert payload["lab_isolated"] is True
    assert payload["mainline_activation_enabled"] is False
    assert payload["mainline_runtime_connected"] is False
    assert payload["runtime_effect_allowed"] is False
    assert payload["manager_context_packet_changed_in_mainline"] is False
    assert payload["durable_product_memory_written_in_mainline"] is False
