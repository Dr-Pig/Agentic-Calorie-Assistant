from __future__ import annotations

import json
from pathlib import Path

from scripts.build_accurate_intake_mvp_live_decision_pack import (
    DECISION_OPTION_IDS,
    build_accurate_intake_live_decision_pack,
    write_accurate_intake_live_decision_pack,
)


_REMOVED_FIXED_FALSE_FIELDS = (
    "readiness_claimed",
    "product_readiness_claimed",
    "private_self_use_approved",
    "production_selected",
    "model_portability_claimed",
    "mutation_rollout_approved",
    "runtime_web_activation_approved",
    "shadow_or_canary_approved",
)


def _assert_removed_fixed_false_fields(pack: dict[str, object]) -> None:
    for field in _REMOVED_FIXED_FALSE_FIELDS:
        assert field not in pack


def _artifact(
    *,
    live_invoked: bool = True,
    strict_pass_count: int = 5,
    repaired_pass_count: int = 0,
    contract_fail_count: int = 0,
    timeout_count: int = 0,
    failure_layers: list[str] | None = None,
    failure_family: str | None = None,
    stages: list[dict[str, object]] | None = None,
    cases: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    case_count = strict_pass_count + repaired_pass_count + contract_fail_count + timeout_count
    return {
        "artifact_type": "accurate_intake_mvp_live_diagnostic",
        "claim_scope": "live_diagnostic",
        "readiness_claimed": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "production_selected": False,
        "mutation_rollout_approved": False,
        "runtime_web_activation_approved": False,
        "live_provider_used_as_truth": False,
        "live_invoked": live_invoked,
        "failure_layer": failure_layers[0] if failure_layers else None,
        "failure_family": failure_family,
        "summary": {
            "case_count": case_count,
            "strict_pass_count": strict_pass_count,
            "repaired_pass_count": repaired_pass_count,
            "contract_fail_count": contract_fail_count,
            "timeout_count": timeout_count,
            "provider_timeout_count": timeout_count,
            "failure_layers": failure_layers if failure_layers is not None else [],
            "failure_families": [failure_family] if failure_family else [],
        },
        "stages": stages if stages is not None else [
            {"stage_id": "provider_health_smoke", "status": "pass"},
            {"stage_id": "schema_contract_probe", "status": "pass"},
            {"stage_id": "fake_provider_active_runtime_gate", "status": "pass"},
            {"stage_id": "single_case_live_probe", "status": "pass"},
            {"stage_id": "full_suite_live_diagnostic", "status": "pass"},
        ],
        "cases": cases
        if cases is not None
        else [{"case_id": f"case-{index}", "case_contract_status": "strict_pass"} for index in range(case_count)],
    }


def _clean_required_stage_manifest(*, include_full_suite: bool = False) -> dict[str, object]:
    stages: list[dict[str, object]] = [
        {
            "stage_id": "provider_health_smoke",
            "status": "pass",
            "result_kind": "strict_pass_first_attempt",
            "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
            "model": "grok-4-fast",
        },
        {
            "stage_id": "schema_contract_probe",
            "status": "pass",
            "result_kind": "strict_pass_first_attempt",
            "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
            "model": "grok-4-fast",
        },
        {
            "stage_id": "fake_provider_active_runtime_gate",
            "status": "pass",
            "result_kind": "strict_pass_first_attempt",
            "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
            "model": "grok-4-fast",
        },
        {
            "stage_id": "single_case_live_probe",
            "status": "pass",
            "result_kind": "strict_pass_first_attempt",
            "case_ids": ["no_plan_consumed_without_budget_target"],
            "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
            "model": "grok-4-fast",
        },
        {
            "stage_id": "single_case_live_probe",
            "status": "pass",
            "result_kind": "strict_pass_first_attempt",
            "case_ids": ["generic_common_food_range"],
            "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
            "model": "grok-4-fast",
        },
                {
                    "stage_id": "single_case_live_probe",
                    "status": "pass",
                    "result_kind": "strict_pass_first_attempt",
                    "case_ids": ["no_plan_consumed_without_budget_target"],
                    "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
                    "model": "grok-4-fast",
                },
                {
                    "stage_id": "single_case_live_probe",
                    "status": "pass",
                    "result_kind": "strict_pass_first_attempt",
                    "case_ids": ["generic_common_food_range"],
                    "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
                    "model": "grok-4-fast",
                },
                {
                    "stage_id": "single_case_live_probe",
                    "status": "pass",
                    "result_kind": "strict_pass_first_attempt",
                    "case_ids": ["explicit_item_removal_seeded"],
                    "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
                    "model": "grok-4-fast",
        },
        {
            "stage_id": "single_case_live_probe",
            "status": "pass",
            "result_kind": "strict_pass_first_attempt",
            "case_ids": ["exact_item_official_label"],
            "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
            "model": "grok-4-fast",
        },
        {
            "stage_id": "single_case_live_probe",
            "status": "pass",
            "result_kind": "strict_pass_first_attempt",
            "case_ids": ["bubble_milk_tea_refinement"],
            "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
            "model": "grok-4-fast",
        },
        {
            "stage_id": "single_case_live_probe",
            "status": "pass",
            "result_kind": "strict_pass_first_attempt",
            "case_ids": ["luwei_bare_to_listed_basket"],
            "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
            "model": "grok-4-fast",
        },
        {
            "stage_id": "single_case_live_probe",
            "status": "pass",
            "result_kind": "strict_pass_first_attempt",
            "case_ids": ["chinese_chicken_rice_correction_removal_debug"],
            "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
            "model": "grok-4-fast",
        },
    ]
    if include_full_suite:
        stages.append(
            {
                "stage_id": "full_suite_live_diagnostic",
                "status": "pass",
                "result_kind": "strict_pass_first_attempt",
                "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
                "model": "grok-4-fast",
            }
        )
    return {
        "artifact_type": "accurate_intake_mvp_live_stage_manifest",
        "input_integrity": {"passed": True, "blockers": []},
        "stages": stages,
    }


def _strict_replay(
    *,
    model_diversity_status: str = "model_diversity_missing",
    sample_run_count: int = 1,
) -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_mvp_offline_shadow_replay",
        "input_integrity": {"passed": True, "blockers": []},
        "summary": {
            "sample_run_count": sample_run_count,
            "strict_replay_ready": True,
            "full_suite_replay_ready": False,
            "full_suite_run_count": 0,
            "repaired_pass_count": 0,
            "timeout_count": 0,
            "model_diversity_status": model_diversity_status,
        },
    }


