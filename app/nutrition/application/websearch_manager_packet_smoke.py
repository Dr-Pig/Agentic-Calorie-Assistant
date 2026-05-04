from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def build_websearch_manager_packet_projection(
    *,
    tool_evidence_artifact: dict[str, Any],
) -> dict[str, Any]:
    tool_result = _tool_result_from_artifact(tool_evidence_artifact)
    cases = []
    for index, packet in enumerate(tool_result.get("evidence_packets") or []):
        if not isinstance(packet, dict):
            continue
        cases.append(_project_case(tool_result=tool_result, packet=packet, index=index))
    return {
        "artifact_type": "accurate_intake_websearch_manager_packet_projection",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "claim_scope": "deterministic_websearch_manager_packet_projection",
        "source_artifact_type": tool_evidence_artifact.get("artifact_type"),
        "runtime_truth_changed": False,
        "live_websearch_used": False,
        "live_provider_used": False,
        "manager_context_changed": False,
        "runtime_packetizer_contract_changed": False,
        "websearch_runtime_truth_allowed": False,
        "cases": cases,
        "summary": {
            "case_count": len(cases),
            "candidate_only_count": sum(1 for case in cases if case["candidate_boundary"]["candidate_only"] is True),
            "runtime_truth_allowed_count": sum(
                1 for case in cases if case["candidate_boundary"]["runtime_truth_allowed"] is True
            ),
            "source_implementation_visible": False,
            "manager_packet_contains_kcal_truth": False,
        },
        "non_claims": [
            "no_live_websearch_call",
            "no_live_provider_call",
            "no_websearch_runtime_truth",
            "no_runtime_truth_promotion",
            "no_manager_context_change",
            "no_runtime_packetizer_contract_change",
            "no_readiness_claim",
        ],
    }


def is_compact_websearch_manager_packet(packet: dict[str, Any]) -> bool:
    return (
        packet.get("packet_type") == "websearch_manager_evidence_packet_v1"
        and packet.get("runtime_mutation_allowed") is False
        and packet.get("truth_selection_forbidden") is True
        and packet.get("raw_search_results_included") is False
        and packet.get("candidate_only_records_included") is False
        and packet.get("websearch_runtime_truth_allowed") is False
        and not _contains_any_key(
            packet,
            {
                "adapter_kind",
                "external_search",
                "final_kcal",
                "final_truth",
                "kcal_range",
                "ledger_mutation_result",
                "raw_source_rows",
                "runtime_truth_allowed",
                "storage_backend",
                "supabase",
            },
        )
    )


def _project_case(*, tool_result: dict[str, Any], packet: dict[str, Any], index: int) -> dict[str, Any]:
    manager_packet = _manager_packet_for_search_candidate(packet=packet, index=index)
    return {
        "case_id": manager_packet["packet_id"],
        "manager_evidence_packet": manager_packet,
        "candidate_boundary": {
            "candidate_only": packet.get("truth_level") == "candidate",
            "runtime_truth_allowed": False,
            "snippet_truth_allowed": False,
            "requires_later_promotion_path": True,
        },
        "manager_expected_behavior": _expected_behavior(packet),
        "compact_manager_packet": is_compact_websearch_manager_packet(manager_packet),
    }


def _manager_packet_for_search_candidate(*, packet: dict[str, Any], index: int) -> dict[str, Any]:
    packet_id = str(packet.get("packet_id") or f"websearch_case_{index}").strip()
    evidence_item = {
        "candidate_packet_id": packet_id,
        "canonical_name": packet.get("canonical_name"),
        "matched_name": packet.get("matched_name"),
        "match_type": packet.get("match_type"),
        "source_quality_label": packet.get("source_quality_label"),
        "source_url": packet.get("url"),
        "serving_basis": packet.get("serving_basis"),
        "brand_match": packet.get("brand_match"),
        "size_or_serving_match": packet.get("size_or_serving_match"),
        "modifier_match": packet.get("modifier_match"),
        "sibling_variant_risk": packet.get("sibling_variant_risk"),
        "manager_may_use_for": [
            "source_candidate_review",
            "identity_disambiguation",
            "followup_or_uncertainty_decision",
        ],
        "manager_must_not_use_for": [
            "runtime_mutation",
            "creating_fooddb_truth",
            "nutrition_truth_selection",
            "exact_card_truth",
        ],
    }
    return {
        "packet_type": "websearch_manager_evidence_packet_v1",
        "packet_id": packet_id,
        "raw_user_input": packet.get("query"),
        "retrieval_scope": "external_websearch_candidate",
        "retrieval_boundary": "candidate_only_no_runtime_truth",
        "runtime_mutation_allowed": False,
        "truth_selection_forbidden": True,
        "raw_search_results_included": False,
        "candidate_only_records_included": False,
        "websearch_runtime_truth_allowed": False,
        "evidence_items": [evidence_item],
        "ambiguity_reason": _ambiguity_reason(packet),
        "followup_hints": _followup_hints(packet),
        "manager_may_use_for": [
            "source_candidate_review",
            "identity_disambiguation",
            "followup_or_uncertainty_decision",
        ],
        "manager_must_not_use_for": [
            "runtime_mutation",
            "creating_fooddb_truth",
            "inventing_source",
            "nutrition_truth_selection",
            "exact_card_truth",
        ],
    }


def _expected_behavior(packet: dict[str, Any]) -> str:
    if packet.get("match_type") == "exact" and packet.get("source_quality_label") in {"brand_menu", "official"}:
        return "candidate_review_or_later_exact_card_promotion_path"
    if packet.get("match_type") == "related":
        return "ask_followup_or_keep_candidate_pending"
    return "reject_or_request_better_source"


def _ambiguity_reason(packet: dict[str, Any]) -> str | None:
    if packet.get("match_type") == "exact":
        return None
    if packet.get("match_type") == "related":
        return "same_brand_nearby_variant"
    return "websearch_identity_not_exact"


def _followup_hints(packet: dict[str, Any]) -> list[str]:
    hints: list[str] = []
    if packet.get("match_type") == "related":
        hints.append("confirm_exact_menu_item_or_variant")
    if packet.get("size_or_serving_match") in {"different", "unknown"}:
        hints.append("confirm_serving_size")
    if packet.get("modifier_match") == "unknown":
        hints.append("confirm_customizations")
    return hints


def _tool_result_from_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    tool_result = artifact.get("tool_evidence_result")
    if isinstance(tool_result, dict):
        return tool_result
    if str(artifact.get("result_type") or "") == "tool_evidence_result_v1":
        return artifact
    raise ValueError("missing_tool_evidence_result")


def _contains_any_key(value: Any, keys: set[str]) -> bool:
    if isinstance(value, dict):
        return any(key in keys or _contains_any_key(child, keys) for key, child in value.items())
    if isinstance(value, (list, tuple)):
        return any(_contains_any_key(item, keys) for item in value)
    return False


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "build_websearch_manager_packet_projection",
    "is_compact_websearch_manager_packet",
]
