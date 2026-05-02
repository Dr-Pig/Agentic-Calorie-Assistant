from __future__ import annotations

import json
from pathlib import Path

from scripts.build_accurate_intake_mvp_live_decision_pack import (
    DECISION_OPTION_IDS,
    build_accurate_intake_live_decision_pack,
    write_accurate_intake_live_decision_pack,
)


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
    assert pack["private_self_use_approved"] is False
    assert pack["product_readiness_claimed"] is False
    assert pack["mutation_rollout_approved"] is False
    assert pack["production_selected"] is False


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
    assert pack["private_self_use_approved"] is False


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
    assert pack["private_self_use_approved"] is False


def test_accurate_intake_live_decision_pack_routes_single_strict_run_to_offline_replay() -> None:
    pack = build_accurate_intake_live_decision_pack(_artifact(strict_pass_count=5, repaired_pass_count=0))

    assert pack["selected_option"] == "offline_shadow_replay"
    assert pack["selection_reason"] == "single_live_run_requires_offline_replay_before_private_self_use_candidate"
    assert pack["private_self_use_approved"] is False


def test_accurate_intake_live_decision_pack_can_prepare_private_candidate_but_not_approve_it() -> None:
    pack = build_accurate_intake_live_decision_pack(
        _artifact(strict_pass_count=5, repaired_pass_count=0),
        offline_replay_artifact={
            "artifact_type": "accurate_intake_mvp_offline_shadow_replay",
            "input_integrity": {"passed": True, "blockers": []},
            "summary": {
                "sample_run_count": 3,
                "all_runs_strict": True,
                "strict_replay_ready": True,
                "repaired_pass_count": 0,
                "timeout_count": 0,
            },
        },
    )

    assert pack["selected_option"] == "prepare_private_self_use_candidate"
    assert pack["selection_reason"] == "strict_live_diagnostic_with_replay_evidence"
    assert pack["private_self_use_candidate_prepared"] is True
    assert pack["private_self_use_approved"] is False
    assert pack["product_readiness_claimed"] is False
    assert pack["mutation_rollout_approved"] is False


def test_accurate_intake_live_decision_pack_writer_creates_artifact(tmp_path: Path) -> None:
    source = tmp_path / "accurate_intake_mvp_live_diagnostic.json"
    source.write_text(json.dumps(_artifact(failure_family="environment_or_provider_blocker"), ensure_ascii=False), encoding="utf-8")

    output = write_accurate_intake_live_decision_pack(live_artifact_path=source, output_dir=tmp_path)

    pack = json.loads(output.read_text(encoding="utf-8"))
    assert output.name == "accurate_intake_mvp_live_decision_pack.json"
    assert pack["artifact_type"] == "accurate_intake_mvp_live_decision_pack"
    assert pack["runtime_web_activation_approved"] is False
