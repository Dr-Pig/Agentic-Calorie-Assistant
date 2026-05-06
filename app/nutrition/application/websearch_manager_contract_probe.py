from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .websearch_manager_contract_probe_source import (
    build_websearch_probe_cases_from_diagnostic_artifact,
)


WEBSEARCH_MANAGER_CONTRACT_PROBE_NON_CLAIMS = [
    "no_live_provider_call",
    "no_live_websearch_call",
    "no_kimi_call",
    "no_prompt_or_schema_change",
    "no_runtime_mutation",
    "no_websearch_runtime_truth",
    "no_fooddb_truth_promotion",
    "no_exact_card_truth_promotion",
    "no_readiness_claim",
]

_REQUIRED_MANAGER_OUTPUT_FIELDS = (
    "manager_action",
    "intent",
    "workflow_effect",
    "target_attachment",
    "exactness",
    "confidence",
    "evidence_posture",
    "repair_ack",
)


def build_fixture_websearch_manager_contract_probe_cases() -> list[dict[str, Any]]:
    return [
        {
            "case_id": "grokfast_websearch_exact_candidate_intent_type_only",
            "source": "r11_live_diagnostic_observed_shape",
            "expected_failure_family": "manager_output_contract_violation",
            "observed_manager_output": {
                "manager_action": "final",
                "tool_calls": [],
                "intent_type": "log_food_item",
                "target_attachment": {
                    "candidate_packet_id": "pkt_web_search_milksha_exact",
                    "candidate_boundary": "candidate_only",
                },
                "final_action": "no_mutation",
                "workflow_effect": "source_candidate_reviewed",
                "semantic_decision": {
                    "current_turn_intent": "log_food_item",
                    "mutation_intent_candidate": "pending_evidence",
                    "final_action_candidate": "no_mutation",
                    "estimation_posture": "evidence_pending",
                },
                "answer_contract": {
                    "response_type": "candidate_review",
                    "followup_question": None,
                },
                "exactness": "high",
                "confidence": "high",
                "evidence_posture": "evidence_pending",
                "repair_ack": True,
                "uncertainty_posture": "candidate_hold",
                "evidence_honesty_posture": "candidate_only",
            },
        },
        {
            "case_id": "grokfast_websearch_size_followup_intent_type_only",
            "source": "r11_live_diagnostic_observed_shape",
            "expected_failure_family": "manager_output_contract_violation",
            "observed_manager_output": {
                "manager_action": "final",
                "tool_calls": [],
                "intent_type": "log_food_item",
                "target_attachment": {
                    "item_name": "Starbucks iced latte large",
                    "serving_size": "large",
                },
                "final_action": "ask_followup",
                "workflow_effect": "no_mutation",
                "semantic_decision": {
                    "current_turn_intent": "log_food_item",
                    "mutation_intent_candidate": "pending_size_clarification",
                    "final_action_candidate": "ask_followup",
                    "estimation_posture": "pending_clarification",
                },
                "answer_contract": {
                    "followup_question": "Confirm the exact size.",
                    "response_mode": "ask_size_clarification",
                },
                "exactness": "low",
                "confidence": "medium",
                "evidence_posture": "evidence_pending",
                "repair_ack": True,
                "uncertainty_posture": "size_clarification",
                "evidence_honesty_posture": "candidate_review",
                "followup_posture": "size_clarification",
            },
        },
    ]


