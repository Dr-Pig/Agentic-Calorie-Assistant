from __future__ import annotations

import pytest

from app.rescue.application.self_use_trace_ingress import (
    RescueIngressScopeError,
    build_rescue_ingress_event_from_self_use_trace,
    build_rescue_trace_ingress_diagnostic_artifact,
)


def test_self_use_trace_ingress_maps_current_budget_body_and_meals() -> None:
    event = build_rescue_ingress_event_from_self_use_trace(
        _self_use_trace(),
        scope_overrides={
            "workspace_id": "workspace-1",
            "project_id": "advanced-product-lab",
            "surface": "web_shell",
            "run_id": "run-1",
        },
    )

    assert event["artifact_type"] == "rescue_ingress_event"
    assert event["event_id"].startswith("rescue-ingress-")
    assert event["request_id"] == "req-123"
    assert event["source_bundle"] == "current_shell_self_use"
    assert event["scope_keys"] == {
        "user_id": "user-1",
        "workspace_id": "workspace-1",
        "project_id": "advanced-product-lab",
        "surface": "web_shell",
        "run_id": "run-1",
    }
    assert event["current_budget_view"] == {
        "local_date": "2026-05-13",
        "base_budget_kcal": 1800,
        "effective_budget_kcal": 1800,
        "meal_consumption_total_kcal": 2130,
        "remaining_kcal": -330,
        "source": "context_snapshot.active_day_state.budget_summary",
    }
    assert event["recent_committed_meals_view"] == {
        "meal_count": 2,
        "meals": [
            {"meal_thread_id": "meal-1", "meal_title": "ramen", "total_kcal": 950},
            {"meal_thread_id": "meal-2", "meal_title": "matsuya beef bowl", "total_kcal": 1180},
        ],
    }
    assert event["active_body_plan_view"] == {
        "safety_floor_kcal": 1500,
        "target_days": [],
        "source": "context_snapshot.active_body_plan",
    }
    assert event["open_proposals_view"] == {"open_rescue_proposal_count": 0}
    assert event["manager_context_contract"]["context_policy_version"] == (
        "accurate_intake_mvp_context_policy_v1"
    )
    assert event["rescue_triggered"] is False
    assert event["runtime_effect_allowed"] is False
    assert event["canonical_mutation_changed"] is False
    assert event["self_use_v1_affected"] is False


def test_self_use_trace_ingress_records_source_refs_and_redacts_secrets() -> None:
    trace = _self_use_trace()
    trace["request"]["text"] = "I ate ramen with token sk-live-abc123"

    event = build_rescue_ingress_event_from_self_use_trace(
        trace,
        scope_overrides={
            "workspace_id": "workspace-1",
            "project_id": "advanced-product-lab",
            "surface": "web_shell",
            "run_id": "run-1",
        },
    )

    source_types = {ref["source_type"] for ref in event["canonical_source_refs"]}
    assert {
        "runtime_request_trace",
        "manager_context_packet",
        "current_budget_view",
        "meal_thread",
        "active_body_plan",
    }.issubset(source_types)
    assert event["raw_user_input_redacted"] == "I ate ramen with token [REDACTED]"
    assert event["secret_redaction"]["raw_secret_values_stored"] is False
    assert "request.text" in event["secret_redaction"]["redacted_fields"]


def test_self_use_trace_ingress_rejects_missing_scope() -> None:
    with pytest.raises(RescueIngressScopeError) as exc_info:
        build_rescue_ingress_event_from_self_use_trace(_self_use_trace())

    assert str(exc_info.value) == "missing_scope_keys:workspace_id,project_id,surface,run_id"


def test_self_use_trace_ingress_diagnostic_batches_rejections_without_effects() -> None:
    artifact = build_rescue_trace_ingress_diagnostic_artifact(
        [_self_use_trace(), {"trace_meta": {"request_id": "bad-scope"}}],
        scope_overrides={
            "workspace_id": "workspace-1",
            "project_id": "advanced-product-lab",
            "surface": "web_shell",
            "run_id": "run-1",
        },
    )

    assert artifact["artifact_type"] == "rescue_trace_ingress_diagnostic"
    assert artifact["status"] == "blocked"
    assert artifact["event_count"] == 1
    assert artifact["rejected_trace_count"] == 1
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["rescue_triggered"] is False
    assert artifact["canonical_mutation_changed"] is False
    assert artifact["production_scheduler_delivery_allowed"] is False
    assert artifact["best_practice_evidence"]["required"] is True
    assert {
        "openai_agents_guardrails",
        "openai_agent_evals",
        "openai_agents_sessions",
    }.issubset(set(artifact["best_practice_evidence"]["sources_checked"]))


def _self_use_trace() -> dict[str, object]:
    return {
        "trace_meta": {
            "request_id": "req-123",
            "user_id": "user-1",
            "local_date": "2026-05-13",
            "bundle": "current_shell_self_use",
        },
        "request": {
            "user_id": "user-1",
            "text": "I ate ramen and a beef bowl today",
            "local_date": "2026-05-13",
        },
        "context_snapshot": {
            "metadata": {
                "context_policy_version": "accurate_intake_mvp_context_policy_v1"
            },
            "active_day_state": {
                "budget_summary": {
                    "budget_kcal": 1800,
                    "consumed_kcal": 2130,
                    "remaining_kcal": -330,
                }
            },
            "active_body_plan": {"safety_floor_kcal": 1500},
            "meal_threads": [
                {
                    "meal_thread_id": "meal-1",
                    "meal_title": "ramen",
                    "active_version": {"total_kcal": 950},
                },
                {
                    "meal_thread_id": "meal-2",
                    "meal_title": "matsuya beef bowl",
                    "active_version": {"total_kcal": 1180},
                },
            ],
        },
    }
