from __future__ import annotations

import importlib
import json
from pathlib import Path


def test_estimable_payload_no_commit_diagnostic_artifact_contract(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.run_wave1_founder_e2e_estimable_payload_no_commit_diagnostic")
    output_path = tmp_path / "wave1_founder_e2e_estimable_payload_no_commit_diagnostic.json"
    source_output_path = tmp_path / "wave1_founder_e2e_deterministic_diagnostic.json"
    source_db_path = tmp_path / "wave1_founder_e2e_source.sqlite3"
    detail_db_path = tmp_path / "wave1_founder_e2e_detail.sqlite3"

    report = module.run_diagnostic(
        output_path=output_path,
        source_output_path=source_output_path,
        source_db_path=source_db_path,
        detail_db_path=detail_db_path,
        local_date="2026-04-30",
    )

    assert output_path.exists()
    assert json.loads(output_path.read_text(encoding="utf-8")) == report
    assert report["artifact_type"] == "wave1_founder_e2e_estimable_payload_no_commit_diagnostic"
    assert report["provider_mode"] == "deterministic"
    assert report["active_entrypoint"] == "app.intake.application.intake_turn_orchestrator.execute_bundle1_turn"
    assert report["active_entrypoint_verified"] is True
    assert report["live_llm_invoked"] is False
    assert report["tavily_live_invoked"] is False
    assert report["source_artifact"] == str(source_output_path)

    primary = report["primary_case"]
    assert primary["case_id"] == "pearl_milk_tea_logged_followup"
    assert primary["nutrition_payload_present"] is True
    assert primary["estimated_kcal"] > 0
    assert primary["attachment_decision"]["disposition"] == "answer_only"
    assert primary["transition_guard_result"]["verdict"] == "answer_only"
    assert primary["root_cause"] == "resolved_manager_semantic_contract"
    assert "transition_guard_blocked" not in primary["contributing_root_causes"]
    assert primary["commit_boundary_preflight"]["manager_final_action"] == "commit"
    assert primary["commit_boundary_preflight"]["blocked"] is False
    assert primary["state_delta"]["canonical_commit"] is True
    assert primary["output_text_encoding_issue_detected"] is False

    legacy_scan = report["legacy_drift_scan"]
    assert legacy_scan["checked"] is True
    assert legacy_scan["matches_are_supporting_evidence_only"] is True
    assert legacy_scan["must_not_override_active_trace_precedence"] is True
    assert primary["root_cause_source"] == "active_trace_precedence"

    guidance = report["next_repair_guidance"]
    assert guidance["repair_target"] == "semantic_owner_inversion"
    assert guidance["deterministic_diagnostic_mode_is_not_semantic_ownership"] is True
    assert guidance["phase_a_should_consume_manager_structured_semantic_decision"] is True
    assert guidance["fake_provider_may_simulate_llm_manager_structured_outputs"] is True
    assert guidance["diagnostic_harness_must_not_infer_user_intent_by_keyword"] is True
    assert guidance["do_not_patch_cjk_keyword_intent_as_semantic_owner"] is True
    assert "all_chat_freeform_mutation_allowed" not in json.dumps(guidance, ensure_ascii=False)


def test_estimable_payload_no_commit_diagnostic_source_guardrails() -> None:
    source = Path("scripts/run_wave1_founder_e2e_estimable_payload_no_commit_diagnostic.py").read_text(
        encoding="utf-8"
    )

    assert "app.runtime.application.phase_a_context" not in source
    assert "matches_are_supporting_evidence_only" in source
    assert "must_not_override_active_trace_precedence" in source
    assert "semantic_owner_inversion" in source
    assert "do_not_patch_cjk_keyword_intent_as_semantic_owner" in source
    assert "all_chat_freeform" not in source
