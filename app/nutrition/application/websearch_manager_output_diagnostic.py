from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


WEBSEARCH_MANAGER_OUTPUT_DIAGNOSTIC_PROFILE = {
    "manager_mode": "fixture_websearch_manager_output",
    "provider_profile_role": "deterministic_fixture_only",
    "live_provider_used": False,
    "production_selected": False,
    "readiness_owner": False,
}

WEBSEARCH_MANAGER_OUTPUT_NON_CLAIMS = [
    "no_live_websearch_call",
    "no_live_provider_call",
    "no_runtime_mutation",
    "no_websearch_runtime_truth",
    "no_fooddb_truth_promotion",
    "no_exact_card_truth_promotion",
    "no_readiness_claim",
]

_MUTATING_FINAL_ACTIONS = frozenset({"commit", "log_food", "write_ledger", "canonical_write"})
_NON_MUTATING_WORKFLOW_EFFECTS = frozenset(
    {
        "answer_only",
        "no_commit",
        "no_mutation",
        "pause_for_clarification",
        "query_only",
        "source_candidate_review",
    }
)
_MUTATING_WORKFLOW_EFFECT_FRAGMENTS = (
    "canonical_write",
    "commit",
    "food_log",
    "ledger",
    "mutation_applied",
)
_FOLLOWUP_FINAL_ACTIONS = frozenset({"ask_followup", "no_commit", "answer_only"})
_REJECTION_FINAL_ACTIONS = frozenset({"no_commit", "answer_only", "ask_followup"})
_FORBIDDEN_OUTPUT_KEYS = frozenset(
    {
        "accepted_usage",
        "exact_card_truth",
        "final_kcal",
        "final_truth",
        "food_evidence_record",
        "kcal_range",
        "ledger_mutation_result",
        "likely_kcal",
        "manager_context_packet",
        "manager_context_packet_v1",
        "packet_ready_anchor",
        "packet_ready_evidence",
        "packetizer_input",
        "packetizer_output",
        "runtime_truth_allowed",
    }
)
_FORBIDDEN_NON_EMPTY_SURFACES = frozenset(
    {
        "target_attachment",
        "tool_calls",
    }
)


def build_fixture_websearch_manager_outputs(*, packet_artifact: dict[str, Any]) -> list[dict[str, Any]]:
    outputs = []
    for packet_case in packet_artifact.get("cases") or []:
        if not isinstance(packet_case, dict):
            continue
        manager_packet = packet_case.get("manager_evidence_packet")
        if not isinstance(manager_packet, dict):
            continue
        candidate_refs = _allowed_candidate_refs(manager_packet)
        expected_behavior = str(packet_case.get("manager_expected_behavior") or "")
        if expected_behavior == "candidate_review_or_later_exact_card_promotion_path":
            manager_output = {
                "manager_action": "final",
                "final_action": "no_commit",
                "workflow_effect": "source_candidate_review",
                "target_attachment": {},
                "tool_calls": [],
                "item_results": [],
                "answer_contract": {
                    "text": "WebSearch returned a candidate only; exact-card promotion is required before kcal use.",
                    "source_candidate_refs": sorted(candidate_refs)[:1],
                },
                "semantic_decision": {"mutation_intent_candidate": "no_mutation"},
            }
        elif expected_behavior == "ask_followup_or_keep_candidate_pending":
            manager_output = {
                "manager_action": "final",
                "final_action": "ask_followup",
                "workflow_effect": "pause_for_clarification",
                "target_attachment": {},
                "tool_calls": [],
                "item_results": [],
                "answer_contract": {
                    "followup_question": "Please confirm the exact menu item or size.",
                    "source_candidate_refs": sorted(candidate_refs)[:1],
                },
                "semantic_decision": {"mutation_intent_candidate": "no_mutation"},
            }
        else:
            manager_output = {
                "manager_action": "final",
                "final_action": "no_commit",
                "workflow_effect": "no_mutation",
                "target_attachment": {},
                "tool_calls": [],
                "item_results": [],
                "answer_contract": {
                    "text": "WebSearch candidate is not sufficient for nutrition truth.",
                    "source_candidate_refs": sorted(candidate_refs)[:1],
                },
                "semantic_decision": {"mutation_intent_candidate": "no_mutation"},
            }
        outputs.append(
            {
                "case_id": packet_case.get("case_id"),
                "manager_output": manager_output,
                "provider_trace": dict(WEBSEARCH_MANAGER_OUTPUT_DIAGNOSTIC_PROFILE),
            }
        )
    return outputs


