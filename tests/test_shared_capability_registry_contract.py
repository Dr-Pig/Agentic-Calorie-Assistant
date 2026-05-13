from __future__ import annotations

from app.advanced_shadow_lab.product_lab_manager_tool_contract import (
    build_product_lab_manager_tool_registry,
)
from app.shared.contracts.capability_registry import build_shared_capability_registry


def test_shared_capability_registry_declares_all_core_capability_families() -> None:
    registry = build_shared_capability_registry()

    assert registry["artifact_type"] == "shared_capability_registry"
    assert registry["status"] == "pass"
    by_id = {item["capability_id"]: item for item in registry["capabilities"]}
    assert set(by_id) == {
        "intake",
        "query",
        "memory",
        "recommendation",
        "rescue",
        "proactive",
        "reusable_meal",
    }
    assert by_id["intake"]["tool_binding_status"] == "bridge_required"
    assert by_id["query"]["tool_binding_status"] == "implemented_in_lab"
    assert by_id["memory"]["tool_binding_status"] == "implemented_in_lab"
    assert by_id["reusable_meal"]["tool_binding_status"] == "implemented_in_lab"


def test_shared_capability_registry_normalizes_shared_tool_vocabulary() -> None:
    registry = build_shared_capability_registry()

    assert registry["shared_tool_vocabulary"] == [
        "intake.run",
        "query.run",
        "memory.search",
        "recommendation.run",
        "rescue.run",
        "proactive.run",
        "reusable_meal.search",
    ]
    assert registry["planner_reads_capability_ids_not_raw_branch_paths"] is True
    assert registry["branch_specific_activation_is_separate_from_registry"] is True


def test_advanced_lab_manager_registry_embeds_shared_capability_registry() -> None:
    registry = build_product_lab_manager_tool_registry()
    shared = registry["shared_capability_registry"]

    assert shared["status"] == "pass"
    by_id = {item["capability_id"]: item for item in shared["capabilities"]}
    assert by_id["recommendation"]["shared_tool_name"] == "recommendation.run"
    assert by_id["rescue"]["shared_tool_name"] == "rescue.run"
    assert by_id["proactive"]["shared_tool_name"] == "proactive.run"
    assert by_id["memory"]["shared_tool_name"] == "memory.search"
