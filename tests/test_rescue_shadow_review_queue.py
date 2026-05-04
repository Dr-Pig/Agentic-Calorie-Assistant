from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.rescue.application.shadow_candidate_artifact import (
    build_rescue_shadow_candidate_artifact,
)
from app.rescue.domain.shadow_context import RescueContextFixture
from app.rescue.fixtures.shadow_scenarios import rescue_shadow_scenario_fixture_pairs


ROOT = Path(__file__).resolve().parents[1]

ACTIVE_RUNTIME_ENTRYPOINTS = [
    "app/main.py",
    "app/routes.py",
    "app/schemas.py",
    "app/models.py",
    "app/composition/intake_routes.py",
    "app/composition/today_routes.py",
    "app/composition/body_plan_routes.py",
    "app/composition/v2_routes.py",
    "app/composition/intake_turn_orchestrator.py",
    "app/composition/intake_execution_orchestrator.py",
    "app/composition/intake_execution_response.py",
    "app/runtime/application/manager_service.py",
    "app/runtime/application/sidecar_service.py",
    "app/composition/intake_manager_tool_batch.py",
    "app/runtime/interface/provider_runtime.py",
    "app/composition/manager_context_runtime.py",
    "app/intake/application/manager_context_policy.py",
    "app/runtime/agent/manager_context_payload.py",
]


def _context_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "user_id": "user-rs7",
        "local_date": "2026-05-04",
        "timezone": "Asia/Taipei",
        "current_budget": {
            "active": True,
            "daily_budget_kcal": 1800,
            "consumed_kcal": 1800,
            "remaining_kcal": 0,
            "day_part": "evening",
        },
        "active_body_plan": {
            "active": True,
            "daily_target_kcal": 1800,
            "safety_floor_kcal": 1400,
        },
        "recent_committed_meals": {
            "meal_count_today": 3,
            "logging_coverage": 0.9,
        },
        "deficit_summary": {
            "weekly_deficit_gap_kcal": 0,
            "weekly_deficit_posture": "on_track",
        },
        "overshoot_summary": {
            "today_overshoot_kcal": 0,
            "weekly_overshoot_kcal": 0,
            "recent_overshoot_days": 0,
        },
        "calibration_posture": {},
        "adherence_summary": {
            "logging_quality": "high",
            "adherence_score": 0.8,
        },
        "rescue_history_summary": {},
        "open_proposals": {},
    }
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(payload.get(key), dict):
            payload[key] = {**payload[key], **value}  # type: ignore[index]
        else:
            payload[key] = value
    return payload


def _context(**overrides: object) -> RescueContextFixture:
    return RescueContextFixture(**_context_payload(**overrides))


def _candidate(scenario_id: str, context: RescueContextFixture):
    return build_rescue_shadow_candidate_artifact(
        scenario_id=scenario_id,
        context=context,
    )


def test_review_queue_prioritizes_high_medium_low_and_deferred_candidates() -> None:
    from app.rescue.application.shadow_review_queue import build_rescue_shadow_review_queue

    high = _candidate(
        "rs7_high_repeated_good_logging",
        _context(
            overshoot_summary={
                "today_overshoot_kcal": 180,
                "weekly_overshoot_kcal": 760,
                "recent_overshoot_days": 4,
            },
            deficit_summary={
                "weekly_deficit_gap_kcal": 850,
                "weekly_deficit_posture": "off_track",
            },
        ),
    )
    medium = _candidate(
        "rs7_medium_one_time_large",
        _context(
            overshoot_summary={"today_overshoot_kcal": 650},
            deficit_summary={
                "weekly_deficit_gap_kcal": 700,
                "weekly_deficit_posture": "off_track",
            },
        ),
    )
    low = _candidate(
        "rs7_low_small_overshoot",
        _context(
            overshoot_summary={"today_overshoot_kcal": 80},
            deficit_summary={
                "weekly_deficit_gap_kcal": -250,
                "weekly_deficit_posture": "on_track",
            },
        ),
    )
    deferred = _candidate(
        "rs7_deferred_open_proposal",
        _context(
            overshoot_summary={"today_overshoot_kcal": 650},
            open_proposals={"has_open_rescue_like_proposal": True},
        ),
    )

    queue = build_rescue_shadow_review_queue(
        candidates=[high, medium, low, deferred]
    )

    assert [item.scenario_id for item in queue.high_priority_rescue_candidates] == [
        "rs7_high_repeated_good_logging"
    ]
    assert (
        queue.high_priority_rescue_candidates[0].selected_shadow_option_type
        == "ask_user_context_first"
    )
    assert [item.scenario_id for item in queue.medium_priority_rescue_candidates] == [
        "rs7_medium_one_time_large"
    ]
    assert [item.scenario_id for item in queue.low_priority_rescue_candidates] == [
        "rs7_low_small_overshoot"
    ]
    assert [item.scenario_id for item in queue.rejected_or_deferred] == [
        "rs7_deferred_open_proposal"
    ]
    assert queue.runtime_effect_allowed is False
    assert queue.rescue_committed is False
    assert queue.summary.total_candidate_count == 4
    assert queue.summary.high_priority_count == 1
    assert queue.summary.medium_priority_count == 1
    assert queue.summary.low_priority_count == 1
    assert queue.summary.rejected_or_deferred_count == 1


