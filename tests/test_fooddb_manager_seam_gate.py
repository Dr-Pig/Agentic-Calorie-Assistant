from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.fooddb_manager_seam_gate import build_fooddb_manager_seam_gate


SMALL_ANCHOR_STORE = Path("app/knowledge/small_anchor_store_tw.json")


def _small_anchor_payload() -> dict:
    return json.loads(SMALL_ANCHOR_STORE.read_text(encoding="utf-8-sig"))


def test_fooddb_manager_seam_gate_passes_without_live_provider_or_runtime_change() -> None:
    artifact = build_fooddb_manager_seam_gate(small_anchor_payload=_small_anchor_payload())

    assert artifact["artifact_type"] == "accurate_intake_fooddb_manager_seam_gate"
    assert artifact["claim_scope"] == "deterministic_manager_fooddb_packet_seam_gate"
    assert artifact["status"] == "pass"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["shared_contract_changed"] is False
    assert artifact["manager_context_changed"] is False
    assert artifact["packetizer_format_changed"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["live_websearch_used"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["summary"] == {
        "check_count": 5,
        "pass_count": 5,
        "fail_count": 0,
        "packet_case_count": 5,
        "compact_packet_pass_count": 5,
        "tool_packet_count": 5,
        "diagnostic_pass_count": 5,
        "diagnostic_fail_count": 0,
        "next_allowed_slice": "grokfast_fooddb_packet_live_diagnostic",
    }
    assert {check["status"] for check in artifact["checks"]} == {"pass"}
    assert set(artifact["non_claims"]) == {
        "no_runtime_truth_promotion",
        "no_mutation_authority_change",
        "no_packetizer_format_change",
        "no_manager_context_change",
        "no_product_loop_integration",
        "no_live_provider_call",
        "no_live_websearch_call",
        "no_readiness_claim",
    }


def test_fooddb_manager_seam_gate_status_is_compact() -> None:
    artifact = build_fooddb_manager_seam_gate(small_anchor_payload=_small_anchor_payload())
    serialized = str(artifact)

    assert "manager_evidence_packet" not in serialized
    assert "evidence_items" not in serialized
    assert "raw_source_rows" not in serialized
    assert "full_fooddb" not in serialized
    assert "local_json" not in serialized
    assert "kcal_point" not in serialized
    assert "kcal_range" not in serialized


def test_fooddb_manager_seam_gate_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_fooddb_manager_seam_gate import main

    output = tmp_path / "fooddb_manager_seam_gate.json"

    assert main(["--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_fooddb_manager_seam_gate"
    assert artifact["status"] == "pass"
    assert artifact["summary"]["next_allowed_slice"] == "grokfast_fooddb_packet_live_diagnostic"


def test_fooddb_manager_seam_gate_blocks_live_step_when_checks_fail(monkeypatch) -> None:
    from app.nutrition.application import fooddb_manager_seam_gate as seam_gate

    original_checks = seam_gate._checks

    def _failing_checks(**kwargs):
        checks = list(original_checks(**kwargs))
        checks[0] = {
            **checks[0],
            "status": "fail",
            "evidence": "forced test failure",
        }
        return checks

    monkeypatch.setattr(seam_gate, "_checks", _failing_checks)

    artifact = seam_gate.build_fooddb_manager_seam_gate(small_anchor_payload=_small_anchor_payload())

    assert artifact["status"] == "fail"
    assert artifact["summary"]["fail_count"] == 1
    assert artifact["summary"]["next_allowed_slice"] == "fooddb_manager_packet_seam_smoke"
