from __future__ import annotations

import json
from pathlib import Path

from app.composition.current_shell_golden_set_request_trace_adapter import (
    build_golden_case_trace_from_request_trace,
    build_golden_trace_artifact_from_request_traces,
)
from app.composition.current_shell_golden_set_trace_adapter import grade_golden_case_trace
from scripts.build_current_shell_self_use_golden_trace_from_request_traces import (
    build_trace_artifact_from_specs,
    write_trace_artifact_from_specs,
)


def _gs5_request_trace() -> dict[str, object]:
    state_delta = {
        "meal_logged": False,
        "canonical_commit": False,
        "draft_saved": True,
        "new_meal_version_created": False,
        "old_version_superseded": False,
        "ledger_updated": False,
    }
    return {
        "request_id": "req-gs5-real",
        "trace_meta": {
            "request_id": "req-gs5-real",
            "bundle": "intake_execution",
            "local_date": "2026-05-14",
        },
        "request": {
            "user_id": "local-self-use-001",
            "local_date": "2026-05-14",
            "text": "breakfast teppan combo",
        },
        "phase_a_trace": {
            "current_turn_context": {
                "surface": "chat",
                "session_id": "session-gs5",
                "candidate_count": 0,
            },
            "attachment_decision": {"disposition": "create_new_workflow"},
            "transition_guard_result": {"verdict": "ask_followup_allowed"},
        },
        "react_trace": {
            "trace_schema_version": "manager_react_trace.v1",
            "manager_pass_count": 2,
            "manager_pass_1": {
                "manager_action": "call_tools",
                "workflow_effect": "ask_followup",
                "prompt_registry": {"manager_prompt_version": "v12"},
                "provider_trace": {
                    "provider": "builderspace_grokfast",
                    "provider_profile_id": "grokfast-self-use",
                    "live_llm_invoked": True,
                },
            },
            "requested_tools": ["estimate_nutrition"],
            "executed_tools": ["estimate_nutrition"],
            "manager_pass_final": {
                "manager_action": "final",
                "final_action": "ask_followup",
                "workflow_effect": "ask_followup",
            },
            "guard_result": {"ok": True},
            "tool_call_count": 1,
            "total_latency_ms": 12400,
        },
        "tool_plan": ["estimate_nutrition"],
        "tool_outputs": {
            "tool_results": [
                {
                    "tool_name": "estimate_nutrition",
                    "evidence": {
                        "nutrition_payload": {
                            "meal_title": "pending teppan combo",
                            "estimated_kcal": 0,
                            "trace_contract": {
                                "canonical_write_decision": {"can_write_canonical": False},
                                "manager_ask_followup_draft_contract": {
                                    "source": "manager_structured_final_action"
                                },
                            },
                        }
                    },
                    "confidence": "available",
                }
            ]
        },
        "manager_final_decision": {
            "workflow_effect": "ask_followup",
            "final_action": "ask_followup",
            "answer_contract": {
                "followup_question": "這份套餐有飲料、蛋或肉片嗎？",
                "assumed_slots": ["main", "egg_or_meat", "drink"],
            },
            "semantic_decision": {
                "semantic_authority": "manager",
                "current_turn_intent": "food_log",
                "workflow_effect": "ask_followup",
                "final_action_candidate": "ask_followup",
                "mutation_intent_candidate": "no_mutation",
            },
            "llm_used": True,
        },
        "state_delta": state_delta,
        "phase_c_trace": {
            "mutation_outcome": {
                "canonical_commit_status": "not_committed",
                "draft_status": "saved",
                "ledger_mutation_status": "not_updated",
                "meal_version_delta": "none",
                "macro_visibility_status": "hidden",
            },
            "same_truth_read_result": {
                "owner_alignment": "aligned",
                "consistency_flags": [],
            },
        },
        "renderer_output": {
            "assistant_message": "我先確認套餐內容：有飲料、蛋或肉片嗎？",
        },
        "sidecar_output": {"state_mutation_summary": state_delta},
        "runtime": {
            "fallback_400_allowed": False,
            "pending_followup_saved": True,
            "assumed_slot_question_required": True,
        },
        "response": {
            "zh_tw_primary": True,
            "internal_debug_words_present": False,
            "state_contradiction": False,
            "invented_nutrition_fact": False,
        },
        "feedback_linkage": {"feedback_links_to_trace": True},
        "latency_tracking": {
            "total_duration_ms": 13000,
            "stage_timings": [{"stage": "manager_loop", "duration_ms": 12000}],
        },
    }


def test_request_trace_adapter_projects_structured_runtime_trace_without_text_semantics() -> None:
    case_trace = build_golden_case_trace_from_request_trace("GS5", _gs5_request_trace())

    assert case_trace["case_id"] == "GS5"
    assert case_trace["trace_id"] == "req-gs5-real"
    assert case_trace["runtime"]["workflow_effect"] == "ask_followup"
    assert case_trace["runtime"]["mutation_allowed"] is False
    assert case_trace["ui"]["today_consumed_updates"] is False
    assert case_trace["ui"]["pending_question_visible"] is True
    assert case_trace["latency"]["llm_calls"] == 2
    assert case_trace["latency"]["tool_calls"] == 1

    grade = grade_golden_case_trace("GS5", case_trace)
    assert grade["status"] == "pass"


def test_request_trace_adapter_does_not_infer_from_raw_request_text() -> None:
    case_trace = build_golden_case_trace_from_request_trace(
        "GS5",
        {
            "request_id": "req-raw-only",
            "request": {"text": "breakfast teppan combo"},
        },
    )

    grade = grade_golden_case_trace("GS5", case_trace)

    assert grade["status"] == "blocked"
    assert "runtime.workflow_effect_expected:ask_followup_actual:None" in grade["blockers"]
    assert "trace_layers.manager_pass_1_decision_missing" in grade["blockers"]


