from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_fixture_evidence_packet_emulator import (
    build_fixture_evidence_packet_emulator_artifact,
)
from scripts import build_accurate_intake_fixture_evidence_packet_emulator as module


def test_fixture_evidence_packet_emulator_covers_fooddb_and_websearch_shapes_without_truth_promotion() -> None:
    artifact = build_fixture_evidence_packet_emulator_artifact()

    assert artifact["artifact_type"] == "accurate_intake_fixture_evidence_packet_emulator"
    assert artifact["status"] == "fixture_packet_emulator_ready"
    assert artifact["scenario_ids"] == [
        "approved_common_serving_anchor_fixture",
        "approved_exact_card_fixture",
        "missing_evidence",
        "ambiguous_candidates",
        "rejected_validator_only_source",
        "websearch_candidate_not_approved",
    ]
    assert artifact["fixture_evidence_used"] is True
    assert artifact["fixture_packet_truth"] is False
    assert artifact["fooddb_evidence_used"] is False
    assert artifact["websearch_evidence_used"] is False
    assert artifact["web_tavily_used"] is False
    assert artifact["raw_sources_read"] is False
    assert artifact["promotion_policy_changed"] is False
    assert artifact["runtime_truth_changed"] is False
    assert artifact["ready_for_fdb_integration"] is False

    for scenario in artifact["scenarios"]:
        assert scenario["fixture_or_real"] == "fixture"
        assert scenario["runtime_truth_allowed"] is False
        assert scenario["product_loop_consumption"] == "diagnostic_only"


def test_fixture_evidence_packet_emulator_validates_no_fixture_becomes_runtime_truth() -> None:
    artifact = build_fixture_evidence_packet_emulator_artifact(
        overrides={
            "approved_exact_card_fixture": {
                "runtime_truth_allowed": True,
                "fixture_or_real": "real",
            }
        }
    )

    assert artifact["status"] == "fail"
    assert "approved_exact_card_fixture.runtime_truth_allowed" in artifact["blockers"]
    assert "approved_exact_card_fixture.fixture_or_real" in artifact["blockers"]


def test_fixture_evidence_packet_emulator_websearch_case_is_candidate_only() -> None:
    artifact = build_fixture_evidence_packet_emulator_artifact()
    websearch = {
        scenario["scenario_id"]: scenario for scenario in artifact["scenarios"]
    }["websearch_candidate_not_approved"]

    assert websearch["source_family"] == "websearch_fixture"
    assert websearch["packet_status"] == "candidate_not_approved"
    assert websearch["manager_consumable"] is False
    assert websearch["web_tavily_used"] is False
    assert websearch["requires_human_approval"] is True


def test_fixture_evidence_packet_emulator_cli_writes_artifact(tmp_path: Path, capsys) -> None:
    output_path = tmp_path / "fixture-packets.json"

    exit_code = module.main(["--output", str(output_path)])
    printed = json.loads(capsys.readouterr().out)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact == printed
    assert artifact["status"] == "fixture_packet_emulator_ready"


def test_fixture_evidence_packet_emulator_script_stays_out_of_fooddb_websearch_and_live_boundaries() -> None:
    source = Path("scripts/build_accurate_intake_fixture_evidence_packet_emulator.py").read_text(encoding="utf-8")

    for fragment in (
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "TavilyClient",
        "BuilderSpaceAdapter",
        "builderspace_adapter",
        "kimi",
        "grok",
    ):
        assert fragment not in source
