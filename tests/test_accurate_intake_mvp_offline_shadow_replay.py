from __future__ import annotations

import json
from pathlib import Path

from scripts.build_accurate_intake_mvp_offline_shadow_replay import (
    build_accurate_intake_offline_shadow_replay,
    write_accurate_intake_offline_shadow_replay,
)


def _stage_manifest(
    *,
    profile_id: str = "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
    model: str = "grok-4-fast",
    result_kinds: list[str] | None = None,
    statuses: list[str] | None = None,
    failure_family: str | None = None,
    include_full_suite: bool = False,
    overclaim: bool = False,
) -> dict[str, object]:
    stage_ids = [
        "provider_health_smoke",
        "schema_contract_probe",
        "fake_provider_active_runtime_gate",
        "single_case_live_probe",
        "single_case_live_probe",
    ]
    if include_full_suite:
        stage_ids.append("full_suite_live_diagnostic")
    kinds = result_kinds or ["strict_pass_first_attempt"] * len(stage_ids)
    case_ids = [
        [],
        [],
        [],
        ["explicit_item_removal_seeded"],
        ["chinese_chicken_rice_correction_removal_debug"],
    ]
    if include_full_suite:
        case_ids.append([])
    stage_statuses = statuses or ["pass"] * len(stage_ids)
    stages = [
        {
            "stage_id": stage_id,
            "artifact_path": f"artifacts/run-{index}.json",
            "status": stage_statuses[index],
            "provider_profile_id": profile_id,
            "model": model,
            "transport_mode": "synthetic_tool_transport",
            "attempt_count": 1,
            "latency_ms": 100 + index,
            "timeout_budget_ms": 180000,
            "failure_layer": "provider_runtime_error" if stage_statuses[index] == "timeout" else None,
            "failure_family": failure_family if stage_statuses[index] != "pass" else None,
            "retry_policy_applied": kinds[index] == "pass_after_retry",
            "result_kind": kinds[index],
            "case_ids": case_ids[index],
        }
        for index, stage_id in enumerate(stage_ids)
    ]
    return {
        "artifact_type": "accurate_intake_mvp_live_stage_manifest",
        "claim_scope": "live_diagnostic_stage_manifest",
        "readiness_claimed": overclaim,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "production_selected": False,
        "mutation_rollout_approved": False,
        "runtime_web_activation_approved": False,
        "input_integrity": {"passed": True, "blockers": []},
        "stages": stages,
        "stage_summary": {
            "result_kind_counts": {kind: kinds.count(kind) for kind in sorted(set(kinds))},
            "failure_family_counts": {failure_family: 1} if failure_family else {},
        },
    }


def test_offline_shadow_replay_records_single_clean_stage_run_without_candidate_claim() -> None:
    replay = build_accurate_intake_offline_shadow_replay([_stage_manifest()])

    assert replay["artifact_type"] == "accurate_intake_mvp_offline_shadow_replay"
    assert replay["claim_scope"] == "offline_shadow_replay"
    assert replay["readiness_claimed"] is False
    assert replay["product_readiness_claimed"] is False
    assert replay["private_self_use_approved"] is False
    assert replay["production_selected"] is False
    assert replay["summary"]["sample_run_count"] == 1
    assert replay["summary"]["strict_pass_first_attempt_count"] == 5
    assert replay["summary"]["pass_after_retry_count"] == 0
    assert replay["summary"]["timeout_count"] == 0
    assert replay["summary"]["strict_replay_ready"] is False
    assert replay["summary"]["eligible_for_private_self_use_candidate"] is False
    assert replay["summary"]["full_suite_run_count"] == 0
    assert replay["summary"]["full_suite_replay_ready"] is False
    assert replay["summary"]["model_diversity_missing"] is True
    assert replay["summary"]["max_model_claim"] == "single_profile_live_diagnostic_observed"


def test_offline_shadow_replay_marks_three_same_profile_runs_as_single_profile_only() -> None:
    replay = build_accurate_intake_offline_shadow_replay(
        [_stage_manifest(), _stage_manifest(), _stage_manifest()]
    )

    assert replay["summary"]["sample_run_count"] == 3
    assert replay["summary"]["strict_replay_ready"] is True
    assert replay["summary"]["full_suite_replay_ready"] is False
    assert replay["summary"]["single_profile_stability"] is True
    assert replay["summary"]["model_diversity_missing"] is True
    assert replay["summary"]["model_diversity_status"] == "model_diversity_missing"
    assert replay["summary"]["eligible_for_private_self_use_candidate"] is False


