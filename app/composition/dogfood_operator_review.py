from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

_NOT_CHECKED_SURFACE_MAP = {
    "same_truth_verified": "same_truth",
    "dogfood_review_queue_compatible": "dogfood_review_queue",
    "local_data_hygiene_respected": "local_data_hygiene",
}
_ALLOWED_MANAGER_CONTEXT_STATUSES = {
    "not_available",
    "not_checked",
    "missing_context_snapshot",
}
_SOURCE_STATUS_TO_REVIEW_STATUS = {
    "diagnostic_pass_with_evidence_gap": "diagnostic_review_with_evidence_gap",
    "browser_diagnostic_pass_with_fixture_evidence_gap": (
        "browser_diagnostic_review_with_fixture_evidence_gap"
    ),
    "browser_diagnostic_pass_with_evidence_gap": (
        "browser_diagnostic_review_with_evidence_gap"
    ),
    "blocked": "blocked",
}


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _first_trace_decision(manager_decision: dict[str, Any]) -> dict[str, Any]:
    trace = _object_dict(manager_decision.get("trace"))
    rounds = trace.get("manager_rounds") if isinstance(trace.get("manager_rounds"), list) else []
    if not rounds:
        return {}
    return _object_dict(_object_dict(rounds[0]).get("decision"))


def _manager_field(
    manager_decision: dict[str, Any],
    key: str,
    *,
    semantic_key: str | None = None,
) -> Any:
    if key in manager_decision:
        return manager_decision.get(key)
    semantic = _object_dict(manager_decision.get("semantic_decision"))
    if semantic_key and semantic_key in semantic:
        return semantic.get(semantic_key)
    if key in semantic:
        return semantic.get(key)
    trace_decision = _first_trace_decision(manager_decision)
    if key in trace_decision:
        return trace_decision.get(key)
    trace_semantic = _object_dict(trace_decision.get("semantic_decision"))
    if semantic_key and semantic_key in trace_semantic:
        return trace_semantic.get(semantic_key)
    return trace_semantic.get(key)


def _active_meal_count(state: dict[str, Any]) -> int:
    return _int_value(state.get("active_meal_count"))


def _budget_kcal(state: dict[str, Any]) -> int:
    return _int_value(state.get("budget_kcal"))


def _state_delta_mutated(state_delta: dict[str, Any]) -> bool:
    mutation_keys = {
        "canonical_commit",
        "draft_saved",
        "ledger_updated",
        "body_plan_seeded",
        "new_meal_version_created",
    }
    return any(value is True for key, value in state_delta.items() if key in mutation_keys)


def _actual_mutation_result(turn: dict[str, Any]) -> dict[str, Any]:
    state_before = _object_dict(turn.get("state_before"))
    state_after = _object_dict(turn.get("state_after"))
    state_delta = _object_dict(turn.get("state_delta"))
    active_meal_count_increased = _active_meal_count(state_after) > _active_meal_count(state_before)
    budget_updated = _budget_kcal(state_after) != _budget_kcal(state_before)
    mutation_applied = (
        str(turn.get("mutation_or_query") or "") == "mutation"
        or _state_delta_mutated(state_delta)
        or active_meal_count_increased
        or budget_updated
    )
    return {
        "mutation_applied": mutation_applied,
        "active_meal_count_before": _active_meal_count(state_before),
        "active_meal_count_after": _active_meal_count(state_after),
        "active_meal_count_increased": active_meal_count_increased,
        "budget_updated": budget_updated,
        "state_delta_mutated": _state_delta_mutated(state_delta),
        "mutation_or_query": str(turn.get("mutation_or_query") or ""),
    }


def _runtime_error_status(turn: dict[str, Any]) -> dict[str, Any]:
    raw_response = _object_dict(turn.get("raw_response"))
    payload_present = raw_response.get("payload") is not None
    error = str(raw_response.get("error") or "").strip()
    present = bool(error) or (
        "payload" in raw_response and not payload_present
    )
    return {
        "present": present,
        "error": error or None,
        "payload_present": payload_present,
    }