def test_review_queue_rs6_fixture_set_routes_expected_blockers() -> None:
    from app.rescue.application.shadow_candidate_artifact import (
        build_rescue_shadow_candidates_artifact,
    )
    from app.rescue.application.shadow_review_queue import build_rescue_shadow_review_queue

    artifact = build_rescue_shadow_candidates_artifact(
        scenarios=rescue_shadow_scenario_fixture_pairs()
    )
    queue = build_rescue_shadow_review_queue(
        candidates=artifact.rescue_shadow_candidates
    )

    deferred_ids = {item.scenario_id for item in queue.rejected_or_deferred}
    assert "existing_open_proposal_blocks_duplicate" in deferred_ids
    assert "no_active_budget_or_body_plan_blocks" in deferred_ids

    low_ids = {item.scenario_id for item in queue.low_priority_rescue_candidates}
    assert "small_overshoot_no_rescue_needed" in low_ids
    assert "low_logging_quality_downgrades_confidence" in low_ids

    all_ids = (
        {item.scenario_id for item in queue.high_priority_rescue_candidates}
        | {item.scenario_id for item in queue.medium_priority_rescue_candidates}
        | low_ids
        | deferred_ids
    )
    assert all_ids == set(artifact.summary.scenario_ids)


def test_review_queue_defers_too_aggressive_correction_risk() -> None:
    from app.rescue.application.shadow_review_queue import build_rescue_shadow_review_queue

    candidate = _candidate(
        "rs7_aggressive_correction_risk",
        _context(
            current_budget={"daily_budget_kcal": 3000},
            active_body_plan={
                "daily_target_kcal": 3000,
                "safety_floor_kcal": 2850,
            },
            overshoot_summary={"today_overshoot_kcal": 1400},
            deficit_summary={
                "weekly_deficit_gap_kcal": 1400,
                "weekly_deficit_posture": "off_track",
            },
        ),
    )
    queue = build_rescue_shadow_review_queue(candidates=[candidate])

    assert queue.rejected_or_deferred[0].scenario_id == "rs7_aggressive_correction_risk"
    assert "rescue_risk_too_aggressive" in queue.rejected_or_deferred[0].reasons


def test_review_queue_contract_rejects_unknown_fields() -> None:
    module = importlib.import_module("app.rescue.domain.shadow_review_queue")

    with pytest.raises(ValidationError):
        module.RescueShadowReviewQueue(
            summary={
                "total_candidate_count": 0,
                "high_priority_count": 0,
                "medium_priority_count": 0,
                "low_priority_count": 0,
                "rejected_or_deferred_count": 0,
                "scenario_ids": [],
            },
            high_priority_rescue_candidates=[],
            medium_priority_rescue_candidates=[],
            low_priority_rescue_candidates=[],
            rejected_or_deferred=[],
            reasons=[],
            unexpected_runtime_field="must_not_be_silently_accepted",
        )


def test_review_queue_summary_must_match_bucket_counts() -> None:
    module = importlib.import_module("app.rescue.domain.shadow_review_queue")

    with pytest.raises(ValidationError):
        module.RescueShadowReviewQueue(
            summary={
                "total_candidate_count": 1,
                "high_priority_count": 1,
                "medium_priority_count": 0,
                "low_priority_count": 0,
                "rejected_or_deferred_count": 0,
                "scenario_ids": ["missing"],
            },
            high_priority_rescue_candidates=[],
            medium_priority_rescue_candidates=[],
            low_priority_rescue_candidates=[],
            rejected_or_deferred=[],
            reasons=[],
        )


def test_active_runtime_entrypoints_do_not_import_shadow_review_queue() -> None:
    forbidden_tokens = [
        "app.rescue.domain.shadow_review_queue",
        "app.rescue.application.shadow_review_queue",
        "shadow_review_queue",
        "RescueShadowReviewQueue",
        "build_rescue_shadow_review_queue",
    ]

    for relative_path in ACTIVE_RUNTIME_ENTRYPOINTS:
        text = (ROOT / relative_path).read_text(encoding="utf-8-sig")
        for token in forbidden_tokens:
            assert token not in text, f"{relative_path} imports or references RS7 sidecar token {token!r}"
