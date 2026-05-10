from __future__ import annotations

import json
from pathlib import Path

from app.advanced_shadow_lab.model_profiles import (
    ADVANCED_LAB_TARGET_REASONING_PROFILE_ID,
)
from app.recommendation.application.three_node_shadow_contract import (
    build_fixture_recommendation_three_node_input,
)


def test_advanced_shadow_live_bundle_runner_writes_existing_terminal_comparison(
    tmp_path: Path,
) -> None:
    from scripts import run_advanced_shadow_lab_live_bundle as runner

    inputs = _write_bundle_inputs(tmp_path)
    output = tmp_path / "advanced_shadow_comparison.json"
    artifact_dir = tmp_path / "intermediate"

    exit_code = runner.main(
        [
            "--memory-dogfood-replay-review",
            str(inputs["memory_review"]),
            "--chain-payload",
            str(inputs["chain_payload"]),
            "--output",
            str(output),
            "--artifact-dir",
            str(artifact_dir),
        ]
    )
    terminal = json.loads(output.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert terminal["artifact_type"] == "advanced_shadow_comparison_artifact"
    assert terminal["status"] == "pass"
    assert terminal["live_diagnostic_signals"]["recommendation_copy_live_diagnostic"] == {
        "live_invoked": False,
        "live_provider_used": False,
        "provider_mode": "fake_provider_contract_test",
        "output_guard_status": "pass",
    }
    assert terminal["live_diagnostic_signals"]["rescue_copy_live_diagnostic"] == {
        "live_invoked": False,
        "live_provider_used": False,
        "provider_mode": "fake_provider_contract_test",
        "output_guard_status": "pass",
    }
    assert terminal["recommendation_served"] is False
    assert terminal["proactive_sent"] is False
    assert terminal["mutation_changed"] is False
    assert terminal["user_facing_behavior_changed"] is False
    assert terminal["product_readiness_claimed"] is False

    intermediate_types = {
        path.name: json.loads(path.read_text(encoding="utf-8"))["artifact_type"]
        for path in artifact_dir.glob("*.json")
    }
    assert intermediate_types == {
        "advanced_shadow_e2e_fixture_chain.json": (
            "advanced_shadow_e2e_fixture_chain_artifact"
        ),
        "advanced_shadow_dogfood_replay.json": "advanced_shadow_dogfood_replay_artifact",
        "advanced_shadow_recommendation_copy_live_diagnostic.json": (
            "advanced_shadow_recommendation_copy_live_diagnostic_artifact"
        ),
        "advanced_shadow_rescue_copy_live_diagnostic.json": (
            "advanced_shadow_rescue_copy_live_diagnostic_artifact"
        ),
    }
    fixture_chain = json.loads(
        (artifact_dir / "advanced_shadow_e2e_fixture_chain.json").read_text(
            encoding="utf-8"
        )
    )
    assert [stage["artifact_type"] for stage in fixture_chain["stage_artifacts"]] == (
        fixture_chain["stage_order"]
    )
    assert fixture_chain["terminal_review_sink"]["status"] == "pass"
    assert fixture_chain["mainline_runtime_connected"] is False
    assert fixture_chain["recommendation_served"] is False
    assert fixture_chain["proactive_sent"] is False
    assert fixture_chain["mutation_changed"] is False
    assert fixture_chain["product_readiness_claimed"] is False


def test_advanced_shadow_live_bundle_runner_blocks_live_without_env(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts import run_advanced_shadow_lab_live_bundle as runner

    monkeypatch.delenv("ADVANCED_SHADOW_LAB_ALLOW_LIVE_LLM_DIAGNOSTIC", raising=False)
    inputs = _write_bundle_inputs(tmp_path)
    output = tmp_path / "advanced_shadow_comparison.json"

    exit_code = runner.main(
        [
            "--memory-dogfood-replay-review",
            str(inputs["memory_review"]),
            "--chain-payload",
            str(inputs["chain_payload"]),
            "--provider-mode",
            "live",
            "--output",
            str(output),
            "--artifact-dir",
            str(tmp_path / "intermediate"),
        ]
    )
    terminal = json.loads(output.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert terminal["artifact_type"] == "advanced_shadow_comparison_artifact"
    assert terminal["status"] == "pass"
    assert terminal["live_diagnostic_signals"]["recommendation_copy_live_diagnostic"] == {
        "live_invoked": False,
        "live_provider_used": False,
        "provider_mode": "not_run",
        "output_guard_status": "not_run",
    }
    assert terminal["live_diagnostic_signals"]["rescue_copy_live_diagnostic"] == {
        "live_invoked": False,
        "live_provider_used": False,
        "provider_mode": "not_run",
        "output_guard_status": "not_run",
    }
    assert terminal["surface_status_rows"][2]["finding"] == "live_diagnostic_not_run"
    assert terminal["surface_status_rows"][3]["finding"] == "live_diagnostic_not_run"
    assert terminal["product_readiness_claimed"] is False
    assert terminal["user_facing_behavior_changed"] is False


def test_advanced_shadow_live_bundle_rejects_unknown_profile_before_reading_inputs(
    tmp_path: Path,
) -> None:
    from scripts import run_advanced_shadow_lab_live_bundle as runner

    output = tmp_path / "blocked_unknown_profile.json"
    artifact_dir = tmp_path / "intermediate"

    exit_code = runner.main(
        [
            "--memory-dogfood-replay-review",
            str(tmp_path / "missing_memory_review.json"),
            "--chain-payload",
            str(tmp_path / "missing_chain_payload.json"),
            "--provider-mode",
            "live",
            "--allow-live-provider",
            "--provider-profile-id",
            "builderspace-unknown-model",
            "--output",
            str(output),
            "--artifact-dir",
            str(artifact_dir),
        ]
    )
    terminal = json.loads(output.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert terminal["artifact_type"] == "advanced_shadow_comparison_artifact"
    assert terminal["status"] == "blocked"
    assert terminal["provider_mode"] == "not_invoked"
    assert terminal["blockers"] == [
        "unsupported_advanced_lab_provider_profile:builderspace-unknown-model"
    ]
    assert terminal["live_provider_used"] is False
    assert terminal["manager_context_packet_changed"] is False
    assert terminal["user_facing_behavior_changed"] is False
    assert not artifact_dir.exists()


def test_advanced_shadow_live_bundle_rejects_kimi_profile_before_reading_inputs(
    tmp_path: Path,
) -> None:
    from scripts import run_advanced_shadow_lab_live_bundle as runner

    output = tmp_path / "blocked_kimi_profile.json"
    artifact_dir = tmp_path / "intermediate"

    exit_code = runner.main(
        [
            "--memory-dogfood-replay-review",
            str(tmp_path / "missing_memory_review.json"),
            "--chain-payload",
            str(tmp_path / "missing_chain_payload.json"),
            "--provider-mode",
            "live",
            "--allow-live-provider",
            "--provider-profile-id",
            ADVANCED_LAB_TARGET_REASONING_PROFILE_ID,
            "--output",
            str(output),
            "--artifact-dir",
            str(artifact_dir),
        ]
    )
    terminal = json.loads(output.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert terminal["artifact_type"] == "advanced_shadow_comparison_artifact"
    assert terminal["status"] == "blocked"
    assert terminal["provider_mode"] == "not_invoked"
    assert terminal["blockers"] == [
        "profile_not_live_diagnostic_allowed;kimi_live_calls_forbidden"
    ]
    assert "not_kimi_activation" in terminal["non_claims"]
    assert terminal["live_provider_used"] is False
    assert terminal["recommendation_served"] is False
    assert terminal["proactive_sent"] is False
    assert terminal["mutation_changed"] is False
    assert not artifact_dir.exists()


def test_advanced_shadow_live_bundle_blocks_synthetic_chain_summary_fallback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from scripts import run_advanced_shadow_lab_live_bundle as runner

    monkeypatch.setattr(runner, "_build_fixture_chain", lambda _: _chain_without_stages())
    inputs = _write_bundle_inputs(tmp_path)
    output = tmp_path / "advanced_shadow_comparison.json"
    artifact_dir = tmp_path / "intermediate"

    exit_code = runner.main(
        [
            "--memory-dogfood-replay-review",
            str(inputs["memory_review"]),
            "--chain-payload",
            str(inputs["chain_payload"]),
            "--output",
            str(output),
            "--artifact-dir",
            str(artifact_dir),
        ]
    )
    recommendation = json.loads(
        (artifact_dir / "advanced_shadow_recommendation_copy_live_diagnostic.json")
        .read_text(encoding="utf-8")
    )

    assert exit_code == 0
    assert recommendation["status"] == "blocked"
    assert recommendation["provider_invoked"] is False
    assert recommendation["recommendation_served"] is False
    assert "recommendation_summary.status_not_pass" in recommendation["blockers"]
    assert (
        "recommendation_summary.stage_artifact_missing:"
        "recommendation_shadow_summary_consumer_quality_report"
    ) in recommendation["blockers"]
    assert recommendation["source_candidate_count"] == 0


def test_advanced_shadow_live_bundle_runner_source_stays_manual_diagnostic() -> None:
    source = Path("scripts/run_advanced_shadow_lab_live_bundle.py").read_text(
        encoding="utf-8"
    )

    forbidden_tokens = [
        "app.routes",
        "app.database",
        "app.models",
        "app.runtime.interface.provider_runtime",
        "FastAPI",
        "APIRouter",
        "Scheduler(",
        "schedule_job",
        "send_notification",
        "create_engine",
        "alembic",
        "scheduler_enabled=True",
        "production_scheduler_delivery_allowed=True",
        "recommendation_served=True",
        "user_facing_behavior_changed=True",
        "BUILDERSPACE_MANAGER_MODEL",
    ]
    for token in forbidden_tokens:
        assert token not in source
    assert "ADVANCED_SHADOW_LAB_ALLOW_LIVE_LLM_DIAGNOSTIC" in source
    assert "--model" not in source
    assert "--provider-profile-id" in source
    assert "resolve_live_bundle_profile_gate" in source
    assert "manager_model_override=str(profile[\"model_id\"])" in source
    assert "advanced_shadow_live_bundle_artifact" not in source
    assert "advanced_shadow_bundle_fixture" not in source


def _write_bundle_inputs(tmp_path: Path) -> dict[str, Path]:
    memory_review = tmp_path / "memory_review.json"
    chain_payload = tmp_path / "chain_payload.json"
    memory_review.write_text(
        json.dumps(_memory_review(), ensure_ascii=False),
        encoding="utf-8",
    )
    chain_payload.write_text(
        json.dumps(_chain_payload(), ensure_ascii=False),
        encoding="utf-8",
    )
    return {"memory_review": memory_review, "chain_payload": chain_payload}


def _memory_review() -> dict[str, object]:
    return {
        "artifact_type": "runtime_lab_memory_dogfood_replay_review",
        "status": "pass",
        "reviewed_case_count": 1,
        "runtime_connected": True,
        "lab_isolated": True,
        "reviewed_case_proposals": [
            {
                "case_id": "dogfood_rt-lab-dogfood-001",
                "case_type": "explicit_preference",
                "split": "holdout",
                "expected_candidate": {
                    "candidate_type": "preference",
                    "human_review_required": True,
                },
                "trace_fields": {"source_refs": ["message:rt-lab-dogfood-001"]},
                "review": {"expected_outcome": "candidate"},
            }
        ],
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
    }


def _chain_payload() -> dict[str, object]:
    return {
        "memory_summary_projection": _memory_projection(),
        "recommendation_payload": _recommendation_payload(),
        "derived_memory_views": _derived_views(),
        "current_budget_view": {
            "base_budget_kcal": 1800,
            "effective_budget_kcal": 1800,
            "meal_consumption_total_kcal": 2100,
        },
        "active_body_plan_view": {
            "safety_floor_kcal": 1200,
            "target_days": [
                {
                    "local_date": "2026-05-10",
                    "base_budget_kcal": 1800,
                    "calibration_adjustment_total_kcal": 0,
                },
                {
                    "local_date": "2026-05-11",
                    "base_budget_kcal": 1800,
                    "calibration_adjustment_total_kcal": 0,
                },
            ],
        },
        "open_proposals_view": {"open_rescue_proposal_count": 0},
        "proposal_candidate_output": {
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
        },
        "user_control_models": {
            "recommendation_prompt": _controls("new_app_open_with_qualified_pool"),
            "rescue_nudge": _controls("material_budget_change_or_user_reopens_rescue"),
        },
        "interaction_plan": [
            {"action": "dismiss", "dismiss_reason": "too_frequent"},
            {"action": "snooze", "snooze_minutes": 120},
        ],
    }


def _chain_without_stages() -> dict[str, object]:
    return {
        "artifact_type": "advanced_shadow_e2e_fixture_chain_artifact",
        "status": "pass",
        "stage_trace": [
            {
                "artifact_type": "recommendation_shadow_summary_consumer_quality_report",
                "status": "pass",
            }
        ],
        "terminal_review_sink": {"status": "pass", "record_count": 0},
        "blockers": [],
        "recommendation_served": False,
        "proactive_sent": False,
        "mutation_changed": False,
        "user_facing_behavior_changed": False,
    }


def _memory_projection() -> dict[str, object]:
    return {
        "artifact_type": "runtime_lab_memory_consumer_summary_projection",
        "status": "pass",
        "preference_profile_summary": {
            "freshness_posture": "fresh",
            "accepted_shadow_candidate_ids": ["pref-1"],
            "negative_preference_blockers": ["neg-1"],
        },
        "golden_order_summary": {
            "orders": [{"candidate_id": "golden-1", "store_name": "FamilyMart"}]
        },
        "suppression_summary": {"suppression_blockers": []},
        "runtime_effect_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "recommendation_served": False,
        "proactive_sent": False,
        "rescue_proposal_committed": False,
    }


def _derived_views() -> dict[str, object]:
    return {
        "rescue_history_summary": {
            "is_durable_memory_truth": False,
            "rescue_event_count": 1,
        },
        "adherence_summary": {
            "is_durable_memory_truth": False,
            "adherence_posture": "mixed",
        },
    }


def _recommendation_payload() -> dict[str, object]:
    payload = build_fixture_recommendation_three_node_input()
    golden = _candidate(payload, "golden-1")
    golden.update(
        {
                "candidate_id": "golden-1",
                "title": "Chicken salad",
                "store_name": "FamilyMart",
                "estimated_kcal": 520,
                "evidence_posture": "exact",
                "availability_posture": "available",
                "realistic_executable": True,
                "user_accessible": True,
                "source_refs": ["memory_candidate:pref-1", "memory_candidate:golden-1"],
                "recommendation_served": False,
                "intake_handoff_created": False,
        }
    )
    return payload


def _candidate(payload: dict[str, object], candidate_id: str) -> dict[str, object]:
    for item in payload["candidate_source_fixture"]:  # type: ignore[index]
        if isinstance(item, dict) and item.get("candidate_id") == candidate_id:
            return item
    raise AssertionError(f"candidate not found: {candidate_id}")


def _controls(next_signal: str) -> dict[str, object]:
    return {
        "dismiss_reason_choices": [
            "not_relevant_now",
            "already_handled",
            "too_frequent",
        ],
        "snooze_window": {"kind": "duration", "minutes": 180},
        "undo_scope": "current_no_send_candidate_only",
        "next_signal_required": next_signal,
    }
