from __future__ import annotations

from pathlib import Path

from app.nutrition.application.exact_card_candidate_promotion_readiness import (
    build_exact_card_candidate_promotion_readiness,
)
from app.nutrition.application.exact_evidence_lane_policy import (
    build_exact_evidence_lane_policy_artifact,
)
from app.nutrition.application.exact_evidence_lane_status_packet import (
    build_exact_evidence_lane_status_packet,
)
from app.nutrition.application.websearch_candidate_lane_status_packet import (
    build_websearch_candidate_lane_status_packet,
)
from app.nutrition.application.websearch_exact_candidate_chain_status import (
    build_websearch_exact_candidate_chain_status,
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


def _selected_extract() -> dict[str, object]:
    readiness = build_exact_card_candidate_promotion_readiness(
        exact_lane_artifact=build_exact_evidence_lane_policy_artifact()
    )
    return build_websearch_selected_extract_packet_smoke(
        exact_card_readiness_artifact=readiness
    )


def _extract_result() -> dict[str, object]:
    return build_websearch_extract_result_candidate_smoke(
        selected_extract_artifact=_selected_extract()
    )


def _review_packet() -> dict[str, object]:
    return build_websearch_exact_candidate_review_packet(
        extract_result_artifact=_extract_result()
    )


def _websearch_lane_ready() -> dict[str, object]:
    return {
        **build_websearch_candidate_lane_status_packet(),
        "upstream_gate": {"status": "clear_for_websearch_lane", "blocked": False},
        "manager_contract_gate": {"status": "clear_for_websearch_lane", "blocked": False},
        "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
    }


def test_exact_candidate_chain_status_proves_source_chain_without_truth() -> None:
    artifact = build_websearch_exact_candidate_chain_status()

    assert artifact["artifact_type"] == "accurate_intake_websearch_exact_candidate_chain_status_v1"
    assert artifact["status"] == "pass"
    assert artifact["classification"] == "deterministic_websearch_exact_candidate_chain_status_only"
    assert artifact["ready_for_live_diagnostic"] is True
    assert artifact["ready_for_runtime_truth"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["runtime_mutation_allowed"] is False
    assert artifact["live_websearch_used"] is False
    assert artifact["live_extract_used"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["summary"]["selected_extract_packet_count"] == 4
    assert artifact["summary"]["extract_result_candidate_count"] == 4
    assert artifact["summary"]["review_packet_count"] == 4
    assert artifact["summary"]["preflight_review_ref_count"] == 4
    assert artifact["next_required_slice"] == "grokfast_websearch_packet_live_diagnostic"


def test_exact_candidate_chain_status_blocks_selected_extract_live_or_truth_leak() -> None:
    selected = _selected_extract()
    selected["live_websearch_used"] = True
    selected["selected_extract_packets"][0]["runtime_truth_allowed"] = True

    artifact = build_websearch_exact_candidate_chain_status(
        selected_extract_artifact=selected,
    )

    assert artifact["status"] == "blocked"
    assert "selected_extract_artifact_used_live_websearch" in artifact["blockers"]
    assert "selected_extract_packet_allowed_runtime_truth" in artifact["blockers"]
    assert artifact["ready_for_live_diagnostic"] is False


def test_exact_candidate_chain_status_blocks_broken_source_lineage() -> None:
    extract = _extract_result()
    extract["extract_result_candidates"][0]["source_selected_extract_packet_id"] = (
        "unknown_selected_packet"
    )

    artifact = build_websearch_exact_candidate_chain_status(
        selected_extract_artifact=_selected_extract(),
        extract_result_artifact=extract,
    )

    assert artifact["status"] == "blocked"
    assert "extract_result_candidate_missing_selected_extract_source" in artifact["blockers"]


def test_exact_candidate_chain_status_blocks_missing_source_lineage_ref() -> None:
    extract = _extract_result()
    extract["extract_result_candidates"][0].pop("source_selected_extract_packet_id")

    artifact = build_websearch_exact_candidate_chain_status(
        selected_extract_artifact=_selected_extract(),
        extract_result_artifact=extract,
    )

    assert artifact["status"] == "blocked"
    assert "extract_result_candidate_missing_selected_extract_source" in artifact["blockers"]


def test_exact_candidate_chain_status_blocks_explicit_empty_artifact() -> None:
    artifact = build_websearch_exact_candidate_chain_status(
        selected_extract_artifact={},
    )

    assert artifact["status"] == "blocked"
    assert "selected_extract_artifact_not_pass" in artifact["blockers"]
    assert "selected_extract_packet_missing" in artifact["blockers"]


def test_exact_candidate_chain_status_blocks_unsupported_artifact_type() -> None:
    selected = _selected_extract()
    selected["artifact_type"] = "wrong"

    artifact = build_websearch_exact_candidate_chain_status(
        selected_extract_artifact=selected,
    )

    assert artifact["status"] == "blocked"
    assert "selected_extract_artifact_unsupported_type" in artifact["blockers"]


def test_exact_candidate_chain_status_blocks_preflight_review_packet_mismatch() -> None:
    from app.nutrition.application.websearch_live_extract_preflight import (
        build_websearch_live_extract_preflight,
    )

    review = _review_packet()
    preflight = build_websearch_live_extract_preflight(exact_review_packet_artifact=review)
    preflight["review_packet_refs"][0]["packet_id"] = "unknown_review_packet"

    artifact = build_websearch_exact_candidate_chain_status(
        exact_review_packet_artifact=review,
        preflight_artifact=preflight,
    )

    assert artifact["status"] == "blocked"
    assert "preflight_review_packet_ref_mismatch" in artifact["blockers"]


def test_exact_lane_status_requires_exact_candidate_chain_after_websearch_lane() -> None:
    artifact = build_exact_evidence_lane_status_packet(
        websearch_status_packet=_websearch_lane_ready(),
    )

    assert artifact["summary"]["upstream_websearch_gate_status"] == (
        "clear_for_exact_websearch_followthrough"
    )
    assert artifact["summary"]["exact_candidate_chain_status"] == "not_provided"
    assert artifact["next_required_slices"] == ["inspect_websearch_exact_candidate_chain_status"]


def test_exact_lane_status_allows_live_diagnostic_only_when_chain_is_clear() -> None:
    artifact = build_exact_evidence_lane_status_packet(
        websearch_status_packet=_websearch_lane_ready(),
        exact_candidate_chain_status_packet=build_websearch_exact_candidate_chain_status(),
    )

    assert artifact["summary"]["upstream_websearch_gate_status"] == (
        "clear_for_exact_websearch_followthrough"
    )
    assert artifact["summary"]["exact_candidate_chain_status"] == (
        "clear_for_websearch_exact_candidate_chain"
    )
    assert artifact["next_required_slices"] == ["grokfast_websearch_packet_live_diagnostic"]


def test_exact_candidate_chain_status_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_exact_candidate_chain_status import main

    selected_path = tmp_path / "selected.json"
    extract_path = tmp_path / "extract.json"
    review_path = tmp_path / "review.json"
    output = tmp_path / "chain.json"
    selected = _selected_extract()
    extract = build_websearch_extract_result_candidate_smoke(
        selected_extract_artifact=selected
    )
    review = build_websearch_exact_candidate_review_packet(
        extract_result_artifact=extract
    )
    write_json_artifact(selected_path, selected)
    write_json_artifact(extract_path, extract)
    write_json_artifact(review_path, review)

    assert (
        main(
            [
                "--selected-extract-artifact",
                str(selected_path),
                "--extract-result-artifact",
                str(extract_path),
                "--exact-review-packet-artifact",
                str(review_path),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_websearch_exact_candidate_chain_status_v1"
    assert artifact["status"] == "pass"