def test_accurate_intake_live_decision_pack_routes_environment_blocker_to_stay_diagnostic() -> None:
    pack = build_accurate_intake_live_decision_pack(
        _artifact(
            live_invoked=False,
            strict_pass_count=0,
            contract_fail_count=0,
            timeout_count=0,
            failure_layers=["provider_runtime_error"],
            failure_family="environment_or_provider_blocker",
            stages=[],
            cases=[],
        )
    )

    assert pack["artifact_type"] == "accurate_intake_mvp_live_decision_pack"
    assert pack["decision_options_ordered"] == list(DECISION_OPTION_IDS)
    assert pack["selected_option"] == "provider_health_blocked"
    assert pack["selection_reason"] == "environment_or_provider_blocker"
    _assert_removed_fixed_false_fields(pack)


def test_accurate_intake_live_decision_pack_blocks_on_failed_provider_health_stage() -> None:
    pack = build_accurate_intake_live_decision_pack(
        _artifact(
            live_invoked=True,
            strict_pass_count=0,
            failure_family="environment_or_provider_blocker",
            stages=[
                {
                    "stage_id": "provider_health_smoke",
                    "status": "timeout",
                    "failure_layer": "provider_runtime_error",
                    "failure_family": "environment_or_provider_blocker",
                }
            ],
            cases=[],
        )
    )

    assert pack["selected_option"] == "provider_health_blocked"
    assert pack["selection_reason"] == "environment_or_provider_blocker"
    assert pack["private_self_use_candidate_prepared"] is False


def test_accurate_intake_live_decision_pack_blocks_on_schema_contract_stage() -> None:
    pack = build_accurate_intake_live_decision_pack(
        _artifact(
            live_invoked=True,
            strict_pass_count=0,
            failure_family="schema_contract_blocked",
            stages=[
                {"stage_id": "provider_health_smoke", "status": "pass"},
                {
                    "stage_id": "schema_contract_probe",
                    "status": "fail",
                    "failure_layer": "provider_contract_non_adherence",
                    "failure_family": "schema_contract_blocked",
                },
            ],
            cases=[],
        )
    )

    assert pack["selected_option"] == "schema_contract_blocked"
    assert pack["selection_reason"] == "schema_contract_blocked"
    _assert_removed_fixed_false_fields(pack)


def test_accurate_intake_live_decision_pack_requires_single_case_before_full_suite() -> None:
    pack = build_accurate_intake_live_decision_pack(
        _artifact(
            strict_pass_count=5,
            stages=[
                {"stage_id": "provider_health_smoke", "status": "pass"},
                {"stage_id": "schema_contract_probe", "status": "pass"},
                {"stage_id": "fake_provider_active_runtime_gate", "status": "pass"},
                {"stage_id": "full_suite_live_diagnostic", "status": "pass"},
            ],
        )
    )

    assert pack["selected_option"] == "single_case_probe_required"
    assert pack["selection_reason"] == "single_case_probe_missing"


