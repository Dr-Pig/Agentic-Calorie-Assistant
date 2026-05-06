from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Callable

from app.nutrition.application.fooddb_live_payload_projection import (
    build_compact_fooddb_live_projection,
    build_diagnostic_allowed_evidence_refs,
)


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

FOODDB_PACKET_MANAGER_REQUIRED_FIELDS = (
    "manager_action",
    "response_mode",
    "intent",
    "workflow_effect",
    "target_attachment",
    "exactness",
    "confidence",
    "evidence_posture",
    "repair_ack",
    "operations",
    "answer_contract",
)

ManagerContractValidator = Callable[[dict[str, Any], dict[str, Any]], list[str]]


def build_fixture_manager_outputs(*, packet_artifact: dict[str, Any]) -> list[dict[str, Any]]:
    outputs = []
    for packet_case in packet_artifact.get("cases") or []:
        packet = packet_case.get("manager_evidence_packet") if isinstance(packet_case, dict) else {}
        evidence_items = packet.get("evidence_items") if isinstance(packet, dict) else []
        if not evidence_items:
            manager_output = {
                "manager_action": "final",
                "response_mode": "clarification",
                "intent": "log_meal",
                "final_action": "request_clarification",
                "workflow_effect": "pause_for_clarification",
                "target_attachment": {},
                "exactness": "none",
                "confidence": "low",
                "evidence_posture": "insufficient_details",
                "repair_ack": False,
                "operations": [],
                "item_results": [],
                "answer_contract": {"followup_question": "Please list the specific items before estimating."},
                "semantic_decision": _fixture_semantic_decision(
                    current_turn_intent="log_meal",
                    workflow_effect="pause_for_clarification",
                    final_action_candidate="ask_followup",
                    estimation_posture="composition_unknown_basket",
                    mutation_intent_candidate="no_mutation",
                    uncertainty_posture="composition_unknown_basket",
                ),
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
                "response_mode": "intake_result",
                "intent": "log_meal",
                "workflow_effect": "food_log_candidate",
                "target_attachment": {},
                "exactness": "range_estimate",
                "confidence": "medium",
                "evidence_posture": "packetized_fooddb",
                "repair_ack": False,
                "operations": [],
                "item_results": item_results,
                "answer_contract": {"text": "Grounded in provided FoodDB packet."},
                "semantic_decision": _fixture_semantic_decision(
                    current_turn_intent="log_meal",
                    workflow_effect="food_log_candidate",
                    final_action_candidate="commit",
                    estimation_posture="synthesized_from_fooddb_packet",
                    mutation_intent_candidate="canonical_write",
                    uncertainty_posture="bounded_range",
                ),
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
    manager_contract_validator: ManagerContractValidator | None = None,
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
            manager_contract_validation_errors=(
                manager_contract_validator(packet_case, dict(output.get("manager_output") or {}))
                if manager_contract_validator is not None
                else []
            ),
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


def build_packet_artifact_from_tool_evidence_result(*, tool_evidence_artifact: dict[str, Any]) -> dict[str, Any]:
    tool_result = _tool_result_from_artifact(tool_evidence_artifact)
    cases = []
    for packet in tool_result.get("evidence_packets") or []:
        if not isinstance(packet, dict):
            continue
        case_id = str(packet.get("case_id") or packet.get("packet_id") or "").strip()
        if not case_id:
            continue
        cases.append(
            {
                "case_id": case_id,
                "raw_user_input": packet.get("raw_user_input"),
                "case_family": _b1_case_family_from_packet_fields(
                    case_id=case_id,
                    expected_behavior=str(packet.get("manager_expected_behavior") or ""),
                    evidence_items=packet.get("evidence_items") or [],
                ),
                "manager_expected_behavior": packet.get("manager_expected_behavior"),
                "manager_evidence_packet": dict(packet),
                "tool_evidence_result": _single_packet_tool_result(tool_result=tool_result, packet=packet),
            }
        )
    return {
        "artifact_type": "accurate_intake_fooddb_manager_packet_smoke",
        "artifact_schema_version": "1.0",
        "source_artifact_type": tool_evidence_artifact.get("artifact_type"),
        "claim_scope": "tool_evidence_result_manager_packet_projection",
        "runtime_truth_changed": False,
        "live_provider_used": False,
        "manager_context_changed": False,
        "runtime_packetizer_contract_changed": False,
        "cases": cases,
        "summary": {
            "case_count": len(cases),
            "tool_evidence_result_used": True,
            "source_implementation_visible": False,
        },
    }


def evaluate_manager_output_against_packet(
    *,
    packet_case: dict[str, Any],
    manager_output: dict[str, Any],
    manager_contract_validation_errors: list[str] | None = None,
) -> dict[str, Any]:
    packet = packet_case.get("manager_evidence_packet") if isinstance(packet_case, dict) else {}
    evidence_items = packet.get("evidence_items") if isinstance(packet, dict) else []
    allowed_refs = build_diagnostic_allowed_evidence_refs(
        packet_case=packet_case,
        evidence_items=evidence_items if isinstance(evidence_items, list) else [],
    )
    case_id = str(packet_case.get("case_id") or "").strip()
    if case_id:
        allowed_refs.add(case_id)
        allowed_refs.add(f"fooddb_packet case_id {case_id}")
    used_refs = _used_evidence_refs(manager_output)
    expected_behavior = str(packet_case.get("manager_expected_behavior") or "")
    missing_contract_fields = _missing_manager_contract_fields(manager_output)
    contract_shape_errors = _manager_contract_shape_errors(manager_output)
    external_contract_errors = list(manager_contract_validation_errors or [])
    failure_families: list[str] = []

    if missing_contract_fields:
        failure_families.append("manager_contract_required_fields_missing")
    if contract_shape_errors or external_contract_errors:
        failure_families.append("manager_contract_schema_validation_failed")

    invented_refs = sorted(ref for ref in used_refs if not _ref_is_allowed(ref, allowed_refs))
    invented_text_refs = _invented_text_evidence_refs(
        manager_output=manager_output,
        allowed_refs=allowed_refs,
    )
    if invented_refs:
        failure_families.append("invented_evidence_reference")
    if invented_text_refs:
        failure_families.append("invented_text_evidence_reference")

    if evidence_items:
        if not any(_ref_is_allowed(ref, allowed_refs) for ref in used_refs):
            failure_families.append("fooddb_packet_not_used")
        if str(manager_output.get("manager_action") or "") != "final":
            failure_families.append("manager_did_not_finalize_after_packet")
        if manager_output.get("tool_calls"):
            failure_families.append("packet_pass2_reopened_tool_calls")
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

    failure_families.extend(
        _modifier_kcal_adjustment_failure_families(
            evidence_items=evidence_items,
            manager_output=manager_output,
        )
    )

    return {
        "case_id": packet_case.get("case_id"),
        "status": "pass" if not failure_families else "fail",
        "failure_families": failure_families,
        "manager_expected_behavior": expected_behavior,
        "used_evidence_refs": sorted(used_refs),
        "allowed_evidence_refs": sorted(allowed_refs),
        "invented_text_evidence_refs": invented_text_refs,
        "manager_action": manager_output.get("manager_action"),
        "final_action": manager_output.get("final_action"),
        "runtime_mutation_attempted": False,
        "missing_manager_contract_fields": missing_contract_fields,
        "manager_contract_validation_errors": contract_shape_errors + external_contract_errors,
        "manager_output": manager_output,
    }


def build_live_manager_payload(*, packet_case: dict[str, Any]) -> dict[str, Any]:
    projection = build_compact_fooddb_live_projection(packet_case=packet_case)
    packet = projection["fooddb_evidence_packet"]
    return {
        "diagnostic_scope": "fooddb_packet_manager_seam_smoke",
        "raw_user_input": packet_case.get("raw_user_input"),
        **projection,
        "instructions": [
            "Return one JSON object matching the active B1 pass-2 manager schema.",
            "Include the required top-level manager fields: manager_action, response_mode, intent, workflow_effect, target_attachment, exactness, confidence, evidence_posture, repair_ack, operations, and answer_contract.",
            "Use only the provided ToolEvidenceResult and FoodDB evidence packet for nutrition evidence.",
            "Do not invent nutrition sources or evidence IDs.",
            "If you include evidence_used, every value must exactly equal one allowed_evidence_refs value; do not add prefixes, ranking labels, match_path labels, or modifier-policy labels.",
            "Use no more than 3 unique evidence_used refs total. Prefer anchor_id plus canonical_name, and optionally the packet case_id when needed for grounding.",
            "Do not combine source IDs with file extensions or rewrite source refs; for example, tfda_fda_food_nutrition_2024.xlsx is forbidden unless that exact value appears in allowed_evidence_refs.",
            "If evidence_items is empty for a bare basket, ask follow-up and do not mutate.",
            "If evidence_items exist, synthesize item_results from those packet items with uncertainty.",
            "Do not include tool_calls in this pass-2 response; the FoodDB evidence packet has already been provided.",
            "If manager_expected_behavior is generic_range_estimate_with_followup_hints and packet_adjustment_available is false, keep kcal_point and kcal_range unchanged from the packet. Treat modifier hints as follow-up only, not arithmetic.",
            "If a packet modifier_compatibility value is unsupported, do not adjust kcal_point or kcal_range for that modifier; keep the packet range and use followup_hints. Do not adjust kcal_point or kcal_range from modifier_compatibility alone. Only use adjusted_kcal_point, adjusted_kcal_range, modifier_adjusted_kcal_point, or modifier_adjusted_kcal_range when those adjusted values are explicitly present in the packet evidence item and packet_adjustment_available is true.",
            "This diagnostic writes no ledger and grants no product readiness.",
        ],
        "expected_output_contract": {
            "required_top_level_fields": list(FOODDB_PACKET_MANAGER_REQUIRED_FIELDS),
            "forbidden_evidence_ref_kinds": [
                "ranking_reasons",
                "match_path_labels",
                "modifier_policy_labels",
                "derived_adjustment_labels",
            ],
            "forbidden_top_level_fields": ["tool_calls"],
            "runtime_mutation_allowed": False,
            "runtime_truth_changed": False,
            "packet_authorized_modifier_adjustment_only": True,
            "max_unique_evidence_refs": 3,
            "preserve_packet_kcal_without_adjusted_values": True,
            "allowed_evidence_refs": list(projection["allowed_evidence_refs"]),
        },
        "constraints": _manager_constraints_for_case(packet_case),
    }


def _fixture_semantic_decision(
    *,
    current_turn_intent: str,
    workflow_effect: str,
    final_action_candidate: str,
    estimation_posture: str,
    mutation_intent_candidate: str,
    uncertainty_posture: str,
) -> dict[str, Any]:
    return {
        "semantic_authority": "deterministic_fake_provider",
        "current_turn_intent": current_turn_intent,
        "target_attachment": {},
        "workflow_effect": workflow_effect,
        "final_action_candidate": final_action_candidate,
        "estimation_posture": estimation_posture,
        "followup_posture": "none",
        "followup_question": None,
        "followup_targets": [],
        "mutation_intent_candidate": mutation_intent_candidate,
        "uncertainty_posture": uncertainty_posture,
        "source": "fixture_fooddb_packet_diagnostic",
        "semantic_owner": "deterministic_fake_provider",
        "deterministic_role": "schema_fixture_only",
    }


def _tool_result_from_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    tool_result = artifact.get("tool_evidence_result")
    if isinstance(tool_result, dict):
        return tool_result
    if str(artifact.get("result_type") or "") == "tool_evidence_result_v1":
        return artifact
    raise ValueError("missing_tool_evidence_result")


def _single_packet_tool_result(*, tool_result: dict[str, Any], packet: dict[str, Any]) -> dict[str, Any]:
    single = {
        key: value
        for key, value in tool_result.items()
        if key not in {"evidence_packets", "trace"}
    }
    trace = dict(tool_result.get("trace") or {})
    trace["packet_count"] = 1
    trace["compact_packet_pass_count"] = 1
    single["evidence_packets"] = [dict(packet)]
    single["trace"] = trace
    return single


def _manager_constraints_for_case(packet_case: dict[str, Any]) -> dict[str, Any]:
    return {
        "phase_b1_manager_role": "pass_2_synthesis",
        "phase_b1_pass1_mode": "natural_tool_selection_probe",
        "phase_b1_case_family": _b1_case_family_for_packet_case(packet_case),
        "fooddb_packet_smoke": True,
    }


def _b1_case_family_for_packet_case(packet_case: dict[str, Any]) -> str | None:
    case_family = str(packet_case.get("case_family") or "").strip()
    if case_family and case_family != "tool_evidence_result_packet":
        return case_family
    packet = packet_case.get("manager_evidence_packet")
    evidence_items = packet.get("evidence_items") if isinstance(packet, dict) else []
    return _b1_case_family_from_packet_fields(
        case_id=str(packet_case.get("case_id") or ""),
        expected_behavior=str(packet_case.get("manager_expected_behavior") or ""),
        evidence_items=evidence_items if isinstance(evidence_items, list) else [],
    )


def _b1_case_family_from_packet_fields(
    *,
    case_id: str,
    expected_behavior: str,
    evidence_items: list[Any],
) -> str:
    if expected_behavior == "ask_followup_no_mutation" or not evidence_items:
        return "composition_unknown_self_selected_basket"
    if expected_behavior == "estimate_listed_components_only":
        return "listed_ingredient_basket"
    if expected_behavior == "generic_range_estimate_with_followup_hints":
        return "common_commercial_meal"
    if "boba" in case_id or expected_behavior in {
        "estimate_from_packet_with_uncertainty",
        "estimate_or_confirm_from_fuzzy_packet",
    }:
        return "common_commercial_drink"
    return "common_food_item"


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


def _recursive_string_values(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for item_value in value.values():
            found.extend(_recursive_string_values(item_value))
    elif isinstance(value, list):
        for item in value:
            found.extend(_recursive_string_values(item))
    elif isinstance(value, str):
        found.append(value)
    return found


def _invented_text_evidence_refs(
    *,
    manager_output: dict[str, Any],
    allowed_refs: set[str],
) -> list[str]:
    invented: set[str] = set()
    for text in _recursive_claim_string_values(manager_output):
        for token in _source_like_tokens(text):
            if not _ref_is_allowed(token, allowed_refs):
                invented.add(token)
    return sorted(invented)


def _recursive_claim_string_values(
    value: Any,
    *,
    key: str | None = None,
) -> list[str]:
    if key in _TEXT_EVIDENCE_REF_SCAN_SKIP_KEYS:
        return []
    if isinstance(value, dict):
        found: list[str] = []
        for item_key, item_value in value.items():
            found.extend(_recursive_claim_string_values(item_value, key=str(item_key)))
        return found
    if isinstance(value, list):
        found = []
        for item in value:
            found.extend(_recursive_claim_string_values(item, key=key))
        return found
    if isinstance(value, str):
        return [value]
    return []


_TEXT_EVIDENCE_REF_SCAN_SKIP_KEYS = {
    "confidence",
    "current_turn_intent",
    "deterministic_role",
    "estimation_posture",
    "evidence_honesty_posture",
    "evidence_posture",
    "evidence_used",
    "exactness",
    "final_action",
    "final_action_candidate",
    "food_name",
    "intent",
    "intent_type",
    "manager_action",
    "mutation_intent_candidate",
    "response_mode",
    "semantic_authority",
    "semantic_owner",
    "source",
    "uncertainty",
    "uncertainty_posture",
    "workflow_effect",
}


def _source_like_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    separators = " \t\r\n,;()[]{}<>\"'，。；：、"
    candidate = ""
    for char in text:
        if char in separators:
            if candidate:
                tokens.append(candidate)
                candidate = ""
        else:
            candidate += char
    if candidate:
        tokens.append(candidate)

    evidence_markers = (
        "alias",
        "anchor",
        "evidence",
        "fda",
        "fooddb",
        "kcal",
        "policy",
        "source",
        "store",
        "tfda",
    )
    return [
        token.strip(".,;:!?")
        for token in tokens
        if _looks_like_evidence_ref_token(token, evidence_markers=evidence_markers)
    ]


def _looks_like_evidence_ref_token(
    token: str,
    *,
    evidence_markers: tuple[str, ...],
) -> bool:
    normalized = token.strip(".,;:!?").lower()
    if not normalized:
        return False
    if not normalized.isascii():
        return False
    if not any(marker in normalized for marker in evidence_markers):
        return False
    if normalized in {"fooddb", "evidence", "source", "packet", "policy"}:
        return False
    return any(char in normalized for char in ("_", ":", "/", "-")) or normalized.startswith(
        ("tfda", "fda")
    )


def _ref_is_allowed(ref: str, allowed_refs: set[str]) -> bool:
    normalized_ref = _normalize_ref(ref)
    return any(normalized_ref == _normalize_ref(allowed) for allowed in allowed_refs if allowed)


def _normalize_ref(value: str) -> str:
    return value.strip().strip(".,;:()[]{}<>\"'").lower()


def _missing_manager_contract_fields(manager_output: dict[str, Any]) -> list[str]:
    return sorted(
        field
        for field in FOODDB_PACKET_MANAGER_REQUIRED_FIELDS
        if field not in manager_output
    )


def _manager_contract_shape_errors(manager_output: dict[str, Any]) -> list[str]:
    expected_types: dict[str, type[Any] | tuple[type[Any], ...]] = {
        "manager_action": str,
        "response_mode": str,
        "intent": str,
        "workflow_effect": str,
        "target_attachment": dict,
        "exactness": str,
        "confidence": str,
        "evidence_posture": str,
        "repair_ack": bool,
        "operations": list,
        "answer_contract": dict,
    }
    errors: list[str] = []
    for field, expected_type in expected_types.items():
        if field not in manager_output:
            continue
        if not isinstance(manager_output.get(field), expected_type):
            type_name = (
                "|".join(item.__name__ for item in expected_type)
                if isinstance(expected_type, tuple)
                else expected_type.__name__
            )
            errors.append(f"{field}:expected_{type_name}")
    return sorted(errors)


def _modifier_kcal_adjustment_failure_families(
    *,
    evidence_items: list[Any],
    manager_output: dict[str, Any],
) -> list[str]:
    failure_families: list[str] = []
    ref_counts = _packet_ref_counts(evidence_items)
    modifier_guarded_items = [
        item
        for item in evidence_items
        if isinstance(item, dict)
        and isinstance(item.get("modifier_compatibility"), dict)
        and bool(item.get("modifier_compatibility"))
    ]
    if not modifier_guarded_items:
        return failure_families

    guarded_items_by_unique_ref: dict[str, dict[str, Any]] = {}
    for item in modifier_guarded_items:
        for ref in _refs_for_packet_item(item):
            normalized_ref = _normalize_ref(ref)
            if ref_counts.get(normalized_ref) == 1:
                guarded_items_by_unique_ref[normalized_ref] = item

    if not guarded_items_by_unique_ref:
        return failure_families

    for item_result in _recursive_values_for_key(manager_output, "item_results"):
        results = item_result if isinstance(item_result, list) else [item_result]
        for result in results:
            if not isinstance(result, dict):
                continue
            matched_item = _unique_packet_item_for_result(
                item_result=result,
                guarded_items_by_unique_ref=guarded_items_by_unique_ref,
            )
            if matched_item is None:
                continue
            if not _manager_kcal_matches_authorized_packet_values(
                item_result=result,
                packet_item=matched_item,
            ):
                if "modifier_adjusted_kcal_without_packet_adjustment" not in failure_families:
                    failure_families.append("modifier_adjusted_kcal_without_packet_adjustment")
                if _has_literal_unsupported_modifier(matched_item):
                    if "unsupported_modifier_adjusted_kcal_range" not in failure_families:
                        failure_families.append("unsupported_modifier_adjusted_kcal_range")
    return failure_families


def _packet_ref_counts(evidence_items: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in evidence_items:
        if not isinstance(item, dict):
            continue
        for ref in _refs_for_packet_item(item):
            normalized_ref = _normalize_ref(ref)
            counts[normalized_ref] = counts.get(normalized_ref, 0) + 1
    return counts


def _refs_for_packet_item(item: dict[str, Any]) -> set[str]:
    return build_diagnostic_allowed_evidence_refs(packet_case={}, evidence_items=[item])


def _unique_packet_item_for_result(
    *,
    item_result: dict[str, Any],
    guarded_items_by_unique_ref: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    evidence_refs = {
        _normalize_ref(str(ref or ""))
        for ref in item_result.get("evidence_used") or []
        if ref
    }
    for key in ("food_name", "canonical_name"):
        value = str(item_result.get(key) or "").strip()
        if value:
            evidence_refs.add(_normalize_ref(value))
    matched_items = {
        id(guarded_items_by_unique_ref[ref]): guarded_items_by_unique_ref[ref]
        for ref in evidence_refs
        if ref in guarded_items_by_unique_ref
    }
    if len(matched_items) != 1:
        return None
    return next(iter(matched_items.values()))


def _manager_kcal_matches_authorized_packet_values(
    *,
    item_result: dict[str, Any],
    packet_item: dict[str, Any],
) -> bool:
    authorized_range = _authorized_kcal_range(packet_item)
    if authorized_range is not None and list(item_result.get("kcal_range") or []) != authorized_range:
        return False

    authorized_point = _authorized_kcal_point(packet_item)
    if authorized_point is not None:
        result_point = item_result.get("likely_kcal")
        if result_point != authorized_point:
            return False
    return True


def _authorized_kcal_range(packet_item: dict[str, Any]) -> list[Any] | None:
    for key in ("adjusted_kcal_range", "modifier_adjusted_kcal_range", "kcal_range"):
        value = packet_item.get(key)
        if isinstance(value, list):
            return list(value)
    return None


def _authorized_kcal_point(packet_item: dict[str, Any]) -> Any:
    for key in ("adjusted_kcal_point", "modifier_adjusted_kcal_point", "kcal_point"):
        if key in packet_item:
            return packet_item.get(key)
    return None


def _has_literal_unsupported_modifier(packet_item: dict[str, Any]) -> bool:
    modifier_compatibility = packet_item.get("modifier_compatibility")
    if not isinstance(modifier_compatibility, dict):
        return False
    return "unsupported" in {str(value) for value in modifier_compatibility.values()}


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "GROKFAST_FOODDB_PACKET_PROFILE",
    "FOODDB_PACKET_MANAGER_REQUIRED_FIELDS",
    "ManagerContractValidator",
    "NON_CLAIMS",
    "build_fixture_manager_outputs",
    "build_grokfast_fooddb_packet_diagnostic",
    "build_live_manager_payload",
    "build_packet_artifact_from_tool_evidence_result",
    "evaluate_manager_output_against_packet",
]
