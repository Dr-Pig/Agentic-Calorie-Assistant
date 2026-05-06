from __future__ import annotations

from pathlib import Path

from app.nutrition.application.exact_card_candidate_promotion_readiness import (
    build_exact_card_candidate_promotion_readiness,
)
from app.nutrition.application.exact_evidence_lane_policy import (
    build_exact_evidence_lane_policy_artifact,
)
from app.nutrition.application.websearch_exact_candidate_review_packet import (
    build_websearch_exact_candidate_review_packet,
)
from app.nutrition.application.websearch_extract_result_candidate_smoke import (
    build_websearch_extract_result_candidate_smoke,
)
from app.nutrition.application.websearch_selected_extract_packet_smoke import (
    build_websearch_selected_extract_packet_smoke,
)


def _extract_result() -> dict[str, object]:
    readiness = build_exact_card_candidate_promotion_readiness(
        exact_lane_artifact=build_exact_evidence_lane_policy_artifact()
    )
    selected = build_websearch_selected_extract_packet_smoke(
        exact_card_readiness_artifact=readiness
    )
    return build_websearch_extract_result_candidate_smoke(
        selected_extract_artifact=selected
    )


def test_exact_candidate_review_packet_is_review_only() -> None:
    artifact = build_websearch_exact_candidate_review_packet(
        extract_result_artifact=_extract_result(),
    )

    assert artifact["artifact_type"] == "accurate_intake_websearch_exact_candidate_review_packet_v1"
    assert artifact["status"] == "pass"
    assert artifact["classification"] == "deterministic_exact_candidate_review_packet_only"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["runtime_mutation_allowed"] is False
    assert artifact["live_websearch_used"] is False
    assert artifact["live_extract_used"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["summary"]["review_packet_count"] == 6
    assert artifact["summary"]["runtime_truth_allowed_count"] == 0
    assert artifact["summary"]["exact_card_created_count"] == 0
    assert artifact["summary"]["approval_allowed_count"] == 0
    assert artifact["next_required_slice"] == "websearch_live_extract_preflight"


def test_exact_candidate_review_packet_preserves_checklist_without_truth() -> None:
    artifact = build_websearch_exact_candidate_review_packet(
        extract_result_artifact=_extract_result(),
    )
    packet = artifact["review_packets"][0]

    assert packet["packet_type"] == "ExactCardReviewPacket"
    assert packet["truth_level"] == "review_candidate"
    assert packet["review_fields"]["kcal_value_candidate"] == 400.0
    assert packet["review_fields"]["kcal_text_present"] is True
    assert packet["review_fields"]["serving_basis_candidate"] == "per_cup"
    assert packet["approval_checklist"]["explicit_exact_card_approval_required"] is True
    assert packet["approval_allowed_by_this_packet"] is False
    assert packet["runtime_truth_allowed"] is False
    assert packet["packet_ready_truth_allowed"] is False
    assert packet["promotion_allowed"] is False
    assert packet["exact_card_created"] is False
    assert packet["runtime_mutation_allowed"] is False
    assert packet["raw_content_included"] is False
    assert packet["raw_source_rows_included"] is False


def test_exact_candidate_review_packet_blocks_extract_candidate_truth_leak() -> None:
    extract_result = _extract_result()
    extract_result["extract_result_candidates"][0]["promotion_allowed"] = True
    extract_result["extract_result_candidates"][0]["runtime_truth_allowed"] = True

    artifact = build_websearch_exact_candidate_review_packet(
        extract_result_artifact=extract_result,
    )

    assert artifact["status"] == "blocked"
    assert "extract_result_candidate_allowed_runtime_truth" in artifact["blockers"]
    assert "extract_result_candidate_allowed_promotion" in artifact["blockers"]
    assert artifact["review_packets"] == []


def test_exact_candidate_review_packet_blocks_missing_kcal_text() -> None:
    extract_result = _extract_result()
    fields = extract_result["extract_result_candidates"][0]["extracted_fields"]
    fields["kcal_text_present"] = False

    artifact = build_websearch_exact_candidate_review_packet(
        extract_result_artifact=extract_result,
    )

    assert artifact["status"] == "blocked"
    assert "extract_result_candidate_missing_kcal_text" in artifact["blockers"]


def test_exact_candidate_review_packet_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_exact_candidate_review_packet import main

    extract_result_path = tmp_path / "extract_result.json"
    output = tmp_path / "review_packet.json"
    write_json_artifact(extract_result_path, _extract_result())

    assert (
        main(
            [
                "--extract-result-artifact",
                str(extract_result_path),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_websearch_exact_candidate_review_packet_v1"
    assert artifact["status"] == "pass"
