from __future__ import annotations

import importlib
import json
from pathlib import Path


def test_founder_e2e_runner_source_avoids_legacy_surfaces() -> None:
    runner_path = Path("scripts/run_wave1_founder_e2e_deterministic_diagnostic.py")
    source = runner_path.read_text(encoding="utf-8")

    forbidden_markers = (
        "app.runtime.application.phase_a_context",
        "old_" + "c001_" + "draft" + "_first_oracle",
        "C-001 " + "draft" + "-first",
        "run_v2_" + "bundle1" + "_live_eval",
        "run_v2_" + "bundle2" + "_live_eval",
        "run_wave1_phase_b_minimal_tool_loop_smoke",
        "docs/" + "archive",
    )
    for marker in forbidden_markers:
        assert marker not in source


def test_founder_fake_provider_emits_manager_semantic_decision_contract() -> None:
    module = importlib.import_module("scripts.run_wave1_founder_e2e_deterministic_diagnostic")
    provider = module.DeterministicFounderProvider()

    payload = provider._final(  # noqa: SLF001 - diagnostic fake provider contract is part of this runner.
        intent_type="log_meal",
        final_action="commit",
        workflow_effect="estimate_with_followup",
        response_summary="bounded estimate",
        target_attachment={"mode": "new_meal"},
    )

    semantic_decision = payload["semantic_decision"]
    assert semantic_decision["semantic_authority"] == "deterministic_fake_provider"
    assert semantic_decision["semantic_owner"] == "manager"
    assert semantic_decision["current_turn_intent"] == "log_meal"
    assert semantic_decision["workflow_effect"] == "estimate_with_followup"
    assert semantic_decision["final_action_candidate"] == "commit"
    assert semantic_decision["deterministic_role"] == "fixture_simulates_manager_output_only"


def test_founder_e2e_deterministic_diagnostic_artifact_contract(tmp_path: Path) -> None:
    module = importlib.import_module("scripts.run_wave1_founder_e2e_deterministic_diagnostic")
    output_path = tmp_path / "wave1_founder_e2e_deterministic_diagnostic.json"
    db_path = tmp_path / "wave1_founder_e2e.sqlite3"

    report = module.run_diagnostic(
        output_path=output_path,
        db_path=db_path,
        local_date="2026-04-30",
    )

    assert output_path.exists()
    persisted = json.loads(output_path.read_text(encoding="utf-8"))
    assert persisted == report
    db_path.unlink()
    assert not db_path.exists()
    assert report["artifact_type"] == "wave1_founder_e2e_deterministic_diagnostic"
    assert report["provider_mode"] == "deterministic"
    assert report["active_entrypoint"] == (
        "app.composition.intake_turn_orchestrator.execute_bundle1_turn"
    )
    assert report["active_entrypoint_verified"] is True
    assert report["live_llm_invoked"] is False
    assert report["tavily_live_invoked"] is False
    assert report["readiness_claimed"] is False
    assert report["exact_brand_web_positive_acceptance"] == "deferred_source_limitation"

    legacy_guard = report["legacy_guard"]
    assert legacy_guard == {
        "checked": True,
        "legacy_dependency_detected": False,
        "legacy_dependency_reason": None,
        "active_entrypoint": "app.composition.intake_turn_orchestrator.execute_bundle1_turn",
        "active_entrypoint_verified": True,
        "legacy_bundle_names_are_not_semantic_owners": True,
        "deprecated_phase_a_facade_used": False,
        "stale_oracle_used_as_truth": False,
        "compatibility_final_mapping_owner_used": False,
    }

    cases = report["cases"]
    assert [case["case_id"] for case in cases] == [
        "pearl_milk_tea_logged_followup",
        "luwei_ask_first",
        "generic_stable_tea_egg",
        "exact_brand_matsuya_beef_bowl",
        "query_only_pearl_milk_tea_calories",
        "correction_prior_pearl_milk_tea_half_sugar",
        "today_ledger_read_model",
    ]
    assert all(case["input"] for case in cases)
    assert all(case["expected_behavior"] for case in cases)
    assert all("manager_semantic_decision" in case["actual_behavior"] for case in cases)
    assert all("manager_semantic_decision" in case["final_mapping"] for case in cases)
    assert all(case["verdict"] in {"pass", "fail", "product_decision_required", "deferred"} for case in cases)
    assert all(
        set(
            [
                "case_id",
                "input",
                "expected_behavior",
                "actual_behavior",
                "verdict",
                "failure_layer",
                "phase_a",
                "b2",
                "final_mapping",
                "mutation",
                "ledger_read",
                "same_truth",
            ]
        ).issubset(case)
        for case in cases
    )
    assert not any(case["failure_layer"] == "legacy_dependency" for case in cases)
    tool_errors = [
        str(tool_result.get("error_message") or "")
        for case in cases
        for tool_result in case["b2"]["tool_results"]
        if tool_result.get("failure_family") == "tool_execution_error"
    ]
    assert "'ConversationRetrievalHit' object has no attribute 'role'" not in "\n".join(tool_errors)
    assert report["summary"]["pass_count"] + report["summary"]["fail_count"] + report["summary"][
        "product_decision_required_count"
    ] + report["summary"]["deferred_count"] == len(cases)
    assert isinstance(report["summary"]["failure_layers"], list)

    pearl = next(case for case in cases if case["case_id"] == "pearl_milk_tea_logged_followup")
    pearl_semantics = pearl["final_mapping"]["manager_semantic_decision"]
    assert pearl["verdict"] == "pass"
    assert pearl_semantics["followup_posture"] == "refinement_not_commit_gate"
    assert pearl_semantics["followup_question"]

    correction = next(case for case in cases if case["case_id"] == "correction_prior_pearl_milk_tea_half_sugar")
    assert correction["verdict"] == "pass"
    assert correction["mutation"]["state_delta"]["old_version_superseded"] is True
