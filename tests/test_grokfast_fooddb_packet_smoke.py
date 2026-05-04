from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.fooddb_manager_packet_smoke import (
    build_fooddb_manager_packet_smoke,
)
from app.nutrition.application.fooddb_retrieval_policy import (
    build_runtime_retrieval_records_from_small_anchor_payload,
)
from app.nutrition.application.grokfast_fooddb_packet_smoke import (
    build_fixture_manager_outputs,
    build_grokfast_fooddb_packet_diagnostic,
    build_live_manager_payload,
    build_packet_artifact_from_tool_evidence_result,
    evaluate_manager_output_against_packet,
)
from app.nutrition.application.tool_evidence_result import build_tool_evidence_result


def _packet_artifact() -> dict:
    payload = json.loads(Path("app/knowledge/small_anchor_store_tw.json").read_text(encoding="utf-8-sig"))
    records = build_runtime_retrieval_records_from_small_anchor_payload(payload)
    return build_fooddb_manager_packet_smoke(retrieval_records=records)


def _tool_evidence_artifact() -> dict:
    packet_artifact = _packet_artifact()
    tool_result = build_tool_evidence_result(
        tool_name="lookup_food_evidence",
        tool_call_id="tool-fooddb-manager-packet-smoke",
        evidence_packets=tuple(case["manager_evidence_packet"] for case in packet_artifact["cases"]),
        index_adapter={
            "adapter_kind": "local_small_anchor_index",
            "storage_backend": "local_json",
        },
    )
    return {
        "artifact_type": "accurate_intake_tool_evidence_result_smoke",
        "adapter_diagnostics": {
            "adapter_kind": "local_small_anchor_index",
            "storage_backend": "local_json",
            "manager_visible": False,
        },
        "tool_evidence_result": tool_result,
    }


def test_grokfast_fooddb_packet_diagnostic_classifies_fixture_evidence_use() -> None:
    packet_artifact = _packet_artifact()
    manager_outputs = build_fixture_manager_outputs(packet_artifact=packet_artifact)

    diagnostic = build_grokfast_fooddb_packet_diagnostic(
        packet_artifact=packet_artifact,
        manager_outputs=manager_outputs,
        live_provider_used=False,
    )

    assert diagnostic["artifact_type"] == "accurate_intake_grokfast_fooddb_packet_smoke"
    assert diagnostic["classification"] == "live_diagnostic_only"
    assert diagnostic["live_provider_used"] is False
    assert diagnostic["readiness_claimed"] is False
    assert diagnostic["self_use_approved"] is False
    assert diagnostic["production_selected"] is False
    assert diagnostic["summary"]["case_count"] == 5
    assert diagnostic["summary"]["pass_count"] == 5
    assert diagnostic["summary"]["fail_count"] == 0
    assert diagnostic["provider_profile"]["model"] == "grok-4-fast"


def test_grokfast_fooddb_packet_diagnostic_flags_invented_evidence() -> None:
    packet_case = _packet_artifact()["cases"][0]
    manager_output = {
        "manager_action": "final",
        "final_action": "commit",
        "tool_calls": [],
        "item_results": [
            {
                "food_name": "invented",
                "kcal_range": [1, 2],
                "likely_kcal": 1,
                "uncertainty": "low",
                "evidence_used": ["not_in_packet"],
            }
        ],
        "evidence_used": ["not_in_packet"],
    }

    result = evaluate_manager_output_against_packet(
        packet_case=packet_case,
        manager_output=manager_output,
    )

    assert result["status"] == "fail"
    assert "invented_evidence_reference" in result["failure_families"]


def test_grokfast_fooddb_packet_projection_can_use_tool_evidence_result_without_backend_leak() -> None:
    packet_artifact = build_packet_artifact_from_tool_evidence_result(
        tool_evidence_artifact=_tool_evidence_artifact()
    )

    assert packet_artifact["summary"]["tool_evidence_result_used"] is True
    first_case = packet_artifact["cases"][0]
    payload = build_live_manager_payload(packet_case=first_case)

    assert payload["tool_results"][0]["truth_level"] == "read_only_food_evidence_result"
    assert payload["tool_evidence_result"]["result_type"] == "tool_evidence_result_v1"
    assert payload["fooddb_evidence_packet"]["packet_type"] == "fooddb_manager_evidence_packet_v1"
    assert "local_json" not in str(payload)
    assert "adapter_diagnostics" not in str(payload)


def test_grokfast_fooddb_packet_smoke_cli_defaults_to_fixture_and_blocks_accidental_live(tmp_path: Path) -> None:
    from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact
    from scripts.run_accurate_intake_grokfast_fooddb_packet_smoke import main

    packet_path = tmp_path / "packet.json"
    output = tmp_path / "diagnostic.json"
    write_json_artifact(packet_path, _packet_artifact())

    assert main(["--mode", "fixture", "--packet-smoke", str(packet_path), "--output", str(output)]) == 0
    artifact = read_json_artifact(output)
    assert artifact["live_provider_used"] is False
    assert artifact["summary"]["pass_count"] == 5

    tool_packet_path = tmp_path / "tool_packet.json"
    tool_output = tmp_path / "tool_diagnostic.json"
    write_json_artifact(tool_packet_path, _tool_evidence_artifact())
    assert (
        main(
            [
                "--mode",
                "fixture",
                "--tool-evidence-result",
                str(tool_packet_path),
                "--output",
                str(tool_output),
            ]
        )
        == 0
    )
    tool_artifact = read_json_artifact(tool_output)
    assert tool_artifact["packet_artifact_type"] == "accurate_intake_fooddb_manager_packet_smoke"
    assert tool_artifact["summary"]["pass_count"] == 5

    blocked_output = tmp_path / "blocked_live.json"
    assert main(["--mode", "live", "--packet-smoke", str(packet_path), "--output", str(blocked_output)]) == 2
    blocked = read_json_artifact(blocked_output)
    assert blocked["status"] == "blocked"
    assert blocked["failure_family"] == "live_mode_requires_explicit_allow_live"
