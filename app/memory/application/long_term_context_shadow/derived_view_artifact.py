from __future__ import annotations

from typing import Any

from app.memory.application.derived_summaries import (
    build_adherence_summary,
    build_calibration_history_summary,
    build_golden_order_summary,
    build_intake_completeness_summary,
    build_preference_profile_summary,
    build_rescue_history_summary,
    build_suppression_summary,
)
from app.memory.application.long_term_context_shadow.contracts import _base_artifact
from app.memory.application.long_term_context_shadow.fixture_reader import (
    _committed_meal_events,
)
from app.memory.application.long_term_context_shadow.utils import (
    _list_of_dicts,
    _model_dict,
    _normalize_datetime,
    _parse_datetime,
)
from app.memory.domain.summaries import InteractionPreferenceEvent


def _derived_memory_views_shadow_artifact(fixture: dict[str, Any]) -> dict[str, Any]:
    meal_events = _committed_meal_events(fixture)
    budget_summaries = _list_of_dicts(fixture.get("budget_summaries"))
    diagnostics = _list_of_dicts(fixture.get("calibration_diagnostics"))
    interaction_events = _interaction_preference_events(fixture)
    rescue_events = _list_of_dicts(fixture.get("rescue_events"))
    derived_views = {
        "preference_profile_summary": _view_payload(
            build_preference_profile_summary(meal_events)
        ),
        "intake_completeness_summary": _view_payload(
            build_intake_completeness_summary(meal_events)
        ),
        "adherence_summary": _view_payload(build_adherence_summary(budget_summaries)),
        "rescue_history_summary": _view_payload(
            build_rescue_history_summary(
                budget_summaries=budget_summaries,
                rescue_events=rescue_events,
            )
        ),
        "calibration_history_summary": _view_payload(
            build_calibration_history_summary(diagnostics)
        ),
        "suppression_summary": _view_payload(
            build_suppression_summary(interaction_events)
        ),
        "golden_order_summary": _view_payload(build_golden_order_summary(meal_events)),
    }
    return _base_artifact(
        artifact_type="derived_memory_views_shadow_eval",
        fixture=fixture,
        extra={
            "source_spec": "docs/specs/L4A_MEMORY_MODEL_SPEC.md",
            "derived_views_written_to_runtime": False,
            "canonical_truth_replaced_by_memory": False,
            "pre_materialized_runtime_summary_written": False,
            "derived_views": derived_views,
            "consumer_alignment": {
                "recommendation": [
                    "preference_profile_summary",
                    "golden_order_summary",
                ],
                "intake_clarification": ["intake_completeness_summary"],
                "calibration": [
                    "intake_completeness_summary",
                    "adherence_summary",
                    "calibration_history_summary",
                ],
                "proactive": ["suppression_summary", "adherence_summary"],
                "rescue_later": ["rescue_history_summary", "adherence_summary"],
            },
        },
    )


def _view_payload(view: object) -> dict[str, Any]:
    payload = _model_dict(view)
    payload["runtime_effect_allowed"] = False
    payload["source_refs_required"] = True
    return payload


def _interaction_preference_events(
    fixture: dict[str, Any],
) -> list[InteractionPreferenceEvent]:
    events: list[InteractionPreferenceEvent] = []
    for index, item in enumerate(_list_of_dicts(fixture.get("interaction_events"))):
        observed_at = item.get("observed_at")
        if not observed_at:
            continue
        parsed = _parse_datetime(observed_at)
        if parsed is None:
            continue
        events.append(
            InteractionPreferenceEvent(
                event_id=str(item.get("trace_id") or f"interaction-{index}"),
                occurred_at=_normalize_datetime(parsed),
                trigger_type=str(item.get("trigger_type") or "unspecified"),
                action=str(item.get("action") or "ignored"),
            )
        )
    return events