def test_request_trace_adapter_projects_target_ambiguity_from_validator_trace_only() -> None:
    trace = _gs5_request_trace()
    trace["request"] = {
        "user_id": "local-self-use-001",
        "local_date": "2026-05-14",
        "text": "早餐那筆刪掉",
    }
    trace["manager_final_decision"] = {
        "workflow_effect": "ask_followup",
        "final_action": "ask_followup",
        "answer_contract": {"followup_question": "請確認要刪除哪一筆早餐？"},
        "semantic_decision": {
            "semantic_authority": "manager_llm",
            "current_turn_intent": "correct_meal",
            "target_attachment": {"operation": "remove_meal"},
            "workflow_effect": "ask_followup",
            "final_action_candidate": "ask_followup",
            "followup_posture": "target_clarification",
            "mutation_intent_candidate": "no_mutation",
            "uncertainty_posture": "target_ambiguous",
            "source": "live_manager_structured_output",
        },
    }
    trace["tool_outputs"] = {
        "tool_results": [
            {
                "tool_name": "resolve_correction_target",
                "provenance": {
                    "correction_target": {
                        "manager_target_proposal_validation": {
                            "status": "rejected",
                            "failure_family": "manager_thread_target_proposal_ambiguous",
                            "target_candidates_supplied": True,
                            "deterministic_target_choice_allowed": False,
                        }
                    }
                },
            }
        ]
    }

    case_trace = build_golden_case_trace_from_request_trace("GS13", trace)

    assert case_trace["runtime"]["target_candidates_supplied"] is True
    assert case_trace["runtime"]["deterministic_target_choice_allowed"] is False


def test_request_trace_adapter_projects_remaining_query_from_budget_read_model_only() -> None:
    trace = _gs5_request_trace()
    trace["request"] = {
        "user_id": "local-self-use-001",
        "local_date": "2026-05-14",
        "text": "我今天熱量還剩多少卡",
    }
    trace["state_delta"] = {
        "meal_logged": False,
        "canonical_commit": False,
        "draft_saved": False,
        "new_meal_version_created": False,
        "old_version_superseded": False,
        "ledger_updated": False,
    }
    trace["tool_outputs"] = {
        "remaining_budget": {
            "status": "ready",
            "daily_target_kcal": 1600,
            "consumed_kcal": 420,
            "remaining_kcal": 1180,
        }
    }
    trace["state_after"] = {
        "current_budget_view": {
            "budget_kcal": 1600,
            "consumed_kcal": 420,
            "remaining_kcal": 1180,
            "source": "current_budget_view",
        }
    }
    trace["manager_final_decision"] = {
        "workflow_effect": "answer_only",
        "final_action": "answer_remaining_budget",
        "answer_contract": {
            "reply_text": "今天還剩 1180 卡。",
            "answer_basis": {"budget_summary": "remaining from read model"},
        },
        "semantic_decision": {
            "semantic_authority": "manager_llm",
            "current_turn_intent": "answer_remaining_budget",
            "target_attachment": {},
            "workflow_effect": "answer_only",
            "final_action_candidate": "answer_remaining_budget",
            "mutation_intent_candidate": "no_mutation",
            "source": "budget_read_model",
        },
    }

    case_trace = build_golden_case_trace_from_request_trace("GS14", trace)

    assert case_trace["runtime"]["remaining_source"] == "budget_read_model"
    assert case_trace["runtime"]["rescue_plan_allowed"] is False
    assert case_trace["ui"]["chat_today_same_truth_required"] is True
    assert case_trace["ui"]["frontend_remaining_math_allowed"] is False


def test_request_trace_adapter_projects_no_plan_degraded_remaining_query() -> None:
    trace = _gs5_request_trace()
    trace["request"] = {
        "user_id": "local-self-use-001",
        "local_date": "2026-05-14",
        "text": "今天還剩多少",
    }
    trace["state_delta"] = {
        "meal_logged": False,
        "canonical_commit": False,
        "draft_saved": False,
        "new_meal_version_created": False,
        "old_version_superseded": False,
        "ledger_updated": False,
    }
    trace["react_trace"] = {
        "manager_pass_count": 1,
        "tool_call_count": 0,
        "manager_pass_1": {
            "manager_action": "final",
            "workflow_effect": "answer_only",
            "final_action": "onboarding_required",
            "tool_calls": [],
        },
        "manager_pass_final": {
            "manager_action": "final",
            "workflow_effect": "answer_only",
            "final_action": "onboarding_required",
            "tool_calls": [],
        },
    }
    trace["tool_outputs"] = {
        "remaining_budget": {
            "status": "onboarding_required",
            "daily_target_kcal": None,
            "consumed_kcal": 0,
            "remaining_kcal": None,
        }
    }
    trace["state_after"] = {
        "active_body_plan_view": {
            "body_plan_id": None,
            "plan_status": "inactive",
            "profile_status": "missing",
            "daily_budget_kcal": 0,
            "estimated_tdee": 0,
        },
        "current_budget_view": {
            "budget_kcal": 0,
            "consumed_kcal": 0,
            "remaining_kcal": 0,
            "source": "current_budget_view",
        },
    }
    trace["manager_final_decision"] = {
        "workflow_effect": "answer_only",
        "final_action": "onboarding_required",
        "answer_contract": {
            "reply_text": "目前尚未設定每日熱量目標，請先完成設定。",
            "answer_basis": {"budget_summary": "no active body plan"},
        },
        "semantic_decision": {
            "semantic_authority": "manager_llm",
            "current_turn_intent": "answer_remaining_budget",
            "target_attachment": {},
            "workflow_effect": "answer_only",
            "final_action_candidate": "onboarding_required",
            "mutation_intent_candidate": "no_mutation",
            "source": "read_model",
        },
    }

    case_trace = build_golden_case_trace_from_request_trace("GS15", trace)
    grade = grade_golden_case_trace("GS15", case_trace)

    assert case_trace["runtime"]["invented_tdee_or_remaining_allowed"] is False
    assert case_trace["runtime"]["guide_to_body_setup"] is True
    assert case_trace["ui"]["today_degraded_state_visible"] is True
    assert case_trace["ui"]["frontend_remaining_math_allowed"] is False
    assert grade["status"] == "pass"