def _query_no_mutation_status(turn: dict[str, Any], actual: dict[str, Any]) -> str | None:
    if actual["mutation_applied"]:
        return None
    before = _object_dict(turn.get("state_before"))
    after = _object_dict(turn.get("state_after"))
    compared_keys = ("budget_kcal", "consumed_kcal", "remaining_kcal", "active_meal_count")
    if all(before.get(key) == after.get(key) for key in compared_keys):
        return "state_unchanged"
    return "no_mutation_with_unchecked_state_delta"


def _remove_item_negative_guard_applies(
    *,
    turn: dict[str, Any],
    scenario_evidence: dict[str, Any],
) -> bool:
    manager_decision = _object_dict(turn.get("manager_decision"))
    guard = _object_dict(scenario_evidence.get("remove_item_negative_guard"))
    return (
        bool(guard.get("attempted"))
        and _manager_field(manager_decision, "mutation_intent_candidate") == "correction_write"
        and str(_manager_field(manager_decision, "workflow_effect") or "")
        == "correction_remove_item"
        and guard.get("correction_or_removal_applied") is False
    )


def _classify_turn(
    *,
    turn: dict[str, Any],
    scenario_evidence: dict[str, Any],
    blockers: list[str],
    actual: dict[str, Any],
) -> tuple[str, str | None, list[str]]:
    manager_decision = _object_dict(turn.get("manager_decision"))
    mutation_intent = str(_manager_field(manager_decision, "mutation_intent_candidate") or "")
    final_action = str(
        _manager_field(manager_decision, "final_action", semantic_key="final_action_candidate")
        or ""
    )
    notes: list[str] = []

    runtime_error = _runtime_error_status(turn)
    if runtime_error["present"]:
        notes.append("runtime_error_or_missing_payload")
        return "manager_context_gap", "runtime_error_or_missing_payload", notes

    if manager_decision.get("unsupported_intent_family"):
        return "unsupported_intent", None, notes

    if _remove_item_negative_guard_applies(turn=turn, scenario_evidence=scenario_evidence):
        return "blocked_mutation", "remove_item_target_missing_existing_item_id", notes

    if final_action == "target_updated" and actual["budget_updated"]:
        return "target_update_success", None, notes

    if mutation_intent == "canonical_write" and not actual["active_meal_count_increased"]:
        notes.append("canonical_write_intent_without_mutation")
        if scenario_evidence.get("evidence_gap_observed") is True or blockers:
            return "food_evidence_gap", "food evidence gap prevented realistic food logging", notes
        return "blocked_mutation", "canonical_write_without_mutation", notes

    if mutation_intent in {"no_mutation", ""} and not actual["mutation_applied"]:
        return "query_no_mutation", None, notes

    if not actual["mutation_applied"]:
        return "not_checked", None, notes

    return "not_checked", None, notes


def _not_checked_surfaces(evidence: dict[str, Any]) -> list[str]:
    return [
        surface
        for key, surface in _NOT_CHECKED_SURFACE_MAP.items()
        if evidence.get(key) == "not_checked"
    ]


def _manager_context_status(value: Any) -> tuple[str, list[str]]:
    status = str(value or "not_checked")
    if status in _ALLOWED_MANAGER_CONTEXT_STATUSES:
        return status, []
    return "not_checked", ["manager_context_status_overclaim"]


