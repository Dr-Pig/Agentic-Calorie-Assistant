from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


GROKFAST_FOODDB_PACKET_PROFILE = {
    "provider_profile_id": "builderspace-grok-4-fast-fooddb-packet-smoke",
    "provider": "builderspace",
    "model": "grok-4-fast",
    "provider_profile_role": "live_diagnostic_probe",
    "cost_tier": "low",
    "production_selected": False,
    "readiness_owner": False,
}

NON_CLAIMS = [
    "no_readiness_claim",
    "no_production_model_selection",
    "no_self_use_approval",
    "no_runtime_mutation",
    "no_fooddb_truth_promotion",
    "no_kimi_call",
    "no_websearch_runtime_truth",
]


def build_fixture_manager_outputs(*, packet_artifact: dict[str, Any]) -> list[dict[str, Any]]:
    outputs = []
    for packet_case in packet_artifact.get("cases") or []:
        packet = packet_case.get("manager_evidence_packet") if isinstance(packet_case, dict) else {}
        evidence_items = packet.get("evidence_items") if isinstance(packet, dict) else []
        if not evidence_items:
            manager_output = {
                "manager_action": "final",
                "final_action": "request_clarification",
                "workflow_effect": "pause_for_clarification",
                "target_attachment": {},
                "tool_calls": [],
                "item_results": [],
                "answer_contract": {"followup_question": "Please list the specific items before estimating."},
                "semantic_decision": {"mutation_intent_candidate": "no_mutation"},
            }
        else:
            item_results = [
                {
                    "food_name": item.get("canonical_name"),
                    "kcal_range": item.get("kcal_range"),
                    "likely_kcal": item.get("kcal_point"),
                    "uncertainty": "packet_grounded_range",
                    "evidence_used": [item.get("anchor_id")],
                }
                for item in evidence_items
            ]
            manager_output = {
                "manager_action": "final",
                "final_action": "commit",
                "workflow_effect": "food_log_candidate",
                "target_attachment": {},
                "tool_calls": [],
                "item_results": item_results,
                "evidence_used": [item.get("anchor_id") for item in evidence_items],
                "answer_contract": {"text": "Grounded in provided FoodDB packet."},
                "semantic_decision": {"mutation_intent_candidate": "canonical_write"},
            }
        outputs.append(
            {
                "case_id": packet_case.get("case_id"),
                "manager_output": manager_output,
                "provider_trace": {
                    "fixture_provider": True,
                    "provider_profile_id": GROKFAST_FOODDB_PACKET_PROFILE["provider_profile_id"],
                    "provider_profile_model": GROKFAST_FOODDB_PACKET_PROFILE["model"],
                },
            }
        )
    return outputs


def build_grokfast_fooddb_packet_diagnostic(
    *,
    packet_artifact: dict[str, Any],
    manager_outputs: list[dict[str, Any]],
    live_provider_used: bool,
    status: str | None = None,
    failure_family: str | None = None,
) -> dict[str, Any]:
    outputs_by_case = {
        str(item.get("case_id")): item
        for item in manager_outputs
        if isinstance(item, dict) and item.get("case_id")
    }
    case_results = []
    for packet_case in packet_artifact.get("cases") or []:
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
        evaluation = evaluate_manager_output_against_packet(
            packet_case=packet_case,
            manager_output=dict(output.get("manager_output") or {}),
        )
        evaluation["provider_trace"] = dict(output.get("provider_trace") or {})
        case_results.append(evaluation)

    pass_count = sum(1 for item in case_results if item.get("status") == "pass")
    fail_count = len(case_results) - pass_count
    return {
        "artifact_type": "accurate_intake_grokfast_fooddb_packet_smoke",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "live_diagnostic_only",
        "status": status or ("pass" if fail_count == 0 else "diagnostic_fail"),
        "failure_family": failure_family,
        "claim_scope": "grokfast_manager_fooddb_packet_seam_smoke",
        "provider_profile": dict(GROKFAST_FOODDB_PACKET_PROFILE),
        "live_provider_used": live_provider_used,
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
                    for item in case_results
                    for family in item.get("failure_families", [])
                    if family
                }
            ),
        },
        "non_claims": list(NON_CLAIMS),
    }