def test_request_trace_adapter_projects_body_observation_write_from_tool_result_only() -> None:
    trace = _gs5_request_trace()
    trace["request"] = {"text": "raw text must not decide body observation semantics"}
    trace["state_delta"] = {
        "meal_logged": False,
        "canonical_commit": False,
        "draft_saved": False,
        "new_meal_version_created": False,
        "old_version_superseded": False,
        "ledger_updated": False,
        "body_observation_recorded": True,
    }
    trace["manager_decision"] = {
        "intent_type": "body_observation",
        "workflow_effect": "record_weight",
        "final_action": "answer_only",
        "answer_contract": {"reply_text": "Recorded today's weight."},
        "tool_results": [
            {
                "tool_name": "body.record_observation",
                "evidence": {
                    "recorded_body_observation": {
                        "observation_type": "weight",
                        "value": 84.0,
                        "unit": "kg",
                        "local_date": "2026-05-14",
                    }
                },
                "mutation_result": {
                    "status": "recorded",
                    "body_observation_recorded": True,
                    "body_plan_mutated": False,
                    "ledger_mutated": False,
                },
                "provenance": {"canonical_tool_name": "body.record_observation"},
            }
        ],
    }
    trace["manager_final_decision"] = trace["manager_decision"]
    trace["runtime"] = {}
    trace["phase_c_trace"] = {}
    trace["tool_outputs"] = {
        "persistence_result": trace["manager_decision"]["tool_results"][0],
    }
    trace["state_after"] = {
        "active_body_plan_view": {
            "body_plan_id": 1,
            "plan_status": "active",
            "profile_status": "ready",
        },
    }

    case_trace = build_golden_case_trace_from_request_trace("GS16", trace)
    grade = grade_golden_case_trace("GS16", case_trace)

    assert case_trace["runtime"]["mutation_allowed"] is True
    assert case_trace["runtime"]["body_plan_rewrite_allowed"] is False
    assert case_trace["runtime"]["manager_tdee_math_allowed"] is False
    assert case_trace["ui"]["latest_weight_visible"] is True
    assert case_trace["ui"]["weight_history_date_scoped"] is True
    assert case_trace["ui"]["body_plan_date_scoped"] is False
    assert case_trace["ui"]["body_form_prefilled_from_saved_truth"] is True
    assert case_trace["ui"]["frontend_tdee_math_allowed"] is False
    assert grade["status"] == "pass"


def test_request_trace_adapter_projects_manager_owned_blocking_basket_outcome() -> None:
    trace = _gs5_request_trace()
    trace.pop("runtime", None)
    trace["tool_outputs"] = {"tool_results": []}
    trace["react_trace"] = {
        "manager_pass_count": 1,
        "tool_call_count": 0,
        "manager_pass_1": {
            "manager_action": "final",
            "workflow_effect": "ask_followup",
            "final_action": "ask_followup",
            "tool_calls": [],
        },
        "manager_pass_final": {
            "manager_action": "final",
            "workflow_effect": "ask_followup",
            "final_action": "ask_followup",
            "tool_calls": [],
        },
    }
    trace["manager_final_decision"] = {
        "workflow_effect": "ask_followup",
        "final_action": "ask_followup",
        "answer_contract": {"followup_question": "請列出自助餐的具體食物和份量"},
        "semantic_decision": {
            "semantic_authority": "manager_llm",
            "current_turn_intent": "log_meal",
            "workflow_effect": "ask_followup",
            "final_action_candidate": "ask_followup",
            "estimation_posture": "composition_unknown_basket",
            "followup_posture": "blocking_composition_clarification",
            "mutation_intent_candidate": "no_mutation",
            "source": "self_selected_basket_without_listed_items",
            "retrieval_goal": "none",
        },
    }
    trace["renderer_output"] = {
        "assistant_message": "自助餐的內容很多元，請告訴我你吃了哪些具體食物和大概份量。"
    }

    case_trace = build_golden_case_trace_from_request_trace("GS6", trace)
    grade = grade_golden_case_trace("GS6", case_trace)

    assert case_trace["runtime"]["one_bundled_question_required"] is True
    assert case_trace["runtime"]["estimate_allowed"] is False
    assert grade["status"] == "pass"


def test_request_trace_adapter_preserves_fixture_provider_blocker() -> None:
    trace = _gs5_request_trace()
    react_trace = dict(trace["react_trace"])  # type: ignore[index]
    pass_1 = dict(react_trace["manager_pass_1"])  # type: ignore[index]
    pass_1["provider_trace"] = {
        "provider": "deterministic_self_use_manager_fixture",
        "live_llm_invoked": False,
    }
    react_trace["manager_pass_1"] = pass_1
    trace["react_trace"] = react_trace

    case_trace = build_golden_case_trace_from_request_trace("GS5", trace)
    grade = grade_golden_case_trace("GS5", case_trace)

    assert grade["status"] == "blocked"
    assert "fixture_decisions.intent_not_allowed" in grade["blockers"]
    assert "fixture_decisions.action_not_allowed" in grade["blockers"]


def test_request_trace_adapter_blocks_pre_manager_guard_feedback_shortcut() -> None:
    trace = _gs5_request_trace()
    react_trace = dict(trace["react_trace"])  # type: ignore[index]
    pass_1 = dict(react_trace["manager_pass_1"])  # type: ignore[index]
    pass_1["guard_feedback_input"] = {"failure_family": "nutrition_evidence_not_commit_eligible"}
    react_trace["manager_pass_1"] = pass_1
    trace["react_trace"] = react_trace

    case_trace = build_golden_case_trace_from_request_trace("GS5", trace)
    grade = grade_golden_case_trace("GS5", case_trace)

    assert grade["status"] == "blocked"
    assert "runtime.pre_manager_estimability_shortcut_allowed_expected:False_actual:True" in grade["blockers"]


