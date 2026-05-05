from __future__ import annotations

from pathlib import Path

from app.nutrition.application.exact_card_candidate_promotion_readiness import (
    build_exact_card_candidate_promotion_readiness,
)
from app.nutrition.application.exact_evidence_lane_policy import (
    build_exact_evidence_lane_policy_artifact,
)


def test_exact_card_candidate_promotion_readiness_keeps_candidates_non_runtime() -> None:
    artifact = build_exact_card_candidate_promotion_readiness(
        exact_lane_artifact=build_exact_evidence_lane_policy_artifact()
    )

    assert artifact["artifact_type"] == "accurate_intake_exact_card_candidate_promotion_readiness_v1"
    assert artifact["status"] == "pass"
    assert artifact["classification"] == "deterministic_exact_candidate_readiness_only"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["live_websearch_used"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["summary"]["exact_card_candidate_count"] == 1
    assert artifact["summary"]["runtime_truth_allowed_count"] == 0
    assert artifact["summary"]["promotion_allowed_count"] == 0
    assert artifact["next_required_slice"] == "websearch_selected_extract_packet_smoke"


def test_exact_card_candidate_promotion_readiness_reports_required_review_metadata() -> None:
    artifact = build_exact_card_candidate_promotion_readiness(
        exact_lane_artifact=build_exact_evidence_lane_policy_artifact()
    )
    candidate = artifact["candidates"][0]

    assert candidate["candidate_id"].startswith("exact_card_candidate:")
    assert candidate["readiness_status"] == "selected_extract_candidate_ready_for_review"
    assert candidate["runtime_truth_allowed"] is False
    assert candidate["promotion_allowed"] is False
    assert candidate["promotion_decision"] == "blocked_until_explicit_exact_card_approval"
    assert candidate["required_before_runtime_truth"] == [
        "selected_extract_content",
        "serving_basis_confirmation",
        "kcal_field_extraction",
        "approval_metadata",
    ]
    assert candidate["source_url"] == "https://milksha.example/menu/pearl-black-tea-latte"


def test_exact_card_candidate_promotion_readiness_fails_closed_on_runtime_truth_leak() -> None:
    exact_lane = build_exact_evidence_lane_policy_artifact()
    candidate = exact_lane["cases"][1]["exact_card_staging"]["candidates"][0]
    candidate["runtime_truth_allowed"] = True

    artifact = build_exact_card_candidate_promotion_readiness(exact_lane_artifact=exact_lane)

    assert artifact["status"] == "blocked"
    assert "exact_card_candidate_runtime_truth_leak" in artifact["blockers"]
    assert artifact["next_required_slice"] == "inspect_exact_card_candidate_readiness_blockers"


def test_exact_card_candidate_promotion_readiness_fails_closed_without_candidates() -> None:
    exact_lane = build_exact_evidence_lane_policy_artifact()
    for case in exact_lane["cases"]:
        case["exact_card_staging"] = {"candidate_count": 0, "candidates": []}

    artifact = build_exact_card_candidate_promotion_readiness(exact_lane_artifact=exact_lane)

    assert artifact["status"] == "blocked"
    assert artifact["summary"]["exact_card_candidate_count"] == 0
    assert "exact_card_candidate_missing" in artifact["blockers"]
    assert artifact["next_required_slice"] == "inspect_exact_card_candidate_readiness_blockers"


def test_exact_card_candidate_promotion_readiness_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_exact_card_candidate_promotion_readiness import main

    exact_lane_path = tmp_path / "exact_lane.json"
    output = tmp_path / "readiness.json"
    write_json_artifact(exact_lane_path, build_exact_evidence_lane_policy_artifact())

    assert main(["--exact-lane-artifact", str(exact_lane_path), "--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_exact_card_candidate_promotion_readiness_v1"
    assert artifact["status"] == "pass"
