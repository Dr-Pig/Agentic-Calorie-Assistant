from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from app.recommendation.application.shadow_scorecard import (
    build_recommendation_shadow_scorecard,
)
from scripts.build_recommendation_shadow_eval import (
    build_default_recommendation_shadow_eval_artifact,
    write_default_recommendation_shadow_eval_artifact,
)


ROOT = Path(__file__).resolve().parents[1]


def test_default_shadow_scorecard_summarizes_modes_sources_and_no_claim_status() -> None:
    artifact = build_default_recommendation_shadow_eval_artifact()

    scorecard = build_recommendation_shadow_scorecard(artifact)

    assert scorecard.scorecard_type == "recommendation_shadow_scorecard"
    assert scorecard.shadow_mode is True
    assert scorecard.product_readiness_claimed is False
    assert scorecard.private_self_use_approved is False
    assert scorecard.gate_passed is True
    assert scorecard.summary["scenario_count"] >= 8
    assert scorecard.summary["mode_counts"]["general"] >= 6
    assert scorecard.summary["source_counts"]["safe_fallback"] >= 1
    assert scorecard.summary["canonical_hint_packet_count"] == 0
    assert scorecard.summary["runtime_effect_allowed_count"] == 0


def test_shadow_scorecard_reports_each_scenario_review_surface() -> None:
    artifact = build_default_recommendation_shadow_eval_artifact()

    scorecard = build_recommendation_shadow_scorecard(artifact)
    cold_start = _scenario(scorecard, "cold_start_lunch")
    negative = _scenario(scorecard, "known_negative_preference")

    assert cold_start["cold_start_used"] is True
    assert cold_start["candidate_count"] >= 1
    assert cold_start["top_pick_candidate_id"]
    assert cold_start["hint_packet_present"] is True
    assert cold_start["hint_packet_canonical"] is False
    assert "location_context_fixture_not_used" in cold_start["coverage_gaps"]
    assert negative["filtered_reason_counts"]["confirmed_negative_preference"] == 1
    assert negative["top_pick_candidate_id"] != "negative-drink-1"


def test_shadow_scorecard_preserves_gate_failures_without_claiming_readiness() -> None:
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

    scorecard = build_recommendation_shadow_scorecard(bad_artifact)

    assert scorecard.gate_passed is False
    assert scorecard.product_readiness_claimed is False
    assert scorecard.private_self_use_approved is False
    assert f"eval:{bad_eval.scenario_id}:no_candidate_items" in scorecard.issue_codes
    assert _scenario(scorecard, bad_eval.scenario_id)["hint_packet_present"] is False


def test_shadow_scorecard_script_writes_json_report_without_pythonpath(
    tmp_path: Path,
) -> None:
    artifact_path = write_default_recommendation_shadow_eval_artifact(
        tmp_path / "recommendation_shadow_eval.json"
    )
    scorecard_path = tmp_path / "recommendation_shadow_scorecard.json"
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_recommendation_shadow_scorecard.py",
            "--artifact",
            str(artifact_path),
            "--output",
            str(scorecard_path),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "wrote" in result.stdout
    payload = json.loads(scorecard_path.read_text(encoding="utf-8"))
    assert payload["scorecard_type"] == "recommendation_shadow_scorecard"
    assert payload["gate_passed"] is True
    assert payload["summary"]["scenario_count"] >= 8
    assert payload["product_readiness_claimed"] is False


def test_shadow_scorecard_script_reports_failing_artifact_without_nonzero_exit(
    tmp_path: Path,
) -> None:
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
    artifact_path = tmp_path / "failing_recommendation_shadow_eval.json"
    scorecard_path = tmp_path / "recommendation_shadow_scorecard.json"
    artifact_path.write_text(
        json.dumps(bad_artifact.model_dump(mode="json"), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_recommendation_shadow_scorecard.py",
            "--artifact",
            str(artifact_path),
            "--output",
            str(scorecard_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(scorecard_path.read_text(encoding="utf-8"))
    assert payload["gate_passed"] is False
    assert f"eval:{bad_eval.scenario_id}:no_candidate_items" in payload["issue_codes"]
    assert payload["product_readiness_claimed"] is False


def test_shadow_scorecard_script_accepts_utf8_bom_artifact(
    tmp_path: Path,
) -> None:
    artifact = build_default_recommendation_shadow_eval_artifact()
    artifact_path = tmp_path / "recommendation_shadow_eval_bom.json"
    scorecard_path = tmp_path / "recommendation_shadow_scorecard.json"
    artifact_path.write_text(
        json.dumps(artifact.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8-sig",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_recommendation_shadow_scorecard.py",
            "--artifact",
            str(artifact_path),
            "--output",
            str(scorecard_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(scorecard_path.read_text(encoding="utf-8"))
    assert payload["scorecard_type"] == "recommendation_shadow_scorecard"


def test_shadow_scorecard_script_preserves_raw_payload_gate_failures(
    tmp_path: Path,
) -> None:
    artifact = build_default_recommendation_shadow_eval_artifact()
    payload = artifact.model_dump(mode="json")
    del payload["real_runtime_effect"]
    artifact_path = tmp_path / "missing_non_claim_field.json"
    scorecard_path = tmp_path / "recommendation_shadow_scorecard.json"
    artifact_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_recommendation_shadow_scorecard.py",
            "--artifact",
            str(artifact_path),
            "--output",
            str(scorecard_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(scorecard_path.read_text(encoding="utf-8"))
    assert payload["gate_passed"] is False
    assert "artifact:missing_field:real_runtime_effect" in payload["issue_codes"]
    assert payload["summary"]["failure_count"] >= 1
    assert payload["product_readiness_claimed"] is False


def test_shadow_scorecard_script_reports_required_field_payload_failures(
    tmp_path: Path,
) -> None:
    artifact = build_default_recommendation_shadow_eval_artifact()
    payload = artifact.model_dump(mode="json")
    scenario_id = payload["evals"][0]["scenario_id"]
    del payload["evals"][0]["input_context_summary"]
    artifact_path = tmp_path / "missing_required_eval_field.json"
    scorecard_path = tmp_path / "recommendation_shadow_scorecard.json"
    artifact_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_recommendation_shadow_scorecard.py",
            "--artifact",
            str(artifact_path),
            "--output",
            str(scorecard_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Traceback" not in result.stderr
    payload = json.loads(scorecard_path.read_text(encoding="utf-8"))
    assert payload["gate_passed"] is False
    assert f"eval:{scenario_id}:missing_field:input_context_summary" in payload[
        "issue_codes"
    ]
    assert "payload:model_validation_error" in payload["issue_codes"]
    assert payload["scenario_scorecards"] == []
    assert payload["product_readiness_claimed"] is False


def _scenario(scorecard, scenario_id: str) -> dict:
    return next(
        scenario
        for scenario in scorecard.scenario_scorecards
        if scenario["scenario_id"] == scenario_id
    )