def build_websearch_manager_contract_probe(
    *,
    cases: list[dict[str, Any]] | None = None,
    diagnostic_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if cases is not None:
        probe_cases = cases
    elif diagnostic_artifact is not None:
        probe_cases = build_websearch_probe_cases_from_diagnostic_artifact(diagnostic_artifact)
    else:
        probe_cases = build_fixture_websearch_manager_contract_probe_cases()
    results = [_evaluate_contract_case(case) for case in probe_cases]
    pass_count = sum(1 for item in results if item.get("status") == "pass")
    fail_count = len(results) - pass_count
    failure_families = sorted(
        {
            family
            for item in results
            for family in item.get("failure_families", [])
            if family
        }
    )
    repair_hypotheses = _repair_hypotheses(results)
    contract_failure_detected = fail_count > 0
    if not contract_failure_detected and _diagnostic_artifact_passed(diagnostic_artifact):
        next_recommended_slice = "inspect_websearch_status_packet"
        websearch_expansion_allowed = True
    elif not contract_failure_detected:
        next_recommended_slice = "inspect_websearch_status_packet"
        websearch_expansion_allowed = False
    else:
        next_recommended_slice = (
            "narrow_prompt_schema_intent_alias_probe"
            if "intent_type_present_intent_missing" in repair_hypotheses
            else "inspect_websearch_manager_contract_failures"
        )
        websearch_expansion_allowed = False
    return {
        "artifact_type": "accurate_intake_websearch_manager_contract_probe",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_contract_probe_only",
        "claim_scope": "grokfast_websearch_manager_contract_failure_localization",
        "status": "pass" if fail_count == 0 else "diagnostic_fail",
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "self_use_approved": False,
        "production_selected": False,
        "contract_failure_detected": contract_failure_detected,
        "runtime_truth_changed": False,
        "runtime_mutation_attempted": False,
        "manager_contract_changed": False,
        "prompt_changed": False,
        "schema_changed": False,
        "source_artifact_type": (
            str(diagnostic_artifact.get("artifact_type") or "")
            if isinstance(diagnostic_artifact, dict)
            else None
        ),
        "cases": results,
        "summary": {
            "case_count": len(results),
            "pass_count": pass_count,
            "fail_count": fail_count,
            "failure_families": failure_families,
            "repair_hypotheses": repair_hypotheses,
            "next_recommended_slice": next_recommended_slice,
            "websearch_expansion_allowed": websearch_expansion_allowed,
        },
        "non_claims": list(WEBSEARCH_MANAGER_CONTRACT_PROBE_NON_CLAIMS),
    }


def _evaluate_contract_case(case: dict[str, Any]) -> dict[str, Any]:
    observed_output = dict(case.get("observed_manager_output") or {})
    validation_errors = _validation_error_list(case.get("manager_contract_validation_errors"))
    missing_fields = _missing_required_fields(observed_output)
    shape_patterns = _shape_patterns(observed_output=observed_output, missing_fields=missing_fields)
    failure_families: list[str] = []
    if missing_fields:
        failure_families.append("manager_output_contract_violation")
    if validation_errors and "manager_output_contract_violation" not in failure_families:
        failure_families.append("manager_output_contract_violation")
    if "intent_type_present_intent_missing" in shape_patterns:
        failure_families.append("manager_intent_alias_gap")
    if _candidate_attachment_present(observed_output):
        failure_families.append("candidate_attachment_requires_boundary_review")

    return {
        "case_id": case.get("case_id"),
        "status": "pass" if not failure_families else "fail",
        "failure_families": failure_families,
        "expected_failure_family": case.get("expected_failure_family"),
        "observed_keys": sorted(observed_output.keys()),
        "missing_required_fields": missing_fields,
        "shape_patterns": shape_patterns,
        "validation_error_family": (
            "manager_output_contract_violation" if (missing_fields or validation_errors) else None
        ),
        "raw_manager_output_included": False,
        "provider_trace_included": False,
    }


def _shape_patterns(*, observed_output: dict[str, Any], missing_fields: list[str]) -> list[str]:
    patterns: list[str] = []
    if "intent" in missing_fields and "intent_type" in observed_output:
        patterns.append("intent_type_present_intent_missing")
    if _candidate_attachment_present(observed_output):
        patterns.append("candidate_only_target_attachment_present")
    semantic_decision = observed_output.get("semantic_decision")
    if isinstance(semantic_decision, dict):
        if str(semantic_decision.get("estimation_posture") or "") in {
            "evidence_pending",
            "pending_clarification",
        }:
            patterns.append("semantic_estimation_pending")
        mutation_intent = str(semantic_decision.get("mutation_intent_candidate") or "")
        if mutation_intent.startswith("pending_"):
            patterns.append("pending_mutation_intent_candidate")
    if str(observed_output.get("final_action") or "") in {"ask_followup", "no_mutation"}:
        patterns.append("no_commit_final_action")
    return sorted(set(patterns))


def _candidate_attachment_present(observed_output: dict[str, Any]) -> bool:
    attachment = observed_output.get("target_attachment")
    if not isinstance(attachment, dict) or not attachment:
        return False
    return any(
        key in attachment
        for key in (
            "candidate_boundary",
            "candidate_packet_id",
            "candidate_items",
            "item_name",
            "serving_size",
        )
    )


def _missing_required_fields(observed_output: dict[str, Any]) -> list[str]:
    return sorted(
        field
        for field in _REQUIRED_MANAGER_OUTPUT_FIELDS
        if field not in observed_output
    )


def _validation_error_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text:
            result.append(text)
    return result


def _repair_hypotheses(results: list[dict[str, Any]]) -> list[str]:
    patterns = {
        pattern
        for result in results
        for pattern in result.get("shape_patterns", [])
        if pattern
    }
    hypotheses: list[str] = []
    if "intent_type_present_intent_missing" in patterns:
        hypotheses.append("intent_type_present_intent_missing")
    if "candidate_only_target_attachment_present" in patterns:
        hypotheses.append("candidate_attachment_boundary_needs_explicit_output_rule")
    if "semantic_estimation_pending" in patterns:
        hypotheses.append("candidate_review_pending_posture_needs_contract_alignment")
    return hypotheses


def _diagnostic_artifact_passed(diagnostic_artifact: dict[str, Any] | None) -> bool:
    if not isinstance(diagnostic_artifact, dict):
        return False
    return (
        str(diagnostic_artifact.get("artifact_type") or "")
        == "accurate_intake_grokfast_websearch_packet_smoke"
        and str(diagnostic_artifact.get("status") or "") == "pass"
    )


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "WEBSEARCH_MANAGER_CONTRACT_PROBE_NON_CLAIMS",
    "build_fixture_websearch_manager_contract_probe_cases",
    "build_websearch_manager_contract_probe",
]
