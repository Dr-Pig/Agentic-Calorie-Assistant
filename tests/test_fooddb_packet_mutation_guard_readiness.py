from __future__ import annotations

from pathlib import Path

from app.nutrition.application.fooddb_packet_mutation_guard_readiness import (
    REQUIRED_TOOL_RESULT_FLAGS,
    build_fooddb_packet_mutation_guard_readiness,
)
from app.nutrition.infrastructure.local_food_evidence_index import (
    LocalSmallAnchorFoodEvidenceIndex,
)


SMALL_ANCHOR_STORE = Path("app/knowledge/small_anchor_store_tw.json")


def _records():
    return LocalSmallAnchorFoodEvidenceIndex.from_path(SMALL_ANCHOR_STORE).load_records()


def test_packet_mutation_guard_readiness_is_contract_backed_without_runtime_change() -> None:
    artifact = build_fooddb_packet_mutation_guard_readiness(retrieval_records=_records())

    assert artifact["artifact_type"] == "accurate_intake_fooddb_packet_mutation_guard_readiness"
    assert artifact["claim_scope"] == "packet_to_mutation_guard_contract_readiness"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["shared_contract_changed"] is False
    assert artifact["manager_context_changed"] is False
    assert artifact["packetizer_format_changed"] is False
    assert artifact["readiness_claimed"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["live_websearch_used"] is False
    assert artifact["summary"] == {
        "check_count": 8,
        "pass_count": 8,
        "fail_count": 0,
        "packet_count": 5,
        "compact_packet_pass_count": 5,
        "packet_to_mutation_guard_status": "contract_backed",
    }
    assert {check["status"] for check in artifact["checks"]} == {"pass"}
    assert set(artifact["non_claims"]) == {
        "no_runtime_truth_promotion",
        "no_mutation_authority_change",
        "no_packetizer_format_change",
        "no_manager_context_change",
        "no_product_loop_integration",
        "no_live_provider_call",
        "no_readiness_claim",
    }


def test_packet_mutation_guard_readiness_checks_required_tool_result_flags() -> None:
    artifact = build_fooddb_packet_mutation_guard_readiness(retrieval_records=_records())
    check_ids = {check["check_id"] for check in artifact["checks"]}

    assert set(REQUIRED_TOOL_RESULT_FLAGS) == {
        "runtime_mutation_allowed",
        "runtime_truth_changed",
        "manager_context_changed",
        "read_model_only",
        "source_implementation_visible",
    }
    assert {
        "tool_result_is_read_only",
        "tool_result_declares_runtime_mutation_forbidden",
        "all_packets_deny_truth_selection_and_mutation",
        "bare_basket_packet_stays_followup_only",
        "source_implementation_hidden_from_manager",
        "negative_mutation_shortcut_rejected",
        "negative_truth_selection_shortcut_rejected",
    } <= check_ids


def test_packet_mutation_guard_readiness_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_fooddb_packet_mutation_guard_readiness import main

    output = tmp_path / "fooddb_packet_mutation_guard_readiness.json"

    assert main(["--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_fooddb_packet_mutation_guard_readiness"
    assert artifact["summary"]["packet_to_mutation_guard_status"] == "contract_backed"
    assert artifact["summary"]["fail_count"] == 0
