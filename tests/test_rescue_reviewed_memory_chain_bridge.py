from __future__ import annotations

from tests.test_runtime_lab_reviewed_memory_consumer_bridge import _context_pack


def _memory_projection(tmp_path):
    from app.memory.application.runtime_lab_reviewed_memory_consumer_bridge import (
        build_consumer_summary_projection_from_shadow_memory_context_pack,
    )

    return build_consumer_summary_projection_from_shadow_memory_context_pack(
        _context_pack(tmp_path)
    )


def _derived_views() -> dict:
    return {
        "rescue_history_summary": {
            "is_durable_memory_truth": False,
            "rescue_event_count": 2,
            "rescue_viability_posture": "mixed",
            "summary": "accepted one gentle spread; ignored one aggressive spread",
        },
        "adherence_summary": {
            "is_durable_memory_truth": False,
            "adherence_posture": "mixed",
        },
    }


def _budget_view(consumed: int = 2100) -> dict[str, int]:
    return {
        "base_budget_kcal": 1800,
        "effective_budget_kcal": 1800,
        "meal_consumption_total_kcal": consumed,
    }


def _body_plan_view() -> dict[str, object]:
    return {
        "safety_floor_kcal": 1200,
        "sex": "unspecified",
        "target_days": [
            {
                "local_date": f"2026-05-{10 + index:02d}",
                "base_budget_kcal": 1800,
                "calibration_adjustment_total_kcal": 0,
            }
            for index in range(5)
        ],
    }


def _candidate_output() -> dict[str, object]:
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


def test_reviewed_memory_bridge_derives_sanitized_rescue_contexts(tmp_path) -> None:
    from app.rescue.application.reviewed_memory_chain_bridge import (
        build_rescue_reviewed_memory_chain_contexts,
    )

    contexts = build_rescue_reviewed_memory_chain_contexts(
        memory_summary_projection=_memory_projection(tmp_path),
        derived_memory_views=_derived_views(),
        current_budget_view=_budget_view(),
        active_body_plan_view=_body_plan_view(),
    )

    assert contexts["budget_context"] == {
        "current_date": "shadow_lab",
        "overshoot_kcal": 300,
        "remaining_budget_kcal": -300,
    }
    assert contexts["body_plan_context"] == {
        "safety_floor_kcal": 1200,
        "target_days_count": 5,
        "sex": "unspecified",
    }
    assert contexts["rescue_history_context"] == {
        "recent_rescue_count": 2,
        "summary": "accepted one gentle spread; ignored one aggressive spread",
        "rescue_viability_posture": "mixed",
    }
    assert contexts["suppression_context"] == []
    assert contexts["runtime_effect_allowed"] is False
    assert contexts["manager_context_injected"] is False


def test_reviewed_memory_bridge_runs_existing_rescue_chain_without_commit(tmp_path) -> None:
    from app.rescue.application.reviewed_memory_chain_bridge import (
        run_rescue_reviewed_memory_shadow_chain,
    )

    artifact = run_rescue_reviewed_memory_shadow_chain(
        memory_summary_projection=_memory_projection(tmp_path),
        derived_memory_views=_derived_views(),
        current_budget_view=_budget_view(),
        active_body_plan_view=_body_plan_view(),
        open_proposals_view={"open_rescue_proposal_count": 0},
        proposal_candidate_output=_candidate_output(),
    )

    assert artifact["artifact_type"] == "rescue_shadow_chain_runner_artifact"
    assert artifact["status"] == "pass"
    assert artifact["reviewed_memory_bridge_used"] is True
    assert artifact["source_memory_artifact_type"] == (
        "runtime_lab_memory_consumer_summary_projection"
    )
    assert artifact["stage_trace"][-1] == {
        "stage": "rescue_proposal_shaping_fake_runner_artifact",
        "status": "pass",
    }
    assert artifact["proposal_committed"] is False
    assert artifact["day_budget_mutated"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["runtime_effect_allowed"] is False


def test_reviewed_memory_bridge_blocks_projection_claim_drift(tmp_path) -> None:
    from app.rescue.application.reviewed_memory_chain_bridge import (
        run_rescue_reviewed_memory_shadow_chain,
    )

    memory = _memory_projection(tmp_path)
    memory["rescue_proposal_committed"] = True

    artifact = run_rescue_reviewed_memory_shadow_chain(
        memory_summary_projection=memory,
        derived_memory_views=_derived_views(),
        current_budget_view=_budget_view(),
        active_body_plan_view=_body_plan_view(),
        open_proposals_view={"open_rescue_proposal_count": 0},
        proposal_candidate_output=_candidate_output(),
    )

    assert artifact["status"] == "blocked"
    assert artifact["reviewed_memory_bridge_used"] is False
    assert "rescue_shadow_summary_context_projection.status_blocked" in artifact[
        "blockers"
    ]
    assert artifact["proposal_committed"] is False
