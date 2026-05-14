from __future__ import annotations

from app.advanced_shadow_lab.context_engineering_overlap_pack import (
    build_context_engineering_overlap_case_pack,
)


def test_context_engineering_overlap_pack_groups_cases_by_branch_lane() -> None:
    pack = build_context_engineering_overlap_case_pack()

    assert (
        pack["artifact_type"]
        == "advanced_product_lab_context_engineering_overlap_case_pack"
    )
    assert pack["status"] == "pass"
    assert {"ce-stress-002", "ce-stress-006", "ce-stress-014"} <= set(
        pack["coverage_lanes"]["advanced_lab"]
    )
    assert {"ce-stress-009", "ce-stress-013"} <= set(
        pack["coverage_lanes"]["current_shell_bridge"]
    )
    assert len(pack["coverage_lanes"]["advanced_lab"]) >= 20
    assert len(pack["coverage_lanes"]["current_shell_bridge"]) >= 4


def test_context_engineering_overlap_pack_defines_cross_lane_pairings() -> None:
    pack = build_context_engineering_overlap_case_pack()
    pairings = {item["pairing_id"]: item["case_ids"] for item in pack["pairings"]}

    assert pairings["current_shell_bridge_intake_query"] == ["ce-stress-009", "ce-stress-013"]
    assert pairings["advanced_lab_memory_recommendation"] == ["ce-stress-002", "ce-stress-014"]
    assert pairings["advanced_lab_pending_intent_loop"] == ["ce-stress-006", "ce-stress-007"]