def test_request_trace_adapter_projects_non_commit_implausible_kcal_flags_from_trace_outcome() -> None:
    trace = _gs5_request_trace()
    trace["request"] = {"text": "unrelated text must not decide GS3 semantics"}
    trace["runtime"] = {}
    manager_final = dict(trace["manager_final_decision"])  # type: ignore[index]
    manager_final["final_action"] = "ask_followup"
    manager_final["workflow_effect"] = "ask_followup"
    manager_final["semantic_decision"] = {
        "semantic_authority": "manager",
        "source": "named_food_user_kcal_conflict",
        "user_provided_kcal": 250,
        "workflow_effect": "ask_followup",
        "final_action_candidate": "ask_followup",
        "mutation_intent_candidate": "no_mutation",
    }
    trace["manager_final_decision"] = manager_final
    trace["state_delta"] = {
        "canonical_commit": False,
        "ledger_updated": False,
        "draft_saved": True,
    }
    trace["phase_c_trace"] = {
        "mutation_outcome": {
            "canonical_commit_status": "not_committed",
            "ledger_mutation_status": "not_updated",
            "draft_status": "saved",
        }
    }

    case_trace = build_golden_case_trace_from_request_trace("GS3", trace)

    assert case_trace["runtime"]["workflow_effect"] == "ask_followup"
    assert case_trace["runtime"]["mutation_allowed"] is False
    assert case_trace["runtime"]["silent_accept_implausible_kcal_allowed"] is False
    assert case_trace["runtime"]["override_with_system_estimate_allowed"] is False


def test_request_trace_adapter_detects_live_provider_from_final_manager_pass() -> None:
    trace = _gs5_request_trace()
    react_trace = dict(trace["react_trace"])  # type: ignore[index]
    pass_1 = dict(react_trace["manager_pass_1"])  # type: ignore[index]
    pass_1["provider_trace"] = {}
    final_pass = dict(react_trace["manager_pass_final"])  # type: ignore[index]
    final_pass["provider_trace"] = {
        "provider": "builderspace",
        "provider_profile_id": "grokfast-self-use",
        "live_llm_invoked": True,
        "semantic_owner": "manager_llm",
    }
    react_trace["manager_pass_1"] = pass_1
    react_trace["manager_pass_final"] = final_pass
    trace["react_trace"] = react_trace

    case_trace = build_golden_case_trace_from_request_trace("GS5", trace)

    assert case_trace["manager_provider"]["provider"] == "builderspace"
    assert case_trace["manager_provider"]["live_llm_invoked"] is True
    assert case_trace["manager_provider"]["semantic_owner"] == "manager_llm"


def test_request_trace_adapter_projects_gs9_answer_query_from_manager_decision_trace() -> None:
    trace = {
        "request_id": "req-gs9-real",
        "request": {"text": "basis inquiry must not be parsed by the adapter"},
        "manager_decision": {
            "workflow_effect": "answer_only",
            "final_action": "answer_only",
            "answer_contract": {
                "reply_text": "I used the active meal basis snapshot and did not change the meal.",
                "answer_basis": "active_meal_estimate_basis total 620 kcal from component evidence.",
                "references_active_meal": True,
            },
            "semantic_decision": {
                "semantic_authority": "manager_llm",
                "current_turn_intent": "answer_query",
                "workflow_effect": "answer_only",
                "final_action_candidate": "answer_only",
                "mutation_intent_candidate": "no_mutation",
                "estimation_posture": "basis_explained",
                "source": "active_meal_estimate_basis",
            },
            "trace": {
                "prompt_registry": {"system_prompt_version": "v26"},
                "react_trace": {
                    "manager_pass_count": 1,
                    "tool_call_count": 0,
                    "manager_pass_1": {
                        "manager_action": "final",
                        "workflow_effect": "answer_only",
                        "provider_trace": {
                            "provider": "builderspace",
                            "model": "grok-4-fast",
                            "request_payload": {"messages": []},
                        },
                    },
                    "requested_tools": [],
                    "executed_tools": [],
                },
            },
        },
        "state_delta": {
            "canonical_commit": False,
            "ledger_updated": False,
            "new_meal_version_created": False,
            "old_version_superseded": False,
        },
        "renderer_output": {
            "assistant_message": "I used the active meal basis snapshot and did not change the meal."
        },
        "feedback_linkage": {"feedback_links_to_trace": True},
    }

    case_trace = build_golden_case_trace_from_request_trace("GS9", trace)
    grade = grade_golden_case_trace("GS9", case_trace)

    assert case_trace["react_trace"]["manager_pass_1"]["workflow_effect"] == "answer_only"
    assert case_trace["manager_provider"]["provider"] == "builderspace"
    assert case_trace["runtime"]["inquiry_may_be_treated_as_correction"] is False
    assert case_trace["runtime"]["estimate_basis_required"] is True
    assert case_trace["ui"]["existing_meal_unchanged"] is True
    assert grade["status"] == "pass"


