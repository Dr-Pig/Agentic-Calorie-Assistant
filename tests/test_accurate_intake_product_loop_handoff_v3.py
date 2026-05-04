from __future__ import annotations

import json
from pathlib import Path

from scripts.build_accurate_intake_product_loop_handoff_v3 import (
    build_product_loop_handoff_v3,
)


def _product_loop_evidence(**overrides: dict) -> dict:
    evidence = {
        "browser_shell_smoke": {"status": "pass", "browser_executed": True},
        "browser_fixture_dogfood": {
            "status": "browser_fixture_pass",
            "fixture_evidence_used": True,
            "real_fooddb_pass_claimed": False,
        },
        "local_dogfood_hygiene": {"status": "pass"},
        "browser_realistic_dogfood": {
            "status": "browser_diagnostic_pass_with_fixture_evidence_gap",
            "fixture_evidence_used": True,
            "real_fooddb_pass_claimed": False,
        },
        "operator_review": {
            "status": "browser_diagnostic_review_with_fixture_evidence_gap",
            "real_fooddb_pass_claimed": False,
        },
        "mvp_gate": {"status": "pass"},
    }
    evidence.update(overrides)
    return evidence


def _fooddb_artifact(
    *,
    fixture_or_real: str = "real",
    source_quality: str = "approved",
    ready_for_product_loop: bool = True,
) -> dict:
    return {
        "approved_packet_ready_evidence_artifact": {
            "path": "artifacts/fdb/approved_packet_ready.json",
            "schema_version": "food_evidence_v1",
            "fixture_or_real": fixture_or_real,
            "source_quality": source_quality,
            "ready_for_product_loop": ready_for_product_loop,
        }
    }


def test_handoff_missing_fooddb_artifact_waits_without_claiming_real_pass() -> None:
    pack = build_product_loop_handoff_v3(_product_loop_evidence())

    assert pack["artifact_type"] == "accurate_intake_product_loop_handoff_v3"
    assert pack["status"] == "product_loop_handoff_waiting_for_fdb_artifact"
    assert pack["fooddb_artifact_status"] == "blocked_waiting_for_fdb_artifact"
    assert pack["ready_for_fdb_integration"] is False
    assert pack["real_fooddb_pass_claimed"] is False
    assert pack["dogfood_pass"] is False
    assert pack["product_readiness_claimed"] is False
    assert pack["shared_contract_changed"] is False


def test_handoff_fixture_fooddb_artifact_still_does_not_claim_real_fooddb_pass() -> None:
    pack = build_product_loop_handoff_v3(
        _product_loop_evidence(),
        fooddb_artifact=_fooddb_artifact(fixture_or_real="fixture"),
    )

    assert pack["status"] == "product_loop_handoff_waiting_for_fdb_artifact"
    assert pack["fooddb_artifact_status"] == "fixture_not_real_fooddb"
    assert pack["ready_for_fdb_integration"] is False
    assert pack["real_fooddb_pass_claimed"] is False
    assert pack["fooddb_evidence_used"] is False


def test_handoff_invalid_fooddb_metadata_blocks_without_autofix() -> None:
    pack = build_product_loop_handoff_v3(
        _product_loop_evidence(),
        fooddb_artifact={"approved_packet_ready_evidence_artifact": {"fixture_or_real": "real"}},
    )

    assert pack["status"] == "blocked"
    assert pack["fooddb_artifact_status"] == "blocked_invalid_fooddb_metadata"
    assert pack["ready_for_fdb_integration"] is False
    assert pack["autofix_attempted"] is False
    assert any(item.startswith("fooddb_metadata_missing:") for item in pack["blockers"])


def test_handoff_valid_real_fooddb_metadata_allows_validation_only_integration() -> None:
    pack = build_product_loop_handoff_v3(
        _product_loop_evidence(),
        fooddb_artifact=_fooddb_artifact(),
    )

    assert pack["status"] == "product_loop_handoff_ready_for_fdb_integration_validation"
    assert pack["fooddb_artifact_status"] == "approved_packet_ready_evidence_metadata_valid"
    assert pack["ready_for_fdb_integration"] is True
    assert pack["fooddb_input_mode"] == "approved_packet_ready_metadata_validation_only"
    assert pack["real_fooddb_pass_claimed"] is False
    assert pack["dogfood_pass"] is False


def test_handoff_blocks_product_loop_overclaims_before_fooddb_validation() -> None:
    pack = build_product_loop_handoff_v3(
        _product_loop_evidence(
            browser_realistic_dogfood={
                "status": "browser_diagnostic_pass_with_fixture_evidence_gap",
                "fixture_evidence_used": True,
                "real_fooddb_pass_claimed": True,
            }
        ),
        fooddb_artifact=_fooddb_artifact(),
    )

    assert pack["status"] == "blocked"
    assert "browser_realistic_dogfood_real_fooddb_overclaim" in pack["blockers"]
    assert pack["ready_for_fdb_integration"] is False


def test_handoff_script_never_reads_unapproved_fooddb_inputs_as_truth() -> None:
    source = Path("scripts/build_accurate_intake_product_loop_handoff_v3.py").read_text(
        encoding="utf-8"
    )

    assert "approved_packet_ready_metadata_validation_only" in source
    for fragment in (
        "raw_source",
        "staging_candidates",
        "validator_only_candidates",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "NutritionEvidenceStorePort",
        "packetizer",
    ):
        assert fragment not in source


def test_handoff_cli_writes_waiting_artifact(tmp_path: Path) -> None:
    evidence_path = tmp_path / "evidence.json"
    output_path = tmp_path / "handoff.json"
    evidence_path.write_text(
        json.dumps(_product_loop_evidence(), ensure_ascii=False),
        encoding="utf-8",
    )

    from scripts.build_accurate_intake_product_loop_handoff_v3 import main

    exit_code = main(["--evidence-json", str(evidence_path), "--output", str(output_path)])

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "product_loop_handoff_waiting_for_fdb_artifact"
    assert artifact["fooddb_artifact_status"] == "blocked_waiting_for_fdb_artifact"


def test_handoff_runbook_documents_validation_only_gate() -> None:
    runbook = Path("docs/quality/ACCURATE_INTAKE_MVP_SELF_USE_RUNBOOK.md").read_text(
        encoding="utf-8-sig"
    )

    assert "build_accurate_intake_product_loop_handoff_v3.py" in runbook
    assert "ready_for_fdb_integration=false" in runbook
    assert "blocked_waiting_for_fdb_artifact" in runbook
    assert "Invalid FoodDB metadata blocks the gate" in runbook
