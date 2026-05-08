from __future__ import annotations

import json
from pathlib import Path

from scripts.build_accurate_intake_mvp_live_stage_manifest import (
    DEFAULT_STAGE_ARTIFACTS,
    build_accurate_intake_live_stage_manifest,
    write_accurate_intake_live_stage_manifest,
)


def _live_artifact(
    *,
    stage_id: str,
    status: str,
    case_ids: list[str] | None = None,
    result_kind: str = "strict_pass_first_attempt",
    retry_policy_applied: bool = False,
    failure_layer: str | None = None,
    failure_family: str | None = None,
    overclaim: bool = False,
) -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_mvp_live_diagnostic",
        "claim_scope": "live_diagnostic",
        "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
        "provider_profile_model": "grok-4-fast",
        "transport_mode": "synthetic_tool_transport",
        "schema_name": "founder_live_manager_contract",
        "schema_version": "v1",
        "readiness_claimed": overclaim,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "production_selected": False,
        "mutation_rollout_approved": False,
        "runtime_web_activation_approved": False,
        "live_provider_used_as_truth": False,
        "stages": [
            {
                "stage_id": stage_id,
                "status": status,
                "provider_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
                "model": "grok-4-fast",
                "transport_mode": "synthetic_tool_transport",
                "attempt_count": 1 if status != "blocked" else 0,
                "latency_ms": 123,
                "timeout_budget_ms": 180000,
                "failure_layer": failure_layer,
                "failure_family": failure_family,
                "retry_policy_applied": retry_policy_applied,
                "result_kind": result_kind,
                "case_ids": case_ids or [],
            }
        ],
        "summary": {
            "case_count": 0,
            "strict_pass_count": 0,
            "repaired_pass_count": 0,
            "contract_fail_count": 0,
            "timeout_count": 0,
            "provider_timeout_count": 0,
            "failure_layers": [failure_layer] if failure_layer else [],
            "failure_families": [failure_family] if failure_family else [],
        },
        "cases": [],
    }


def test_live_stage_manifest_links_stage_artifacts_and_preserves_non_claims(tmp_path: Path) -> None:
    health = tmp_path / "health.json"
    schema = tmp_path / "schema.json"
    single = tmp_path / "single.json"
    health.write_text(json.dumps(_live_artifact(stage_id="provider_health_smoke", status="pass")), encoding="utf-8")
    schema.write_text(json.dumps(_live_artifact(stage_id="schema_contract_probe", status="pass")), encoding="utf-8")
    single.write_text(
        json.dumps(
            _live_artifact(
                stage_id="single_case_live_probe",
                status="fail",
                failure_layer="provider_contract_non_adherence",
                failure_family="synthetic_decision_tool_call_missing",
            )
        ),
        encoding="utf-8",
    )

    manifest = build_accurate_intake_live_stage_manifest([health, schema, single])

    assert manifest["artifact_type"] == "accurate_intake_mvp_live_stage_manifest"
    assert manifest["claim_scope"] == "live_diagnostic_stage_manifest"
    assert "readiness_claimed" not in manifest
    assert "product_readiness_claimed" not in manifest
    assert "private_self_use_approved" not in manifest
    assert "production_selected" not in manifest
    assert "mutation_rollout_approved" not in manifest
    assert "runtime_web_activation_approved" not in manifest
    assert manifest["input_integrity"]["passed"] is True
    assert manifest["stage_summary"]["single_case_probe_status"] == "fail"
    assert manifest["stage_summary"]["stage_failures"] == [
        {
            "stage_id": "single_case_live_probe",
            "status": "fail",
            "failure_layer": "provider_contract_non_adherence",
            "failure_family": "synthetic_decision_tool_call_missing",
        }
    ]
    assert [stage["artifact_path"] for stage in manifest["stages"]] == [str(health), str(schema), str(single)]


def test_live_stage_manifest_integrity_blocks_overclaiming_source(tmp_path: Path) -> None:
    health = tmp_path / "health.json"
    health.write_text(
        json.dumps(_live_artifact(stage_id="provider_health_smoke", status="pass", overclaim=True)),
        encoding="utf-8",
    )

    manifest = build_accurate_intake_live_stage_manifest([health])

    assert manifest["input_integrity"]["passed"] is False
    assert "source_0_readiness_claimed" in manifest["input_integrity"]["blockers"]
    assert "readiness_claimed" not in manifest


