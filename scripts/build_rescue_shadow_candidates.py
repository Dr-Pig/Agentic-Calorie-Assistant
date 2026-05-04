from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.rescue.application.shadow_candidate_artifact import (  # noqa: E402
    build_rescue_shadow_candidates_artifact,
)
from app.rescue.domain.shadow_context import RescueContextFixture  # noqa: E402
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_OUTPUT = "artifacts/rescue_shadow_candidates.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the offline RescueShadow RS5 candidate artifact."
    )
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    artifact = build_rescue_shadow_candidates_artifact(
        scenarios=(("rs5_default_large_overshoot_fixture", _default_context()),)
    )
    payload = artifact.model_dump(mode="json")
    write_json_artifact(Path(args.output), payload)
    print(
        json.dumps(
            {
                "artifact": args.output,
                "candidate_count": payload["summary"]["candidate_count"],
                "real_runtime_effect": payload["real_runtime_effect"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def _default_context() -> RescueContextFixture:
    return RescueContextFixture(
        user_id="user-rs5-default",
        local_date="2026-05-04",
        timezone="Asia/Taipei",
        current_budget={
            "active": True,
            "daily_budget_kcal": 1800,
            "consumed_kcal": 1800,
            "remaining_kcal": 0,
            "day_part": "evening",
        },
        active_body_plan={
            "active": True,
            "daily_target_kcal": 1800,
            "safety_floor_kcal": 1400,
        },
        recent_committed_meals={
            "meal_count_today": 3,
            "logging_coverage": 0.9,
        },
        deficit_summary={
            "weekly_deficit_gap_kcal": 700,
            "weekly_deficit_posture": "off_track",
        },
        overshoot_summary={
            "today_overshoot_kcal": 650,
            "weekly_overshoot_kcal": 0,
            "recent_overshoot_days": 0,
        },
        calibration_posture={},
        adherence_summary={
            "logging_quality": "high",
            "adherence_score": 0.8,
        },
        rescue_history_summary={},
        open_proposals={},
    )


if __name__ == "__main__":
    raise SystemExit(main())