def _browser_surface_findings(browser: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    if (
        browser.get("browser_reload_checked") is not True
        or browser.get("chat_history_reloaded") is not True
    ):
        findings.append("browser_reload_gap")
    if browser.get("forbidden_storage_used") is True:
        findings.append("storage_violation")
    for key, finding in (
        ("today_summary_rendered", "today_summary_surface_gap"),
        ("debug_surface_rendered", "debug_surface_gap"),
        ("runtime_status_surface_rendered", "runtime_status_surface_gap"),
        ("cjk_messages_rendered", "cjk_render_gap"),
        ("assistant_bubbles_rendered", "assistant_bubble_gap"),
    ):
        if browser.get(key) is not True:
            findings.append(finding)
    return findings


def _browser_v2_turns(browser: dict[str, Any]) -> list[dict[str, Any]]:
    turns: list[dict[str, Any]] = []
    for item in list(browser.get("turn_results") or []):
        if not isinstance(item, dict):
            continue
        expected_decision = _object_dict(item.get("expected_manager_decision"))
        runtime_error_present = item.get("runtime_error_present") is True
        payload_parseable = item.get("last_payload_parseable") is True
        raw_response: dict[str, Any] = {}
        if runtime_error_present or not payload_parseable:
            raw_response = {
                "error": "runtime_error_or_missing_payload",
                "payload": None,
            }
        turns.append(
            {
                "turn_id": str(item.get("turn_id") or ""),
                "raw_user_input": str(item.get("raw_user_input") or ""),
                "assistant_response_summary": "browser payload parseable"
                if payload_parseable
                else "browser payload missing or failed",
                "manager_decision": expected_decision,
                "mutation_or_query": "query",
                "state_before": {},
                "state_after": {},
                "state_delta": {},
                "raw_response": raw_response,
            }
        )
    return turns


def _scenario_from_report(report: dict[str, Any]) -> tuple[
    dict[str, Any],
    str,
    str,
    list[str],
]:
    legacy = _object_dict(report.get("one_day_realistic_web_dogfood"))
    if legacy:
        return (
            legacy,
            "accurate_intake_one_day_realistic_web_dogfood",
            "not_checked",
            [],
        )

    if report.get("artifact_type") == "accurate_intake_browser_realistic_web_dogfood_v2":
        browser = _object_dict(report.get("browser"))
        manager_context_status, context_findings = _manager_context_status(
            browser.get("manager_context_status")
        )
        findings = [*context_findings, *_browser_surface_findings(browser)]
        scenario = {
            "status": str(report.get("status") or "unknown"),
            "turns": _browser_v2_turns(browser),
            "blockers": [
                *[str(item) for item in list(report.get("blockers") or [])],
                *findings,
            ],
            "evidence": {
                "evidence_gap_observed": browser.get("evidence_gap_observed") is True
                or report.get("fixture_evidence_used") is True,
                "pending_followup_used": "not_checked",
                "same_truth_verified": "not_checked",
                "dogfood_review_queue_compatible": "not_checked",
                "local_data_hygiene_respected": "not_checked",
            },
        }
        return (
            scenario,
            "accurate_intake_browser_realistic_web_dogfood_v2",
            manager_context_status,
            findings,
        )

    return ({}, str(report.get("artifact_type") or "unknown"), "not_checked", [])


def _review_status_for_source(source_status: str) -> str:
    return _SOURCE_STATUS_TO_REVIEW_STATUS.get(source_status, "generated")


def build_dogfood_operator_review_surface(report: dict[str, Any]) -> dict[str, Any]:
    scenario, source_artifact, manager_context_status, browser_surface_findings = (
        _scenario_from_report(report)
    )
    evidence = _object_dict(scenario.get("evidence"))
    blockers = [str(item) for item in list(scenario.get("blockers") or [])]
    turn_reviews: list[dict[str, Any]] = []

    for turn in list(scenario.get("turns") or []):
        if not isinstance(turn, dict):
            continue
        manager_decision = _object_dict(turn.get("manager_decision"))
        actual = _actual_mutation_result(turn)
        runtime_error = _runtime_error_status(turn)
        classification, evidence_gap_reason, reviewer_notes = _classify_turn(
            turn=turn,
            scenario_evidence=evidence,
            blockers=blockers,
            actual=actual,
        )
        turn_reviews.append(
            {
                "turn_id": str(turn.get("turn_id") or ""),
                "classification": classification,
                "display_raw_user_input": str(turn.get("raw_user_input") or ""),
                "display_assistant_response_summary": turn.get("assistant_response_summary"),
                "manager_decision_summary": {
                    "intent_type": _manager_field(
                        manager_decision,
                        "intent_type",
                        semantic_key="current_turn_intent",
                    ),
                    "workflow_effect": _manager_field(manager_decision, "workflow_effect"),
                    "final_action": _manager_field(
                        manager_decision,
                        "final_action",
                        semantic_key="final_action_candidate",
                    ),
                    "mutation_intent_candidate": _manager_field(
                        manager_decision,
                        "mutation_intent_candidate",
                    ),
                    "target_attachment": _json_safe(
                        _manager_field(manager_decision, "target_attachment")
                    ),
                },
                "mutation_intent": _manager_field(
                    manager_decision,
                    "mutation_intent_candidate",
                ),
                "actual_mutation_result": actual,
                "evidence_gap_reason": evidence_gap_reason,
                "pending_followup_state": {
                    "pending_followup_used": evidence.get("pending_followup_used"),
                },
                "query_no_mutation_status": _query_no_mutation_status(turn, actual),
                "same_truth_status": evidence.get("same_truth_verified", "not_checked"),
                "runtime_error_status": runtime_error,
                "non_claim_flags": {
                    "product_readiness_claimed": False,
                    "private_self_use_approved": False,
                    "food_kb_truth_updated": False,
                    "canonical_eval_promoted": False,
                },
                "reviewer_notes": reviewer_notes,
                "classification_inputs": {
                    "allowed_fields_only": True,
                    "raw_user_input_used_for_classification": False,
                    "assistant_text_used_for_classification": False,
                    "calories_recomputed": False,
                },
            }
        )

    summary = {
        "total_turns": len(turn_reviews),
        "successful_target_updates": sum(
            1 for turn in turn_reviews if turn["classification"] == "target_update_success"
        ),
        "successful_food_logs": sum(
            1
            for turn in turn_reviews
            if turn["actual_mutation_result"]["active_meal_count_increased"]
        ),
        "food_evidence_gap_turns": sum(
            1 for turn in turn_reviews if turn["classification"] == "food_evidence_gap"
        ),
        "query_no_mutation_turns": sum(
            1 for turn in turn_reviews if turn["classification"] == "query_no_mutation"
        ),
        "blocked_mutation_turns": sum(
            1 for turn in turn_reviews if turn["classification"] == "blocked_mutation"
        ),
        "manager_context_gap_turns": sum(
            1 for turn in turn_reviews if turn["classification"] == "manager_context_gap"
        ),
        "not_checked_surfaces": _not_checked_surfaces(evidence),
        "manager_context_status": manager_context_status,
        "browser_surface_findings": browser_surface_findings,
    }
    source_status = str(scenario.get("status") or "unknown")
    review_status = _review_status_for_source(source_status)
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_dogfood_operator_review_surface",
        "status": review_status,
        "source_artifact": source_artifact,
        "source_status": source_status,
        "review_status": "generated",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "claim_scope": "local_dogfood_operator_review_surface",
        "local_only": True,
        "contains_personal_diet_logs": True,
        "do_not_commit": True,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "food_kb_truth_updated": False,
        "canonical_eval_promoted": False,
        "real_fooddb_pass_claimed": False,
        "dogfood_pass": False,
        "manager_context_review": {
            "status": manager_context_status,
            "diagnostic_only": True,
            "context_engineering_fault_claimed": False,
        },
        "classification_policy": {
            "allowed_inputs": [
                "turn_id",
                "manager_decision",
                "mutation_intent_candidate",
                "mutation_or_query",
                "state_before",
                "state_after",
                "state_delta",
                "raw_response.error",
                "raw_response.payload_presence",
                "evidence",
                "blockers",
            ],
            "raw_user_input_role": "display_only",
            "assistant_text_role": "display_only",
            "kcal_recomputed": False,
            "food_kb_truth_update_allowed": False,
            "frontend_semantic_owner": False,
        },
        "summary": summary,
        "turn_reviews": _json_safe(turn_reviews),
    }


__all__ = ["build_dogfood_operator_review_surface"]
