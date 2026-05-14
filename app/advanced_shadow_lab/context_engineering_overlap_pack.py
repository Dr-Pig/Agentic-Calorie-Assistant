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
        "pairings": _stress_pairings(cases),
        "blockers": [],
    }


def _case_ids(cases: list[dict[str, Any]], coverage_scope: str) -> list[str]:
    return [str(item["case_id"]) for item in cases if item["coverage_scope"] == coverage_scope]


def _stress_pairings(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {str(item["case_id"]): item for item in cases}
    candidate_pairings = [
        {
            "pairing_id": "current_shell_bridge_intake_query",
            "case_ids": ["ce-stress-009", "ce-stress-013"],
        },
        {
            "pairing_id": "advanced_lab_memory_recommendation",
            "case_ids": ["ce-stress-002", "ce-stress-014"],
        },
        {
            "pairing_id": "advanced_lab_pending_intent_loop",
            "case_ids": ["ce-stress-006", "ce-stress-007"],
        },
    ]
    return [
        pairing
        for pairing in candidate_pairings
        if all(case_id in by_id for case_id in pairing["case_ids"])
    ]


__all__ = ["build_context_engineering_overlap_case_pack"]
