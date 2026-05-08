from __future__ import annotations

import json
from pathlib import Path

from scripts.build_accurate_intake_mvp_live_robustness_matrix import (
    build_accurate_intake_live_robustness_matrix,
    write_accurate_intake_live_robustness_matrix,
)


def _stage_artifact(
    *,
    stage_id: str,
    status: str,
    result_kind: str,
    retry_policy_applied: bool = False,
    failure_layer: str | None = None,
    failure_family: str | None = None,
    provider_profile_id: str = "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
    model: str = "grok-4-fast",
) -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_mvp_live_diagnostic",
        "claim_scope": "live_diagnostic",
        "provider_profile_id": provider_profile_id,
        "provider_profile_model": model,
        "readiness_claimed": False,
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
                "provider_profile_id": provider_profile_id,
                "model": model,
                "transport_mode": "synthetic_tool_transport",
                "attempt_count": 1,
                "latency_ms": 123,
                "timeout_budget_ms": 180000,
                "failure_layer": failure_layer,
                "failure_family": failure_family,
                "retry_policy_applied": retry_policy_applied,
                "result_kind": result_kind,
            }
        ],
    }


def test_live_robustness_matrix_tracks_result_kinds_and_blocks_activation() -> None:
    matrix = build_accurate_intake_live_robustness_matrix(
        [
            _stage_artifact(
                stage_id="provider_health_smoke",
                status="pass",
                result_kind="strict_pass_first_attempt",
            ),
            _stage_artifact(
                stage_id="single_case_live_probe",
                status="pass",
                result_kind="pass_after_retry",
                retry_policy_applied=True,
            ),
            _stage_artifact(
                stage_id="single_case_live_probe",
                status="timeout",
                result_kind="timeout_after_retry",
                retry_policy_applied=True,
                failure_layer="provider_runtime_error",
                failure_family="environment_or_provider_blocker",
            ),
        ]
    )

    assert matrix["artifact_type"] == "accurate_intake_mvp_live_robustness_matrix"
    assert matrix["claim_scope"] == "live_diagnostic_robustness_matrix"
    assert "readiness_claimed" not in matrix
    assert "private_self_use_approved" not in matrix
    assert matrix["result_kind_counts"] == {
        "strict_pass_first_attempt": 1,
        "pass_after_retry": 1,
        "timeout_after_retry": 1,
    }
    assert matrix["failure_layer_counts"] == {"provider_runtime_error": 1}
    assert matrix["failure_family_counts"] == {"environment_or_provider_blocker": 1}
    assert matrix["has_retry_dependent_evidence"] is True
    assert matrix["has_timeout_evidence"] is True
    assert matrix["private_self_use_candidate_blocked"] is True
    assert matrix["max_model_claim"] == "single_profile_live_diagnostic_observed"
    assert "model_portability_claimed" not in matrix
    assert matrix["model_diversity_status"] == "model_diversity_missing"
    assert matrix["model_inversion_evidence_passed"] is False


def test_live_robustness_matrix_writer_creates_artifact(tmp_path: Path) -> None:
    source = tmp_path / "provider_health.json"
    source.write_text(
        json.dumps(
            _stage_artifact(
                stage_id="provider_health_smoke",
                status="pass",
                result_kind="strict_pass_first_attempt",
            )
        ),
        encoding="utf-8",
    )

    output = write_accurate_intake_live_robustness_matrix(stage_artifact_paths=[source], output_dir=tmp_path)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert output.name == "accurate_intake_mvp_live_robustness_matrix.json"
    assert payload["artifact_type"] == "accurate_intake_mvp_live_robustness_matrix"
    assert payload["result_kind_counts"] == {"strict_pass_first_attempt": 1}


def test_live_robustness_matrix_writer_accepts_run_specific_output_path(tmp_path: Path) -> None:
    source = tmp_path / "provider_health.json"
    output_path = tmp_path / "run_i" / "accurate_intake_mvp_live_robustness_matrix_run_i.json"
    source.write_text(
        json.dumps(
            _stage_artifact(
                stage_id="provider_health_smoke",
                status="pass",
                result_kind="strict_pass_first_attempt",
            )
        ),
        encoding="utf-8",
    )

    output = write_accurate_intake_live_robustness_matrix(
        stage_artifact_paths=[source],
        output_path=output_path,
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert output == output_path
    assert payload["artifact_type"] == "accurate_intake_mvp_live_robustness_matrix"


def test_live_robustness_matrix_marks_clean_multi_profile_evidence_without_portability_claim() -> None:
    matrix = build_accurate_intake_live_robustness_matrix(
        [
            _stage_artifact(
                stage_id="single_case_live_probe",
                status="pass",
                result_kind="strict_pass_first_attempt",
                provider_profile_id="builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
                model="grok-4-fast",
            ),
            _stage_artifact(
                stage_id="single_case_live_probe",
                status="pass",
                result_kind="strict_pass_first_attempt",
                provider_profile_id="alternate-accurate-intake-mvp-live-diagnostic",
                model="alternate-model",
            ),
        ]
    )

    assert matrix["single_profile_only"] is False
    assert matrix["model_diversity_status"] == "provider_diversity_present"
    assert matrix["model_inversion_evidence_passed"] is True
    assert matrix["contract_overfit_risk"] is False
    assert "model_portability_claimed" not in matrix
    assert matrix["max_model_claim"] == "multi_profile_live_diagnostic_observed"


def test_live_robustness_matrix_flags_contract_overfit_risk_on_alternate_profile_failure() -> None:
    matrix = build_accurate_intake_live_robustness_matrix(
        [
            _stage_artifact(
                stage_id="single_case_live_probe",
                status="pass",
                result_kind="strict_pass_first_attempt",
                provider_profile_id="builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic",
                model="grok-4-fast",
            ),
            _stage_artifact(
                stage_id="single_case_live_probe",
                status="fail",
                result_kind="fail",
                failure_layer="provider_contract_non_adherence",
                failure_family="semantic_contract_violation",
                provider_profile_id="alternate-accurate-intake-mvp-live-diagnostic",
                model="alternate-model",
            ),
        ]
    )

    assert matrix["model_diversity_status"] == "provider_diversity_present"
    assert matrix["model_inversion_evidence_passed"] is False
    assert matrix["contract_overfit_risk"] is True
    assert matrix["private_self_use_candidate_blocked"] is True