def test_accurate_intake_live_decision_pack_prefers_valid_stage_manifest() -> None:
    live_artifact = _artifact(strict_pass_count=5, repaired_pass_count=0)
    stage_manifest = {
        "artifact_type": "accurate_intake_mvp_live_stage_manifest",
        "input_integrity": {"passed": True, "blockers": []},
        "stages": [
            {"stage_id": "provider_health_smoke", "status": "pass"},
            {"stage_id": "schema_contract_probe", "status": "pass"},
            {"stage_id": "fake_provider_active_runtime_gate", "status": "pass"},
            {
                "stage_id": "single_case_live_probe",
                "status": "fail",
                "failure_layer": "provider_contract_non_adherence",
                "failure_family": "synthetic_decision_tool_call_missing",
            },
        ],
    }

    pack = build_accurate_intake_live_decision_pack(live_artifact, stage_manifest_artifact=stage_manifest)

    assert pack["selected_option"] == "stay_diagnostic"
    assert pack["selection_reason"] == "live_diagnostic_contract_failures"
    assert pack["stage_summary"]["source"] == "stage_manifest"
    assert pack["stage_summary"]["single_case_probe_status"] == "fail"
    assert pack["private_self_use_candidate_prepared"] is False


def test_accurate_intake_live_decision_pack_blocks_invalid_stage_manifest() -> None:
    pack = build_accurate_intake_live_decision_pack(
        _artifact(strict_pass_count=5, repaired_pass_count=0),
        stage_manifest_artifact={
            "artifact_type": "accurate_intake_mvp_live_stage_manifest",
            "input_integrity": {"passed": False, "blockers": ["source_0_readiness_claimed"]},
            "stages": [{"stage_id": "provider_health_smoke", "status": "pass"}],
        },
    )

    assert pack["selected_option"] == "stay_diagnostic"
    assert pack["selection_reason"] == "stage_manifest_integrity_blocked"
    assert pack["input_integrity"]["passed"] is False
    assert "stage_manifest_source_0_readiness_claimed" in pack["input_integrity"]["blockers"]


def test_accurate_intake_live_decision_pack_repeats_on_retry_dependent_manifest() -> None:
    live_artifact = _artifact(strict_pass_count=5, repaired_pass_count=0)
    stage_manifest = {
        "artifact_type": "accurate_intake_mvp_live_stage_manifest",
        "input_integrity": {"passed": True, "blockers": []},
        "stages": [
            {"stage_id": "provider_health_smoke", "status": "pass", "result_kind": "strict_pass_first_attempt"},
            {"stage_id": "schema_contract_probe", "status": "pass", "result_kind": "strict_pass_first_attempt"},
            {
                "stage_id": "single_case_live_probe",
                "status": "pass",
                "result_kind": "pass_after_retry",
                "retry_policy_applied": True,
            },
        ],
    }

    pack = build_accurate_intake_live_decision_pack(live_artifact, stage_manifest_artifact=stage_manifest)

    assert pack["selected_option"] == "repeat_single_profile_diagnostic"
    assert pack["selection_reason"] == "retry_dependent_evidence"
    assert pack["stage_summary"]["has_retry_dependent_stage"] is True
    assert pack["private_self_use_candidate_prepared"] is False


def test_accurate_intake_live_decision_pack_uses_clean_stage_manifest_over_stale_live_artifact() -> None:
    stale_live_artifact = _artifact(
        live_invoked=True,
        strict_pass_count=1,
        timeout_count=3,
        failure_layers=["provider_runtime_error"],
        failure_family="environment_or_provider_blocker",
    )
    stage_manifest = {
        "artifact_type": "accurate_intake_mvp_live_stage_manifest",
        "input_integrity": {"passed": True, "blockers": []},
        "stages": [
            {
                "stage_id": "provider_health_smoke",
                "status": "pass",
                "result_kind": "strict_pass_first_attempt",
                "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
                "model": "grok-4-fast",
            },
            {
                "stage_id": "schema_contract_probe",
                "status": "pass",
                "result_kind": "strict_pass_first_attempt",
                "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
                "model": "grok-4-fast",
            },
            {
                "stage_id": "fake_provider_active_runtime_gate",
                "status": "pass",
                "result_kind": "strict_pass_first_attempt",
                "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
                "model": "grok-4-fast",
            },
            {
                "stage_id": "single_case_live_probe",
                "status": "pass",
                "result_kind": "strict_pass_first_attempt",
                "case_ids": ["no_plan_consumed_without_budget_target"],
                "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
                "model": "grok-4-fast",
            },
            {
                "stage_id": "single_case_live_probe",
                "status": "pass",
                "result_kind": "strict_pass_first_attempt",
                "case_ids": ["generic_common_food_range"],
                "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
                "model": "grok-4-fast",
            },
            {
                "stage_id": "single_case_live_probe",
                "status": "pass",
                "result_kind": "strict_pass_first_attempt",
                "case_ids": ["explicit_item_removal_seeded"],
                "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
                "model": "grok-4-fast",
            },
            {
                "stage_id": "single_case_live_probe",
                "status": "pass",
                "result_kind": "strict_pass_first_attempt",
                "case_ids": ["exact_item_official_label"],
                "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
                "model": "grok-4-fast",
            },
            {
                "stage_id": "single_case_live_probe",
                "status": "pass",
                "result_kind": "strict_pass_first_attempt",
                "case_ids": ["bubble_milk_tea_refinement"],
                "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
                "model": "grok-4-fast",
            },
            {
                "stage_id": "single_case_live_probe",
                "status": "pass",
                "result_kind": "strict_pass_first_attempt",
                "case_ids": ["luwei_bare_to_listed_basket"],
                "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
                "model": "grok-4-fast",
            },
            {
                "stage_id": "single_case_live_probe",
                "status": "pass",
                "result_kind": "strict_pass_first_attempt",
                "case_ids": ["chinese_chicken_rice_correction_removal_debug"],
                "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
                "model": "grok-4-fast",
            },
        ],
    }

    pack = build_accurate_intake_live_decision_pack(stale_live_artifact, stage_manifest_artifact=stage_manifest)

    assert pack["selected_option"] == "offline_shadow_replay"
    assert pack["selection_reason"] == "clean_stage_manifest_requires_replay_before_private_self_use_candidate"
    assert pack["stage_summary"]["source"] == "stage_manifest"
    assert pack["stage_summary"]["result_kind_counts"] == {"strict_pass_first_attempt": 10}
    assert pack["private_self_use_candidate_prepared"] is False