def test_request_trace_adapter_projects_manager_owned_optional_drink_refinement() -> None:
    request_trace = {
        "trace_id": "trace-gs10",
        "manager_decision": {
            "workflow_effect": "canonical_write",
            "final_action": "commit",
            "semantic_decision": {
                "current_turn_intent": "log_meal",
                "workflow_effect": "canonical_write",
                "mutation_intent_candidate": "canonical_write",
                "followup_posture": "refinement_optional",
                "followup_question": "如果紅茶的糖度或杯型不同，可以補充，我會幫你修正。",
                "listed_items": ["鐵板麵", "紅茶"],
            },
            "answer_contract": {
                "followup_question": "如果紅茶的糖度或杯型不同，可以補充，我會幫你修正。"
            },
            "trace": {
                "react_trace": {
                    "manager_pass_1": {"manager_action": "call_tools"},
                    "requested_tools": ["estimate_nutrition"],
                    "executed_tools": ["estimate_nutrition"],
                }
            },
        },
        "manager_final_decision": {
            "workflow_effect": "canonical_write",
            "final_action": "commit",
            "semantic_decision": {
                "current_turn_intent": "log_meal",
                "workflow_effect": "canonical_write",
                "mutation_intent_candidate": "canonical_write",
                "followup_posture": "refinement_optional",
                "followup_question": "如果紅茶的糖度或杯型不同，可以補充，我會幫你修正。",
                "listed_items": ["鐵板麵", "紅茶"],
            },
            "answer_contract": {
                "followup_question": "如果紅茶的糖度或杯型不同，可以補充，我會幫你修正。"
            },
        },
        "compact_packets": [
            {
                "tool_name": "estimate_nutrition",
                "evidence": {
                    "nutrition_payload": {
                        "trace_contract": {
                            "optional_refinement_allowed": True,
                            "optional_refinement_targets": ["紅茶"],
                            "optional_refinement_question": (
                                "如果紅茶的糖度或杯型不同，可以補充，我會幫你修正。"
                            ),
                        }
                    }
                },
            }
        ],
        "phase_c_trace": {
            "mutation_outcome": {
                "canonical_commit_status": "committed",
                "ledger_mutation_status": "updated",
            }
        },
        "state_delta": {"canonical_commit": True, "ledger_updated": True},
        "renderer_output": {"assistant_message": "已記錄，若紅茶糖度或杯型不同可以補充。"},
    }

    case_trace = build_golden_case_trace_from_request_trace("GS10", request_trace)

    assert case_trace["runtime"]["optional_tea_refinement_allowed"] is True


def test_request_trace_adapter_defaults_configured_provider_trace_to_live_invoked() -> None:
    trace = _gs5_request_trace()
    react_trace = dict(trace["react_trace"])  # type: ignore[index]
    pass_1 = dict(react_trace["manager_pass_1"])  # type: ignore[index]
    pass_1["provider_trace"] = {}
    final_pass = dict(react_trace["manager_pass_final"])  # type: ignore[index]
    final_pass["provider_trace"] = {
        "provider": "builderspace",
        "model": "grok-4-fast",
        "request_payload": {"messages": []},
    }
    react_trace["manager_pass_1"] = pass_1
    react_trace["manager_pass_final"] = final_pass
    trace["react_trace"] = react_trace

    case_trace = build_golden_case_trace_from_request_trace("GS5", trace)

    assert case_trace["manager_provider"]["provider"] == "builderspace"
    assert case_trace["manager_provider"]["live_llm_invoked"] is True


def test_request_trace_adapter_blocks_visible_kcal_when_fallback_400_is_not_allowed() -> None:
    trace = _gs5_request_trace()
    trace["renderer_output"] = {"assistant_message": "About 400 kcal. What was in the combo?"}

    case_trace = build_golden_case_trace_from_request_trace("GS5", trace)
    grade = grade_golden_case_trace("GS5", case_trace)

    assert case_trace["runtime"]["fallback_400_allowed"] is False
    assert case_trace["response"]["invented_nutrition_fact"] is True
    assert "response.invented_nutrition_fact" in grade["blockers"]


def test_request_trace_adapter_projects_component_basis_from_approved_packet() -> None:
    trace = _gs5_request_trace()
    trace["runtime"] = {"fallback_400_allowed": False}
    trace["renderer_output"] = {"assistant_message": "Recorded 650 kcal from component evidence."}
    trace["tool_outputs"] = {
        "tool_results": [
            {
                "tool_name": "estimate_nutrition",
                "evidence": {
                    "nutrition_payload": {
                        "meal_title": "component meal",
                        "estimated_kcal": 650,
                        "components": [
                            {"name": "noodle", "estimated_kcal": 430},
                            {"name": "egg", "estimated_kcal": 90},
                        ],
                        "trace_contract": {
                            "db_hit_type": "approved_fooddb_packet",
                            "shadow_stub": False,
                            "approved_fooddb_evidence_trace": {
                                "source_lane": "listed_component",
                                "runtime_truth_allowed": True,
                            },
                            "canonical_write_decision": {"can_write_canonical": True},
                        },
                    }
                },
            }
        ]
    }
    trace["phase_c_trace"]["mutation_outcome"]["canonical_commit_status"] = "committed"  # type: ignore[index]
    trace["phase_c_trace"]["mutation_outcome"]["ledger_mutation_status"] = "updated"  # type: ignore[index]
    trace["state_delta"]["canonical_commit"] = True  # type: ignore[index]
    trace["state_delta"]["ledger_updated"] = True  # type: ignore[index]
    trace["renderer_input_basis"] = {
        "state_after": {
            "active_meal": {
                "item_candidates": [{"canonical_name": "noodle"}, {"canonical_name": "egg"}]
            }
        }
    }

    case_trace = build_golden_case_trace_from_request_trace("GS1", trace)

    assert case_trace["runtime"]["component_basis_required"] is True
    assert case_trace["runtime"]["fallback_400_allowed"] is False
    assert case_trace["ui"]["meal_level_basis_visible"] is True
    assert case_trace["response"].get("invented_nutrition_fact") is not True


