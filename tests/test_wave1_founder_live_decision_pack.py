from __future__ import annotations

import json
from pathlib import Path

from scripts.build_wave1_founder_live_decision_pack import (
    DECISION_OPTION_IDS,
    build_founder_live_decision_pack,
    write_founder_live_decision_pack,
)


def _artifact(
    *,
    live_invoked: bool = True,
    pass_count: int = 1,
    fail_count: int = 6,
    product_decision_required_count: int = 0,
    failure_layers: list[str] | None = None,
    strict_pass_count: int = 1,
    repaired_pass_count: int = 0,
    contract_fail_count: int = 6,
    cases: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "artifact_type": "wave1_founder_e2e_live_diagnostic",
        "readiness_claimed": False,
        "live_invoked": live_invoked,
        "production_selected": False,
        "runtime_web_activation_approved": False,
        "mutation_enabled": False,
        "summary": {
            "pass_count": pass_count,
            "fail_count": fail_count,
            "product_decision_required_count": product_decision_required_count,
            "failure_layers": failure_layers if failure_layers is not None else ["provider_contract_non_adherence"],
            "strict_pass_count": strict_pass_count,
            "repaired_pass_count": repaired_pass_count,
            "contract_fail_count": contract_fail_count,
            "shadow_or_canary_unlock_allowed": False,
        },
        "cases": cases
        if cases is not None
        else [
            {"case_id": "case-1", "case_contract_status": "strict_pass"},
            {"case_id": "case-2", "case_contract_status": "fail"},
        ],
    }


def _offline_replay(*, sample_run_count: int = 3, all_strict: bool = True) -> dict[str, object]:
    strict_replay_ready = all_strict and sample_run_count >= 3
    return {
        "artifact_type": "wave1_founder_offline_shadow_replay",
        "readiness_claimed": False,
        "shadow_or_canary_approved": False,
        "input_integrity": {"passed": True, "blockers": []},
        "summary": {
            "sample_run_count": sample_run_count,
            "all_runs_strict": all_strict,
            "all_sampled_runs_7_strict": all_strict,
            "strict_replay_ready": strict_replay_ready,
            "single_profile_stability": strict_replay_ready,
            "model_diversity_status": "model_diversity_missing" if strict_replay_ready else "insufficient_evidence",
            "eligible_for_shadow_candidate": False,
            "strict_pass_count": sample_run_count * 7 if all_strict else 6,
            "repaired_pass_count": 0 if all_strict else 1,
            "repaired_case_ids": [] if all_strict else ["correction_prior_pearl_milk_tea_half_sugar"],
        },
        "strictness_gate": {
            "prepare_shadow_candidate_requires_repeated_all_strict": True,
            "model_diversity_required_for_shadow_candidate": True,
            "single_profile_stability_is_shadow_ready": False,
            "minimum_strict_replay_runs": 3,
            "repaired_pass_unlocks_shadow": False,
        },
    }


def _provider_matrix(*, status: str = "provider_diversity_present") -> dict[str, object]:
    return {
        "artifact_type": "wave1_founder_provider_robustness_matrix",
        "readiness_claimed": False,
        "production_manager_selected": False,
        "shadow_or_canary_approved": False,
        "input_integrity": {"passed": True, "blockers": []},
        "matrix_summary": {
            "provider_diversity_status": status,
            "model_inversion_evidence_passed": status == "provider_diversity_present",
            "contract_overfit_risk": status == "contract_overfit_risk",
            "strict_pass_rate": 1.0 if status == "provider_diversity_present" else 0.85,
            "repaired_pass_rate": 0.0 if status == "provider_diversity_present" else 0.15,
            "timeout_rate": 0.0,
        },
        "provider_rows": [],
    }


def test_founder_live_decision_pack_routes_provider_contract_failures_to_followup() -> None:
    pack = build_founder_live_decision_pack(_artifact())

    assert pack["artifact_type"] == "wave1_founder_live_decision_pack"
    assert pack["decision_options_ordered"] == list(DECISION_OPTION_IDS)
    assert pack["selected_option"] == "narrow_live_contract_followup"
    assert pack["readiness_claimed"] is False
    assert pack["shadow_or_canary_approved"] is False
    assert pack["production_rollout_approved"] is False


