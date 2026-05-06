from __future__ import annotations

from pathlib import Path

from app.nutrition.application.exact_card_candidate_promotion_readiness import (
    build_exact_card_candidate_promotion_readiness,
)
from app.nutrition.application.exact_evidence_lane_policy import (
    build_exact_evidence_lane_policy_artifact,
)
from app.nutrition.application.websearch_extract_result_candidate_smoke import (
    build_websearch_extract_result_candidate_smoke,
)
from app.nutrition.application.websearch_selected_extract_packet_smoke import (
    build_websearch_selected_extract_packet_smoke,
)


def _selected_extract() -> dict[str, object]:
    readiness = build_exact_card_candidate_promotion_readiness(
        exact_lane_artifact=build_exact_evidence_lane_policy_artifact()
    )
    return build_websearch_selected_extract_packet_smoke(
        exact_card_readiness_artifact=readiness
    )


def test_extract_result_candidate_smoke_builds_review_candidate_only() -> None:
    artifact = build_websearch_extract_result_candidate_smoke(
        selected_extract_artifact=_selected_extract(),
    )

    assert artifact["artifact_type"] == "accurate_intake_websearch_extract_result_candidate_smoke_v1"
    assert artifact["status"] == "pass"
    assert artifact["classification"] == "deterministic_extract_result_candidate_smoke_only"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["runtime_mutation_allowed"] is False
    assert artifact["live_websearch_used"] is False
    assert artifact["live_extract_used"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["summary"]["extract_result_candidate_count"] == 6
    assert artifact["summary"]["runtime_truth_allowed_count"] == 0
    assert artifact["summary"]["exact_card_created_count"] == 0
    assert artifact["next_required_slice"] == "websearch_exact_candidate_review_packet"


def test_extract_result_candidate_has_fields_but_no_truth_or_raw_content() -> None:
    artifact = build_websearch_extract_result_candidate_smoke(
        selected_extract_artifact=_selected_extract(),
    )
    candidate = artifact["extract_result_candidates"][0]

    assert candidate["candidate_role"] == "websearch_extract_result_review_candidate"
    assert candidate["promotion_status"] == "review_candidate_only"
    assert candidate["extracted_fields"]["kcal_value_candidate"] == 400.0
    assert candidate["extracted_fields"]["kcal_text_present"] is True
    assert candidate["extracted_fields"]["serving_basis_candidate"] == "per_cup"
    assert candidate["runtime_truth_allowed"] is False
    assert candidate["packet_ready_truth_allowed"] is False
    assert candidate["promotion_allowed"] is False
    assert candidate["exact_card_created"] is False
    assert candidate["runtime_mutation_allowed"] is False
    assert candidate["raw_content_included"] is False
    assert candidate["raw_source_rows_included"] is False
    assert candidate["approval_metadata"]["approval_mode"] == "none"


def test_extract_result_candidate_smoke_blocks_selected_extract_runtime_leak() -> None:
    selected = _selected_extract()
    selected["selected_extract_packets"][0]["runtime_truth_allowed"] = True

    artifact = build_websearch_extract_result_candidate_smoke(
        selected_extract_artifact=selected,
    )

    assert artifact["status"] == "blocked"
    assert "selected_extract_packet_allowed_runtime_truth" in artifact["blockers"]


def test_extract_result_candidate_smoke_blocks_mixed_selected_extract_packet_leak() -> None:
    selected = _selected_extract()
    unsafe = dict(selected["selected_extract_packets"][0])
    unsafe["packet_id"] = "unsafe_selected_extract"
    unsafe["promotion_allowed"] = True
    unsafe["raw_content_included"] = True
    unsafe["source_boundary"] = {
        **unsafe["source_boundary"],
        "selected_extract_is_truth": True,
    }
    selected["selected_extract_packets"].append(unsafe)

    artifact = build_websearch_extract_result_candidate_smoke(
        selected_extract_artifact=selected,
    )

    assert artifact["status"] == "blocked"
    assert "selected_extract_packet_allowed_promotion" in artifact["blockers"]
    assert "selected_extract_packet_included_raw_content" in artifact["blockers"]
    assert "selected_extract_packet_source_boundary_claimed_truth" in artifact["blockers"]
    assert artifact["extract_result_candidates"] == []


def test_extract_result_candidate_smoke_blocks_raw_content_in_extract_result() -> None:
    selected = _selected_extract()
    packet = selected["selected_extract_packets"][0]

    artifact = build_websearch_extract_result_candidate_smoke(
        selected_extract_artifact=selected,
        extract_result_rows=[
            {
                "selected_extract_packet_id": packet["packet_id"],
                "source_url": packet["source_url"],
                "serving_basis_candidate": "per_cup",
                "kcal_value_candidate": 400,
                "identity_text_present": True,
                "raw_content": "full page content must not enter this packet",
            }
        ],
    )

    assert artifact["status"] == "blocked"
    assert "extract_result_row_included_raw_content" in artifact["blockers"]
    assert artifact["extract_result_candidates"] == []


def test_extract_result_candidate_smoke_blocks_missing_kcal_candidate() -> None:
    selected = _selected_extract()
    packet = selected["selected_extract_packets"][0]

    artifact = build_websearch_extract_result_candidate_smoke(
        selected_extract_artifact=selected,
        extract_result_rows=[
            {
                "selected_extract_packet_id": packet["packet_id"],
                "source_url": packet["source_url"],
                "serving_basis_candidate": "per_cup",
                "identity_text_present": True,
            }
        ],
    )

    assert artifact["status"] == "blocked"
    assert "extract_result_row_missing_kcal_candidate" in artifact["blockers"]


def test_extract_result_candidate_smoke_blocks_missing_kcal_text_evidence() -> None:
    selected = _selected_extract()
    packet = selected["selected_extract_packets"][0]

    artifact = build_websearch_extract_result_candidate_smoke(
        selected_extract_artifact=selected,
        extract_result_rows=[
            {
                "selected_extract_packet_id": packet["packet_id"],
                "source_url": packet["source_url"],
                "serving_basis_candidate": "per_cup",
                "kcal_value_candidate": 400,
                "kcal_text_present": False,
                "identity_text_present": True,
            }
        ],
    )

    assert artifact["status"] == "blocked"
    assert "extract_result_row_missing_kcal_text" in artifact["blockers"]


def test_extract_result_candidate_smoke_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_extract_result_candidate_smoke import main

    selected_extract_path = tmp_path / "selected_extract.json"
    output = tmp_path / "extract_result.json"
    write_json_artifact(selected_extract_path, _selected_extract())

    assert (
        main(
            [
                "--selected-extract-artifact",
                str(selected_extract_path),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_websearch_extract_result_candidate_smoke_v1"
    assert artifact["status"] == "pass"