def test_request_trace_adapter_projects_generic_range_basis_from_approved_packet() -> None:
    trace = _gs5_request_trace()
    trace["runtime"] = {"fallback_400_allowed": False}
    trace["renderer_output"] = {
        "assistant_message": "已記錄：雞肉飯 560 kcal。這餐約 560 kcal。以常見份量估算，參考範圍 450-700 kcal。今天還剩約 752 kcal。"
    }
    trace["tool_outputs"] = {
        "tool_results": [
            {
                "tool_name": "estimate_nutrition",
                "evidence": {
                    "nutrition_payload": {
                        "meal_title": "雞肉飯",
                        "estimated_kcal": 560,
                        "component_breakdown": [
                            {
                                "name": "雞肉飯",
                                "estimated_kcal": 560,
                                "source_lane": "generic_common_serving",
                                "kcal_range": [450, 700],
                            }
                        ],
                        "trace_contract": {
                            "db_hit_type": "approved_fooddb_packet",
                            "shadow_stub": False,
                            "approved_fooddb_evidence_trace": {
                                "source_lane": "generic_common_serving",
                                "runtime_truth_allowed": True,
                                "kcal_range": [450, 700],
                            },
                            "canonical_write_decision": {"can_write_canonical": True},
                        },
                    }
                },
            }
        ]
    }
    trace["phase_c_trace"]["mutation_outcome"]["canonical_commit_status"] = "committed"  # type: ignore[index]
    trace["phase_c_trace"]["mutation_outcome"]["ledger_mutation_status"] = "updated"  # type: ignore[index]
    trace["state_delta"]["canonical_commit"] = True  # type: ignore[index]
    trace["state_delta"]["ledger_updated"] = True  # type: ignore[index]

    case_trace = build_golden_case_trace_from_request_trace("GS4", trace)

    assert case_trace["runtime"]["uncertainty_basis_required"] is True
    assert case_trace["runtime"]["fake_exactness_allowed"] is False
    assert case_trace["ui"]["range_or_basis_visible"] is True


def test_request_trace_adapter_projects_component_basis_from_compact_packets() -> None:
    trace = _gs5_request_trace()
    trace["runtime"] = {"fallback_400_allowed": False}
    trace.pop("tool_outputs", None)
    trace["renderer_output"] = {"assistant_message": "已記錄這餐約 650 kcal。"}
    trace["compact_packets"] = [
        {
            "tool_name": "estimate_nutrition",
            "evidence": {
                "nutrition_payload": {
                    "meal_title": "鐵板麵 + 荷包蛋 + 豬肉片",
                    "estimated_kcal": 650,
                    "trace_contract": {
                        "db_hit_type": "approved_fooddb_packet",
                        "approved_fooddb_evidence_trace": {
                            "source_lane": "listed_component",
                            "runtime_truth_allowed": True,
                            "evidence_ids": [
                                "local_component_stub:鐵板麵",
                                "local_component_stub:荷包蛋",
                                "local_component_stub:早餐店豬肉片",
                            ],
                        },
                        "commit_request_candidate": {
                            "components": [
                                {"name": "鐵板麵", "estimated_kcal": 430},
                                {"name": "荷包蛋", "estimated_kcal": 90},
                                {"name": "早餐店豬肉片", "estimated_kcal": 130},
                            ]
                        },
                    },
                }
            },
        }
    ]
    trace["phase_c_trace"]["mutation_outcome"]["canonical_commit_status"] = "committed"  # type: ignore[index]
    trace["phase_c_trace"]["mutation_outcome"]["ledger_mutation_status"] = "updated"  # type: ignore[index]
    trace["state_delta"]["canonical_commit"] = True  # type: ignore[index]
    trace["state_delta"]["ledger_updated"] = True  # type: ignore[index]
    trace["renderer_input_basis"] = {
        "state_after": {
            "active_meal": {
                "item_candidates": [
                    {"canonical_name": "鐵板麵"},
                    {"canonical_name": "荷包蛋"},
                    {"canonical_name": "早餐店豬肉片"},
                ]
            }
        }
    }

    case_trace = build_golden_case_trace_from_request_trace("GS1", trace)

    assert case_trace["runtime"]["component_basis_required"] is True
    assert case_trace["runtime"]["fallback_400_allowed"] is False
    assert case_trace["ui"]["meal_level_basis_visible"] is True
    assert case_trace["response"].get("invented_nutrition_fact") is not True


def test_request_trace_adapter_projects_gs7_pending_listed_component_commit() -> None:
    trace = _gs5_request_trace()
    trace["runtime"] = {"fallback_400_allowed": False}
    trace["manager_final_decision"] = {
        "workflow_effect": "canonical_write",
        "final_action": "commit",
        "answer_contract": {"reply_text": "已記錄這份自助餐，約 710 kcal。"},
        "semantic_decision": {
            "semantic_authority": "manager_llm",
            "current_turn_intent": "log_meal",
            "workflow_effect": "canonical_write",
            "final_action_candidate": "commit",
            "target_attachment": {
                "operation": "attach_to_pending_followup",
                "target_resolution_source": "pending_followup_state",
            },
            "listed_items": ["rice", "chicken", "greens", "egg"],
            "retrieval_goal": "listed_item_lookup",
        },
    }
    trace["tool_outputs"] = {
        "tool_results": [
            {
                "tool_name": "estimate_nutrition",
                "evidence": {
                    "nutrition_payload": {
                        "meal_title": "rice + chicken + greens + egg",
                        "estimated_kcal": 710,
                        "component_breakdown": [
                            {"name": "rice", "estimated_kcal": 180},
                            {"name": "chicken", "estimated_kcal": 320},
                            {"name": "greens", "estimated_kcal": 120},
                            {"name": "egg", "estimated_kcal": 90},
                        ],
                        "trace_contract": {
                            "db_hit_type": "approved_fooddb_packet",
                            "shadow_stub": False,
                            "approved_fooddb_evidence_trace": {
                                "source_lane": "listed_component",
                                "runtime_truth_allowed": True,
                                "retrieval_boundary": "listed_basket_component_recall",
                                "evidence_ids": [
                                    "listed_component_white_rice_half_bowl",
                                    "listed_component_chicken_leg_one",
                                    "listed_component_greens_two_servings",
                                    "listed_component_braised_egg_one",
                                ],
                            },
                            "commit_request_candidate": {
                                "components": [
                                    {"name": "rice", "estimated_kcal": 180},
                                    {"name": "chicken", "estimated_kcal": 320},
                                    {"name": "greens", "estimated_kcal": 120},
                                    {"name": "egg", "estimated_kcal": 90},
                                ]
                            },
                        },
                    }
                },
            }
        ]
    }
    trace["phase_c_trace"]["mutation_outcome"]["canonical_commit_status"] = "committed"  # type: ignore[index]
    trace["phase_c_trace"]["mutation_outcome"]["ledger_mutation_status"] = "updated"  # type: ignore[index]
    trace["state_delta"]["canonical_commit"] = True  # type: ignore[index]
    trace["state_delta"]["ledger_updated"] = True  # type: ignore[index]
    trace["renderer_input_basis"] = {
        "state_after": {
            "active_meal": {
                "item_candidates": [
                    {"canonical_name": "rice"},
                    {"canonical_name": "chicken"},
                    {"canonical_name": "greens"},
                    {"canonical_name": "egg"},
                ]
            }
        }
    }

    case_trace = build_golden_case_trace_from_request_trace("GS7", trace)
    grade = grade_golden_case_trace("GS7", case_trace)

    assert case_trace["runtime"]["component_estimate_required"] is True
    assert case_trace["ui"]["meal_components_visible"] is True
    assert grade["status"] == "pass"


