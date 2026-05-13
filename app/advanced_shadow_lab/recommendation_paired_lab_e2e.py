from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_memory_store import ProductLabMemoryStore
from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn
from app.advanced_shadow_lab.product_lab_turn_policy import LAB_MODE
from app.advanced_shadow_lab.recommendation_paired_lab_e2e_summary import (
    any_pair_flag_true,
    build_recommendation_pair_comparison,
    build_recommendation_pair_path_summary,
    recommendation_pair_blockers,
)


def run_recommendation_paired_lab_e2e(
    *,
    turn: Mapping[str, Any],
    fixture_inputs: Mapping[str, Any],
    baseline_manager_script: list[Mapping[str, Any]] | None,
    recommendation_manager_script: list[Mapping[str, Any]] | None,
    baseline_store: ProductLabMemoryStore | None = None,
    recommendation_store: ProductLabMemoryStore | None = None,
    lab_mode: str = LAB_MODE,
) -> dict[str, Any]:
    baseline = build_recommendation_pair_path_summary(
        "baseline",
        _run_path(
            turn=turn,
            fixture_inputs=fixture_inputs,
            manager_script=baseline_manager_script,
            store=baseline_store,
            lab_mode=lab_mode,
        ),
    )
    recommendation_enabled = build_recommendation_pair_path_summary(
        "recommendation_enabled",
        _run_path(
            turn=turn,
            fixture_inputs=fixture_inputs,
            manager_script=recommendation_manager_script,
            store=recommendation_store,
            lab_mode=lab_mode,
        ),
    )
    comparison = build_recommendation_pair_comparison(
        baseline=baseline,
        recommendation_enabled=recommendation_enabled,
    )
    blockers = recommendation_pair_blockers(
        baseline=baseline,
        recommendation_enabled=recommendation_enabled,
        comparison=comparison,
    )
    return {
        "artifact_type": "advanced_product_lab_recommendation_paired_e2e",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "owner": "app/advanced_shadow_lab/recommendation_paired_lab_e2e.py",
        "consumer": "advanced_product_lab_recommendation_quality_decision_pack",
        "lab_enabled": lab_mode == LAB_MODE,
        "lab_isolated": lab_mode == LAB_MODE,
        "mainline_activation_enabled": any_pair_flag_true(
            baseline,
            recommendation_enabled,
            "mainline_activation_enabled",
        ),
        "canonical_product_mutation_allowed": any_pair_flag_true(
            baseline,
            recommendation_enabled,
            "canonical_product_mutation_allowed",
        ),
        "baseline": baseline,
        "recommendation_enabled": recommendation_enabled,
        "comparison": comparison,
        "blockers": blockers,
    }


def _run_path(
    *,
    turn: Mapping[str, Any],
    fixture_inputs: Mapping[str, Any],
    manager_script: list[Mapping[str, Any]] | None,
    store: ProductLabMemoryStore | None,
    lab_mode: str,
) -> dict[str, Any]:
    return run_advanced_product_lab_turn(
        lab_mode=lab_mode,
        turn=deepcopy(dict(turn)),
        fixture_inputs=deepcopy(dict(fixture_inputs)),
        manager_script=manager_script,
        manager_tool_store=store,
    )


__all__ = ["run_recommendation_paired_lab_e2e"]
