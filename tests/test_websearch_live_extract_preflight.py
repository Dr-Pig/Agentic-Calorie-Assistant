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
from app.nutrition.application.websearch_live_extract_preflight import (
    build_websearch_live_extract_preflight,
)
from app.nutrition.application.websearch_selected_extract_packet_smoke import (
    build_websearch_selected_extract_packet_smoke,
)


def _review_packet() -> dict[str, object]:
    readiness = build_exact_card_candidate_promotion_readiness(
        exact_lane_artifact=build_exact_evidence_lane_policy_artifact()
    )
    selected = build_websearch_selected_extract_packet_smoke(
        exact_card_readiness_artifact=readiness
    )
    extract_result = build_websearch_extract_result_candidate_smoke(
        selected_extract_artifact=selected
    )
    return build_websearch_exact_candidate_review_packet(
        extract_result_artifact=extract_result
    )


def test_live_extract_preflight_enables_diagnostic_only_not_truth() -> None:
    artifact = build_websearch_live_extract_preflight(
        exact_review_packet_artifact=_review_packet(),
    )

    assert artifact["artifact_type"] == "accurate_intake_websearch_live_extract_preflight_v1"
    assert artifact["status"] == "pass"
    assert artifact["classification"] == "deterministic_live_extract_preflight_only"
    assert artifact["ready_for_live_extract_diagnostic"] is True
    assert artifact["ready_for_runtime_truth"] is False
    assert artifact["live_websearch_used"] is False
    assert artifact["live_extract_used"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["runtime_mutation_allowed"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["summary"]["review_packet_count"] == 1
    assert artifact["summary"]["ready_for_runtime_truth_count"] == 0
    assert artifact["next_required_slice"] == "grokfast_websearch_packet_live_diagnostic"


def test_live_extract_preflight_contract_requires_explicit_live_flag_and_cache() -> None:
    artifact = build_websearch_live_extract_preflight(
        exact_review_packet_artifact=_review_packet(),
    )
    contract = artifact["diagnostic_contract"]

    assert contract["live_call_allowed_by_this_artifact"] is False
    assert contract["requires_explicit_allow_live_flag"] is True
    assert contract["max_search_attempts"] == 2
    assert contract["max_extract_urls_per_case"] == 1
    assert contract["max_chunks_per_source"] == 3
    assert contract["cache_required"] is True
    assert contract["raw_content_allowed_in_manager_context"] is False
    assert contract["extract_result_role"] == "review_candidate_only"
    assert contract["ledger_mutation_allowed"] is False
    assert contract["exact_card_creation_allowed"] is False
    assert artifact["review_packet_refs"][0]["packet_digest"]


def test_live_extract_preflight_blocks_review_packet_truth_leak() -> None:
    review_packet = _review_packet()
    review_packet["review_packets"][0]["runtime_truth_allowed"] = True
    review_packet["summary"]["runtime_truth_allowed_count"] = 1

    artifact = build_websearch_live_extract_preflight(
        exact_review_packet_artifact=review_packet,
    )

    assert artifact["status"] == "blocked"
    assert "exact_review_packet_artifact_summary_runtime_truth_allowed" in artifact["blockers"]
    assert "exact_review_packet_allowed_runtime_truth" in artifact["blockers"]
    assert artifact["ready_for_live_extract_diagnostic"] is False


def test_live_extract_preflight_blocks_review_artifact_live_or_readiness_overclaim() -> None:
    review_packet = _review_packet()
    review_packet["live_extract_used"] = True
    review_packet["readiness_claimed"] = True

    artifact = build_websearch_live_extract_preflight(
        exact_review_packet_artifact=review_packet,
    )

    assert artifact["status"] == "blocked"
    assert "exact_review_packet_artifact_used_live_extract" in artifact["blockers"]
    assert "exact_review_packet_artifact_claimed_readiness" in artifact["blockers"]


def test_live_extract_preflight_blocks_missing_kcal_value_candidate() -> None:
    review_packet = _review_packet()
    review_packet["review_packets"][0]["review_fields"].pop("kcal_value_candidate")

    artifact = build_websearch_live_extract_preflight(
        exact_review_packet_artifact=review_packet,
    )

    assert artifact["status"] == "blocked"
    assert "exact_review_packet_missing_kcal_candidate" in artifact["blockers"]
    assert artifact["ready_for_live_extract_diagnostic"] is False


def test_live_extract_preflight_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_live_extract_preflight import main

    review_packet_path = tmp_path / "review_packet.json"
    output = tmp_path / "preflight.json"
    write_json_artifact(review_packet_path, _review_packet())

    assert (
        main(
            [
                "--review-packet-artifact",
                str(review_packet_path),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_websearch_live_extract_preflight_v1"
    assert artifact["status"] == "pass"
