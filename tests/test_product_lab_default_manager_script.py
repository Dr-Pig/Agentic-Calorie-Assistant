from __future__ import annotations

from app.advanced_shadow_lab.product_lab_default_manager_script import (
    build_product_lab_default_manager_script,
)


def test_default_manager_script_compiles_core_advanced_loop_when_memory_store_present() -> None:
    artifact = build_product_lab_default_manager_script(
        turn={
            "surface": "chat",
            "semantic_intent_fixture": "advanced_recommendation_rescue_proactive_loop",
        },
        manager_tool_store_present=True,
    )

    assert artifact["status"] == "pass"
    assert artifact["requested_capabilities"] == [
        "memory",
        "recommendation",
        "rescue",
        "proactive",
    ]
    assert artifact["executable_capabilities"] == [
        "memory",
        "recommendation",
        "rescue",
        "proactive",
    ]
    assert artifact["omitted_capabilities"] == []
    assert artifact["source_tool_call_ids"] == [
        "memory-search-1",
        "recommendation-1",
        "rescue-1",
        "proactive-1",
    ]


def test_default_manager_script_omits_memory_when_store_missing() -> None:
    artifact = build_product_lab_default_manager_script(
        turn={
            "surface": "chat",
            "semantic_intent_fixture": "advanced_recommendation_rescue_proactive_loop",
        },
        manager_tool_store_present=False,
    )

    assert artifact["status"] == "pass"
    assert artifact["executable_capabilities"] == [
        "recommendation",
        "rescue",
        "proactive",
    ]
    assert artifact["omitted_capabilities"] == ["memory.requires_manager_tool_store"]
    assert artifact["source_tool_call_ids"] == [
        "recommendation-1",
        "rescue-1",
        "proactive-1",
    ]


def test_default_manager_script_compiles_query_plus_recommendation_shape() -> None:
    artifact = build_product_lab_default_manager_script(
        turn={
            "surface": "chat",
            "semantic_intent_fixture": "exercise_budget_bonus",
        },
        manager_tool_store_present=False,
    )

    assert artifact["status"] == "pass"
    assert artifact["requested_capabilities"] == ["query", "recommendation"]
    assert artifact["source_tool_call_ids"] == ["query-1", "recommendation-1"]
