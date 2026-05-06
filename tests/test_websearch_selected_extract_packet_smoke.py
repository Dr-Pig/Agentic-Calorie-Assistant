from __future__ import annotations

from pathlib import Path

from app.nutrition.application.exact_card_candidate_promotion_readiness import (
    build_exact_card_candidate_promotion_readiness,
)
from app.nutrition.application.exact_evidence_lane_policy import (
    build_exact_evidence_lane_policy_artifact,
)
from app.nutrition.application.websearch_cache_rate_license_wall import (
    MAX_CHUNKS_PER_SOURCE,
    build_websearch_cache_rate_license_wall,
)
from app.nutrition.application.websearch_selected_extract_packet_smoke import (
    build_websearch_selected_extract_packet_smoke,
)


def _readiness() -> dict[str, object]:
    return build_exact_card_candidate_promotion_readiness(
        exact_lane_artifact=build_exact_evidence_lane_policy_artifact()
    )


def test_selected_extract_packet_smoke_builds_compact_non_runtime_request() -> None:
    artifact = build_websearch_selected_extract_packet_smoke(
        exact_card_readiness_artifact=_readiness(),
        cache_rate_license_artifact=build_websearch_cache_rate_license_wall(),
    )

    assert artifact["artifact_type"] == "accurate_intake_websearch_selected_extract_packet_smoke_v1"
    assert artifact["status"] == "pass"
    assert artifact["classification"] == "deterministic_selected_extract_packet_smoke_only"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["runtime_mutation_allowed"] is False
    assert artifact["live_websearch_used"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["summary"]["selected_extract_packet_count"] == 6
    assert artifact["summary"]["runtime_truth_allowed_count"] == 0
    assert artifact["summary"]["raw_content_included_count"] == 0
    assert artifact["next_required_slice"] == "websearch_extract_result_candidate_smoke"


def test_selected_extract_packet_request_is_bounded_and_candidate_only() -> None:
    artifact = build_websearch_selected_extract_packet_smoke(
        exact_card_readiness_artifact=_readiness(),
    )
    packet = {packet["canonical_name"]: packet for packet in artifact["selected_extract_packets"]}[
        "Milksha pearl black tea latte nutrition PDF"
    ]
    request = packet["extract_request_policy"]

    assert packet["packet_type"] == "SelectedWebExtractRequestPacket"
    assert packet["truth_level"] == "candidate_extract_request"
    assert packet["runtime_truth_allowed"] is False
    assert packet["packet_ready_truth_allowed"] is False
    assert packet["promotion_allowed"] is False
    assert packet["exact_card_created"] is False
    assert packet["raw_source_rows_included"] is False
    assert packet["raw_content_included"] is False
    assert packet["source_boundary"]["selected_extract_is_truth"] is False
    assert request["extract_depth"] == "basic"
    assert request["chunks_per_source"] == MAX_CHUNKS_PER_SOURCE
    assert request["raw_content_truth_allowed"] is False
    assert request["runtime_truth_allowed"] is False
    assert request["urls"] == ["https://milksha.example/nutrition/pearl-black-tea-latte.pdf"]


def test_selected_extract_packet_smoke_fails_closed_on_candidate_runtime_leak() -> None:
    readiness = _readiness()
    readiness["candidates"][0]["runtime_truth_allowed"] = True

    artifact = build_websearch_selected_extract_packet_smoke(
        exact_card_readiness_artifact=readiness,
    )

    assert artifact["status"] == "blocked"
    assert "selected_extract_candidate_allowed_runtime_truth" in artifact["blockers"]
    assert artifact["next_required_slice"] == "inspect_websearch_selected_extract_packet_blockers"


def test_selected_extract_packet_smoke_fails_closed_without_candidates() -> None:
    readiness = _readiness()
    readiness["candidates"] = []
    readiness["summary"]["exact_card_candidate_count"] = 0

    artifact = build_websearch_selected_extract_packet_smoke(
        exact_card_readiness_artifact=readiness,
    )

    assert artifact["status"] == "blocked"
    assert "selected_extract_candidate_missing" in artifact["blockers"]


def test_selected_extract_packet_smoke_blocks_failed_cache_wall() -> None:
    cache_wall = build_websearch_cache_rate_license_wall()
    cache_wall["status"] = "blocked"

    artifact = build_websearch_selected_extract_packet_smoke(
        exact_card_readiness_artifact=_readiness(),
        cache_rate_license_artifact=cache_wall,
    )

    assert artifact["status"] == "blocked"
    assert "websearch_cache_rate_license_wall_not_pass" in artifact["blockers"]
    assert artifact["selected_extract_packets"] == []


def test_selected_extract_packet_smoke_blocks_cache_wall_live_provider_overclaim() -> None:
    cache_wall = build_websearch_cache_rate_license_wall()
    cache_wall["live_provider_used"] = True
    cache_wall["readiness_claimed"] = True

    artifact = build_websearch_selected_extract_packet_smoke(
        exact_card_readiness_artifact=_readiness(),
        cache_rate_license_artifact=cache_wall,
    )

    assert artifact["status"] == "blocked"
    assert "websearch_cache_rate_license_wall_used_live_provider" in artifact["blockers"]
    assert "websearch_cache_rate_license_wall_claimed_readiness" in artifact["blockers"]
    assert artifact["selected_extract_packets"] == []


def test_selected_extract_packet_smoke_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_websearch_selected_extract_packet_smoke import main

    readiness_path = tmp_path / "readiness.json"
    cache_wall_path = tmp_path / "cache_wall.json"
    output = tmp_path / "selected_extract.json"
    write_json_artifact(readiness_path, _readiness())
    write_json_artifact(cache_wall_path, build_websearch_cache_rate_license_wall())

    assert (
        main(
            [
                "--exact-card-readiness-artifact",
                str(readiness_path),
                "--cache-rate-license-artifact",
                str(cache_wall_path),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_websearch_selected_extract_packet_smoke_v1"
    assert artifact["status"] == "pass"
