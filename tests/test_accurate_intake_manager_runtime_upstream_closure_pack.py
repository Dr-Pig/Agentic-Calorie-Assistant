from __future__ import annotations

from pathlib import Path

from app.composition.accurate_intake_manager_runtime_upstream_closure_pack import (
    build_manager_runtime_upstream_closure_pack,
)
from scripts.run_accurate_intake_free_text_manual_target_gate import (
    build_free_text_manual_target_gate_artifact,
)
from scripts.run_accurate_intake_manager_runtime_upstream_closure_pack import (
    main,
)


def test_upstream_closure_pack_closes_rt2_through_rt5_from_existing_evidence() -> None:
    artifact = build_manager_runtime_upstream_closure_pack(
        manual_target_gate=build_free_text_manual_target_gate_artifact()
    )

    assert artifact["status"] == "pass"
    assert artifact["summary"] == {"green_gate_count": 4, "target_gate_count": 4}
    gate_by_id = {entry["gate_id"]: entry for entry in artifact["gates"]}
    assert artifact["target_gate_ids"] == [
        "rt2_coarse_tool_surface_convergence",
        "rt3_react_trace_contract",
        "rt4_context_packet_acceptance",
        "rt5_intent_tool_argument_walls",
    ]
    assert gate_by_id["rt2_coarse_tool_surface_convergence"]["status"] == "green"
    assert gate_by_id["rt3_react_trace_contract"]["status"] == "green"
    assert gate_by_id["rt4_context_packet_acceptance"]["status"] == "green"
    assert gate_by_id["rt5_intent_tool_argument_walls"]["status"] == "green"
    assert artifact["runtime_truth_changed"] is False
    assert artifact["mutation_changed"] is False
    assert artifact["manager_context_packet_schema_changed"] is False


def test_upstream_closure_pack_blocks_rt5_when_manual_target_gate_fails() -> None:
    manual_target_gate = build_free_text_manual_target_gate_artifact()
    manual_target_gate["status"] = "blocked"
    manual_target_gate["blockers"] = ["manual_target_gate_forced_block"]

    artifact = build_manager_runtime_upstream_closure_pack(
        manual_target_gate=manual_target_gate
    )

    assert artifact["status"] == "blocked"
    gate_by_id = {entry["gate_id"]: entry for entry in artifact["gates"]}
    assert gate_by_id["rt5_intent_tool_argument_walls"]["status"] == "blocked"
    assert "manual_target_gate_forced_block" in gate_by_id["rt5_intent_tool_argument_walls"]["blockers"]
    assert "rt5_intent_tool_argument_walls.not_green" in artifact["blockers"]


def test_upstream_closure_pack_cli_writes_artifact(tmp_path: Path) -> None:
    output = tmp_path / "manager_runtime_upstream_closure_pack.json"

    exit_code = main(["--output", str(output)])

    assert exit_code == 0
    artifact = output.read_text(encoding="utf-8")
    assert "accurate_intake_manager_runtime_upstream_closure_pack" in artifact