def test_offline_shadow_replay_excludes_retry_and_timeout_from_strict_replay() -> None:
    replay = build_accurate_intake_offline_shadow_replay(
        [
            _stage_manifest(),
            _stage_manifest(result_kinds=["strict_pass_first_attempt", "pass_after_retry", "strict_pass_first_attempt", "strict_pass_first_attempt", "strict_pass_first_attempt"]),
            _stage_manifest(
                result_kinds=[
                    "strict_pass_first_attempt",
                    "strict_pass_first_attempt",
                    "strict_pass_first_attempt",
                    "strict_pass_first_attempt",
                    "timeout_after_retry",
                ],
                statuses=["pass", "pass", "pass", "pass", "timeout"],
                failure_family="environment_or_provider_blocker",
            ),
        ]
    )

    assert replay["summary"]["pass_after_retry_count"] == 1
    assert replay["summary"]["timeout_count"] == 1
    assert replay["summary"]["failure_family_counts"] == {"environment_or_provider_blocker": 1}
    assert replay["summary"]["strict_replay_ready"] is False
    assert replay["summary"]["eligible_for_private_self_use_candidate"] is False


def test_offline_shadow_replay_tracks_full_suite_window_separately_from_stage_replay() -> None:
    replay = build_accurate_intake_offline_shadow_replay(
        [
            _stage_manifest(include_full_suite=True),
            _stage_manifest(include_full_suite=True),
            _stage_manifest(include_full_suite=True),
        ]
    )

    assert replay["summary"]["strict_replay_ready"] is True
    assert replay["summary"]["full_suite_run_count"] == 3
    assert replay["summary"]["full_suite_strict_first_attempt_count"] == 3
    assert replay["summary"]["full_suite_pass_after_retry_count"] == 0
    assert replay["summary"]["full_suite_timeout_count"] == 0
    assert replay["summary"]["full_suite_replay_ready"] is True
    assert replay["summary"]["eligible_for_private_self_use_candidate"] is False


def test_offline_shadow_replay_rejects_retry_dependent_full_suite_window() -> None:
    replay = build_accurate_intake_offline_shadow_replay(
        [
            _stage_manifest(include_full_suite=True),
            _stage_manifest(
                include_full_suite=True,
                result_kinds=[
                    "strict_pass_first_attempt",
                    "strict_pass_first_attempt",
                    "strict_pass_first_attempt",
                    "strict_pass_first_attempt",
                    "strict_pass_first_attempt",
                    "pass_after_retry",
                ],
            ),
            _stage_manifest(include_full_suite=True),
        ]
    )

    assert replay["summary"]["full_suite_run_count"] == 3
    assert replay["summary"]["full_suite_pass_after_retry_count"] == 1
    assert replay["summary"]["full_suite_replay_ready"] is False
    assert replay["summary"]["eligible_for_private_self_use_candidate"] is False


def test_offline_shadow_replay_fails_integrity_on_stage_manifest_overclaim() -> None:
    replay = build_accurate_intake_offline_shadow_replay([_stage_manifest(overclaim=True)])

    assert replay["input_integrity"]["passed"] is False
    assert "run_1_readiness_claimed" in replay["input_integrity"]["blockers"]
    assert replay["summary"]["strict_replay_ready"] is False


def test_offline_shadow_replay_writer_creates_artifact(tmp_path: Path) -> None:
    source = tmp_path / "manifest.json"
    source.write_text(json.dumps(_stage_manifest(), ensure_ascii=False), encoding="utf-8")

    output = write_accurate_intake_offline_shadow_replay(
        stage_manifest_paths=[source],
        output_dir=tmp_path,
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert output.name == "accurate_intake_mvp_offline_shadow_replay.json"
    assert payload["artifact_type"] == "accurate_intake_mvp_offline_shadow_replay"
    assert payload["summary"]["sample_run_count"] == 1
