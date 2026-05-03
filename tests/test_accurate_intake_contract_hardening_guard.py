from __future__ import annotations

import json
from pathlib import Path

from scripts.build_accurate_intake_contract_hardening_guard import (
    build_accurate_intake_contract_hardening_guard,
    write_accurate_intake_contract_hardening_guard,
)


def _legal_flow_matrix(*, legal_flows_broken: list[str] | None = None) -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_contract_legal_flow_matrix",
        "artifact_schema_version": "1.0",
        "status": "pass" if not legal_flows_broken else "blocked",
        "updated_for_change_ids": ["PR84"],
        "legal_flows_broken": legal_flows_broken or [],
        "flows": [
            {
                "flow_id": "composition_unknown_basket",
                "manager_action": "final",
                "final_action": "ask_followup",
                "tool_calls": [],
                "ledger_mutation_allowed": False,
            },
            {
                "flow_id": "listed_basket_followup",
                "manager_action": "call_tools",
                "final_action": "commit",
                "tool_calls": ["estimate_nutrition"],
                "ledger_mutation_allowed": True,
            },
            {
                "flow_id": "stable_common_item_optional_refinement",
                "manager_action": "call_tools",
                "final_action": "commit",
                "tool_calls": ["estimate_nutrition"],
                "followup_posture": "refinement_optional",
                "ledger_mutation_allowed": True,
            },
            {
                "flow_id": "query_only_today_consumed",
                "manager_action": "final",
                "final_action": "answer_only",
                "tool_calls": [],
                "ledger_mutation_allowed": False,
            },
            {
                "flow_id": "explicit_remove_item",
                "manager_action": "final",
                "final_action": "correction_applied",
                "required_evidence": "target_evidence",
                "ledger_mutation_allowed": True,
            },
            {
                "flow_id": "nutrition_changing_correction",
                "manager_action": "call_tools",
                "final_action": "correction_applied",
                "tool_calls": ["estimate_nutrition"],
                "ledger_mutation_allowed": True,
            },
        ],
    }


def _drift_audit() -> dict[str, object]:
    return {
        "artifact_type": "accurate_intake_pr74_84_semantic_drift_audit",
        "artifact_schema_version": "1.0",
        "status": "reviewed",
        "pr_range": "PR74-PR84",
        "entries": [
            {
                "pr_number": 84,
                "change_type": "schema_hardening",
                "triggered_by_live_failure": True,
                "canonical_spec_refs": ["WAVE_1_PHASE_B2_SEMANTIC_DECISION_REGISTER"],
                "provider_overfit_risk": "medium",
                "mitigation_tests": ["legal_flow_matrix"],
            }
        ],
    }


def _change_manifest(**overrides: object) -> dict[str, object]:
    manifest: dict[str, object] = {
        "artifact_type": "accurate_intake_contract_change_manifest",
        "artifact_schema_version": "1.0",
        "change_id": "PR84",
        "proposed_change_type": "schema_hardening",
        "fixed_case_ids": ["luwei_bare_to_listed_basket"],
        "live_failure_only": False,
        "canonical_rule_exists": True,
        "canonical_rule_refs": [
            "docs/specs/WAVE_1_PHASE_B2_SEMANTIC_DECISION_REGISTER.md#self_selected_basket_without_listed_items"
        ],
        "legal_flow_matrix_updated": True,
        "holdout_tests_added": True,
        "holdout_test_refs": ["tests/test_accurate_intake_basket_holdout_regression.py"],
        "raw_text_routing_risk": False,
        "provider_overfit_risk": "medium",
        "legal_flows_broken": [],
    }
    manifest.update(overrides)
    return manifest


