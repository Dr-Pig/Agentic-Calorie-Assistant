from __future__ import annotations

from typing import Any

from app.nutrition.application.grokfast_websearch_packet_profile import (
    WEBSEARCH_PACKET_MANAGER_REQUIRED_FIELDS,
)


def evaluate_manager_output_against_review_packet(
    *,
    review_packet: dict[str, Any],
    manager_output: dict[str, Any],
    manager_contract_validation_errors: list[str] | None = None,
) -> dict[str, Any]:
    allowed_refs = allowed_review_packet_refs(review_packet)
    used_refs = _used_evidence_refs(manager_output)
    invented_refs = sorted(ref for ref in used_refs if not _ref_is_allowed(ref, allowed_refs))
    missing_contract_fields = _missing_manager_contract_fields(manager_output)
    contract_shape_errors = _manager_contract_shape_errors(manager_output)
    external_contract_errors = list(manager_contract_validation_errors or [])
    failure_families: list[str] = []

    if missing_contract_fields:
        failure_families.append("manager_contract_required_fields_missing")
    if contract_shape_errors or external_contract_errors:
        failure_families.append("manager_contract_schema_validation_failed")
    if invented_refs:
        failure_families.append("invented_evidence_reference")
    if not any(_ref_is_allowed(ref, allowed_refs) for ref in used_refs):
        failure_families.append("websearch_review_packet_not_used")
    if str(manager_output.get("manager_action") or "") != "final":
        failure_families.append("manager_did_not_finalize_after_packet")
    if str(manager_output.get("final_action") or "") in {"commit", "log_food", "add_food"}:
        failure_families.append("review_candidate_used_for_commit")
    if _review_candidate_attached_as_target(manager_output):
        failure_families.append("review_candidate_attached_as_mutation_target")
    if any(bool(item) for item in _recursive_values_for_key(manager_output, "item_results")):
        failure_families.append("review_candidate_used_as_item_result")
    if manager_output.get("tool_calls"):
        failure_families.append("review_packet_triggered_additional_tools")
    if _has_truth_or_promotion_claim(manager_output):
        failure_families.append("review_candidate_promoted_to_truth")
    mutation_intent = str(((manager_output.get("semantic_decision") or {}).get("mutation_intent_candidate")) or "")
    if mutation_intent and mutation_intent != "no_mutation":
        failure_families.append("review_candidate_mutation_intent")

    return {
        "packet_id": review_packet.get("packet_id"),
        "status": "pass" if not failure_families else "fail",
        "failure_families": failure_families,
        "used_evidence_refs": sorted(used_refs),
        "allowed_evidence_refs": sorted(allowed_refs),
        "manager_action": manager_output.get("manager_action"),
        "final_action": manager_output.get("final_action"),
        "runtime_mutation_attempted": False,
        "missing_manager_contract_fields": missing_contract_fields,
        "manager_contract_validation_errors": contract_shape_errors + external_contract_errors,
        "manager_output": manager_output,
    }


def allowed_review_packet_refs(review_packet: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    for key in (
        "packet_id",
        "source_url",
        "source_title",
        "canonical_name",
        "matched_name",
        "source_extract_result_candidate_id",
        "source_selected_extract_packet_id",
        "source_exact_card_candidate_id",
    ):
        value = str(review_packet.get(key) or "").strip()
        if value:
            refs.add(value)
    source = review_packet.get("source_provenance") if isinstance(review_packet.get("source_provenance"), dict) else {}
    for key in ("raw_extract_ref", "selected_extract_packet_id", "source_url"):
        value = str(source.get(key) or "").strip()
        if value:
            refs.add(value)
    return refs


def _used_evidence_refs(manager_output: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    for value in _recursive_values_for_key(manager_output, "evidence_used"):
        values = value if isinstance(value, list) else [value]
        for ref in values:
            cleaned = str(ref or "").strip()
            if cleaned:
                refs.add(cleaned)
    return refs


def _missing_manager_contract_fields(manager_output: dict[str, Any]) -> list[str]:
    return sorted(
        field
        for field in WEBSEARCH_PACKET_MANAGER_REQUIRED_FIELDS
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


def _review_candidate_attached_as_target(manager_output: dict[str, Any]) -> bool:
    attachment = manager_output.get("target_attachment")
    if not isinstance(attachment, dict):
        return False
    risky_keys = {
        "packet_id",
        "candidate_packet_id",
        "review_kcal_candidate",
        "review_serving_basis_candidate",
        "kcal_value_candidate",
        "serving_basis_candidate",
        "candidate_boundary",
    }
    return any(key in attachment for key in risky_keys)


def _has_truth_or_promotion_claim(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {
                "runtime_truth_allowed",
                "packet_ready_truth_allowed",
                "promotion_allowed",
                "exact_card_created",
                "runtime_mutation_allowed",
            } and item is True:
                return True
            if key == "exactness" and str(item or "").lower() == "exact":
                return True
            if _has_truth_or_promotion_claim(item):
                return True
    elif isinstance(value, list):
        return any(_has_truth_or_promotion_claim(item) for item in value)
    elif isinstance(value, str):
        return _has_textual_truth_overclaim(value)
    return False


def _has_textual_truth_overclaim(text: str) -> bool:
    normalized = " ".join(text.lower().split())
    overclaim_phrases = (
        "approved for runtime",
        "runtime use approved",
        "approved as truth",
        "runtime truth allowed",
        "promotion approved",
        "ready to create the exact card",
        "can create exact card",
        "created exact card",
        "exact card approved",
    )
    return any(phrase in normalized for phrase in overclaim_phrases)


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
    normalized_ref = _normalize_ref(ref)
    return any(normalized_ref == _normalize_ref(allowed) for allowed in allowed_refs if allowed)


def _normalize_ref(value: str) -> str:
    return value.strip().strip(".,;:()[]{}<>\"'").lower()


__all__ = [
    "allowed_review_packet_refs",
    "evaluate_manager_output_against_review_packet",
]
