from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from app.recommendation.application.shadow_artifact_gate import (
    evaluate_recommendation_shadow_artifact_payload,
    evaluate_recommendation_shadow_artifact_quality,
)
from scripts.build_recommendation_shadow_eval import (
    build_default_recommendation_shadow_eval_artifact,
    write_default_recommendation_shadow_eval_artifact,
)


ROOT = Path(__file__).resolve().parents[1]


def test_default_shadow_artifact_passes_offline_quality_gate() -> None:
    artifact = build_default_recommendation_shadow_eval_artifact()

    result = evaluate_recommendation_shadow_artifact_quality(artifact)

    assert result.passed is True
    assert result.failure_codes == []
    assert result.summary["scenario_count"] >= 8
    assert result.summary["missing_required_scenario_ids"] == []
    assert result.summary["mode_counts"]["general"] >= 6
    assert result.summary["mode_counts"]["menu_scan"] == 1
    assert result.summary["mode_counts"]["swap_suggestion"] == 1


def test_artifact_gate_rejects_runtime_effect_and_readiness_claims() -> None:
    artifact = build_default_recommendation_shadow_eval_artifact()
    bad_eval = artifact.evals[0].model_copy(
        update={
            "runtime_effect_allowed": True,
            "recommendation_served": True,
            "intake_committed": True,
        }
    )
    bad_artifact = artifact.model_copy(
        update={
            "real_runtime_effect": True,
            "product_readiness_claimed": True,
            "evals": [bad_eval, *artifact.evals[1:]],
        }
    )

    result = evaluate_recommendation_shadow_artifact_quality(bad_artifact)

    assert result.passed is False
    assert "artifact:real_runtime_effect_true" in result.failure_codes
    assert "artifact:product_readiness_claimed_true" in result.failure_codes
    assert f"eval:{bad_eval.scenario_id}:runtime_effect_allowed_true" in result.failure_codes
    assert f"eval:{bad_eval.scenario_id}:recommendation_served_true" in result.failure_codes
    assert f"eval:{bad_eval.scenario_id}:intake_committed_true" in result.failure_codes


def test_artifact_gate_rejects_canonical_hint_packet_claim() -> None:
    artifact = build_default_recommendation_shadow_eval_artifact()
    assert artifact.evals[0].hint_packet is not None
    bad_hint = artifact.evals[0].hint_packet.model_copy(
        update={"is_canonical_truth": True}
    )
    bad_eval = artifact.evals[0].model_copy(update={"hint_packet": bad_hint})
    bad_artifact = artifact.model_copy(update={"evals": [bad_eval, *artifact.evals[1:]]})

    result = evaluate_recommendation_shadow_artifact_quality(bad_artifact)

    assert result.passed is False
    assert f"eval:{bad_eval.scenario_id}:canonical_hint_packet" in result.failure_codes


def test_artifact_payload_gate_rejects_missing_required_non_claim_fields() -> None:
    artifact = build_default_recommendation_shadow_eval_artifact()
    payload = artifact.model_dump(mode="json")
    first_eval = payload["evals"][0]

    del payload["real_runtime_effect"]
    del payload["integrity"]["runtime_effect_allowed_count"]
    del first_eval["runtime_effect_allowed"]
    del first_eval["flags"]["durable_memory_written"]
    del first_eval["hint_packet"]["is_canonical_truth"]

    result = evaluate_recommendation_shadow_artifact_payload(payload)

    assert result.passed is False
    assert "artifact:missing_field:real_runtime_effect" in result.failure_codes
    assert "integrity:missing_field:runtime_effect_allowed_count" in result.failure_codes
    assert (
        f"eval:{first_eval['scenario_id']}:missing_field:runtime_effect_allowed"
        in result.failure_codes
    )
    assert (
        f"eval:{first_eval['scenario_id']}:flags_missing_field:durable_memory_written"
        in result.failure_codes
    )
    assert (
        f"eval:{first_eval['scenario_id']}:hint_packet_missing_field:is_canonical_truth"
        in result.failure_codes
    )