def test_request_trace_adapter_projects_gs8_optional_refinement_supersede() -> None:
    trace = _gs5_request_trace()
    trace["runtime"] = {"fallback_400_allowed": False}
    trace["manager_final_decision"] = {
        "workflow_effect": "canonical_write",
        "final_action": "correction_applied",
        "answer_contract": {"reply_text": "已更新上一筆餐點：珍珠奶茶中杯半糖，約 450 kcal。"},
        "semantic_decision": {
            "semantic_authority": "manager_llm",
            "current_turn_intent": "correct_meal",
            "workflow_effect": "canonical_write",
            "final_action_candidate": "correction_applied",
            "target_attachment": {
                "meal_thread_id": 2,
                "meal_item_id": 2,
                "canonical_name": "珍珠奶茶",
                "target_resolution_source": "active_meal_view",
                "operation": "refine_item",
            },
            "mutation_intent_candidate": "correction_write",
            "base_dish": "珍珠奶茶",
            "size_hint": "中杯",
            "modifier_hints": ["半糖"],
        },
    }
    trace["phase_c_trace"]["mutation_outcome"].update(  # type: ignore[index, union-attr]
        {
            "canonical_commit_status": "committed",
            "ledger_mutation_status": "updated",
            "meal_version_delta": "superseded_previous",
            "canonical_ids": {"meal_version_id": 3, "superseded_version_id": 2},
        }
    )
    trace["state_delta"].update(  # type: ignore[union-attr]
        {
            "canonical_commit": True,
            "ledger_updated": True,
            "draft_saved": False,
            "old_version_superseded": True,
            "new_meal_version_created": True,
        }
    )
    trace["tool_outputs"] = {
        "tool_results": [
            {
                "tool_name": "estimate_nutrition",
                "evidence": {
                    "nutrition_payload": {
                        "meal_title": "珍珠奶茶",
                        "estimated_kcal": 450,
                        "trace_contract": {
                            "db_hit_type": "approved_fooddb_packet",
                            "shadow_stub": False,
                            "approved_fooddb_evidence_trace": {
                                "source_lane": "generic_common_serving",
                                "runtime_truth_allowed": True,
                                "kcal_range": [350, 550],
                            },
                            "canonical_write_decision": {"can_write_canonical": True},
                        },
                    }
                },
            }
        ]
    }
    trace["renderer_output"] = {
        "assistant_message": "已更新上一筆餐點：珍珠奶茶 450 kcal。今天還剩約 862 kcal。"
    }
    trace["sidecar_output"] = {
        "ui": {
            "today": {
                "consumed_kcal": 450,
                "meals": [{"meal_version_id": 3, "meal_title": "珍珠奶茶"}],
            }
        }
    }

    case_trace = build_golden_case_trace_from_request_trace("GS8", trace)
    grade = grade_golden_case_trace("GS8", case_trace)

    assert case_trace["runtime"]["old_version_superseded"] is True
    assert case_trace["runtime"]["ledger_delta_trace_required"] is True
    assert case_trace["ui"]["old_version_not_counted"] is True
    assert grade["status"] == "pass"


def test_request_trace_adapter_projects_gs11_thread_level_correction_ledger_recompute() -> None:
    trace = _gs5_request_trace()
    trace["runtime"] = {"fallback_400_allowed": False}
    trace["manager_final_decision"] = {
        "workflow_effect": "correction_applied",
        "final_action": "correction_applied",
        "target_attachment": {
            "meal_thread_id": 5,
            "operation": "correct_active_meal",
            "correction_operation": "correct_active_meal",
            "target_resolution_source": "tool_result_validated",
        },
        "answer_contract": {"reply_text": "已修正上一筆餐點，今天剩餘熱量已更新。"},
        "semantic_decision": {
            "semantic_authority": "manager_llm",
            "current_turn_intent": "correct_meal",
            "workflow_effect": "correction_applied",
            "final_action_candidate": "correction_applied",
            "target_attachment": {
                "meal_thread_id": 5,
                "operation": "correct_active_meal",
                "correction_operation": "correct_active_meal",
                "target_resolution_source": "tool_result_validated",
            },
            "mutation_intent_candidate": "correction_write",
        },
    }
    trace["phase_c_trace"]["mutation_outcome"].update(  # type: ignore[index, union-attr]
        {
            "canonical_commit_status": "committed",
            "ledger_mutation_status": "updated",
            "meal_version_delta": "superseded_previous",
            "canonical_ids": {"meal_version_id": 6, "superseded_version_id": 5},
        }
    )
    trace["state_delta"].update(  # type: ignore[union-attr]
        {
            "canonical_commit": True,
            "ledger_updated": True,
            "draft_saved": False,
            "old_version_superseded": True,
            "new_meal_version_created": True,
        }
    )
    trace["renderer_output"] = {"assistant_message": "已更新上一筆餐點，這餐約 300 kcal。"}
    trace["tool_outputs"] = {
        "tool_results": [
            {
                "tool_name": "estimate_nutrition",
                "evidence": {
                    "nutrition_payload": {
                        "estimated_kcal": 300,
                        "trace_contract": {
                            "db_hit_type": "approved_fooddb_packet",
                            "shadow_stub": False,
                            "approved_fooddb_evidence_trace": {
                                "source_lane": "listed_component",
                                "runtime_truth_allowed": True,
                                "evidence_ids": ["local_component_stub:half_chicken_rice"],
                            },
                            "canonical_write_decision": {"can_write_canonical": True},
                        },
                    }
                },
            }
        ]
    }
    trace["sidecar_output"] = {
        "ui": {
            "today": {
                "consumed_kcal": 300,
                "meals": [{"meal_version_id": 6, "meal_title": "corrected meal"}],
            }
        }
    }

    case_trace = build_golden_case_trace_from_request_trace("GS11", trace)
    grade = grade_golden_case_trace("GS11", case_trace)

    assert case_trace["runtime"]["workflow_effect"] == "correction_applied"
    assert case_trace["runtime"]["ledger_recomputed"] is True
    assert case_trace["runtime"]["old_version_superseded"] is True
    assert grade["status"] == "pass"


