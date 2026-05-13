from __future__ import annotations

from typing import Any

from app.advanced_shadow_lab.context_engineering_case_loader import (
    load_context_engineering_golden_set,
)


def build_context_engineering_overlap_case_pack() -> dict[str, Any]:
    golden_set = load_context_engineering_golden_set()
    cases = list(golden_set["cases"])
    return {
        "artifact_type": "advanced_product_lab_context_engineering_overlap_case_pack",
        "artifact_schema_version": "1.0",
        "status": "pass",
        "coverage_lanes": {
            "shared": _case_ids(cases, "shared"),
            "advanced_lab": _case_ids(cases, "advanced_lab"),
            "current_shell_bridge": _case_ids(cases, "current_shell_bridge"),
        },
        "pairings": [
            {
                "pairing_id": "shared_vs_current_shell_query_memory",
                "case_ids": ["ce-001", "ce-005"],
            },
            {
                "pairing_id": "shared_vs_advanced_lab_rescue_memory",
                "case_ids": ["ce-002", "ce-004"],
            },
            {
                "pairing_id": "shared_vs_reusable_meal_entry",
                "case_ids": ["ce-003", "ce-006"],
            },
        ],
        "blockers": [],
    }


def _case_ids(cases: list[dict[str, Any]], coverage_scope: str) -> list[str]:
    return [str(item["case_id"]) for item in cases if item["coverage_scope"] == coverage_scope]


__all__ = ["build_context_engineering_overlap_case_pack"]