def build_websearch_manager_output_diagnostic(
    *,
    packet_artifact: dict[str, Any],
    manager_outputs: list[dict[str, Any]],
    live_provider_used: bool = False,
    status: str | None = None,
) -> dict[str, Any]:
    outputs_by_case = {
        str(output.get("case_id")): output
        for output in manager_outputs
        if isinstance(output, dict) and output.get("case_id")
    }
    case_results = []
    for packet_case in packet_artifact.get("cases") or []:
        if not isinstance(packet_case, dict):
            continue
        output = outputs_by_case.get(str(packet_case.get("case_id") or ""))
        if output is None:
            case_results.append(
                {
                    "case_id": packet_case.get("case_id"),
                    "status": "fail",
                    "failure_families": ["missing_manager_output"],
                    "provider_trace": {},
                }
            )
            continue
        evaluation = evaluate_manager_output_against_websearch_packet(
            packet_case=packet_case,
            manager_output=dict(output.get("manager_output") or {}),
        )
        evaluation["provider_trace"] = dict(output.get("provider_trace") or {})
        case_results.append(evaluation)

    artifact_failure_families = []
    if live_provider_used:
        artifact_failure_families.append("live_provider_used_in_deterministic_diagnostic")

    pass_count = sum(1 for item in case_results if item.get("status") == "pass")
    fail_count = len(case_results) - pass_count + len(artifact_failure_families)
    resolved_status = "diagnostic_fail" if fail_count else (status or "pass")
    return {
        "artifact_type": "accurate_intake_websearch_manager_output_diagnostic",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_diagnostic_only",
        "status": resolved_status,
        "claim_scope": "websearch_manager_output_candidate_boundary",
        "live_provider_used": live_provider_used,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "self_use_approved": False,
        "production_selected": False,
        "runtime_mutation_attempted": False,
        "runtime_truth_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "packet_artifact_type": packet_artifact.get("artifact_type"),
        "cases": case_results,
        "summary": {
            "case_count": len(case_results),
            "pass_count": pass_count,
            "fail_count": fail_count,
            "failure_families": sorted(
                {
                    family
                    for family in artifact_failure_families
                }
                | {
                    family
                    for item in case_results
                    for family in item.get("failure_families", [])
                    if family
                }
            ),
        },
        "non_claims": list(WEBSEARCH_MANAGER_OUTPUT_NON_CLAIMS),
    }


def evaluate_manager_output_against_websearch_packet(
    *,
    packet_case: dict[str, Any],
    manager_output: dict[str, Any],
) -> dict[str, Any]:
    manager_packet = packet_case.get("manager_evidence_packet")
    if not isinstance(manager_packet, dict):
        manager_packet = {}
    expected_behavior = str(packet_case.get("manager_expected_behavior") or "")
    allowed_refs = _allowed_candidate_refs(manager_packet)
    used_refs = _used_evidence_refs(manager_output)
    mutation_attempted = _mutation_attempted(manager_output)
    failure_families: list[str] = []

    if _contains_forbidden_key(manager_output, _FORBIDDEN_OUTPUT_KEYS):
        failure_families.append("websearch_truth_shortcut")

    if _contains_non_empty_surface(manager_output, _FORBIDDEN_NON_EMPTY_SURFACES):
        failure_families.append("websearch_truth_surface_leak")

    invented_refs = sorted(ref for ref in used_refs if not _ref_is_allowed(ref, allowed_refs))
    if invented_refs:
        failure_families.append("invented_websearch_evidence_reference")

    if not used_refs:
        failure_families.append("websearch_candidate_not_used")
    elif not any(_ref_is_allowed(ref, allowed_refs) for ref in used_refs):
        failure_families.append("websearch_candidate_not_used")

    if mutation_attempted:
        failure_families.append("websearch_candidate_mutated_runtime")

    item_results = _recursive_values_for_key(manager_output, "item_results")
    if any(bool(item) for item in item_results):
        failure_families.append("websearch_candidate_created_item_results")

    final_actions = _final_action_candidates(manager_output)
    if (
        expected_behavior == "ask_followup_or_keep_candidate_pending"
        and not final_actions.intersection(_FOLLOWUP_FINAL_ACTIONS)
    ):
        failure_families.append("websearch_ambiguous_candidate_missing_followup")
    if (
        expected_behavior == "reject_or_request_better_source"
        and not final_actions.intersection(_REJECTION_FINAL_ACTIONS)
    ):
        failure_families.append("websearch_weak_candidate_not_rejected")

    return {
        "case_id": packet_case.get("case_id"),
        "status": "pass" if not failure_families else "fail",
        "failure_families": failure_families,
        "manager_expected_behavior": expected_behavior,
        "used_evidence_refs": sorted(used_refs),
        "allowed_evidence_ref_count": len(allowed_refs),
        "invented_evidence_refs": invented_refs,
        "manager_action": manager_output.get("manager_action"),
        "final_action": _resolved_final_action(manager_output),
        "runtime_mutation_attempted": mutation_attempted,
        "mutation_signal": _mutation_signal(manager_output),
        "manager_output": manager_output,
    }