def test_live_stage_manifest_writer_creates_artifact(tmp_path: Path) -> None:
    source = tmp_path / "health.json"
    source.write_text(json.dumps(_live_artifact(stage_id="provider_health_smoke", status="pass")), encoding="utf-8")

    output = write_accurate_intake_live_stage_manifest(stage_artifact_paths=[source], output_dir=tmp_path)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert output.name == "accurate_intake_mvp_live_stage_manifest.json"
    assert payload["artifact_type"] == "accurate_intake_mvp_live_stage_manifest"
    assert payload["stage_summary"]["provider_health_status"] == "pass"


def test_live_stage_manifest_writer_accepts_run_specific_output_path(tmp_path: Path) -> None:
    source = tmp_path / "health.json"
    output_path = tmp_path / "run_i" / "accurate_intake_mvp_live_stage_manifest_run_i.json"
    source.write_text(json.dumps(_live_artifact(stage_id="provider_health_smoke", status="pass")), encoding="utf-8")

    output = write_accurate_intake_live_stage_manifest(
        stage_artifact_paths=[source],
        output_path=output_path,
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert output == output_path
    assert payload["artifact_type"] == "accurate_intake_mvp_live_stage_manifest"


def test_live_stage_manifest_preserves_retry_result_kind(tmp_path: Path) -> None:
    single = tmp_path / "single.json"
    payload = _live_artifact(stage_id="single_case_live_probe", status="pass")
    payload["stages"][0]["result_kind"] = "pass_after_retry"  # type: ignore[index]
    payload["stages"][0]["retry_policy_applied"] = True  # type: ignore[index]
    single.write_text(json.dumps(payload), encoding="utf-8")

    manifest = build_accurate_intake_live_stage_manifest([single])

    assert manifest["stages"][0]["result_kind"] == "pass_after_retry"
    assert manifest["stage_summary"]["has_retry_dependent_stage"] is True


def test_live_stage_manifest_default_sources_match_runbook_stage_artifacts() -> None:
    assert [path.name for path in DEFAULT_STAGE_ARTIFACTS] == [
        "accurate_intake_mvp_live_diagnostic_provider_health.json",
        "accurate_intake_mvp_live_diagnostic_schema_probe.json",
        "accurate_intake_mvp_live_diagnostic_fake_runtime_gate.json",
        "accurate_intake_mvp_live_diagnostic_seeded_removal.json",
        "accurate_intake_mvp_live_diagnostic_exact_item.json",
        "accurate_intake_mvp_live_diagnostic_bubble_refinement.json",
        "accurate_intake_mvp_live_diagnostic_luwei_basket.json",
        "accurate_intake_mvp_live_diagnostic_single_case.json",
    ]


def test_live_stage_manifest_summarizes_required_single_case_coverage_and_result_kinds(tmp_path: Path) -> None:
    sources = [
        ("health.json", _live_artifact(stage_id="provider_health_smoke", status="pass")),
        ("schema.json", _live_artifact(stage_id="schema_contract_probe", status="pass")),
        ("fake.json", _live_artifact(stage_id="fake_provider_active_runtime_gate", status="pass")),
        (
            "seeded.json",
            _live_artifact(
                stage_id="single_case_live_probe",
                status="pass",
                case_ids=["explicit_item_removal_seeded"],
            ),
        ),
        (
            "exact.json",
            _live_artifact(
                stage_id="single_case_live_probe",
                status="pass",
                case_ids=["exact_item_official_label"],
            ),
        ),
        (
            "bubble.json",
            _live_artifact(
                stage_id="single_case_live_probe",
                status="pass",
                case_ids=["bubble_milk_tea_refinement"],
            ),
        ),
        (
            "luwei.json",
            _live_artifact(
                stage_id="single_case_live_probe",
                status="pass",
                case_ids=["luwei_bare_to_listed_basket"],
            ),
        ),
        (
            "single.json",
            _live_artifact(
                stage_id="single_case_live_probe",
                status="pass",
                case_ids=["chinese_chicken_rice_correction_removal_debug"],
                result_kind="pass_after_retry",
                retry_policy_applied=True,
            ),
        ),
    ]
    paths: list[Path] = []
    for filename, payload in sources:
        path = tmp_path / filename
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths.append(path)

    manifest = build_accurate_intake_live_stage_manifest(paths)

    summary = manifest["stage_summary"]
    assert summary["missing_required_stage_ids"] == []
    assert summary["missing_required_single_case_ids"] == []
    assert summary["has_missing_required_stage"] is False
    assert summary["result_kind_counts"] == {
        "strict_pass_first_attempt": 7,
        "pass_after_retry": 1,
    }
    assert summary["has_retry_dependent_stage"] is True
    assert summary["single_case_probe_results"] == [
        {
            "case_ids": ["explicit_item_removal_seeded"],
            "status": "pass",
            "result_kind": "strict_pass_first_attempt",
        },
        {
            "case_ids": ["exact_item_official_label"],
            "status": "pass",
            "result_kind": "strict_pass_first_attempt",
        },
        {
            "case_ids": ["bubble_milk_tea_refinement"],
            "status": "pass",
            "result_kind": "strict_pass_first_attempt",
        },
        {
            "case_ids": ["luwei_bare_to_listed_basket"],
            "status": "pass",
            "result_kind": "strict_pass_first_attempt",
        },
        {
            "case_ids": ["chinese_chicken_rice_correction_removal_debug"],
            "status": "pass",
            "result_kind": "pass_after_retry",
        },
    ]


def test_live_stage_manifest_records_case_order_trace_layers_model_and_timeout_policy(tmp_path: Path) -> None:
    paths: list[Path] = []
    for filename, payload in [
        ("health.json", _live_artifact(stage_id="provider_health_smoke", status="pass")),
        ("schema.json", _live_artifact(stage_id="schema_contract_probe", status="pass")),
        ("fake.json", _live_artifact(stage_id="fake_provider_active_runtime_gate", status="pass")),
        (
            "seeded.json",
            _live_artifact(
                stage_id="single_case_live_probe",
                status="pass",
                case_ids=["explicit_item_removal_seeded"],
            ),
        ),
    ]:
        path = tmp_path / filename
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths.append(path)

    manifest = build_accurate_intake_live_stage_manifest(paths)

    assert [item["case_id"] for item in manifest["diagnostic_case_order"]] == [
        "provider_health_smoke",
        "schema_contract_probe",
        "fake_provider_active_runtime_gate",
        "explicit_item_removal_seeded",
        "exact_item_official_label",
        "bubble_milk_tea_refinement",
        "luwei_bare_to_listed_basket",
        "chinese_chicken_rice_correction_removal_debug",
        "full_suite_live_diagnostic",
    ]
    assert manifest["model_profile_policy"] == {
        "primary_diagnostic_profile_id": "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
        "primary_model": "grok-4-fast",
        "single_profile_per_live_run": True,
        "same_profile_across_manager_passes": True,
        "cross_model_replay_is_separate_run": True,
        "fallback_profile_mix_cannot_be_counted_as_clean_success": True,
        "production_selected": False,
    }
    assert manifest["prompt_cache_policy"] == {
        "stable_prefix_required": True,
        "static_system_tools_schema_before_dynamic_context": True,
        "dynamic_context_packet_after_static_prefix": True,
        "stable_tool_order_required": True,
        "cache_hit_not_required_for_pass": True,
        "cached_tokens_must_be_reported_when_provider_exposes_usage": True,
        "prompt_cache_does_not_change_output_semantics": True,
        "cross_model_cache_not_assumed": True,
    }
    assert manifest["timeout_policy"] == {
        "max_provider_concurrency": 1,
        "default_provider_timeout_ms": 180_000,
        "default_provider_request_retry_count": 0,
        "retry_only_failed_provider_request": True,
        "never_rerun_whole_workflow_as_retry_success": True,
        "strict_pass_first_attempt_only_clean": True,
        "pass_after_retry_is_diagnostic_only": True,
        "timeout_after_retry_blocks_full_suite": True,
    }
    assert manifest["trace_grade_layers"] == [
        "provider_profile_and_prompt_versions",
        "current_turn_context_packet",
        "manager_pass_1_decision",
        "requested_tools",
        "filtered_tool_plan",
        "executed_tools",
        "compact_packets",
        "manager_pass_2_synthesis",
        "guard_result",
        "mutation_result",
        "renderer_input_basis",
        "final_response_basis",
        "latency_cost_cache_usage",
    ]
    summary = manifest["stage_summary"]
    assert summary["missing_required_single_case_ids"] == [
        "exact_item_official_label",
        "bubble_milk_tea_refinement",
        "luwei_bare_to_listed_basket",
        "chinese_chicken_rice_correction_removal_debug",
    ]