def test_accurate_intake_live_decision_pack_advances_strict_replay_to_full_suite_gate() -> None:
    pack = build_accurate_intake_live_decision_pack(
        _artifact(strict_pass_count=1),
        stage_manifest_artifact=_clean_required_stage_manifest(),
        offline_replay_artifact=_strict_replay(),
    )

    assert pack["selected_option"] == "full_suite_blocked"
    assert pack["selection_reason"] == "full_suite_diagnostic_required"
    assert pack["offline_replay_summary"]["strict_replay_ready"] is True
    assert pack["offline_replay_summary"]["sample_run_count"] == 1
    assert pack["offline_replay_summary"]["model_diversity_status"] == "model_diversity_missing"
    assert pack["private_self_use_candidate_prepared"] is False
    _assert_removed_fixed_false_fields(pack)


def test_accurate_intake_live_decision_pack_blocks_after_full_suite_when_model_diversity_missing() -> None:
    pack = build_accurate_intake_live_decision_pack(
        _artifact(strict_pass_count=5),
        stage_manifest_artifact=_clean_required_stage_manifest(include_full_suite=True),
        offline_replay_artifact=_strict_replay(model_diversity_status="model_diversity_missing"),
    )

    assert pack["selected_option"] == "offline_shadow_replay"
    assert pack["selection_reason"] == "model_diversity_missing"
    assert pack["stage_summary"]["full_suite_status"] == "pass"
    assert pack["private_self_use_candidate_prepared"] is False
    _assert_removed_fixed_false_fields(pack)


def test_accurate_intake_live_decision_pack_blocks_missing_required_stage_manifest() -> None:
    live_artifact = _artifact(strict_pass_count=5, repaired_pass_count=0)
    stage_manifest = {
        "artifact_type": "accurate_intake_mvp_live_stage_manifest",
        "input_integrity": {"passed": True, "blockers": []},
        "stage_summary": {
            "has_missing_required_stage": True,
            "missing_required_stage_ids": ["fake_provider_active_runtime_gate"],
            "missing_required_single_case_ids": [],
        },
        "stages": [
            {"stage_id": "provider_health_smoke", "status": "pass", "result_kind": "strict_pass_first_attempt"},
            {"stage_id": "schema_contract_probe", "status": "pass", "result_kind": "strict_pass_first_attempt"},
            {"stage_id": "single_case_live_probe", "status": "pass", "result_kind": "strict_pass_first_attempt"},
        ],
    }

    pack = build_accurate_intake_live_decision_pack(live_artifact, stage_manifest_artifact=stage_manifest)

    assert pack["selected_option"] == "stay_diagnostic"
    assert pack["selection_reason"] == "stage_evidence_missing"
    assert pack["stage_summary"]["has_missing_required_stage"] is True
    assert pack["private_self_use_candidate_prepared"] is False