def evaluate_manager_output_against_packet(
    *,
    packet_case: dict[str, Any],
    manager_output: dict[str, Any],
) -> dict[str, Any]:
    packet = packet_case.get("manager_evidence_packet") if isinstance(packet_case, dict) else {}
    evidence_items = packet.get("evidence_items") if isinstance(packet, dict) else []
    allowed_refs = _allowed_evidence_refs(evidence_items)
    case_id = str(packet_case.get("case_id") or "").strip()
    if case_id:
        allowed_refs.add(case_id)
        allowed_refs.add(f"fooddb_packet case_id {case_id}")
    used_refs = _used_evidence_refs(manager_output)
    expected_behavior = str(packet_case.get("manager_expected_behavior") or "")
    failure_families: list[str] = []

    invented_refs = sorted(ref for ref in used_refs if not _ref_is_allowed(ref, allowed_refs))
    if invented_refs:
        failure_families.append("invented_evidence_reference")

    if evidence_items:
        if not any(_ref_is_allowed(ref, allowed_refs) for ref in used_refs):
            failure_families.append("fooddb_packet_not_used")
        if str(manager_output.get("manager_action") or "") != "final":
            failure_families.append("manager_did_not_finalize_after_packet")
    else:
        item_results = _recursive_values_for_key(manager_output, "item_results")
        if any(bool(item) for item in item_results):
            failure_families.append("bare_basket_estimated_without_components")
        if manager_output.get("tool_calls"):
            failure_families.append("bare_basket_called_tools")
        final_action = str(manager_output.get("final_action") or "")
        if final_action not in {"request_clarification", "ask_followup"}:
            failure_families.append("bare_basket_missing_followup")
        mutation_intent = str(((manager_output.get("semantic_decision") or {}).get("mutation_intent_candidate")) or "")
        if mutation_intent and mutation_intent != "no_mutation":
            failure_families.append("bare_basket_mutation_intent")

    if expected_behavior == "generic_range_estimate_with_followup_hints":
        if str(manager_output.get("exactness") or "").lower() == "exact":
            failure_families.append("generic_meal_overclaimed_exact")

    return {
        "case_id": packet_case.get("case_id"),
        "status": "pass" if not failure_families else "fail",
        "failure_families": failure_families,
        "manager_expected_behavior": expected_behavior,
        "used_evidence_refs": sorted(used_refs),
        "allowed_evidence_refs": sorted(allowed_refs),
        "manager_action": manager_output.get("manager_action"),
        "final_action": manager_output.get("final_action"),
        "runtime_mutation_attempted": False,
        "manager_output": manager_output,
    }


def build_live_manager_payload(*, packet_case: dict[str, Any]) -> dict[str, Any]:
    packet = dict(packet_case.get("manager_evidence_packet") or {})
    return {
        "diagnostic_scope": "fooddb_packet_manager_seam_smoke",
        "raw_user_input": packet_case.get("raw_user_input"),
        "fooddb_evidence_packet": packet,
        "tool_results": [
            {
                "tool_name": "lookup_generic_food",
                "truth_level": "runtime_food_evidence_packet",
                "output": packet,
            }
        ],
        "instructions": [
            "Use only the provided FoodDB evidence packet for nutrition evidence.",
            "Do not invent nutrition sources or evidence IDs.",
            "If evidence_items is empty for a bare basket, ask follow-up and do not mutate.",
            "If evidence_items exist, synthesize item_results from those packet items with uncertainty.",
            "This diagnostic writes no ledger and grants no product readiness.",
        ],
        "constraints": _manager_constraints_for_case(packet_case),
    }


def _manager_constraints_for_case(packet_case: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase_b1_manager_role": "pass_2_synthesis",
        "phase_b1_pass1_mode": "natural_tool_selection_probe",
        "phase_b1_case_family": packet_case.get("case_family"),
        "fooddb_packet_smoke": True,
    }


def _allowed_evidence_refs(evidence_items: list[Any]) -> set[str]:
    refs: set[str] = set()
    for item in evidence_items:
        if not isinstance(item, dict):
            continue
        for key in ("anchor_id", "canonical_name"):
            value = str(item.get(key) or "").strip()
            if value:
                refs.add(value)
        source = item.get("source_provenance") if isinstance(item.get("source_provenance"), dict) else {}
        source_id = str(source.get("source_id") or "").strip()
        if source_id:
            refs.add(source_id)
        source_file = str(source.get("source_file") or "").strip()
        if source_file:
            refs.add(source_file)
        approval = item.get("approval_metadata") if isinstance(item.get("approval_metadata"), dict) else {}
        policy_version = str(approval.get("policy_version") or "").strip()
        if policy_version:
            refs.add(policy_version)
        portion_basis = item.get("portion_basis") if isinstance(item.get("portion_basis"), dict) else {}
        for ref in portion_basis.get("derived_from") or []:
            value = str(ref or "").strip()
            if value:
                refs.add(value)
    return refs


def _used_evidence_refs(manager_output: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    for value in _recursive_values_for_key(manager_output, "evidence_used"):
        if isinstance(value, list):
            values = value
        else:
            values = [value]
        for ref in values:
            value = str(ref or "").strip()
            if value:
                refs.add(value)
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


def _ref_is_allowed(ref: str, allowed_refs: set[str]) -> bool:
    if ref in allowed_refs:
        return True
    normalized_ref = ref.lower()
    return any(allowed.lower() in normalized_ref for allowed in allowed_refs if allowed)


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "GROKFAST_FOODDB_PACKET_PROFILE",
    "NON_CLAIMS",
    "build_fixture_manager_outputs",
    "build_grokfast_fooddb_packet_diagnostic",
    "build_live_manager_payload",
    "evaluate_manager_output_against_packet",
]
