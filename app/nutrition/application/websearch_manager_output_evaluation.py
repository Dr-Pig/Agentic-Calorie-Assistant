from __future__ import annotations

from typing import Any

from app.nutrition.application.websearch_manager_output_policy import (
    FOLLOWUP_FINAL_ACTIONS,
    FORBIDDEN_NON_EMPTY_SURFACES,
    FORBIDDEN_OUTPUT_KEYS,
    MUTATING_FINAL_ACTIONS,
    MUTATING_WORKFLOW_EFFECT_FRAGMENTS,
    NON_MUTATING_WORKFLOW_EFFECTS,
    REJECTION_FINAL_ACTIONS,
)


def evaluate_manager_output_against_websearch_packet(
    *,
    packet_case: dict[str, Any],
    manager_output: dict[str, Any],
) -> dict[str, Any]:
    manager_packet = packet_case.get("manager_evidence_packet")
    if not isinstance(manager_packet, dict):
        manager_packet = {}
    expected_behavior = str(packet_case.get("manager_expected_behavior") or "")
    allowed_refs = allowed_candidate_refs(manager_packet)
    used_refs = _used_evidence_refs(manager_output)
    mutation_attempted = _mutation_was_attempted(manager_output)
    failure_families: list[str] = []

    if _contains_forbidden_key(manager_output, FORBIDDEN_OUTPUT_KEYS):
        failure_families.append("websearch_truth_shortcut")

    if _contains_non_empty_surface(manager_output, FORBIDDEN_NON_EMPTY_SURFACES):
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

    final_action = str(manager_output.get("final_action") or "")
    if expected_behavior == "ask_followup_or_keep_candidate_pending" and final_action not in FOLLOWUP_FINAL_ACTIONS:
        failure_families.append("websearch_ambiguous_candidate_missing_followup")
    if expected_behavior == "reject_or_request_better_source" and final_action not in REJECTION_FINAL_ACTIONS:
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
        "final_action": final_action,
        "runtime_mutation_attempted": mutation_attempted,
        "mutation_signal": _mutation_signal(manager_output),
        "manager_output": manager_output,
    }


def _mutation_was_attempted(manager_output: dict[str, Any]) -> bool:
    signal = _mutation_signal(manager_output)
    final_action = signal["final_action"]
    workflow_effect = signal["workflow_effect"]
    mutation_intent = signal["mutation_intent_candidate"]
    return (
        final_action in MUTATING_FINAL_ACTIONS
        or (
            workflow_effect not in NON_MUTATING_WORKFLOW_EFFECTS
            and any(fragment in workflow_effect for fragment in MUTATING_WORKFLOW_EFFECT_FRAGMENTS)
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
        "workflow_effect": workflow_effect,
        "mutation_intent_candidate": mutation_intent,
    }


def allowed_candidate_refs(manager_packet: dict[str, Any]) -> set[str]:
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
            (key in forbidden_keys and bool(child)) or _contains_non_empty_surface(child, forbidden_keys)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_non_empty_surface(item, forbidden_keys) for item in value)
    return False


def _ref_is_allowed(ref: str, allowed_refs: set[str]) -> bool:
    return ref in allowed_refs


__all__ = [
    "allowed_candidate_refs",
    "evaluate_manager_output_against_websearch_packet",
]
