from __future__ import annotations

from pathlib import Path

from app.nutrition.application.websearch_exact_candidate_chain_status import (
    build_websearch_exact_candidate_chain_status,
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
from app.nutrition.application.websearch_live_runner_readiness_packet import (
    build_websearch_live_runner_readiness_packet,
    is_websearch_live_runner_readiness_clear,
)
from app.nutrition.application.websearch_selected_extract_packet_smoke import (
    build_websearch_selected_extract_packet_smoke,
)
from app.nutrition.application.exact_card_candidate_promotion_readiness import (
    build_exact_card_candidate_promotion_readiness,
)
from app.nutrition.application.exact_evidence_lane_policy import (
    build_exact_evidence_lane_policy_artifact,
)


def _selected_extract() -> dict[str, object]:
    readiness = build_exact_card_candidate_promotion_readiness(
        exact_lane_artifact=build_exact_evidence_lane_policy_artifact()
    )
    return build_websearch_selected_extract_packet_smoke(
        exact_card_readiness_artifact=readiness
    )


def _review_packet() -> dict[str, object]:
    selected = _selected_extract()
    extract = build_websearch_extract_result_candidate_smoke(
        selected_extract_artifact=selected
    )
    return build_websearch_exact_candidate_review_packet(extract_result_artifact=extract)


def _clear_inputs() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    review = _review_packet()
    preflight = build_websearch_live_extract_preflight(exact_review_packet_artifact=review)
    chain = build_websearch_exact_candidate_chain_status(
        exact_review_packet_artifact=review,
        preflight_artifact=preflight,
    )
    return review, preflight, chain


def test_websearch_live_runner_readiness_packet_passes_without_live() -> None:
    review, preflight, chain = _clear_inputs()

    artifact = build_websearch_live_runner_readiness_packet(
        review_packet_artifact=review,
        preflight_artifact=preflight,
        exact_candidate_chain_status_artifact=chain,
    )

    assert artifact["artifact_type"] == "accurate_intake_websearch_live_runner_readiness_packet_v1"
    assert artifact["status"] == "pass"
    assert artifact["ready_for_grokfast_websearch_packet_live_diagnostic"] is True
    assert artifact["live_provider_used"] is False
    assert artifact["live_websearch_used"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["runtime_mutation_allowed"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["provider_readiness_checked"] is False
    assert artifact["runner_contract"]["requires_explicit_allow_live_flag"] is True
    assert is_websearch_live_runner_readiness_clear(artifact) is True


def test_websearch_live_runner_readiness_blocks_preflight_not_clear() -> None:
    review, preflight, chain = _clear_inputs()
    preflight["ready_for_live_extract_diagnostic"] = False

    artifact = build_websearch_live_runner_readiness_packet(
        review_packet_artifact=review,
        preflight_artifact=preflight,
        exact_candidate_chain_status_artifact=chain,
    )

    assert artifact["status"] == "blocked"
    assert "websearch_live_extract_preflight_not_clear" in artifact["blockers"]
    assert is_websearch_live_runner_readiness_clear(artifact) is False


def test_websearch_live_runner_readiness_blocks_chain_not_clear() -> None:
    review, preflight, chain = _clear_inputs()
    chain["ready_for_live_diagnostic"] = False

    artifact = build_websearch_live_runner_readiness_packet(
        review_packet_artifact=review,
        preflight_artifact=preflight,
        exact_candidate_chain_status_artifact=chain,
    )

    assert artifact["status"] == "blocked"
    assert "websearch_exact_candidate_chain_status_not_clear" in artifact["blockers"]


def test_websearch_live_runner_readiness_blocks_review_packet_mismatch() -> None:
    review, preflight, chain = _clear_inputs()
    preflight["review_packet_refs"][0]["packet_id"] = "different-review-packet"

    artifact = build_websearch_live_runner_readiness_packet(
        review_packet_artifact=review,
        preflight_artifact=preflight,
        exact_candidate_chain_status_artifact=chain,
    )

    assert artifact["status"] == "blocked"
    assert "websearch_live_preflight_review_packet_mismatch" in artifact["blockers"]


def test_websearch_live_runner_readiness_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_live_runner_readiness_packet import main

    review, preflight, chain = _clear_inputs()
    review_path = tmp_path / "review.json"
    preflight_path = tmp_path / "preflight.json"
    chain_path = tmp_path / "chain.json"
    output = tmp_path / "readiness.json"
    write_json_artifact(review_path, review)
    write_json_artifact(preflight_path, preflight)
    write_json_artifact(chain_path, chain)

    assert (
        main(
            [
                "--review-packet-artifact",
                str(review_path),
                "--preflight-artifact",
                str(preflight_path),
                "--exact-candidate-chain-status-artifact",
                str(chain_path),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output)
    assert artifact["status"] == "pass"
    assert artifact["ready_for_grokfast_websearch_packet_live_diagnostic"] is True