def test_contract_hardening_guard_blocks_live_failure_only_changes() -> None:
    guard = build_accurate_intake_contract_hardening_guard(
        _change_manifest(
            live_failure_only=True,
            canonical_rule_exists=False,
            canonical_rule_refs=[],
        ),
        legal_flow_matrix_artifact=_legal_flow_matrix(),
        semantic_drift_audit_artifact=_drift_audit(),
    )

    assert guard["artifact_type"] == "accurate_intake_contract_hardening_guard"
    assert guard["contract_hardening_debt"]["present"] is True
    assert guard["merge_allowed"] is False
    assert "live_failure_only" in guard["blockers"]
    assert "canonical_rule_missing" in guard["blockers"]
    assert guard["raw_text_routing_risk"] is False
    assert guard["fixed_case_ids"] == ["luwei_bare_to_listed_basket"]


def test_contract_hardening_guard_requires_legal_flow_matrix_and_holdout_tests() -> None:
    guard = build_accurate_intake_contract_hardening_guard(
        _change_manifest(
            legal_flow_matrix_updated=False,
            holdout_tests_added=False,
        ),
        legal_flow_matrix_artifact=_legal_flow_matrix(),
        semantic_drift_audit_artifact=_drift_audit(),
    )

    assert guard["merge_allowed"] is False
    assert guard["contract_hardening_debt"]["present"] is True
    assert "legal_flow_matrix_missing_or_stale" in guard["blockers"]
    assert "holdout_tests_missing" in guard["blockers"]


def test_contract_hardening_guard_blocks_raw_text_routing_risk_and_broken_flows() -> None:
    guard = build_accurate_intake_contract_hardening_guard(
        _change_manifest(
            raw_text_routing_risk=True,
            provider_overfit_risk="high",
            legal_flows_broken=["stable_common_item_optional_refinement"],
        ),
        legal_flow_matrix_artifact=_legal_flow_matrix(
            legal_flows_broken=["stable_common_item_optional_refinement"]
        ),
        semantic_drift_audit_artifact=_drift_audit(),
    )

    assert guard["merge_allowed"] is False
    assert guard["provider_overfit_risk"] == "high"
    assert guard["legal_flows_broken"] == ["stable_common_item_optional_refinement"]
    assert "raw_text_routing_risk" in guard["blockers"]
    assert "provider_overfit_risk_high" in guard["blockers"]
    assert "legal_flows_broken" in guard["blockers"]


def test_contract_hardening_guard_allows_audited_general_rule_change() -> None:
    guard = build_accurate_intake_contract_hardening_guard(
        _change_manifest(),
        legal_flow_matrix_artifact=_legal_flow_matrix(),
        semantic_drift_audit_artifact=_drift_audit(),
    )

    assert guard["merge_allowed"] is True
    assert guard["contract_hardening_debt"]["present"] is False
    assert guard["blockers"] == []
    assert guard["legal_flows_broken"] == []
    assert guard["canonical_rule_exists"] is True
    assert guard["legal_flow_matrix_updated"] is True
    assert guard["holdout_tests_added"] is True


def test_contract_hardening_guard_writer_creates_artifact(tmp_path: Path) -> None:
    change_manifest = tmp_path / "change_manifest.json"
    legal_flow_matrix = tmp_path / "legal_flow_matrix.json"
    drift_audit = tmp_path / "drift_audit.json"
    output_path = tmp_path / "guard.json"
    change_manifest.write_text(json.dumps(_change_manifest(), ensure_ascii=False), encoding="utf-8")
    legal_flow_matrix.write_text(json.dumps(_legal_flow_matrix(), ensure_ascii=False), encoding="utf-8")
    drift_audit.write_text(json.dumps(_drift_audit(), ensure_ascii=False), encoding="utf-8")

    output = write_accurate_intake_contract_hardening_guard(
        change_manifest_path=change_manifest,
        legal_flow_matrix_path=legal_flow_matrix,
        semantic_drift_audit_path=drift_audit,
        output_path=output_path,
    )

    artifact = json.loads(output.read_text(encoding="utf-8"))
    assert output == output_path
    assert artifact["artifact_type"] == "accurate_intake_contract_hardening_guard"
    assert artifact["merge_allowed"] is True