def _mutation_attempted(manager_output: dict[str, Any]) -> bool:
    signal = _mutation_signal(manager_output)
    final_actions = _final_action_candidates(manager_output)
    workflow_effect = signal["workflow_effect"]
    mutation_intent = signal["mutation_intent_candidate"]
    return (
        bool(final_actions.intersection(_MUTATING_FINAL_ACTIONS))
        or (
            workflow_effect not in _NON_MUTATING_WORKFLOW_EFFECTS
            and any(fragment in workflow_effect for fragment in _MUTATING_WORKFLOW_EFFECT_FRAGMENTS)
        )
        or (mutation_intent and mutation_intent != "no_mutation")
    )


def _mutation_signal(manager_output: dict[str, Any]) -> dict[str, str]:
    final_action = str(manager_output.get("final_action") or "")
    workflow_effect = str(manager_output.get("workflow_effect") or "").lower()
    semantic_decision = manager_output.get("semantic_decision")
    mutation_intent = (
        str((semantic_decision or {}).get("mutation_intent_candidate") or "")
        if isinstance(semantic_decision, dict)
        else ""
    )
    return {
        "final_action": final_action,
        "semantic_final_action_candidate": _semantic_final_action_candidate(manager_output),
        "workflow_effect": workflow_effect,
        "mutation_intent_candidate": mutation_intent,
    }


def _final_action_candidates(manager_output: dict[str, Any]) -> set[str]:
    actions = {
        str(manager_output.get("final_action") or "").strip(),
        _semantic_final_action_candidate(manager_output),
    }
    response_mode = str(manager_output.get("response_mode") or "").strip()
    if response_mode == "ask_followup":
        actions.add("ask_followup")
    return {action for action in actions if action}


def _resolved_final_action(manager_output: dict[str, Any]) -> str:
    top_level = str(manager_output.get("final_action") or "").strip()
    if top_level:
        return top_level
    return _semantic_final_action_candidate(manager_output)


def _semantic_final_action_candidate(manager_output: dict[str, Any]) -> str:
    semantic_decision = manager_output.get("semantic_decision")
    if not isinstance(semantic_decision, dict):
        return ""
    return str(semantic_decision.get("final_action_candidate") or "").strip()


def _allowed_candidate_refs(manager_packet: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    packet_id = str(manager_packet.get("packet_id") or "").strip()
    if packet_id:
        refs.add(packet_id)
    for item in manager_packet.get("evidence_items") or []:
        if not isinstance(item, dict):
            continue
        for key in ("candidate_packet_id",):
            value = str(item.get(key) or "").strip()
            if value:
                refs.add(value)
    return refs


def _used_evidence_refs(manager_output: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    for key in ("evidence_used", "source_candidate_refs", "candidate_refs"):
        for value in _recursive_values_for_key(manager_output, key):
            refs.update(_ref_values(value))
    return refs


def _ref_values(value: Any) -> set[str]:
    refs: set[str] = set()
    values = value if isinstance(value, list) else [value]
    for ref in values:
        value_text = str(ref or "").strip()
        if value_text:
            refs.add(value_text)
    return refs


def _recursive_values_for_key(value: Any, key: str) -> list[Any]:
    found: list[Any] = []
    if isinstance(value, dict):
        for item_key, item_value in value.items():
            if item_key == key:
                found.append(item_value)
            found.extend(_recursive_values_for_key(item_value, key))
    elif isinstance(value, list):
        for item in value:
            found.extend(_recursive_values_for_key(item, key))
    return found


def _contains_forbidden_key(value: Any, forbidden_keys: frozenset[str]) -> bool:
    if isinstance(value, dict):
        return any(
            key in forbidden_keys or _contains_forbidden_key(child, forbidden_keys)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_forbidden_key(item, forbidden_keys) for item in value)
    return False


def _contains_non_empty_surface(value: Any, forbidden_keys: frozenset[str]) -> bool:
    if isinstance(value, dict):
        return any(
            (key in forbidden_keys and bool(child))
            or _contains_non_empty_surface(child, forbidden_keys)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_non_empty_surface(item, forbidden_keys) for item in value)
    return False


def _ref_is_allowed(ref: str, allowed_refs: set[str]) -> bool:
    return ref in allowed_refs


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "WEBSEARCH_MANAGER_OUTPUT_NON_CLAIMS",
    "WEBSEARCH_MANAGER_OUTPUT_DIAGNOSTIC_PROFILE",
    "build_fixture_websearch_manager_outputs",
    "build_websearch_manager_output_diagnostic",
    "evaluate_manager_output_against_websearch_packet",
]
