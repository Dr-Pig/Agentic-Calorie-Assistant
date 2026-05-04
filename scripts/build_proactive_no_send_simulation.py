from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.runtime.application.proactive_no_send_shadow_evaluator import (
    ProactiveNoSendShadowInput,
    build_proactive_no_send_simulation,
)


DEFAULT_OUTPUT_DIR = ROOT / "artifacts"


def default_proactive_no_send_inputs() -> list[ProactiveNoSendShadowInput]:
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
) -> Path:
    artifact = build_proactive_no_send_simulation(default_proactive_no_send_inputs())
    path = output_path or output_dir / "proactive_no_send_simulation.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build proactive no-send shadow simulation artifact.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--output")
    args = parser.parse_args()
    path = write_proactive_no_send_simulation(
        output_dir=Path(args.output_dir),
        output_path=Path(args.output) if args.output else None,
    )
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