def test_request_trace_adapter_flags_saved_change_contradiction_after_commit() -> None:
    trace = _gs5_request_trace()
    trace["renderer_output"] = {
        "assistant_message": (
            "I’m treating this as a tentative reference to meal thread 2; "
            "this is not a saved change yet. 已更新上一筆餐點：珍珠奶茶 450 kcal。"
        )
    }
    trace["phase_c_trace"]["mutation_outcome"].update(  # type: ignore[index, union-attr]
        {"canonical_commit_status": "committed", "ledger_mutation_status": "updated"}
    )
    trace["state_delta"].update(  # type: ignore[union-attr]
        {"canonical_commit": True, "ledger_updated": True}
    )

    case_trace = build_golden_case_trace_from_request_trace("GS8", trace)
    grade = grade_golden_case_trace("GS8", case_trace)

    assert case_trace["response"]["state_contradiction"] is True
    assert case_trace["response"]["internal_debug_words_present"] is True
    assert "response.state_contradiction" in grade["blockers"]
    assert "response.internal_debug_words_present" in grade["blockers"]


def test_request_trace_adapter_flags_internal_fooddb_or_basis_labels_in_visible_reply() -> None:
    trace = _gs5_request_trace()
    trace["renderer_output"] = {
        "assistant_message": (
            "This came from fooddb and active_meal_estimate_basis, not a user-facing explanation."
        )
    }

    case_trace = build_golden_case_trace_from_request_trace("GS9", trace)
    grade = grade_golden_case_trace("GS9", case_trace)

    assert case_trace["response"]["internal_debug_words_present"] is True
    assert "response.internal_debug_words_present" in grade["blockers"]


def test_request_trace_adapter_flags_internal_object_ids_in_visible_reply() -> None:
    trace = _gs5_request_trace()
    trace["renderer_output"] = {
        "assistant_message": "早餐飯糰是最近的早餐記錄（meal_thread_id: 8），請確認要刪哪一筆。"
    }

    case_trace = build_golden_case_trace_from_request_trace("GS13", trace)
    grade = grade_golden_case_trace("GS13", case_trace)

    assert case_trace["response"]["internal_debug_words_present"] is True
    assert "response.internal_debug_words_present" in grade["blockers"]


def test_request_trace_adapter_projects_meal_level_basis_from_state_after() -> None:
    trace = _gs5_request_trace()
    trace["state_after"] = {
        "active_meal": {
            "item_candidates": [
                {"canonical_name": "鐵板麵"},
                {"canonical_name": "荷包蛋"},
            ]
        }
    }

    case_trace = build_golden_case_trace_from_request_trace("GS1", trace)

    assert case_trace["ui"]["meal_level_basis_visible"] is True


def test_request_trace_adapter_detects_shadow_stub_from_manager_final_tool_results() -> None:
    trace = _gs5_request_trace()
    trace.pop("runtime", None)
    trace["tool_outputs"] = {
        "tool_results": [
            {
                "tool_name": "estimate_nutrition",
                "evidence": {
                    "nutrition_payload": {
                        "estimated_kcal": 0,
                        "trace_contract": {
                            "manager_ask_followup_draft_contract": {"source": "manager_structured_final_action"}
                        },
                    }
                },
            }
        ]
    }
    manager_final = dict(trace["manager_final_decision"])  # type: ignore[index]
    manager_final["tool_results"] = [
        {
            "tool_name": "estimate_nutrition",
            "evidence": {
                "nutrition_payload": {
                    "estimated_kcal": 400,
                    "trace_contract": {"shadow_stub": True},
                }
            },
        }
    ]
    trace["manager_final_decision"] = manager_final

    case_trace = build_golden_case_trace_from_request_trace("GS5", trace)

    assert case_trace["runtime"]["fallback_400_allowed"] is False


def test_request_trace_artifact_builder_groups_projected_cases() -> None:
    case_trace = build_golden_case_trace_from_request_trace("GS5", _gs5_request_trace())
    artifact = build_golden_trace_artifact_from_request_traces([case_trace])

    assert artifact["artifact_type"] == "current_shell_self_use_golden_set_trace_artifact"
    assert artifact["claim_scope"] == "real_request_trace_projection"
    assert artifact["runner_inferred_semantics"] is False
    assert artifact["cases"] == [case_trace]


def test_request_trace_projection_script_writes_artifact(tmp_path: Path) -> None:
    trace_path = tmp_path / "request_trace.json"
    output_path = tmp_path / "golden_trace.json"
    trace_path.write_text(json.dumps(_gs5_request_trace(), ensure_ascii=False), encoding="utf-8")

    output = write_trace_artifact_from_specs(
        case_trace_specs=[f"GS5={trace_path}"],
        output_path=output_path,
    )
    built = build_trace_artifact_from_specs([f"GS5={trace_path}"])

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert output == output_path
    assert payload["artifact_type"] == "current_shell_self_use_golden_set_trace_artifact"
    assert payload["cases"][0]["case_id"] == "GS5"
    assert built["cases"][0]["case_id"] == "GS5"