def test_artifact_payload_gate_reports_true_non_claim_fields_before_model_validation() -> None:
    artifact = build_default_recommendation_shadow_eval_artifact()
    payload = artifact.model_dump(mode="json")
    first_eval = payload["evals"][0]

    payload["real_runtime_effect"] = True
    payload["product_readiness_claimed"] = True
    payload["track_status"]["recommendation_served"] = True
    payload["integrity"]["runtime_effect_allowed_count"] = 1
    first_eval["runtime_effect_allowed"] = True
    first_eval["recommendation_served"] = True
    first_eval["flags"]["durable_memory_written"] = True
    first_eval["hint_packet"]["is_canonical_truth"] = True

    result = evaluate_recommendation_shadow_artifact_payload(payload)

    assert result.passed is False
    assert "artifact:real_runtime_effect_true" in result.failure_codes
    assert "artifact:product_readiness_claimed_true" in result.failure_codes
    assert "track_status:recommendation_served_unexpected" in result.failure_codes
    assert "integrity:runtime_effect_allowed_count_nonzero" in result.failure_codes
    assert (
        f"eval:{first_eval['scenario_id']}:runtime_effect_allowed_true"
        in result.failure_codes
    )
    assert (
        f"eval:{first_eval['scenario_id']}:recommendation_served_true"
        in result.failure_codes
    )
    assert (
        f"eval:{first_eval['scenario_id']}:flags_durable_memory_written_true"
        in result.failure_codes
    )
    assert f"eval:{first_eval['scenario_id']}:canonical_hint_packet" in result.failure_codes
    assert "payload:model_validation_error" in result.failure_codes


def test_artifact_payload_gate_rejects_null_integrity_counters() -> None:
    artifact = build_default_recommendation_shadow_eval_artifact()
    payload = artifact.model_dump(mode="json")
    payload["integrity"]["invalid_scenario_count"] = None
    payload["integrity"]["runtime_effect_allowed_count"] = None
    payload["integrity"]["canonical_hint_packet_count"] = None

    result = evaluate_recommendation_shadow_artifact_payload(payload)

    assert result.passed is False
    assert "integrity:invalid_scenario_count_nonzero" in result.failure_codes
    assert "integrity:runtime_effect_allowed_count_nonzero" in result.failure_codes
    assert "integrity:canonical_hint_packet_count_nonzero" in result.failure_codes


def test_artifact_payload_gate_dedupes_duplicate_failure_codes() -> None:
    artifact = build_default_recommendation_shadow_eval_artifact()
    payload = artifact.model_dump(mode="json")
    payload["track_status"]["recommendation_served"] = True

    result = evaluate_recommendation_shadow_artifact_payload(payload)

    assert result.passed is False
    assert result.failure_codes.count("track_status:recommendation_served_unexpected") == 1
    assert result.summary["failure_count"] == len(result.failure_codes)


def test_artifact_payload_gate_dedupes_validation_error_failure_codes() -> None:
    artifact = build_default_recommendation_shadow_eval_artifact()
    payload = artifact.model_dump(mode="json")
    bad_eval = payload["evals"][0]
    bad_eval["runtime_effect_allowed"] = True
    payload["evals"] = [bad_eval, bad_eval]

    result = evaluate_recommendation_shadow_artifact_payload(payload)

    assert result.passed is False
    failure_code = f"eval:{bad_eval['scenario_id']}:runtime_effect_allowed_true"
    assert result.failure_codes.count(failure_code) == 1
    assert result.failure_codes.count("payload:model_validation_error") == 1
    assert result.summary["failure_count"] == len(result.failure_codes)


def test_artifact_gate_rejects_missing_candidate_ranking_and_hint_packet() -> None:
    artifact = build_default_recommendation_shadow_eval_artifact()
    bad_eval = artifact.evals[0].model_copy(
        update={
            "candidate_items": [],
            "ranked_candidates": [],
            "top_pick": None,
            "hint_packet": None,
        }
    )
    bad_artifact = artifact.model_copy(update={"evals": [bad_eval, *artifact.evals[1:]]})

    result = evaluate_recommendation_shadow_artifact_quality(bad_artifact)

    assert result.passed is False
    assert f"eval:{bad_eval.scenario_id}:no_candidate_items" in result.failure_codes
    assert f"eval:{bad_eval.scenario_id}:no_ranked_candidates" in result.failure_codes
    assert f"eval:{bad_eval.scenario_id}:missing_top_pick" in result.failure_codes
    assert f"eval:{bad_eval.scenario_id}:missing_hint_packet" in result.failure_codes


def test_shadow_artifact_gate_script_runs_by_file_path_without_pythonpath(
    tmp_path: Path,
) -> None:
    artifact_path = write_default_recommendation_shadow_eval_artifact(
        tmp_path / "recommendation_shadow_eval.json"
    )
    report_path = tmp_path / "recommendation_shadow_eval_gate_report.json"
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_recommendation_shadow_eval.py",
            "--artifact",
            str(artifact_path),
            "--report",
            str(report_path),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "recommendation shadow artifact gate passed" in result.stdout
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["passed"] is True
    assert payload["summary"]["scenario_count"] >= 8
