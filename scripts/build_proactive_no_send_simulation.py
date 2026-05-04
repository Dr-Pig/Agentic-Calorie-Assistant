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
        ),
        ProactiveNoSendShadowInput(
            trigger_type="weight_reminder",
            local_time="08:30",
            data_sufficiency_status="basic",
            user_benefit_strength="moderate",
        ),
        ProactiveNoSendShadowInput(
            trigger_type="missing_log_reminder_with_cooldown",
            local_time="20:30",
            data_sufficiency_status="basic",
            user_benefit_strength="moderate",
        ),
        ProactiveNoSendShadowInput(
            trigger_type="low_frequency_weight_log_reminder",
            local_time="08:30",
            data_sufficiency_status="basic",
            user_benefit_strength="moderate",
        ),
        ProactiveNoSendShadowInput(
            trigger_type="weekly_insight",
            local_time="08:00",
            data_sufficiency_status="higher",
            user_benefit_strength="strong",
        ),
        ProactiveNoSendShadowInput(
            trigger_type="pre_meal_budget_awareness",
            local_time="17:00",
            data_sufficiency_status="higher",
            user_benefit_strength="strong",
            lower_frequency_ready=True,
        ),
        ProactiveNoSendShadowInput(
            trigger_type="overshoot_risk",
            local_time="17:30",
            data_sufficiency_status="higher",
            user_benefit_strength="strong",
            lower_frequency_ready=True,
        ),
        ProactiveNoSendShadowInput(
            trigger_type="recommendation_prompt",
            local_time="17:30",
            data_sufficiency_status="higher",
            user_benefit_strength="strong",
            lower_frequency_ready=True,
            delivery_surface="app_open",
        ),
        ProactiveNoSendShadowInput(
            trigger_type="recommendation_nudge_meal_time",
            local_time="17:00",
            data_sufficiency_status="higher",
            user_benefit_strength="strong",
        ),
        ProactiveNoSendShadowInput(
            trigger_type="recommendation_nudge_nearby",
            local_time="17:15",
            data_sufficiency_status="higher",
            user_benefit_strength="strong",
        ),
        ProactiveNoSendShadowInput(
            trigger_type="swap_suggestion",
            local_time="19:00",
            data_sufficiency_status="higher",
            user_benefit_strength="moderate",
        ),
        ProactiveNoSendShadowInput(
            trigger_type="calibration_insight",
            local_time="09:30",
            data_sufficiency_status="higher",
            user_benefit_strength="strong",
            lower_frequency_ready=True,
        ),
        ProactiveNoSendShadowInput(
            trigger_type="calibration_nudge",
            local_time="09:30",
            data_sufficiency_status="higher",
            user_benefit_strength="strong",
        ),
        ProactiveNoSendShadowInput(
            trigger_type="rescue_nudge",
            local_time="19:30",
            data_sufficiency_status="higher",
            user_benefit_strength="strong",
        ),
        ProactiveNoSendShadowInput(trigger_type="location_based_food_push"),
        ProactiveNoSendShadowInput(trigger_type="strict_multi_day_correction"),
        ProactiveNoSendShadowInput(trigger_type="emotional_coaching_nudge"),
        ProactiveNoSendShadowInput(trigger_type="memory_driven_intervention"),
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