def test_accurate_intake_live_decision_pack_blocks_missing_required_single_case() -> None:
    live_artifact = _artifact(strict_pass_count=5, repaired_pass_count=0)
    stage_manifest = {
        "artifact_type": "accurate_intake_mvp_live_stage_manifest",
        "input_integrity": {"passed": True, "blockers": []},
        "stage_summary": {
            "has_missing_required_stage": True,
            "missing_required_stage_ids": [],
            "missing_required_single_case_ids": ["chinese_chicken_rice_correction_removal_debug"],
        },
        "stages": [
            {"stage_id": "provider_health_smoke", "status": "pass", "result_kind": "strict_pass_first_attempt"},
            {"stage_id": "schema_contract_probe", "status": "pass", "result_kind": "strict_pass_first_attempt"},
            {"stage_id": "fake_provider_active_runtime_gate", "status": "pass", "result_kind": "strict_pass_first_attempt"},
            {
                "stage_id": "single_case_live_probe",
                "status": "pass",
                "result_kind": "strict_pass_first_attempt",
                "case_ids": ["no_plan_consumed_without_budget_target"],
            },
            {
                "stage_id": "single_case_live_probe",
                "status": "pass",
                "result_kind": "strict_pass_first_attempt",
                "case_ids": ["generic_common_food_range"],
            },
            {
                "stage_id": "single_case_live_probe",
                "status": "pass",
                "result_kind": "strict_pass_first_attempt",
                "case_ids": ["explicit_item_removal_seeded"],
            },
            {
                "stage_id": "single_case_live_probe",
                "status": "pass",
                "result_kind": "strict_pass_first_attempt",
                "case_ids": ["exact_item_official_label"],
            },
            {
                "stage_id": "single_case_live_probe",
                "status": "pass",
                "result_kind": "strict_pass_first_attempt",
                "case_ids": ["bubble_milk_tea_refinement"],
            },
            {
                "stage_id": "single_case_live_probe",
                "status": "pass",
                "result_kind": "strict_pass_first_attempt",
                "case_ids": ["luwei_bare_to_listed_basket"],
            },
        ],
    }

    pack = build_accurate_intake_live_decision_pack(live_artifact, stage_manifest_artifact=stage_manifest)

    assert pack["selected_option"] == "single_case_probe_required"
    assert pack["selection_reason"] == "single_case_probe_missing"
    assert pack["stage_summary"]["missing_required_single_case_ids"] == ["chinese_chicken_rice_correction_removal_debug"]
    assert pack["private_self_use_candidate_prepared"] is False


def test_accurate_intake_live_decision_pack_blocks_full_suite_when_offline_replay_gate_fails() -> None:
    live_artifact = _artifact(strict_pass_count=5, repaired_pass_count=0)
    stage_manifest = {
        "artifact_type": "accurate_intake_mvp_live_stage_manifest",
        "input_integrity": {"passed": True, "blockers": []},
        "stages": [
            {"stage_id": "provider_health_smoke", "status": "pass", "result_kind": "strict_pass_first_attempt"},
            {"stage_id": "schema_contract_probe", "status": "pass", "result_kind": "strict_pass_first_attempt"},
            {"stage_id": "fake_provider_active_runtime_gate", "status": "pass", "result_kind": "strict_pass_first_attempt"},
            {
                "stage_id": "single_case_live_probe",
                "status": "pass",
                "result_kind": "strict_pass_first_attempt",
                "case_ids": ["no_plan_consumed_without_budget_target"],
            },
            {
                "stage_id": "single_case_live_probe",
                "status": "pass",
                "result_kind": "strict_pass_first_attempt",
                "case_ids": ["generic_common_food_range"],
            },
            {
                "stage_id": "single_case_live_probe",
                "status": "pass",
                "result_kind": "strict_pass_first_attempt",
                "case_ids": ["explicit_item_removal_seeded"],
            },
            {
                "stage_id": "single_case_live_probe",
                "status": "pass",
                "result_kind": "strict_pass_first_attempt",
                "case_ids": ["exact_item_official_label"],
            },
            {
                "stage_id": "single_case_live_probe",
                "status": "pass",
                "result_kind": "strict_pass_first_attempt",
                "case_ids": ["bubble_milk_tea_refinement"],
            },
            {
                "stage_id": "single_case_live_probe",
                "status": "pass",
                "result_kind": "strict_pass_first_attempt",
                "case_ids": ["luwei_bare_to_listed_basket"],
            },
            {
                "stage_id": "single_case_live_probe",
                "status": "pass",
                "result_kind": "strict_pass_first_attempt",
                "case_ids": ["chinese_chicken_rice_correction_removal_debug"],
            },
            {
                "stage_id": "full_suite_live_diagnostic",
                "status": "blocked",
                "result_kind": "blocked",
                "failure_layer": "diagnostic_ordering",
                "failure_family": "offline_replay_required",
            },
        ],
    }

    pack = build_accurate_intake_live_decision_pack(live_artifact, stage_manifest_artifact=stage_manifest)

    assert pack["selected_option"] == "full_suite_blocked"
    assert pack["selection_reason"] == "offline_replay_required"
    assert pack["private_self_use_candidate_prepared"] is False


