from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.advanced_core_golden_sets import (
    load_proactive_golden_set,
    validate_golden_set_contract,
)


def build_proactive_golden_gate_report(
    proactive_golden_set: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    artifact = dict(proactive_golden_set or load_proactive_golden_set())
    validation = validate_golden_set_contract(artifact)
    blockers = list(validation["blockers"])
    status = "pass" if not blockers else "blocked"
    return {
        "artifact_type": "advanced_product_lab_proactive_golden_gate_report",
        "artifact_schema_version": "1.0",
        "status": status,
        "owner": "app/advanced_shadow_lab/proactive_golden_gate.py",
        "consumer": "advanced_product_lab_proactive_chat_first_pr_train.pr3",
        "validated_artifact_type": validation["validated_artifact_type"],
        "case_count": validation["case_count"],
        "split_counts": validation["split_counts"],
        "case_types": validation["case_types"],
        "semantic_width": validation["semantic_contract_width"],
        "raw_keyword_semantic_oracle_allowed": artifact.get("raw_keyword_semantic_oracle_allowed"),
        "runner_inferred_semantics_allowed": False,
        "ready_for_deterministic_trigger_gate_pr4": status == "pass",
        "mainline_activation_enabled": False,
        "blockers": blockers,
    }


__all__ = ["build_proactive_golden_gate_report"]
