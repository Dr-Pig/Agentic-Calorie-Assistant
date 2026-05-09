from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.runtime.application.proactive_no_send_shadow_evaluator import (  # noqa: E402
    ProactiveNoSendShadowInput,
    build_proactive_no_send_simulation,
)
from app.runtime.application.proactive_rescue_nudge_bridge import (  # noqa: E402
    build_rescue_nudge_no_send_review,
)


DEFAULT_OUTPUT_DIR = ROOT / "artifacts"
SUMMARY_CONSUMER_ARTIFACT = "proactive_no_send_summary_consumer_projection"
RESCUE_CONTEXT_ARTIFACT = "rescue_shadow_summary_context_projection"


def default_proactive_no_send_inputs(
    *,
    recommendation_prompt_review: dict[str, object] | None = None,
    rescue_nudge_review: dict[str, object] | None = None,
) -> list[ProactiveNoSendShadowInput]:
    return [
        ProactiveNoSendShadowInput(
            trigger_type="meal_reminder",
            local_time="18:30",
            data_sufficiency_status="basic",
            user_benefit_strength="moderate",
            wake_source="scheduled_check",
            user_relevant_reason="meal_window_missing_log_may_reduce_logging_burden",
        ),
        ProactiveNoSendShadowInput(
            trigger_type="weight_reminder",
            local_time="08:30",
            data_sufficiency_status="basic",
            user_benefit_strength="moderate",
            wake_source="scheduled_check",
            user_relevant_reason="weight_trend_accuracy_needs_opted_in_observation",
        ),
        ProactiveNoSendShadowInput(
            trigger_type="missing_log_reminder_with_cooldown",
            local_time="20:30",
            data_sufficiency_status="basic",
            user_benefit_strength="moderate",
            ignored_count=2,
            wake_source="scheduled_check",
            user_relevant_reason="today_missing_log_affects_daily_accuracy",
        ),
        ProactiveNoSendShadowInput(
            trigger_type="low_frequency_weight_log_reminder",
            local_time="08:30",
            data_sufficiency_status="basic",
            user_benefit_strength="moderate",
            wake_source="scheduled_check",
            user_relevant_reason="weight_trend_accuracy_needs_opted_in_observation",
        ),
        ProactiveNoSendShadowInput(
            trigger_type="weekly_insight",
            local_time="08:00",
            data_sufficiency_status="higher",
            user_benefit_strength="strong",
            dismissed_count=1,
            wake_source="scheduled_check",
            user_relevant_reason="weekly_summary_expected_after_enough_data",
        ),
        ProactiveNoSendShadowInput(
            trigger_type="pre_meal_budget_awareness",
            local_time="17:00",
            data_sufficiency_status="higher",
            user_benefit_strength="strong",
            lower_frequency_ready=True,
            wake_source="scheduled_check",
            user_relevant_reason="pre_meal_budget_context_may_help_decision",
        ),
        ProactiveNoSendShadowInput(
            trigger_type="overshoot_risk",
            local_time="17:30",
            data_sufficiency_status="higher",
            user_benefit_strength="strong",
            lower_frequency_ready=True,
            wake_source="state_threshold",
            user_relevant_reason="budget_threshold_may_help_next_meal_decision",
        ),
        ProactiveNoSendShadowInput(
            trigger_type="recommendation_prompt",
            local_time="17:30",
            data_sufficiency_status="higher",
            user_benefit_strength="strong",
            lower_frequency_ready=True,
            delivery_surface="app_open",
            wake_source="app_open",
            user_relevant_reason="app_open_dinner_context_can_reduce_decision_cost",
            recommendation_prompt_review=recommendation_prompt_review,
        ),
        ProactiveNoSendShadowInput(
            trigger_type="recommendation_nudge_meal_time",
            local_time="17:00",
            data_sufficiency_status="higher",
            user_benefit_strength="strong",
            wake_source="scheduled_check",
            user_relevant_reason="meal_time_context_without_push_permission",
        ),
        ProactiveNoSendShadowInput(
            trigger_type="recommendation_nudge_nearby",
            local_time="17:15",
            data_sufficiency_status="higher",
            user_benefit_strength="strong",
            wake_source="event_driven",
            user_relevant_reason="nearby_signal_requires_user_safe_surface",
        ),
        ProactiveNoSendShadowInput(
            trigger_type="swap_suggestion",
            local_time="19:00",
            data_sufficiency_status="higher",
            user_benefit_strength="moderate",
            wake_source="state_threshold",
            user_relevant_reason="post_commit_swap_requires_low_annoyance_context",
        ),
        ProactiveNoSendShadowInput(
            trigger_type="calibration_insight",
            local_time="09:30",
            data_sufficiency_status="higher",
            user_benefit_strength="strong",
            lower_frequency_ready=True,
            wake_source="state_threshold",
            user_relevant_reason="calibration_candidate_requires_explicit_consent",
        ),
        ProactiveNoSendShadowInput(
            trigger_type="calibration_nudge",
            local_time="09:30",
            data_sufficiency_status="higher",
            user_benefit_strength="strong",
            explicit_trigger_opt_out=True,
            wake_source="state_threshold",
            user_relevant_reason="calibration_nudge_opted_out_by_user_feedback",
        ),
        ProactiveNoSendShadowInput(
            trigger_type="rescue_nudge",
            local_time="19:30",
            data_sufficiency_status="higher",
            user_benefit_strength="strong",
            wake_source="state_threshold",
            user_relevant_reason="rescue_review_requires_later_consent",
            rescue_nudge_review=rescue_nudge_review,
        ),
        ProactiveNoSendShadowInput(
            trigger_type="location_based_food_push",
            wake_source="event_driven",
            user_relevant_reason="location_push_requires_later_explicit_consent",
        ),
        ProactiveNoSendShadowInput(
            trigger_type="strict_multi_day_correction",
            wake_source="state_threshold",
            user_relevant_reason="strict_correction_requires_later_explicit_consent",
        ),
        ProactiveNoSendShadowInput(
            trigger_type="emotional_coaching_nudge",
            wake_source="event_driven",
            user_relevant_reason="emotional_coaching_requires_later_explicit_consent",
        ),
        ProactiveNoSendShadowInput(
            trigger_type="memory_driven_intervention",
            wake_source="state_threshold",
            user_relevant_reason="memory_intervention_requires_later_explicit_consent",
        ),
    ]