def test_accurate_intake_live_decision_pack_stays_diagnostic_on_product_loop_contract_failure() -> None:
    pack = build_accurate_intake_live_decision_pack(
        _artifact(
            strict_pass_count=0,
            contract_fail_count=1,
            failure_layers=["provider_contract_non_adherence"],
            failure_family="provider_contract_non_adherence",
            stages=[
                {
                    "stage_id": "single_case_live_probe",
                    "status": "fail",
                    "failure_layer": "provider_contract_non_adherence",
                    "failure_family": "provider_contract_non_adherence",
                }
            ],
            cases=[
                {
                    "case_id": "chinese_chicken_rice_correction_removal_debug",
                    "case_contract_status": "fail",
                    "failure_layer": "provider_contract_non_adherence",
                    "failure_family": "provider_contract_non_adherence",
                }
            ],
        )
    )

    assert pack["selected_option"] == "stay_diagnostic"
    assert pack["selection_reason"] == "live_diagnostic_contract_failures"
    assert pack["private_self_use_candidate_prepared"] is False


def test_accurate_intake_live_decision_pack_blocks_private_candidate_for_repaired_pass() -> None:
    pack = build_accurate_intake_live_decision_pack(
        _artifact(
            strict_pass_count=4,
            repaired_pass_count=1,
            cases=[
                {"case_id": "bubble_milk_tea_refinement", "case_contract_status": "strict_pass"},
                {
                    "case_id": "chinese_chicken_rice_correction_removal_debug",
                    "case_contract_status": "repaired_pass",
                    "repair_failure_family": "commit_without_evidence",
                    "failed_invariant": "commit_requires_evidence",
                },
            ],
        )
    )

    assert pack["selected_option"] == "repeat_single_profile_diagnostic"
    assert pack["selection_reason"] == "live_clean_but_repair_dependent"
    assert pack["evidence_summary"]["repaired_case_ids"] == ["chinese_chicken_rice_correction_removal_debug"]
    _assert_removed_fixed_false_fields(pack)


def test_accurate_intake_live_decision_pack_routes_single_strict_run_to_offline_replay() -> None:
    pack = build_accurate_intake_live_decision_pack(_artifact(strict_pass_count=5, repaired_pass_count=0))

    assert pack["selected_option"] == "offline_shadow_replay"
    assert pack["selection_reason"] == "single_live_run_requires_offline_replay_before_private_self_use_candidate"
    _assert_removed_fixed_false_fields(pack)


def test_accurate_intake_live_decision_pack_can_prepare_private_candidate_but_not_approve_it() -> None:
    pack = build_accurate_intake_live_decision_pack(
        _artifact(strict_pass_count=5, repaired_pass_count=0),
        stage_manifest_artifact=_clean_required_stage_manifest(include_full_suite=True),
        offline_replay_artifact={
            "artifact_type": "accurate_intake_mvp_offline_shadow_replay",
            "input_integrity": {"passed": True, "blockers": []},
            "summary": {
                "sample_run_count": 3,
                "all_runs_strict": True,
                "strict_replay_ready": True,
                "full_suite_replay_ready": True,
                "full_suite_run_count": 3,
                "repaired_pass_count": 0,
                "timeout_count": 0,
                "model_diversity_status": "provider_diversity_present",
            },
        },
        provider_robustness_artifact={
            "artifact_type": "accurate_intake_mvp_live_robustness_matrix",
            "input_integrity": {"passed": True, "blockers": []},
            "model_inversion_evidence_passed": True,
            "contract_overfit_risk": False,
            "model_diversity_status": "provider_diversity_present",
        },
    )

    assert pack["selected_option"] == "prepare_private_self_use_candidate"
    assert pack["selection_reason"] == "strict_live_diagnostic_with_replay_evidence"
    assert pack["private_self_use_candidate_prepared"] is True
    _assert_removed_fixed_false_fields(pack)
    assert pack["max_model_claim"] == "multi_profile_live_diagnostic_observed"


def test_accurate_intake_live_decision_pack_requires_full_suite_replay_window_before_private_candidate() -> None:
    pack = build_accurate_intake_live_decision_pack(
        _artifact(strict_pass_count=5, repaired_pass_count=0),
        stage_manifest_artifact=_clean_required_stage_manifest(include_full_suite=True),
        offline_replay_artifact={
            "artifact_type": "accurate_intake_mvp_offline_shadow_replay",
            "input_integrity": {"passed": True, "blockers": []},
            "summary": {
                "sample_run_count": 3,
                "strict_replay_ready": True,
                "full_suite_replay_ready": False,
                "full_suite_run_count": 1,
                "repaired_pass_count": 0,
                "timeout_count": 0,
                "model_diversity_status": "provider_diversity_present",
            },
        },
        provider_robustness_artifact={
            "artifact_type": "accurate_intake_mvp_live_robustness_matrix",
            "input_integrity": {"passed": True, "blockers": []},
            "model_inversion_evidence_passed": True,
            "contract_overfit_risk": False,
            "model_diversity_status": "provider_diversity_present",
        },
    )

    assert pack["selected_option"] == "offline_shadow_replay"
    assert pack["selection_reason"] == "full_suite_replay_window_required"
    assert pack["offline_replay_summary"]["full_suite_replay_ready"] is False
    assert pack["private_self_use_candidate_prepared"] is False


