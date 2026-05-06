from __future__ import annotations

from pathlib import Path

from app.nutrition.application.exact_evidence_lane_status_packet import (
    build_exact_evidence_lane_status_packet,
)
from app.nutrition.application.websearch_exact_candidate_chain_status import (
    build_websearch_exact_candidate_chain_status,
)


def _websearch_status_packet() -> dict:
    return {
        "artifact_type": "accurate_intake_websearch_candidate_lane_status_packet_v1",
        "upstream_gate": {"status": "blocked_on_fooddb_upstream_gate", "blocked": True},
        "next_required_slices": ["await_manager_contract_owner_repair"],
    }


def test_exact_evidence_lane_status_packet_summarizes_exact_lane_without_live_probe() -> None:
    artifact = build_exact_evidence_lane_status_packet()

    assert artifact["artifact_type"] == "accurate_intake_exact_evidence_lane_status_packet_v1"
    assert artifact["classification"] == "deterministic_exact_evidence_lane_status_only"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["live_websearch_used"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["summary"]["local_exact_preferred_count"] >= 1
    assert artifact["summary"]["websearch_candidate_review_count"] >= 1
    assert artifact["summary"]["exact_card_staging_candidate_count"] >= 1
    assert artifact["summary"]["upstream_websearch_gate_status"] == "not_provided"
    assert artifact["next_required_slices"] == ["inspect_websearch_status_packet"]


def test_exact_evidence_lane_status_packet_blocks_when_websearch_upstream_not_ready() -> None:
    artifact = build_exact_evidence_lane_status_packet(
        websearch_status_packet=_websearch_status_packet()
    )

    assert artifact["summary"]["upstream_websearch_gate_status"] == "blocked_on_websearch_upstream_gate"
    assert artifact["summary"]["upstream_websearch_next_required_slice"] == "await_manager_contract_owner_repair"
    assert artifact["next_required_slices"] == ["await_manager_contract_owner_repair"]


def test_exact_evidence_lane_status_packet_requires_exact_candidate_chain_after_websearch() -> None:
    artifact = build_exact_evidence_lane_status_packet(
        websearch_status_packet={
            "artifact_type": "accurate_intake_websearch_candidate_lane_status_packet_v1",
            "upstream_gate": {"status": "clear_for_websearch_lane", "blocked": False},
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        }
    )

    assert artifact["summary"]["upstream_websearch_gate_status"] == "clear_for_exact_websearch_followthrough"
    assert artifact["summary"]["exact_candidate_chain_status"] == "not_provided"
    assert artifact["next_required_slices"] == ["inspect_websearch_exact_candidate_chain_status"]


def test_exact_evidence_lane_status_packet_allows_when_websearch_and_chain_clear() -> None:
    artifact = build_exact_evidence_lane_status_packet(
        websearch_status_packet={
            "artifact_type": "accurate_intake_websearch_candidate_lane_status_packet_v1",
            "upstream_gate": {"status": "clear_for_websearch_lane", "blocked": False},
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        },
        exact_candidate_chain_status_packet=build_websearch_exact_candidate_chain_status(),
    )

    assert artifact["summary"]["upstream_websearch_gate_status"] == "clear_for_exact_websearch_followthrough"
    assert artifact["summary"]["exact_candidate_chain_status"] == (
        "clear_for_websearch_exact_candidate_chain"
    )
    assert artifact["next_required_slices"] == ["grokfast_websearch_packet_live_diagnostic"]


def test_exact_evidence_lane_status_packet_blocks_misaligned_websearch_live_pointer() -> None:
    artifact = build_exact_evidence_lane_status_packet(
        websearch_status_packet={
            "artifact_type": "accurate_intake_websearch_candidate_lane_status_packet_v1",
            "upstream_gate": {"status": "blocked_on_fooddb_upstream_gate", "blocked": True},
            "next_required_slices": ["grokfast_websearch_packet_live_diagnostic"],
        }
    )

    assert artifact["summary"]["upstream_websearch_gate_status"] == "blocked_on_websearch_upstream_gate"
    assert artifact["summary"]["upstream_websearch_next_required_slice"] == "inspect_websearch_status_packet"
    assert artifact["next_required_slices"] == ["inspect_websearch_status_packet"]


def test_exact_evidence_lane_status_packet_sanitizes_untrusted_next_slice() -> None:
    artifact = build_exact_evidence_lane_status_packet(
        websearch_status_packet={
            "artifact_type": "accurate_intake_websearch_candidate_lane_status_packet_v1",
            "upstream_gate": {"status": "clear_for_websearch_lane", "blocked": False},
            "next_required_slices": ["raw_response_excerpt forbidden"],
        }
    )

    serialized = str(artifact)
    assert "raw_response_excerpt" not in serialized
    assert "forbidden" not in serialized
    assert artifact["summary"]["upstream_websearch_next_required_slice"] == "inspect_websearch_status_packet"
    assert artifact["next_required_slices"] == ["inspect_websearch_status_packet"]


def test_exact_evidence_lane_status_packet_rejects_unexpected_websearch_status_type() -> None:
    try:
        build_exact_evidence_lane_status_packet(
            websearch_status_packet={"artifact_type": "wrong", "next_required_slices": []}
        )
    except ValueError as exc:
        assert "unsupported_exact_lane_websearch_status_packet" in str(exc)
    else:
        raise AssertionError("unexpected WebSearch status packet type must fail")


def test_exact_evidence_lane_status_packet_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.build_accurate_intake_exact_evidence_lane_status_packet import main

    websearch_input = tmp_path / "websearch_status.json"
    output = tmp_path / "exact_lane_status.json"
    write_json_artifact(websearch_input, _websearch_status_packet())

    assert (
        main(
            [
                "--websearch-status-packet",
                str(websearch_input),
                "--output",
                str(output),
            ]
        )
        == 0
    )

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_exact_evidence_lane_status_packet_v1"
    assert artifact["next_required_slices"] == ["await_manager_contract_owner_repair"]


def test_exact_evidence_lane_status_packet_has_no_live_or_shared_contract_imports() -> None:
    source_paths = [
        Path("app/nutrition/application/exact_evidence_lane_status_packet.py"),
        Path("scripts/build_accurate_intake_exact_evidence_lane_status_packet.py"),
    ]
    forbidden = [
        "BuilderSpaceAdapter",
        "Tavily",
        "allow_live",
        "run_live",
        "ManagerContextPacket",
        "NutritionEvidenceStorePort",
    ]
    for path in source_paths:
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source
