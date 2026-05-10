from __future__ import annotations

import json
from pathlib import Path

from app.advanced_shadow_lab.model_profiles import (
    ADVANCED_LAB_TARGET_REASONING_PROFILE_ID,
)
from app.advanced_shadow_lab.live_bundle_inputs import write_live_bundle_inputs


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
    assert terminal["live_diagnostic_signals"]["proactive_copy_live_diagnostic"] == {
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
        "advanced_shadow_proactive_copy_live_diagnostic.json": (
            "advanced_shadow_proactive_copy_live_diagnostic_artifact"
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
    assert fixture_chain["chat_ux_packet"]["copy_alignment_summary"] == {
        "status": "pass",
        "aligned_count": 2,
        "not_applicable_count": 1,
        "blocked_count": 0,
        "not_run_count": 0,
    }
    assert [item["copy_status"] for item in fixture_chain["chat_ux_packet"]["chat_packets"]] == [
        "copy_diagnostic_aligned",
        "copy_diagnostic_aligned",
    ]
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
    assert terminal["live_diagnostic_signals"]["proactive_copy_live_diagnostic"] == {
        "live_invoked": False,
        "live_provider_used": False,
        "provider_mode": "not_run",
        "output_guard_status": "not_run",
    }
    rows = {row["surface"]: row for row in terminal["surface_status_rows"]}
    assert rows["recommendation_prompt_reason_copy"]["finding"] == "live_diagnostic_not_run"
    assert rows["rescue_proposal_copy_posture"]["finding"] == "live_diagnostic_not_run"
    assert rows["proactive_chat_copy_posture"]["finding"] == "live_diagnostic_not_run"
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
    result = write_live_bundle_inputs(tmp_path / "inputs")
    return {
        "memory_review": result["memory_review_path"],
        "chain_payload": result["chain_payload_path"],
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