def test_accurate_intake_live_decision_pack_requires_robustness_matrix_after_replay_diversity() -> None:
    pack = build_accurate_intake_live_decision_pack(
        _artifact(strict_pass_count=5, repaired_pass_count=0),
        offline_replay_artifact={
            "artifact_type": "accurate_intake_mvp_offline_shadow_replay",
            "input_integrity": {"passed": True, "blockers": []},
            "summary": {
                "sample_run_count": 3,
                "strict_replay_ready": True,
                "repaired_pass_count": 0,
                "timeout_count": 0,
                "model_diversity_status": "provider_diversity_present",
            },
        },
    )

    assert pack["selected_option"] == "offline_shadow_replay"
    assert pack["selection_reason"] == "provider_robustness_matrix_required"
    assert pack["private_self_use_candidate_prepared"] is False


def test_accurate_intake_live_decision_pack_blocks_candidate_on_contract_overfit_risk() -> None:
    pack = build_accurate_intake_live_decision_pack(
        _artifact(strict_pass_count=5, repaired_pass_count=0),
        offline_replay_artifact={
            "artifact_type": "accurate_intake_mvp_offline_shadow_replay",
            "input_integrity": {"passed": True, "blockers": []},
            "summary": {
                "sample_run_count": 3,
                "strict_replay_ready": True,
                "repaired_pass_count": 0,
                "timeout_count": 0,
                "model_diversity_status": "provider_diversity_present",
            },
        },
        provider_robustness_artifact={
            "artifact_type": "accurate_intake_mvp_live_robustness_matrix",
            "input_integrity": {"passed": True, "blockers": []},
            "model_inversion_evidence_passed": False,
            "contract_overfit_risk": True,
            "model_diversity_status": "provider_diversity_present",
        },
    )

    assert pack["selected_option"] == "offline_shadow_replay"
    assert pack["selection_reason"] == "contract_overfit_risk"
    assert pack["private_self_use_candidate_prepared"] is False


def test_accurate_intake_live_decision_pack_blocks_candidate_on_contract_hardening_debt() -> None:
    pack = build_accurate_intake_live_decision_pack(
        _artifact(strict_pass_count=5, repaired_pass_count=0),
        stage_manifest_artifact=_clean_required_stage_manifest(include_full_suite=True),
        offline_replay_artifact={
            "artifact_type": "accurate_intake_mvp_offline_shadow_replay",
            "input_integrity": {"passed": True, "blockers": []},
            "summary": {
                "sample_run_count": 3,
                "strict_replay_ready": True,
                "full_suite_replay_ready": True,
                "full_suite_run_count": 3,
                "repaired_pass_count": 0,
                "timeout_count": 0,
                "model_diversity_status": "provider_diversity_present",
            },
        },
        provider_robustness_artifact={
            "artifact_type": "accurate_intake_mvp_live_robustness_matrix",
            "input_integrity": {"passed": True, "blockers": []},
            "model_inversion_evidence_passed": True,
            "contract_overfit_risk": False,
            "model_diversity_status": "provider_diversity_present",
        },
        contract_hardening_guard_artifact={
            "artifact_type": "accurate_intake_contract_hardening_guard",
            "input_integrity": {"passed": True, "blockers": []},
            "merge_allowed": False,
            "contract_hardening_debt": {
                "present": True,
                "reasons": ["live_failure_only", "holdout_tests_missing"],
            },
            "blockers": ["live_failure_only", "holdout_tests_missing"],
        },
    )

    assert pack["selected_option"] == "offline_shadow_replay"
    assert pack["selection_reason"] == "contract_hardening_debt"
    assert pack["contract_hardening_summary"]["present"] is True
    assert pack["contract_hardening_summary"]["debt_present"] is True
    assert pack["private_self_use_candidate_prepared"] is False
    _assert_removed_fixed_false_fields(pack)


