from __future__ import annotations

import importlib
import json
from pathlib import Path


def test_calorie_deficit_logging_mvp_scope_is_repo_tracked() -> None:
    scope_path = Path("docs/quality/accurate_intake_calorie_deficit_mvp_scope.json")

    assert scope_path.exists()

    scope = json.loads(scope_path.read_text(encoding="utf-8"))
    assert scope["artifact_type"] == "accurate_intake_calorie_deficit_mvp_scope"
    assert scope["current_mainline"] == "Accurate Intake local web self-use MVP"
    assert scope["strategic_verdict"] == "mainline"
    assert scope["target_acceptance"] == "seven_day_local_dogfood"
    assert scope["active_pr93_live_profile"] == "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic"
    assert scope["deferred_target_live_profile"] == "builderspace-kimi-k2-5-accurate-intake-mvp-live-diagnostic"
    assert scope["claim_flags"] == {
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "production_selected": False,
        "mutation_rollout_approved": False,
        "model_portability_claimed": False,
    }
    assert scope["reviewer_policy"] == {
        "subagent_reviewer_required_after_live_or_provider_affecting_stage_count": "3_to_5",
        "subagent_reviewer_required_before_prompt_schema_or_contract_hardening": True,
        "reviewer_mode": "read_only",
        "reviewer_checks": [
            "canonical_rule_source",
            "legal_flow_or_holdout_coverage",
            "raw_text_routing_risk",
            "provider_overfit_risk",
            "readiness_overclaim",
            "global_mvp_goal_alignment",
        ],
    }
    assert scope["included_capabilities"] == [
        "free_text_intake",
        "current_session_conversation_context",
        "manager_owned_intent_and_workflow",
        "calorie_estimation",
        "food_log_commit",
        "correction_and_scoped_item_removal",
        "manual_daily_kcal_target",
        "today_consumed_and_remaining",
        "static_fastapi_fake_line_chat",
        "local_sqlite_persistence",
        "dogfood_trace_log",
    ]
    assert scope["dogfood_trace_lifecycle_policy"]["canonical_eval_case_requires"] == [
        "human_approval",
        "product_semantic_source",
        "stable_expected_behavior",
        "regression_test_or_eval_registration",
    ]
    assert scope["unsupported_free_text_policy"] == {
        "default_final_action": "answer_only",
        "default_answer_only_subtype": "general_guidance",
        "mutation_allowed": False,
        "target_change_allowed": False,
        "meal_plan_persistence_allowed": False,
        "reminder_creation_allowed": False,
        "product_capability_claimed": False,
    }
    assert scope["session_date_policy_mvp"] == {
        "default_active_date_source": "backend_local_today_or_current_active_date",
        "supported": ["today", "current_active_date"],
        "limited_or_unsupported": ["yesterday_backfill", "cross_midnight_assignment", "weekly_history_query"],
        "ambiguous_date_mutation_behavior": "block_mutation_or_ask_clarification",
    }
    assert scope["best_practice_evidence"]["adopted_guidance"] == [
        "log_traces_for_eval_case_mining",
        "use_human_feedback_to_calibrate_automated_scoring",
        "use_trace_grading_for_agent_error_identification",
    ]
    assert scope["best_practice_evidence"]["rejected_guidance"] == [
        "auto_promote_raw_production_trace_to_canonical_eval_truth"
    ]
    assert scope["excluded_capabilities"] == [
        "long_term_memory",
        "proactive_reminders",
        "rescue_or_recommendation",
        "production_database",
        "tavily_or_web_runtime_truth",
        "public_rollout",
        "production_default_manager_selection",
    ]
    assert scope["model_cost_strategy"] == {
        "grokfast_role": "low_cost_diagnostic_probe",
        "grokfast_is_target_production_model": False,
        "kimi_role": "deferred_target_model_validation",
        "kimi_provider_calls_before_target_validation_slice": False,
        "kimi_full_suite_hardening_allowed": False,
        "product_mainline_model_agnostic": True,
    }
    assert scope["deferred_kimi_validation_policy"]["allowed_in_deferred_validation_slice"] == [
        "provider_health_smoke",
        "schema_contract_probe",
        "fake_provider_active_runtime_gate",
        "selected_staged_probes",
        "cost_latency_capture",
        "failure_attribution",
    ]
    assert "full_suite_hardening_loop" in scope["deferred_kimi_validation_policy"][
        "not_allowed_before_deferred_validation_slice"
    ]


def test_kimi_target_profile_is_deferred_not_registered_in_pr93() -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")

    try:
        module.provider_profile("builderspace-kimi-k2-5-accurate-intake-mvp-live-diagnostic")
    except ValueError as exc:
        assert "Unsupported Accurate Intake live diagnostic provider profile" in str(exc)
    else:
        raise AssertionError("Kimi should stay deferred and unregistered during PR93")


def test_runbook_records_deferred_kimi_validation_without_full_suite_hardening() -> None:
    runbook_path = Path("docs/quality/ACCURATE_INTAKE_MVP_LIVE_DIAGNOSTIC_RUNBOOK.md")

    runbook = runbook_path.read_text(encoding="utf-8-sig")

    required_fragments = [
        "Kimi Deferred Target-Model Validation",
        "builderspace-kimi-k2-5-accurate-intake-mvp-live-diagnostic",
        "Do not run Kimi provider calls during PR93-PR100",
        "Kimi failure creates attribution and review records only",
        "Do not run a Kimi full-suite hardening loop before the deferred target-model validation slice",
        "After every 3-5 live/provider-affecting stages",
        "before any prompt/schema/contract hardening",
        "must not claim production/default selection or private self-use approval",
    ]
    for fragment in required_fragments:
        assert fragment in runbook


def test_manager_candidate_matrix_records_deferred_kimi_validation_boundary() -> None:
    matrix_path = Path("docs/provider/MANAGER_MODEL_CANDIDATE_MATRIX.md")

    matrix = matrix_path.read_text(encoding="utf-8-sig")

    required_fragments = [
        "Accurate Intake MVP Deferred Kimi Validation",
        "builderspace-kimi-k2-5-accurate-intake-mvp-live-diagnostic",
        "PR93-PR100 should not register Kimi as an active Accurate Intake live diagnostic runtime profile",
        "Kimi validation starts after the model-agnostic local web self-use loop is green",
        "Kimi remains outside production/default selection",
    ]
    for fragment in required_fragments:
        assert fragment in matrix


def test_grokfast_remains_low_cost_diagnostic_probe_for_pr93() -> None:
    module = importlib.import_module("scripts.run_accurate_intake_mvp_live_diagnostic")

    profile = module.provider_profile(module.DEFAULT_ACCURATE_INTAKE_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID)

    assert profile["provider_profile_id"] == "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic"
    assert profile["model"] == "grok-4-fast"
    assert profile["production_selected"] is False
    assert profile["not_production_selection"] is True
    assert profile["readiness_owner"] is False
