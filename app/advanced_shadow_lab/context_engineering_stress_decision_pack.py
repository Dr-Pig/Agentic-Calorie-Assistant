from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml

from app.advanced_shadow_lab.context_engineering_final_response_boundary import (
    build_context_engineering_final_response_boundary_grade,
)
from app.advanced_shadow_lab.context_engineering_fixture_planner_provider import (
    build_context_engineering_fixture_planner_trace,
)
from app.advanced_shadow_lab.context_engineering_holdout_gate import (
    build_context_engineering_holdout_gate,
)
from app.advanced_shadow_lab.product_lab_fixture_inputs import build_product_lab_fixture_inputs


ROOT = Path(__file__).resolve().parents[2]
TRAIN_PATH = ROOT / "docs" / "quality" / "advanced_product_lab_context_engineering_stress_pr_train.yaml"


def build_ce_stress_decision_pack() -> dict[str, Any]:
    fixture = build_context_engineering_fixture_planner_trace(
        case_ids=["ce-stress-001", "ce-stress-006", "ce-stress-007", "ce-stress-012"]
    )
    holdout = build_context_engineering_holdout_gate()
    final_response = build_context_engineering_final_response_boundary_grade(
        case_id="ce-stress-001",
        fixture_inputs=build_product_lab_fixture_inputs(),
    )
    live_evidence = _train().get("last_live_diagnostic_evidence") or {}
    blockers = context_engineering_decision_pack_blockers(
        fixture_status=str(fixture.get("status") or ""),
        holdout_status=str(holdout.get("status") or ""),
        final_response_status=str(final_response.get("status") or ""),
        live_evidence=_mapping(live_evidence),
    )
    return {
        "artifact_type": "advanced_product_lab_ce_stress_decision_pack",
        "artifact_schema_version": "1.0",
        "status": "pass" if not blockers else "blocked",
        "fixture_gate_status": str(fixture.get("status") or ""),
        "holdout_gate_status": str(holdout.get("status") or ""),
        "final_response_boundary_status": str(final_response.get("status") or ""),
        "live_grokfast_diagnostic_status": str(live_evidence.get("status") or ""),
        "live_grokfast_diagnostic_evidence": dict(live_evidence),
        "proactive_entry_gate": _proactive_entry_gate(blockers),
        "mainline_activation_enabled": False,
        "production_scheduler_delivery_allowed": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "blockers": blockers,
    }


def context_engineering_decision_pack_blockers(
    *,
    fixture_status: str,
    holdout_status: str,
    final_response_status: str,
    live_evidence: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if fixture_status != "pass":
        blockers.append("fixture_gate.status_not_pass")
    if holdout_status != "pass":
        blockers.append("holdout_gate.status_not_pass")
    if final_response_status != "pass":
        blockers.append("final_response_boundary.status_not_pass")
    if live_evidence.get("status") != "pass":
        blockers.append("live_grokfast_diagnostic.status_not_pass")
    if live_evidence.get("live_provider_used") is not True:
        blockers.append("live_grokfast_diagnostic.live_provider_not_used")
    if live_evidence.get("live_grokfast_diagnostic_pass") is not True:
        blockers.append("live_grokfast_diagnostic.pass_flag_false")
    return blockers


def _proactive_entry_gate(blockers: list[str]) -> dict[str, Any]:
    return {
        "status": "blocked" if blockers else "ready_for_proactive_train",
        "allowed_next_train": (
            "" if blockers else "advanced_product_lab_proactive_context_engineering"
        ),
        "mainline_activation_enabled": False,
        "production_scheduler_delivery_allowed": False,
    }


def _train() -> Mapping[str, Any]:
    return yaml.safe_load(TRAIN_PATH.read_text(encoding="utf-8-sig"))


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["build_ce_stress_decision_pack", "context_engineering_decision_pack_blockers"]
