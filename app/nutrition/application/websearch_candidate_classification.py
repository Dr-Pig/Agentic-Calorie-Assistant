from __future__ import annotations

from typing import Any

from .websearch_source_class import source_class_from_packet
from .websearch_source_policy import classify_websearch_source_candidate


def classify_candidate_packet(
    packet: dict[str, Any],
    *,
    selected_extract_packet_id: str | None,
) -> dict[str, Any]:
    source_class = _source_class_from_packet(packet)
    source_policy = classify_websearch_source_candidate(
        {
            "source_url": packet.get("source_url"),
            "source_class": source_class,
            "license_status": packet.get("license_status"),
            "robots_status": packet.get("robots_status"),
            "identity_confidence": packet.get("identity_confidence"),
            "serving_basis_candidate": packet.get("serving_basis_candidate"),
            "nutrition_fields_present": packet.get("nutrition_fields_present"),
        }
    )
    risks = [str(risk) for risk in packet.get("hard_recheck_risks", [])]
    packet_id = str(packet.get("packet_id") or "")
    source_quality = str(packet.get("source_quality_label") or "")
    match_type = str(packet.get("match_type") or "")
    size_match = str(packet.get("size_or_serving_match") or "")
    modifier_match = str(packet.get("modifier_match") or "")
    sibling_risk = bool((packet.get("sibling_variant_risk") or {}).get("present"))
    if source_policy["candidate_class"] == "blocked_source_policy_candidate":
        candidate_class = "blocked_source_policy_candidate"
        manager_signal = "source_policy_blocked"
    elif source_quality == "third_party":
        candidate_class = "weak_or_unusable_candidate"
        manager_signal = "source_not_sufficient"
    elif source_policy["block_reasons"]:
        candidate_class = "blocked_source_policy_candidate"
        manager_signal = "source_policy_blocked"
    elif "wrong_size" in risks or size_match == "different":
        candidate_class = "near_exact_wrong_size_candidate"
        manager_signal = "needs_disambiguation"
    elif modifier_match == "unknown":
        candidate_class = "near_exact_modifier_unknown_candidate"
        manager_signal = "needs_disambiguation"
    elif sibling_risk or "sibling_variant" in risks or match_type == "related":
        candidate_class = "near_exact_sibling_candidate"
        manager_signal = "needs_disambiguation"
    elif packet_id == selected_extract_packet_id and source_policy["extract_candidate_allowed"] is True:
        candidate_class = "exact_candidate_for_extract_review"
        manager_signal = "candidate_review_no_commit"
    elif match_type == "exact":
        candidate_class = "exact_candidate_blocked_by_policy"
        manager_signal = "candidate_review_no_commit"
    else:
        candidate_class = "weak_or_unusable_candidate"
        manager_signal = "source_not_sufficient"

    return {
        "packet_id": packet_id,
        "candidate_class": candidate_class,
        "manager_signal": manager_signal,
        "extract_candidate_allowed": (
            packet_id == selected_extract_packet_id
            and candidate_class == "exact_candidate_for_extract_review"
            and source_policy["extract_candidate_allowed"] is True
        ),
        "runtime_truth_allowed": False,
        "packet_ready_truth_allowed": False,
        "requires_later_promotion_path": True,
        "source_quality_label": source_quality,
        "source_class": source_class,
        "match_type": match_type,
        "size_or_serving_match": size_match,
        "modifier_match": modifier_match,
        "hard_recheck_risks": risks,
        "source_policy_block_reasons": list(source_policy["block_reasons"]),
    }


def source_policy_filtered_extract_decision_trace(
    *,
    extract_decision_trace: dict[str, object],
    classifications: list[dict[str, Any]],
) -> dict[str, object]:
    selected_packet_id = str(extract_decision_trace.get("selected_search_packet_id") or "")
    if not selected_packet_id:
        return dict(extract_decision_trace)

    selected_classification = next(
        (
            classification
            for classification in classifications
            if str(classification.get("packet_id") or "") == selected_packet_id
        ),
        None,
    )
    if (
        selected_classification is not None
        and selected_classification.get("extract_candidate_allowed") is True
    ):
        return dict(extract_decision_trace)

    return {
        **extract_decision_trace,
        "selected_search_packet_id": None,
        "extract_reason": "source_policy_blocked_selected_extract",
        "extract_allowed_by_policy": False,
        "extract_count": 0,
        "source_policy_block_reasons": list(
            (selected_classification or {}).get("source_policy_block_reasons") or []
        ),
    }


def _source_class_from_packet(packet: dict[str, Any]) -> str:
    return source_class_from_packet(packet)


__all__ = [
    "classify_candidate_packet",
    "source_policy_filtered_extract_decision_trace",
]
