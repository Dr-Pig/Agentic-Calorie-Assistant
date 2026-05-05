from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any


REQUIRED_CASE_IDS = (
    "context_live_001_general_chat_no_mutation",
    "context_live_002_simple_food_log_candidate",
    "context_live_003_pending_followup_answer",
    "context_live_004_remove_previous_item",
    "context_live_005_remove_older_meal_item",
    "context_live_006_query_previous_drink_no_mutation",
    "context_live_007_daily_target_update",
    "context_live_008_meal_estimate_not_target",
    "context_live_009_simultaneous_log_and_modify",
    "context_live_010_cancel_do_not_log",
    "context_live_011_ambiguous_back_reference",
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _case(
    *,
    case_id: str,
    utterance: str,
    prior_context: dict[str, Any],
    expected_manager_intent: str,
    expected_workflow_effect: str,
    expected_context_fields: list[str],
    must_not_happen: list[str],
    mutation_allowed: bool = False,
    fooddb_used: bool = False,
    live_provider_invoked: bool = False,
    ambiguity_expected: bool = False,
    target_candidates_expected: bool = False,
    pending_pin_expected: bool = False,
) -> dict[str, Any]:
    return _json_safe(
        {
            "case_id": case_id,
            "utterance": utterance,
            "prior_context": prior_context,
            "expected_manager_intent": expected_manager_intent,
            "expected_workflow_effect": expected_workflow_effect,
            "expected_context_fields": expected_context_fields,
            "must_not_happen": must_not_happen,
            "mutation_allowed": mutation_allowed,
            "fooddb_used": fooddb_used,
            "live_provider_invoked": live_provider_invoked,
            "ambiguity_expected": ambiguity_expected,
            "target_candidates_expected": target_candidates_expected,
            "pending_pin_expected": pending_pin_expected,
            "semantic_owner": "live_manager_diagnostic_provider_when_approved",
            "deterministic_role": "validate_context_shape_and_reject_forbidden_outputs",
            "frontend_role": "render_backend_structured_fields_only",
            "manager_context_packet_schema_changed": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
        }
    )


def _cases() -> list[dict[str, Any]]:
    common_context = [
        "context_policy_version",
        "loaded_context_summary",
        "omitted_context_summary",
    ]
    no_semantic_shortcuts = [
        "deterministic_selected_intent",
        "frontend_raw_text_semantic_router",
        "frontend_selected_target",
        "mutation_without_guard",
        "fooddb_truth_used",
        "readiness_claimed",
    ]
    return [
        _case(
            case_id="context_live_001_general_chat_no_mutation",
            utterance="今天好累喔",
            prior_context={"recent_chat": [], "active_day_state": "available"},
            expected_manager_intent="general_chat",
            expected_workflow_effect="no_mutation",
            expected_context_fields=common_context,
            must_not_happen=[*no_semantic_shortcuts, "meal_logged"],
        ),
        _case(
            case_id="context_live_002_simple_food_log_candidate",
            utterance="我早餐吃一顆茶葉蛋",
            prior_context={"active_day_state": "available", "pending_draft": None},
            expected_manager_intent="food_log_candidate",
            expected_workflow_effect="route_to_intake_or_need_evidence",
            expected_context_fields=common_context + ["active_day_state"],
            must_not_happen=[*no_semantic_shortcuts, "claim_fooddb_exact_truth"],
        ),
        _case(
            case_id="context_live_003_pending_followup_answer",
            utterance="豆干、海帶、貢丸",
            prior_context={
                "pending_followup": "luwei_components_question",
                "pending_draft": "luwei_basket",
            },
            expected_manager_intent="answer_pending_followup",
            expected_workflow_effect="attach_to_pending_draft",
            expected_context_fields=common_context + ["pending_followup_pin", "pending_draft_pin"],
            must_not_happen=[*no_semantic_shortcuts, "new_unrelated_meal"],
            pending_pin_expected=True,
        ),
        _case(
            case_id="context_live_004_remove_previous_item",
            utterance="把剛剛那個拿掉",
            prior_context={"active_meals": ["tea_egg", "boba"], "target_candidates": ["boba"]},
            expected_manager_intent="removal_candidate",
            expected_workflow_effect="targeted_removal_candidate",
            expected_context_fields=common_context + ["target_candidates"],
            must_not_happen=[*no_semantic_shortcuts, "delete_without_manager_decision"],
            target_candidates_expected=True,
        ),
        _case(
            case_id="context_live_005_remove_older_meal_item",
            utterance="中午那個豆干拿掉",
            prior_context={
                "active_meals": ["breakfast", "lunch_luwei", "dinner"],
                "target_candidates": ["lunch_luwei.tofu"],
            },
            expected_manager_intent="older_meal_removal_candidate",
            expected_workflow_effect="targeted_removal_candidate",
            expected_context_fields=common_context + ["active_day_state", "target_candidates"],
            must_not_happen=[*no_semantic_shortcuts, "remove_latest_item_by_default"],
            target_candidates_expected=True,
        ),
        _case(
            case_id="context_live_006_query_previous_drink_no_mutation",
            utterance="剛剛那杯多少熱量？",
            prior_context={"active_meals": ["boba"], "target_candidates": ["boba"]},
            expected_manager_intent="nutrition_query",
            expected_workflow_effect="query_only",
            expected_context_fields=common_context + ["target_candidates"],
            must_not_happen=[*no_semantic_shortcuts, "ledger_mutation"],
            target_candidates_expected=True,
        ),
        _case(
            case_id="context_live_007_daily_target_update",
            utterance="今天目標改成 1800",
            prior_context={"budget_summary": "current_target_available"},
            expected_manager_intent="daily_target_update_candidate",
            expected_workflow_effect="target_update_candidate",
            expected_context_fields=common_context + ["budget_summary"],
            must_not_happen=[*no_semantic_shortcuts, "treat_as_meal_kcal_estimate"],
        ),
        _case(
            case_id="context_live_008_meal_estimate_not_target",
            utterance="這餐大概 800",
            prior_context={"active_day_state": "available", "pending_draft": None},
            expected_manager_intent="meal_estimate_context",
            expected_workflow_effect="meal_estimate_context",
            expected_context_fields=common_context + ["active_day_state"],
            must_not_happen=[*no_semantic_shortcuts, "daily_target_update"],
        ),
        _case(
            case_id="context_live_009_simultaneous_log_and_modify",
            utterance="我晚餐吃滷味，然後把中午飯改少一點",
            prior_context={
                "active_meals": ["lunch_rice"],
                "target_candidates": ["lunch_rice"],
            },
            expected_manager_intent="compound_log_and_correction_candidate",
            expected_workflow_effect="compound_requires_manager_decomposition",
            expected_context_fields=common_context + ["active_day_state", "target_candidates"],
            must_not_happen=[*no_semantic_shortcuts, "drop_one_intent_silently"],
            target_candidates_expected=True,
        ),
        _case(
            case_id="context_live_010_cancel_do_not_log",
            utterance="算了不要記",
            prior_context={"pending_followup": "meal_details_question", "pending_draft": "meal_draft"},
            expected_manager_intent="cancel_pending_logging_candidate",
            expected_workflow_effect="cancel_or_clarify_no_commit",
            expected_context_fields=common_context + ["pending_followup_pin", "pending_draft_pin"],
            must_not_happen=[*no_semantic_shortcuts, "commit_pending_draft"],
            pending_pin_expected=True,
        ),
        _case(
            case_id="context_live_011_ambiguous_back_reference",
            utterance="那個改少一點",
            prior_context={"active_meals": ["rice", "boba"], "target_candidates": ["rice", "boba"]},
            expected_manager_intent="ambiguous_correction_reference",
            expected_workflow_effect="ask_clarification",
            expected_context_fields=common_context + ["target_candidates"],
            must_not_happen=[*no_semantic_shortcuts, "choose_first_target"],
            ambiguity_expected=True,
            target_candidates_expected=True,
        ),
    ]


def _validate(cases: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    case_ids = [str(case.get("case_id") or "") for case in cases]
    if case_ids != list(REQUIRED_CASE_IDS):
        blockers.append("required_case_order_mismatch")
    for case in cases:
        case_id = str(case.get("case_id") or "unknown")
        if not case.get("utterance"):
            blockers.append(f"{case_id}.utterance_missing")
        if not isinstance(case.get("prior_context"), dict):
            blockers.append(f"{case_id}.prior_context_missing")
        if not case.get("expected_manager_intent"):
            blockers.append(f"{case_id}.expected_manager_intent_missing")
        if not case.get("expected_workflow_effect"):
            blockers.append(f"{case_id}.expected_workflow_effect_missing")
        fields = case.get("expected_context_fields")
        if not isinstance(fields, list) or "context_policy_version" not in fields:
            blockers.append(f"{case_id}.context_policy_version_not_required")
        must_not_happen = case.get("must_not_happen")
        if not isinstance(must_not_happen, list) or "deterministic_selected_intent" not in must_not_happen:
            blockers.append(f"{case_id}.deterministic_intent_guard_missing")
        if case.get("mutation_allowed") is not False:
            blockers.append(f"{case_id}.mutation_allowed")
        if case.get("fooddb_used") is not False:
            blockers.append(f"{case_id}.fooddb_used")
        if case.get("live_provider_invoked") is not False:
            blockers.append(f"{case_id}.live_provider_invoked")
        if case.get("manager_context_packet_schema_changed") is not False:
            blockers.append(f"{case_id}.manager_context_packet_schema_changed")
        if case.get("runtime_truth_changed") is not False:
            blockers.append(f"{case_id}.runtime_truth_changed")
        if case.get("mutation_changed") is not False:
            blockers.append(f"{case_id}.mutation_changed")
        if case.get("target_candidates_expected") is True:
            if "target_candidates" not in fields:
                blockers.append(f"{case_id}.target_candidates_not_required")
        if case.get("pending_pin_expected") is True:
            if "pending_followup_pin" not in fields and "pending_draft_pin" not in fields:
                blockers.append(f"{case_id}.pending_pin_not_required")
        if case.get("ambiguity_expected") is True:
            if case.get("expected_workflow_effect") != "ask_clarification":
                blockers.append(f"{case_id}.ambiguity_without_clarification")
    return blockers


def build_context_live_diagnostic_case_matrix_artifact() -> dict[str, Any]:
    cases = _cases()
    blockers = _validate(cases)
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_live_diagnostic_case_matrix",
            "status": "pass" if not blockers else "fail",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "claim_scope": "pl_ce_context_live_diagnostic_case_selection_contract",
            "diagnostic_only": True,
            "plan_only": True,
            "local_only": True,
            "live_llm_invoked": False,
            "live_provider_invoked": False,
            "live_provider_approved": False,
            "fooddb_used": False,
            "web_tavily_used": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "shared_contract_changed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "blockers": blockers,
            "summary": {
                "case_count": len(cases),
                "target_candidate_cases": sum(1 for case in cases if case["target_candidates_expected"]),
                "pending_pin_cases": sum(1 for case in cases if case["pending_pin_expected"]),
                "ambiguity_cases": sum(1 for case in cases if case["ambiguity_expected"]),
                "compound_cases": sum(
                    1 for case in cases if case["case_id"] == "context_live_009_simultaneous_log_and_modify"
                ),
            },
            "cases": cases,
        }
    )


__all__ = ["build_context_live_diagnostic_case_matrix_artifact"]
