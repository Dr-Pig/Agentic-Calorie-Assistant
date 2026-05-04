from __future__ import annotations

from pathlib import Path

import pytest

from app.nutrition.application.food_evidence_packet_builder import (
    build_food_evidence_recall_packet,
)
from app.nutrition.application.fooddb_retrieval_policy import retrieve_fooddb_candidates
from app.nutrition.application.tool_evidence_result import (
    build_tool_evidence_result,
)
from app.nutrition.infrastructure.local_food_evidence_index import (
    LocalSmallAnchorFoodEvidenceIndex,
)


SMALL_ANCHOR_STORE = Path("app/knowledge/small_anchor_store_tw.json")


def _packet(raw_user_input: str = "large boba") -> dict:
    records = LocalSmallAnchorFoodEvidenceIndex.from_path(SMALL_ANCHOR_STORE).load_records()
    retrieval = retrieve_fooddb_candidates(raw_user_input, retrieval_records=records)
    return build_food_evidence_recall_packet(
        packet_id=f"case:{raw_user_input}",
        raw_user_input=raw_user_input,
        retrieval_result=retrieval,
    )


def test_tool_evidence_result_wraps_compact_packets_without_mutation_authority() -> None:
    result = build_tool_evidence_result(
        tool_name="lookup_food_evidence",
        tool_call_id="tool-call-001",
        evidence_packets=(_packet(),),
        index_adapter={
            "adapter_kind": "local_small_anchor_index",
            "storage_backend": "local_json",
        },
    )

    assert result["result_type"] == "tool_evidence_result_v1"
    assert result["tool_name"] == "lookup_food_evidence"
    assert result["tool_call_id"] == "tool-call-001"
    assert result["runtime_mutation_allowed"] is False
    assert result["runtime_truth_changed"] is False
    assert result["manager_context_changed"] is False
    assert result["read_model_only"] is True
    assert result["evidence_packets"][0]["packet_type"] == "food_evidence_recall_packet_v1"
    assert result["trace"]["packet_count"] == 1
    assert result["trace"]["compact_packet_pass_count"] == 1
    assert result["trace"]["raw_source_rows_included"] is False
    assert result["source_implementation_visible"] is False
    assert "index_adapter" not in result
    assert "dependency_inversion" not in result
    assert "adapter" not in str(result).lower()
    assert "supabase" not in str(result).lower()
    assert "local_json" not in str(result)
    assert "runtime_mutation" in result["manager_must_not_use_for"]


def test_tool_evidence_result_rejects_non_compact_packet_structures() -> None:
    packet = _packet()
    packet["raw_source_rows"] = [{"source_id": "raw"}]

    with pytest.raises(ValueError, match="non_compact_evidence_packet"):
        build_tool_evidence_result(
            tool_name="lookup_food_evidence",
            tool_call_id="tool-call-raw",
            evidence_packets=(packet,),
            index_adapter={"adapter_kind": "local_small_anchor_index"},
        )


def test_tool_evidence_result_rejects_compact_looking_malformed_packets() -> None:
    malformed_packet = {
        "raw_source_rows_included": False,
        "candidate_only_records_included": False,
        "full_fooddb_included": False,
    }

    with pytest.raises(ValueError, match="malformed_evidence_packet"):
        build_tool_evidence_result(
            tool_name="lookup_food_evidence",
            tool_call_id="tool-call-malformed",
            evidence_packets=(malformed_packet,),
            index_adapter={"adapter_kind": "local_small_anchor_index"},
        )

    shallow_packet = {
        "packet_type": "food_evidence_recall_packet_v1",
        "packet_id": "case:shallow",
        "evidence_items": [],
        "raw_source_rows_included": False,
        "candidate_only_records_included": False,
        "full_fooddb_included": False,
    }

    with pytest.raises(ValueError, match="malformed_evidence_packet"):
        build_tool_evidence_result(
            tool_name="lookup_food_evidence",
            tool_call_id="tool-call-shallow",
            evidence_packets=(shallow_packet,),
            index_adapter={"adapter_kind": "local_small_anchor_index"},
        )


def test_tool_evidence_result_script_roundtrip(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact
    from scripts.build_accurate_intake_tool_evidence_result_smoke import main

    output = tmp_path / "tool_evidence_result.json"

    assert main(["--output", str(output)]) == 0

    artifact = read_json_artifact(output)
    assert artifact["artifact_type"] == "accurate_intake_tool_evidence_result_smoke"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["live_provider_used"] is False
    assert artifact["adapter_diagnostics"]["storage_backend"] == "local_json"
    assert "adapter_diagnostics" not in artifact["tool_evidence_result"]
    assert artifact["tool_evidence_result"]["result_type"] == "tool_evidence_result_v1"
    assert artifact["tool_evidence_result"]["trace"]["compact_packet_pass_count"] == 5


def test_tool_evidence_result_stays_out_of_shared_contracts() -> None:
    source = Path("app/nutrition/application/tool_evidence_result.py").read_text(encoding="utf-8")
    forbidden = [
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "ManagerContextPacket",
        "app.routes",
        "app.schemas",
    ]

    for token in forbidden:
        assert token not in source
