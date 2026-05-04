from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.contracts import _base_artifact
from app.memory.application.long_term_context_shadow.utils import (
    _float_value,
    _list_of_dicts,
)


def _weekly_insight_shadow_artifact(fixture: dict[str, Any]) -> dict[str, Any]:
    metrics = _deterministic_metrics(fixture)
    return _base_artifact(
        artifact_type="weekly_insight_shadow_plan",
        fixture=fixture,
        extra={
            "source_spec": "docs/specs/L4A_MEMORY_MODEL_SPEC.md#93a-1-weeklyinsightreport",
            "weekly_insight_report_written": False,
            "proactive_sent": False,
            "scheduler_activated": False,
            "manager_context_injected": False,
            "narrative_summary_generated": False,
            "future_surface_policy": _future_surface_policy(),
            "deterministic_metrics": metrics,
            "llm_boundary": _llm_boundary(),
            "review_packet": _review_packet(metrics),
            "blocked_runtime_dependencies": _blocked_runtime_dependencies(),
        },
    )


def _deterministic_metrics(fixture: dict[str, Any]) -> dict[str, Any]:
    budgets = _list_of_dicts(fixture.get("budget_summaries"))
    body_observations = _list_of_dicts(fixture.get("body_observations"))
    meal_logs = _list_of_dicts(fixture.get("meal_logs"))
    overshoot_days = sum(
        1 for item in budgets if _float_value(item.get("overshoot_kcal")) > 0
    )
    at_or_under_budget = max(0, len(budgets) - overshoot_days)
    weight_logs = sum(1 for item in body_observations if item.get("weight_kg"))
    return {
        "math_truth_owner": "budget_body_calibration_canonical_summaries",
        "budget_day_count": len(budgets),
        "meal_log_count": len(meal_logs),
        "body_observation_count": len(body_observations),
        "overshoot_day_count": overshoot_days,
        "at_or_under_budget_day_count": at_or_under_budget,
        "weight_log_count": weight_logs,
        "insufficient_week_window": len(budgets) < 7,
        "calorie_or_weight_math_mutated": False,
    }


def _future_surface_policy() -> dict[str, Any]:
    return {
        "primary_surface": "chat_draft",
        "ui_history_mirror_allowed_later": True,
        "push_send_allowed_now": False,
        "user_dismiss_or_snooze_required_before_runtime": True,
    }


def _llm_boundary() -> dict[str, bool]:
    return {
        "may_write_narrative_later": True,
        "may_invent_metrics": False,
        "may_send_without_proactive_gate": False,
    }


def _review_packet(metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "human_review_required": True,
        "runtime_effect_allowed": False,
        "draft_sections": [
            "positive_highlights",
            "logging_consistency",
            "budget_pattern_summary",
            "annoyance_suppression_check",
        ],
        "positive_highlight_candidates": _positive_highlights(metrics),
        "suppression_checks": [
            {
                "check_id": "insufficient_week_window",
                "should_stay_silent": bool(metrics["insufficient_week_window"]),
                "reason": "avoid overconfident weekly insight with too little data",
            },
            {
                "check_id": "no_new_signal",
                "should_stay_silent": metrics["budget_day_count"] == 0
                and metrics["meal_log_count"] == 0,
                "reason": "do not send empty weekly insight",
            },
        ],
    }


def _positive_highlights(metrics: dict[str, Any]) -> list[dict[str, str]]:
    highlights: list[dict[str, str]] = []
    if metrics["at_or_under_budget_day_count"] > 0:
        highlights.append(
            {
                "highlight_id": "budget_days_at_or_under_target",
                "text": (
                    f"{metrics['at_or_under_budget_day_count']} fixture day(s) "
                    "at or under budget"
                ),
            }
        )
    if metrics["weight_log_count"] > 0:
        highlights.append(
            {
                "highlight_id": "weight_logging_present",
                "text": f"{metrics['weight_log_count']} fixture weight log(s)",
            }
        )
    return highlights


def _blocked_runtime_dependencies() -> list[str]:
    return [
        "approved_proactive_scheduler_gate",
        "chat_draft_review_surface",
        "weekly_window_canonical_export",
        "live_llm_narrative_eval",
        "user_dismiss_snooze_correction_trace",
    ]


__all__ = ["_weekly_insight_shadow_artifact"]
