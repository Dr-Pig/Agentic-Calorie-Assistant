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
    assert pack["coverage_lanes"]["advanced_lab"] == ["ce-002"]
    assert pack["coverage_lanes"]["current_shell_bridge"] == ["ce-005"]
    assert pack["coverage_lanes"]["shared"] == ["ce-001", "ce-003", "ce-004", "ce-006"]


def test_context_engineering_overlap_pack_defines_cross_lane_pairings() -> None:
    pack = build_context_engineering_overlap_case_pack()
    pairings = {item["pairing_id"]: item["case_ids"] for item in pack["pairings"]}

    assert pairings["shared_vs_current_shell_query_memory"] == ["ce-001", "ce-005"]
    assert pairings["shared_vs_advanced_lab_rescue_memory"] == ["ce-002", "ce-004"]
    assert pairings["shared_vs_reusable_meal_entry"] == ["ce-003", "ce-006"]