def test_founder_live_decision_pack_does_not_unlock_shadow_for_all_repaired_passes() -> None:
    pack = build_founder_live_decision_pack(
        _artifact(
            pass_count=7,
            fail_count=0,
            failure_layers=[],
            strict_pass_count=0,
            repaired_pass_count=7,
            contract_fail_count=0,
            product_decision_required_count=0,
        )
    )

    assert pack["selected_option"] == "offline_shadow_replay"
    assert pack["selection_reason"] == "live_clean_but_repair_dependent"
    assert pack["shadow_or_canary_approved"] is False


def test_founder_live_decision_pack_lists_repaired_case_ids_before_offline_replay() -> None:
    pack = build_founder_live_decision_pack(
        _artifact(
            pass_count=7,
            fail_count=0,
            failure_layers=[],
            strict_pass_count=6,
            repaired_pass_count=1,
            contract_fail_count=0,
            product_decision_required_count=0,
            cases=[
                {"case_id": "pearl_milk_tea_logged_followup", "case_contract_status": "strict_pass"},
                {
                    "case_id": "correction_prior_pearl_milk_tea_half_sugar",
                    "case_contract_status": "repaired_pass",
                    "repair_failure_family": "commit_without_evidence",
                    "failed_invariant": "commit_requires_evidence",
                },
            ],
        )
    )

    assert pack["selected_option"] == "offline_shadow_replay"
    assert pack["evidence_summary"]["repaired_case_ids"] == ["correction_prior_pearl_milk_tea_half_sugar"]
    assert pack["evidence_summary"]["repaired_cases"] == [
        {
            "case_id": "correction_prior_pearl_milk_tea_half_sugar",
            "repair_failure_family": "commit_without_evidence",
            "failed_invariant": "commit_requires_evidence",
        }
    ]


def test_founder_live_decision_pack_derives_schema_repair_invariant_from_trace() -> None:
    pack = build_founder_live_decision_pack(
        _artifact(
            pass_count=7,
            fail_count=0,
            failure_layers=[],
            strict_pass_count=6,
            repaired_pass_count=1,
            contract_fail_count=0,
            product_decision_required_count=0,
            cases=[
                {
                    "case_id": "generic_stable_tea_egg",
                    "case_contract_status": "repaired_pass",
                    "actual_behavior": {
                        "manager_rounds": [
                            {
                                "trace": {
                                    "parse_attempts": [
                                        {"failure_family": "manager_output_contract_violation"}
                                    ]
                                }
                            }
                        ]
                    },
                },
            ],
        )
    )

    assert pack["evidence_summary"]["repaired_cases"] == [
        {
            "case_id": "generic_stable_tea_egg",
            "repair_failure_family": "manager_output_contract_violation",
            "failed_invariant": "manager_contract_schema_adherence",
        }
    ]


def test_founder_live_decision_pack_blocks_shadow_candidate_for_single_profile_strict_only() -> None:
    pack = build_founder_live_decision_pack(
        _artifact(
            pass_count=7,
            fail_count=0,
            failure_layers=[],
            strict_pass_count=7,
            repaired_pass_count=0,
            contract_fail_count=0,
            product_decision_required_count=0,
        ),
        offline_shadow_replay_artifact=_offline_replay(sample_run_count=3, all_strict=True),
    )

    assert pack["selected_option"] == "offline_shadow_replay"
    assert pack["selection_reason"] == "model_diversity_missing"
    assert pack["offline_shadow_replay_summary"]["single_profile_stability"] is True
    assert pack["shadow_or_canary_approved"] is False


def test_founder_live_decision_pack_requires_provider_matrix_before_shadow_candidate() -> None:
    pack = build_founder_live_decision_pack(
        _artifact(
            pass_count=7,
            fail_count=0,
            failure_layers=[],
            strict_pass_count=7,
            repaired_pass_count=0,
            contract_fail_count=0,
            product_decision_required_count=0,
        ),
        offline_shadow_replay_artifact={
            **_offline_replay(sample_run_count=3, all_strict=True),
            "summary": {
                **_offline_replay(sample_run_count=3, all_strict=True)["summary"],  # type: ignore[index]
                "model_diversity_status": "provider_diversity_present",
                "eligible_for_shadow_candidate": True,
            },
        },
    )

    assert pack["selected_option"] == "offline_shadow_replay"
    assert pack["selection_reason"] == "provider_robustness_matrix_required_before_shadow_candidate"
    assert pack["shadow_or_canary_approved"] is False


