from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.fooddb_evidence_status_packet import (
    _next_required_slices,
    build_fooddb_evidence_status_packet,
)


def _small_anchor_payload() -> dict:
    return json.loads(Path("app/knowledge/small_anchor_store_tw.json").read_text(encoding="utf-8-sig"))


def _tfda_source_payload() -> dict:
    return json.loads(
        Path("app/knowledge/tfda_per100g_source_evidence_tw.json").read_text(encoding="utf-8-sig")
    )


def _exact_card_payload() -> dict:
    return json.loads(Path("app/knowledge/exact_item_cards_tw.json").read_text(encoding="utf-8-sig"))


def _contract_handoff_artifact() -> dict:
    return {
        "artifact_type": "accurate_intake_fooddb_manager_contract_handoff_v1",
        "status": "ready_for_manager_contract_owner",
        "handoff_ready": True,
        "selected_next_step": "tighten_fooddb_manager_contract_prompt_or_transport",
        "summary": {"live_seam_status": "provider_contract_blocked"},
    }


def test_fooddb_evidence_status_packet_summarizes_current_fdb_without_runtime_change() -> None:
    packet = build_fooddb_evidence_status_packet(
        small_anchor_payload=_small_anchor_payload(),
        tfda_source_payload=_tfda_source_payload(),
        exact_card_payload=_exact_card_payload(),
    )

    assert packet["artifact_type"] == "accurate_intake_fooddb_evidence_status_packet_v1"
    assert packet["claim_scope"] == "fooddb_websearch_evidence_status_for_future_seams"
    assert packet["runtime_truth_changed"] is False
    assert packet["mutation_changed"] is False
    assert packet["manager_context_changed"] is False
    assert packet["live_provider_used"] is False
    assert packet["live_websearch_used"] is False
    assert packet["readiness_claimed"] is False
    assert packet["summary"] == {
        "runtime_common_serving_anchor_count": 51,
        "listed_component_anchor_count": 30,
        "source_evidence_only_count": 848,
        "semantic_only_basket_family_count": 4,
        "exact_card_staging_candidate_count": 1,
        "exact_card_existing_report_only_count": 5,
        "integration_edges_contract_backed": 13,
        "integration_edges_draft": 0,
        "manager_fooddb_packet_seam_gate_status": "pass",
        "manager_contract_live_seam_status": "not_run",
        "manager_contract_handoff_status": "not_run",
        "manager_contract_owner_handoff_ready": False,
    }
    assert packet["activation_thresholds"] == {
        "minimum_common_serving_anchors": 40,
        "minimum_listed_component_anchors": 30,
        "meets_common_serving_anchor_minimum": True,
        "meets_listed_component_minimum": True,
    }
    assert packet["next_required_slices"] == [
        "grokfast_fooddb_packet_live_diagnostic",
    ]


def test_fooddb_evidence_status_packet_exposes_manager_contract_handoff_when_available() -> None:
    packet = build_fooddb_evidence_status_packet(
        small_anchor_payload=_small_anchor_payload(),
        tfda_source_payload=_tfda_source_payload(),
        exact_card_payload=_exact_card_payload(),
        contract_handoff_artifact=_contract_handoff_artifact(),
    )

    assert packet["summary"]["manager_contract_live_seam_status"] == "provider_contract_blocked"
    assert packet["summary"]["manager_contract_handoff_status"] == "ready_for_manager_contract_owner"
    assert packet["summary"]["manager_contract_owner_handoff_ready"] is True
    assert packet["integration_status"]["manager_contract_selected_next_step"] == (
        "tighten_fooddb_manager_contract_prompt_or_transport"
    )
    assert packet["next_required_slices"] == ["await_manager_contract_owner_repair"]


def test_fooddb_evidence_status_packet_exposes_only_compact_downstream_metadata() -> None:
    packet = build_fooddb_evidence_status_packet(
        small_anchor_payload=_small_anchor_payload(),
        tfda_source_payload=_tfda_source_payload(),
        exact_card_payload=_exact_card_payload(),
    )
    serialized = str(packet)

    assert "raw_source_rows" not in serialized
    assert "full_fooddb" not in serialized
    assert "runtime_truth_allowed': True" not in serialized
    assert "candidate_review_no_commit" not in serialized
    assert "manager_signal" not in serialized
    assert "canonical_name" not in serialized
    assert "aliases" not in serialized
    assert "kcal_point" not in serialized
    assert "kcal_range" not in serialized
    assert "portion_basis" not in serialized
    assert packet["websearch_status"]["websearch_runtime_truth_allowed"] is False
    assert packet["websearch_status"]["exact_card_staging"]["runtime_truth_allowed"] is False
    assert packet["websearch_status"]["exact_card_staging"]["packet_ready_truth_allowed"] is False
    assert packet["fooddb_status"]["runtime_anchor_catalog_included"] is False
    assert "runtime_common_serving_anchors" not in packet["fooddb_status"]
    for key in (
        "raw_source_rows",
        "full_fooddb",
        "canonical_name",
        "aliases",
        "kcal",
        "kcal_point",
        "kcal_range",
        "portion_basis",
    ):
        assert not _contains_key(packet, key)


def test_fooddb_evidence_status_packet_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_fooddb_evidence_status_packet import main

    output = tmp_path / "fooddb_evidence_status_packet.json"

    assert main(["--output", str(output)]) == 0

    packet = read_json_artifact(output)
    assert packet["artifact_type"] == "accurate_intake_fooddb_evidence_status_packet_v1"
    assert packet["summary"]["runtime_common_serving_anchor_count"] == 51
    assert packet["summary"]["exact_card_staging_candidate_count"] == 1
    assert packet["summary"]["manager_contract_handoff_status"] == "not_run"


def test_fooddb_evidence_status_packet_does_not_unlock_seam_before_all_thresholds() -> None:
    assert _next_required_slices(
        runtime_anchor_count=39,
        listed_component_count=30,
        integration_summary={"draft": 0},
    ) == ["common_serving_anchor_expansion"]


def test_fooddb_evidence_status_packet_requires_manager_seam_before_live_diagnostic() -> None:
    assert _next_required_slices(
        runtime_anchor_count=40,
        listed_component_count=30,
        integration_summary={"draft": 0},
        manager_seam_gate_status="not_run",
    ) == ["manager_fooddb_packet_seam_smoke"]


def test_fooddb_evidence_status_packet_blocks_on_contract_handoff_alignment_failure() -> None:
    assert _next_required_slices(
        runtime_anchor_count=40,
        listed_component_count=30,
        integration_summary={"draft": 0},
        manager_seam_gate_status="pass",
        contract_handoff_status="blocked_contract_handoff_alignment",
        contract_handoff_next_step="repair_artifact_alignment_required",
    ) == ["repair_artifact_alignment_required"]


def test_fooddb_evidence_status_packet_unknown_handoff_status_fails_closed() -> None:
    packet = build_fooddb_evidence_status_packet(
        small_anchor_payload=_small_anchor_payload(),
        tfda_source_payload=_tfda_source_payload(),
        exact_card_payload=_exact_card_payload(),
        contract_handoff_artifact={
            "artifact_type": "accurate_intake_fooddb_manager_contract_handoff_v1",
            "status": "foo",
            "handoff_ready": False,
            "selected_next_step": "bar",
            "summary": {"live_seam_status": "provider_contract_blocked"},
        },
    )

    assert packet["summary"]["manager_contract_handoff_status"] == "blocked_contract_handoff_alignment"
    assert packet["next_required_slices"] == ["inspect_contract_handoff_status"]


def _contains_key(value: object, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(child, key) for child in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False
