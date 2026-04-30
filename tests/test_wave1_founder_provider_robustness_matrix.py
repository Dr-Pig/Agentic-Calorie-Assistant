from __future__ import annotations

from scripts.build_wave1_founder_provider_robustness_matrix import (
    build_founder_provider_robustness_matrix,
)


def _live_artifact(
    *,
    profile_id: str = "builderspace-grok-4-fast-founder-live-contract",
    model: str = "grok-4-fast",
    strict_pass_count: int = 5,
    repaired_pass_count: int = 2,
    contract_fail_count: int = 0,
    provider_timeout_count: int = 0,
    deferred_count: int = 0,
) -> dict[str, object]:
    return {
        "artifact_type": "wave1_founder_e2e_live_diagnostic",
        "readiness_claimed": False,
        "live_invoked": True,
        "production_selected": False,
        "runtime_web_activation_approved": False,
        "mutation_enabled": False,
        "provider_profile_id": profile_id,
        "provider_profile_model": model,
        "summary": {
            "pass_count": strict_pass_count + repaired_pass_count,
            "fail_count": contract_fail_count,
            "product_decision_required_count": 0,
            "failure_layers": [],
            "strict_pass_count": strict_pass_count,
            "repaired_pass_count": repaired_pass_count,
            "contract_fail_count": contract_fail_count,
            "provider_timeout_count": provider_timeout_count,
            "deferred_count": deferred_count,
            "repaired_case_ids": ["generic_stable_tea_egg"] if repaired_pass_count else [],
        },
        "cases": [
            {"case_id": "generic_stable_tea_egg", "case_contract_status": "repaired_pass"}
            if repaired_pass_count
            else {"case_id": "generic_stable_tea_egg", "case_contract_status": "strict_pass"}
        ],
    }


def test_provider_robustness_matrix_tracks_repaired_rate_not_only_pass_fail() -> None:
    matrix = build_founder_provider_robustness_matrix([_live_artifact(), _live_artifact()])

    row = matrix["provider_rows"][0]
    assert row["provider_profile_id"] == "builderspace-grok-4-fast-founder-live-contract"
    assert row["sample_run_count"] == 2
    assert row["pass_count"] == 14
    assert row["fail_count"] == 0
    assert row["strict_pass_count"] == 10
    assert row["repaired_pass_count"] == 4
    assert row["repaired_pass_rate"] == 4 / 14
    assert row["provider_timeout_count"] == 0
    assert row["timeout_rate"] == 0.0
    assert row["all_runs_strict"] is False
    assert row["repaired_case_ids"] == ["generic_stable_tea_egg"]
    assert matrix["readiness_claimed"] is False
    assert matrix["production_manager_selected"] is False
    assert matrix["matrix_summary"]["provider_diversity_status"] == "model_diversity_missing"
    assert matrix["matrix_summary"]["model_inversion_evidence_passed"] is False


def test_provider_robustness_matrix_keeps_deepseek_as_comparison_only() -> None:
    matrix = build_founder_provider_robustness_matrix(
        [
            _live_artifact(),
            _live_artifact(profile_id="builderspace-deepseek-founder-live-comparison", model="deepseek-chat"),
        ]
    )

    roles = {row["provider_profile_id"]: row["matrix_role"] for row in matrix["provider_rows"]}
    assert roles["builderspace-grok-4-fast-founder-live-contract"] == "diagnostic_candidate"
    assert roles["builderspace-deepseek-founder-live-comparison"] == "comparison_only"
    assert matrix["matrix_summary"]["provider_diversity_status"] == "model_diversity_missing"


def test_provider_robustness_matrix_tracks_timeout_and_deferred_rates() -> None:
    matrix = build_founder_provider_robustness_matrix(
        [
            _live_artifact(strict_pass_count=6, repaired_pass_count=0, provider_timeout_count=1),
            _live_artifact(strict_pass_count=6, repaired_pass_count=0, deferred_count=1),
        ]
    )

    row = matrix["provider_rows"][0]
    assert row["provider_timeout_count"] == 1
    assert row["deferred_count"] == 1
    assert row["timeout_rate"] == 1 / 14
    assert row["deferred_rate"] == 1 / 14
    assert row["single_profile_all_strict"] is False


def test_provider_robustness_matrix_passes_model_inversion_with_alternate_strict_profile() -> None:
    matrix = build_founder_provider_robustness_matrix(
        [
            _live_artifact(strict_pass_count=7, repaired_pass_count=0),
            _live_artifact(
                profile_id="builderspace-kimi-founder-live-canary",
                model="kimi-k2",
                strict_pass_count=7,
                repaired_pass_count=0,
            ),
        ]
    )

    roles = {row["provider_profile_id"]: row["matrix_role"] for row in matrix["provider_rows"]}
    assert roles["builderspace-kimi-founder-live-canary"] == "alternate_diagnostic_candidate"
    assert matrix["matrix_summary"]["provider_diversity_status"] == "provider_diversity_present"
    assert matrix["matrix_summary"]["model_inversion_evidence_passed"] is True
    assert matrix["matrix_summary"]["contract_overfit_risk"] is False


def test_provider_robustness_matrix_classifies_alternate_regression_as_contract_overfit_risk() -> None:
    matrix = build_founder_provider_robustness_matrix(
        [
            _live_artifact(strict_pass_count=7, repaired_pass_count=0),
            _live_artifact(
                profile_id="builderspace-kimi-founder-live-canary",
                model="kimi-k2",
                strict_pass_count=5,
                repaired_pass_count=2,
            ),
        ]
    )

    assert matrix["matrix_summary"]["provider_diversity_status"] == "contract_overfit_risk"
    assert matrix["matrix_summary"]["model_inversion_evidence_passed"] is False
    assert matrix["matrix_summary"]["contract_overfit_risk"] is True


def test_provider_robustness_matrix_blocks_production_or_readiness_inputs() -> None:
    artifact = _live_artifact()
    artifact["production_selected"] = True
    artifact["readiness_claimed"] = True

    matrix = build_founder_provider_robustness_matrix([artifact])

    assert matrix["input_integrity"]["passed"] is False
    assert "input_production_selected" in matrix["input_integrity"]["blockers"]
    assert "input_readiness_claimed" in matrix["input_integrity"]["blockers"]
    assert matrix["production_manager_selected"] is False