def write_proactive_no_send_simulation(
    *,
    output_path: Path | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    summary_consumer_projection_path: Path | None = None,
    rescue_summary_context_projection_path: Path | None = None,
) -> Path:
    artifact = build_proactive_no_send_simulation(
        default_proactive_no_send_inputs(
            recommendation_prompt_review=_recommendation_prompt_review_from_projection(
                summary_consumer_projection_path
            ),
            rescue_nudge_review=_rescue_nudge_review_from_projection(
                rescue_summary_context_projection_path
            ),
        )
    )
    path = output_path or output_dir / "proactive_no_send_simulation.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _recommendation_prompt_review_from_projection(path: Path | None) -> dict[str, object] | None:
    if path is None:
        return None
    projection = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(projection, dict):
        raise ValueError("summary_consumer_projection.invalid_json_shape")
    if projection.get("artifact_type") != SUMMARY_CONSUMER_ARTIFACT:
        raise ValueError("summary_consumer_projection.unsupported_artifact_type")
    if projection.get("status") != "pass":
        raise ValueError("summary_consumer_projection.status_not_pass")
    review = projection.get("recommendation_prompt_review")
    return review if isinstance(review, dict) else None


def _rescue_nudge_review_from_projection(path: Path | None) -> dict[str, object] | None:
    if path is None:
        return None
    projection = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(projection, dict):
        raise ValueError("rescue_summary_context_projection.invalid_json_shape")
    if projection.get("artifact_type") != RESCUE_CONTEXT_ARTIFACT:
        raise ValueError("rescue_summary_context_projection.unsupported_artifact_type")
    if projection.get("status") != "pass":
        raise ValueError("rescue_summary_context_projection.status_not_pass")
    return build_rescue_nudge_no_send_review(projection)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build proactive no-send shadow simulation artifact.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--output")
    parser.add_argument("--summary-consumer-projection")
    parser.add_argument("--rescue-summary-context-projection")
    args = parser.parse_args()
    path = write_proactive_no_send_simulation(
        output_dir=Path(args.output_dir),
        output_path=Path(args.output) if args.output else None,
        summary_consumer_projection_path=Path(args.summary_consumer_projection)
        if args.summary_consumer_projection
        else None,
        rescue_summary_context_projection_path=Path(args.rescue_summary_context_projection)
        if args.rescue_summary_context_projection
        else None,
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
