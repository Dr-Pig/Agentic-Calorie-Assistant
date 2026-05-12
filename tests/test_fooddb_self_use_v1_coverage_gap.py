from __future__ import annotations

from pathlib import Path

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.application.fooddb_self_use_v1_coverage_gap import (
    build_fooddb_self_use_v1_coverage_gap,
)


def _approved_artifact() -> dict:
    return build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/accurate_intake_approved_packet_ready_fooddb_artifact.json",
        selection_profile="full_current_shell",
    )


def test_fooddb_self_use_v1_gap_reports_current_packet_ready_counts_against_1000_target() -> None:
    report = build_fooddb_self_use_v1_coverage_gap(
        approved_packet_ready_artifact=_approved_artifact(),
    )

    assert report["artifact_type"] == "fooddb_self_use_v1_1000_packet_ready_coverage_gap"
    assert report["target"]["packet_ready_item_count"] == 1000
    assert report["target"]["lane_counts"] == {
        "exact_item_card": 250,
        "generic_common_serving": 400,
        "listed_component": 350,
    }
    assert report["current"]["packet_ready_item_count"] == 194
    assert report["current"]["lane_counts"] == {
        "exact_item_card": 46,
        "generic_common_serving": 74,
        "listed_component": 74,
    }
    assert report["gap"]["packet_ready_item_count"] == 806
    assert report["gap"]["lane_counts"] == {
        "exact_item_card": 204,
        "generic_common_serving": 326,
        "listed_component": 276,
    }
    assert report["gap"]["exact_macro_complete_count"] == 154
    assert report["status"] == "below_target"


def test_fooddb_self_use_v1_gap_is_report_only_and_preserves_boundaries() -> None:
    report = build_fooddb_self_use_v1_coverage_gap(
        approved_packet_ready_artifact=_approved_artifact(),
    )

    assert report["runtime_truth_changed"] is False
    assert report["fooddb_truth_updated"] is False
    assert report["product_readiness_claimed"] is False
    assert report["private_self_use_approved"] is False
    assert "no_fooddb_promotion" in report["non_claims"]
    assert "no_manager_semantic_change" in report["non_claims"]


def test_fooddb_self_use_v1_gap_cli_writes_roundtrippable_artifact(tmp_path: Path) -> None:
    output = tmp_path / "coverage_gap.json"

    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_fooddb_self_use_v1_coverage_gap import main

    assert main(["--build-current-artifact", "--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert artifact["status"] == "below_target"
    assert artifact["gap"]["packet_ready_item_count"] == 806