def test_founder_live_decision_pack_can_prepare_shadow_candidate_with_model_inversion_evidence() -> None:
    pack = build_founder_live_decision_pack(
        _artifact(
            pass_count=7,
            fail_count=0,
            failure_layers=[],
            strict_pass_count=7,
            repaired_pass_count=0,
            contract_fail_count=0,
            product_decision_required_count=0,
        ),
        offline_shadow_replay_artifact={
            **_offline_replay(sample_run_count=3, all_strict=True),
            "summary": {
                **_offline_replay(sample_run_count=3, all_strict=True)["summary"],  # type: ignore[index]
                "model_diversity_status": "provider_diversity_present",
                "eligible_for_shadow_candidate": True,
            },
        },
        provider_robustness_matrix_artifact=_provider_matrix(status="provider_diversity_present"),
    )

    assert pack["selected_option"] == "prepare_shadow_candidate"
    assert pack["selection_reason"] == "repeated_all_strict_with_model_inversion_evidence"
    assert pack["shadow_or_canary_approved"] is False


def test_founder_live_decision_pack_classifies_alternate_model_regression_as_overfit_risk() -> None:
    pack = build_founder_live_decision_pack(
        _artifact(
            pass_count=7,
            fail_count=0,
            failure_layers=[],
            strict_pass_count=7,
            repaired_pass_count=0,
            contract_fail_count=0,
            product_decision_required_count=0,
        ),
        offline_shadow_replay_artifact={
            **_offline_replay(sample_run_count=3, all_strict=True),
            "summary": {
                **_offline_replay(sample_run_count=3, all_strict=True)["summary"],  # type: ignore[index]
                "model_diversity_status": "provider_diversity_present",
                "eligible_for_shadow_candidate": True,
            },
        },
        provider_robustness_matrix_artifact=_provider_matrix(status="contract_overfit_risk"),
    )

    assert pack["selected_option"] == "narrow_live_contract_followup"
    assert pack["selection_reason"] == "contract_overfit_risk"
    assert pack["provider_robustness_summary"]["contract_overfit_risk"] is True


def test_founder_live_decision_pack_requires_repeated_strict_replay_before_shadow_candidate() -> None:
    pack = build_founder_live_decision_pack(
        _artifact(
            pass_count=7,
            fail_count=0,
            failure_layers=[],
            strict_pass_count=7,
            repaired_pass_count=0,
            contract_fail_count=0,
            product_decision_required_count=0,
        )
    )

    assert pack["selected_option"] == "offline_shadow_replay"
    assert pack["selection_reason"] == "offline_shadow_replay_required_before_shadow_candidate"
    assert pack["shadow_or_canary_approved"] is False


def test_founder_live_decision_pack_rejects_repaired_replay_for_shadow_candidate() -> None:
    pack = build_founder_live_decision_pack(
        _artifact(
            pass_count=7,
            fail_count=0,
            failure_layers=[],
            strict_pass_count=7,
            repaired_pass_count=0,
            contract_fail_count=0,
            product_decision_required_count=0,
        ),
        offline_shadow_replay_artifact=_offline_replay(sample_run_count=3, all_strict=False),
    )

    assert pack["selected_option"] == "offline_shadow_replay"
    assert pack["selection_reason"] == "offline_shadow_replay_not_all_strict"
    assert pack["shadow_or_canary_approved"] is False


def test_founder_live_decision_pack_defers_to_product_decision_when_needed() -> None:
    pack = build_founder_live_decision_pack(
        _artifact(
            pass_count=6,
            fail_count=0,
            product_decision_required_count=1,
            failure_layers=[],
            strict_pass_count=6,
            repaired_pass_count=0,
            contract_fail_count=0,
        )
    )

    assert pack["selected_option"] == "defer_until_product_decision"
    assert pack["requires_human_decision"] is True


def test_founder_live_decision_pack_writer_creates_artifact(tmp_path: Path) -> None:
    source = tmp_path / "wave1_founder_e2e_live_diagnostic.json"
    source.write_text(json.dumps(_artifact(), ensure_ascii=False), encoding="utf-8")

    output = write_founder_live_decision_pack(founder_live_artifact_path=source, output_dir=tmp_path)

    pack = json.loads(output.read_text(encoding="utf-8"))
    assert output.name == "wave1_founder_live_decision_pack.json"
    assert pack["selected_option"] == "narrow_live_contract_followup"
    assert pack["runtime_web_activation_approved"] is False
