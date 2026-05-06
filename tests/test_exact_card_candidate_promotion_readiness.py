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
    assert artifact["summary"]["exact_card_candidate_count"] == 4
    assert artifact["summary"]["runtime_truth_allowed_count"] == 0
    assert artifact["summary"]["promotion_allowed_count"] == 0
    assert artifact["summary"]["candidate_ready_for_review_count"] == 4
    assert artifact["next_required_slice"] == "websearch_selected_extract_packet_smoke"


def test_exact_card_candidate_promotion_readiness_reports_required_review_metadata() -> None:
    artifact = build_exact_card_candidate_promotion_readiness(
        exact_lane_artifact=build_exact_evidence_lane_policy_artifact()
    )
    cases = {candidate["case_id"]: candidate for candidate in artifact["candidates"]}
    assert set(cases) == {
        "websearch_candidate_review_fallback",
        "official_pdf_review_priority",
        "large_size_review_priority",
        "modifier_match_review_priority",
    }
    candidate = cases["official_pdf_review_priority"]

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
    assert candidate["source_url"] == "https://milksha.example/nutrition/pearl-black-tea-latte.pdf"
    assert candidate["source_class"] == "official_nutrition_pdf"


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


def test_exact_card_candidate_promotion_readiness_sanitizes_source_artifact_type() -> None:
    artifact = build_exact_card_candidate_promotion_readiness(
        exact_lane_artifact={
            "artifact_type": "raw_response_excerpt forbidden",
            "runtime_truth_changed": False,
            "runtime_mutation_allowed": False,
            "live_websearch_used": False,
            "live_provider_used": False,
        }
    )

    serialized = str(artifact)
    assert artifact["status"] == "blocked"
    assert artifact["source_artifact_type"] == "unsupported_exact_lane_artifact"
    assert "raw_response_excerpt" not in serialized
    assert "forbidden" not in serialized


def test_exact_card_candidate_promotion_readiness_blocks_leaky_candidate_metadata() -> None:
    exact_lane = build_exact_evidence_lane_policy_artifact()
    candidate = exact_lane["cases"][1]["exact_card_staging"]["candidates"][0]
    candidate["candidate_id"] = "raw_response_excerpt"
    candidate["source_url"] = "raw_response_excerpt forbidden"
    candidate["canonical_name"] = "raw_response_excerpt forbidden"
    candidate["matched_name"] = "raw_response_excerpt forbidden"
    candidate["selected_search_packet_id"] = "raw_response_excerpt"

    artifact = build_exact_card_candidate_promotion_readiness(exact_lane_artifact=exact_lane)
    serialized = str(artifact)

    assert artifact["status"] == "blocked"
    assert artifact["candidates"] == []
    assert artifact["summary"]["exact_card_candidate_count"] == 0
    assert "exact_card_candidate_invalid_candidate_id" in artifact["blockers"]
    assert "exact_card_candidate_invalid_source_url" in artifact["blockers"]
    assert "exact_card_candidate_leaky_canonical_name" in artifact["blockers"]
    assert "raw_response_excerpt" not in serialized
    assert "forbidden" not in serialized


def test_exact_card_candidate_promotion_readiness_blocks_unknown_marker_free_metadata() -> None:
    exact_lane = build_exact_evidence_lane_policy_artifact()
    candidate = exact_lane["cases"][1]["exact_card_staging"]["candidates"][0]
    candidate["candidate_id"] = "exact_card_candidate:private_payload_token_abc123"
    candidate["source_url"] = "https://private-payload-token.example/menu"
    candidate["canonical_name"] = "private payload token"
    candidate["matched_name"] = "private payload token"
    candidate["selected_search_packet_id"] = "private_payload_token_abc123"

    artifact = build_exact_card_candidate_promotion_readiness(exact_lane_artifact=exact_lane)
    serialized = str(artifact)

    assert artifact["status"] == "blocked"
    assert artifact["candidates"] == []
    assert "private_payload_token" not in serialized
    assert "private payload token" not in serialized
    assert "exact_card_candidate_invalid_candidate_id" in artifact["blockers"]
    assert "exact_card_candidate_invalid_selected_search_packet_id" in artifact["blockers"]


def test_exact_card_candidate_promotion_readiness_blocks_allowed_host_with_unknown_path_and_serving() -> None:
    exact_lane = build_exact_evidence_lane_policy_artifact()
    case = exact_lane["cases"][1]
    case["case_id"] = "private_payload_case"
    candidate = case["exact_card_staging"]["candidates"][0]
    candidate["source_url"] = "https://milksha.example/menu/private_payload_token"
    candidate["source_policy"]["serving_basis_candidate"] = "private_payload_serving"

    artifact = build_exact_card_candidate_promotion_readiness(exact_lane_artifact=exact_lane)
    serialized = str(artifact)

    assert artifact["status"] == "blocked"
    assert artifact["candidates"] == []
    assert "private_payload" not in serialized
    assert "exact_card_candidate_invalid_serving_basis_candidate" in artifact["blockers"]


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
