from __future__ import annotations

from scripts.build_wave1_founder_offline_shadow_replay import (
    build_founder_offline_shadow_replay,
)


def _live_artifact(*, case_status: str = "repaired_pass", include_invariant: bool = True) -> dict[str, object]:
    repaired_case: dict[str, object] = {
        "case_id": "correction_prior_pearl_milk_tea_half_sugar",
        "case_contract_status": case_status,
        "actual_behavior": {
            "manager_rounds": [
                {
                    "trace": {
                        "request_payload": {
                            "tools": [
                                {
                                    "function": {
                                        "parameters": {
                                            "x-repair-contract": {
                                                "failure_family": "commit_without_evidence",
                                                "required_tool": "estimate_nutrition",
                                            }
                                        }
                                    }
                                }
                            ]
                        }
                    }
                }
            ]
        },
    }
    if include_invariant:
        repaired_case["failed_invariant"] = "commit_requires_evidence"
    return {
        "artifact_type": "wave1_founder_e2e_live_diagnostic",
        "readiness_claimed": False,
        "live_invoked": True,
        "production_selected": False,
        "runtime_web_activation_approved": False,
        "mutation_enabled": False,
        "summary": {
            "pass_count": 7,
            "fail_count": 0,
            "product_decision_required_count": 0,
            "failure_layers": [],
            "strict_pass_count": 6 if case_status == "repaired_pass" else 7,
            "repaired_pass_count": 1 if case_status == "repaired_pass" else 0,
            "contract_fail_count": 0,
        },
        "cases": [
            {"case_id": "pearl_milk_tea_logged_followup", "case_contract_status": "strict_pass"},
            repaired_case,
        ],
    }


def test_offline_shadow_replay_records_repaired_case_ids_and_failed_invariant() -> None:
    replay = build_founder_offline_shadow_replay([_live_artifact()])

    assert replay["artifact_type"] == "wave1_founder_offline_shadow_replay"
    assert replay["readiness_claimed"] is False
    assert replay["shadow_or_canary_approved"] is False
    assert replay["summary"]["repaired_pass_count"] == 1
    assert replay["summary"]["repaired_case_ids"] == ["correction_prior_pearl_milk_tea_half_sugar"]
    assert replay["runs"][0]["cases"][1]["repair_failure_family"] == "commit_without_evidence"
    assert replay["runs"][0]["cases"][1]["failed_invariant"] == "commit_requires_evidence"
    assert replay["strictness_gate"]["repaired_pass_unlocks_shadow"] is False


def test_offline_shadow_replay_fails_integrity_when_repaired_case_lacks_invariant() -> None:
    artifact = _live_artifact(include_invariant=False)
    artifact["cases"][1]["actual_behavior"] = {"manager_rounds": []}  # type: ignore[index]

    replay = build_founder_offline_shadow_replay([artifact])

    assert replay["input_integrity"]["passed"] is False
    assert "repaired_case_missing_failed_invariant" in replay["input_integrity"]["blockers"]
    assert replay["summary"]["eligible_for_shadow_candidate"] is False


def test_offline_shadow_replay_maps_schema_repair_to_contract_invariant() -> None:
    artifact = _live_artifact(include_invariant=False)
    artifact["cases"][1]["actual_behavior"] = {  # type: ignore[index]
        "manager_rounds": [
            {
                "trace": {
                    "parse_attempts": [
                        {
                            "failure_family": "manager_output_contract_violation",
                            "failing_component": "builderspace_runtime_contract.validate_manager_payload",
                        }
                    ]
                }
            }
        ]
    }

    replay = build_founder_offline_shadow_replay([artifact])

    assert replay["input_integrity"]["passed"] is True
    assert replay["runs"][0]["cases"][1]["repair_failure_family"] == "manager_output_contract_violation"
    assert replay["runs"][0]["cases"][1]["failed_invariant"] == "manager_contract_schema_adherence"


def test_offline_shadow_replay_marks_repeated_all_strict_as_candidate_only() -> None:
    replay = build_founder_offline_shadow_replay(
        [
            _live_artifact(case_status="strict_pass"),
            _live_artifact(case_status="strict_pass"),
            _live_artifact(case_status="strict_pass"),
        ]
    )

    assert replay["summary"]["sample_run_count"] == 3
    assert replay["summary"]["all_sampled_runs_7_strict"] is True
    assert replay["summary"]["single_profile_stability"] is True
    assert replay["summary"]["model_diversity_status"] == "model_diversity_missing"
    assert replay["summary"]["eligible_for_shadow_candidate"] is False
    assert replay["shadow_or_canary_approved"] is False
    assert replay["strictness_gate"]["single_profile_stability_is_shadow_ready"] is False
    assert replay["strictness_gate"]["model_diversity_required_for_shadow_candidate"] is True


def test_offline_shadow_replay_excludes_timeout_runs_from_stability_claims() -> None:
    artifact = _live_artifact(case_status="strict_pass")
    artifact["summary"]["provider_timeout_count"] = 1  # type: ignore[index]

    replay = build_founder_offline_shadow_replay(
        [
            artifact,
            _live_artifact(case_status="strict_pass"),
            _live_artifact(case_status="strict_pass"),
        ]
    )

    assert replay["summary"]["provider_timeout_count"] == 1
    assert replay["summary"]["all_sampled_runs_7_strict"] is False
    assert replay["summary"]["single_profile_stability"] is False
    assert replay["summary"]["eligible_for_shadow_candidate"] is False