def test_accurate_intake_live_decision_pack_requires_full_suite_evidence_before_private_candidate() -> None:
    pack = build_accurate_intake_live_decision_pack(
        _artifact(
            strict_pass_count=5,
            repaired_pass_count=0,
            stages=[
                {"stage_id": "provider_health_smoke", "status": "pass"},
                {"stage_id": "schema_contract_probe", "status": "pass"},
                {"stage_id": "fake_provider_active_runtime_gate", "status": "pass"},
                {"stage_id": "single_case_live_probe", "status": "pass"},
            ],
        ),
        offline_replay_artifact={
            "artifact_type": "accurate_intake_mvp_offline_shadow_replay",
            "input_integrity": {"passed": True, "blockers": []},
            "summary": {
                "sample_run_count": 3,
                "strict_replay_ready": True,
                "repaired_pass_count": 0,
                "timeout_count": 0,
                "model_diversity_status": "provider_diversity_present",
            },
        },
        provider_robustness_artifact={
            "artifact_type": "accurate_intake_mvp_live_robustness_matrix",
            "input_integrity": {"passed": True, "blockers": []},
            "model_inversion_evidence_passed": True,
            "contract_overfit_risk": False,
            "model_diversity_status": "provider_diversity_present",
        },
    )

    assert pack["selected_option"] == "full_suite_blocked"
    assert pack["selection_reason"] == "full_suite_diagnostic_required"
    assert pack["private_self_use_candidate_prepared"] is False


def test_accurate_intake_live_decision_pack_blocks_private_candidate_when_replay_is_single_profile_only() -> None:
    pack = build_accurate_intake_live_decision_pack(
        _artifact(strict_pass_count=5, repaired_pass_count=0),
        offline_replay_artifact={
            "artifact_type": "accurate_intake_mvp_offline_shadow_replay",
            "input_integrity": {"passed": True, "blockers": []},
            "summary": {
                "sample_run_count": 3,
                "strict_replay_ready": True,
                "repaired_pass_count": 0,
                "timeout_count": 0,
                "model_diversity_status": "model_diversity_missing",
            },
        },
    )

    assert pack["selected_option"] == "offline_shadow_replay"
    assert pack["selection_reason"] == "model_diversity_missing"
    assert pack["private_self_use_candidate_prepared"] is False
    _assert_removed_fixed_false_fields(pack)


def test_accurate_intake_live_decision_pack_writer_creates_artifact(tmp_path: Path) -> None:
    source = tmp_path / "accurate_intake_mvp_live_diagnostic.json"
    source.write_text(json.dumps(_artifact(failure_family="environment_or_provider_blocker"), ensure_ascii=False), encoding="utf-8")

    output = write_accurate_intake_live_decision_pack(live_artifact_path=source, output_dir=tmp_path)

    pack = json.loads(output.read_text(encoding="utf-8"))
    assert output.name == "accurate_intake_mvp_live_decision_pack.json"
    assert pack["artifact_type"] == "accurate_intake_mvp_live_decision_pack"
    _assert_removed_fixed_false_fields(pack)


def test_accurate_intake_live_decision_pack_writer_accepts_run_specific_output_path(tmp_path: Path) -> None:
    source = tmp_path / "accurate_intake_mvp_live_diagnostic.json"
    output_path = tmp_path / "run_i" / "accurate_intake_mvp_live_decision_pack_run_i.json"
    source.write_text(json.dumps(_artifact(failure_family="environment_or_provider_blocker"), ensure_ascii=False), encoding="utf-8")

    output = write_accurate_intake_live_decision_pack(
        live_artifact_path=source,
        output_path=output_path,
    )

    pack = json.loads(output.read_text(encoding="utf-8"))
    assert output == output_path
    assert pack["artifact_type"] == "accurate_intake_mvp_live_decision_pack"


def test_accurate_intake_live_decision_pack_writer_accepts_stage_manifest(tmp_path: Path) -> None:
    source = tmp_path / "accurate_intake_mvp_live_diagnostic.json"
    manifest = tmp_path / "accurate_intake_mvp_live_stage_manifest.json"
    source.write_text(json.dumps(_artifact(strict_pass_count=5), ensure_ascii=False), encoding="utf-8")
    manifest.write_text(
        json.dumps(
            {
                "artifact_type": "accurate_intake_mvp_live_stage_manifest",
                "input_integrity": {"passed": True, "blockers": []},
                "stages": [
                    {"stage_id": "provider_health_smoke", "status": "pass"},
                    {"stage_id": "schema_contract_probe", "status": "pass"},
                    {"stage_id": "fake_provider_active_runtime_gate", "status": "pass"},
                    {"stage_id": "full_suite_live_diagnostic", "status": "pass"},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    output = write_accurate_intake_live_decision_pack(
        live_artifact_path=source,
        stage_manifest_artifact_path=manifest,
        output_dir=tmp_path,
    )

    pack = json.loads(output.read_text(encoding="utf-8"))
    assert pack["selected_option"] == "single_case_probe_required"
    assert pack["stage_summary"]["source"] == "stage_manifest"
    assert pack["source_stage_manifest_type"] == "accurate_intake_mvp_live_stage_manifest"
