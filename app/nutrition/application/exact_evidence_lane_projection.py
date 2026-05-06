from __future__ import annotations

from typing import Any

from .websearch_source_class import source_class_from_packet
from .websearch_candidate_pipeline import (
    WebSearchPipelineCase,
    build_websearch_candidate_pipeline_diagnostic,
)


def build_websearch_case_summary(
    websearch_case: WebSearchPipelineCase | None,
) -> dict[str, Any]:
    if websearch_case is None:
        return {
            "case_id": None,
            "candidate_classifications": [],
            "extract_candidate_allowed_count": 0,
            "runtime_truth_allowed_count": 0,
        }
    artifact = build_websearch_candidate_pipeline_diagnostic(cases=(websearch_case,))
    case = artifact["cases"][0]
    return {
        "case_id": case["case_id"],
        "candidate_classifications": [
            _classification_projection(classification)
            for classification in case["candidate_classifications"]
        ],
        "extract_candidate_allowed_count": sum(
            1
            for item in case["candidate_classifications"]
            if item["extract_candidate_allowed"] is True
        ),
        "runtime_truth_allowed_count": sum(
            1
            for item in case["candidate_classifications"]
            if item["runtime_truth_allowed"] is True
        ),
        "selected_extract_decision": _selected_extract_projection(case["selected_extract_decision"]),
        "candidate_packets": [
            _candidate_packet_projection(packet)
            for packet in case["candidate_packets"]
        ],
    }


def build_exact_card_staging(websearch_pipeline: dict[str, Any]) -> dict[str, Any]:
    selected_decision = websearch_pipeline.get("selected_extract_decision") or {}
    selected_id = str(selected_decision.get("selected_search_packet_id") or "").strip()
    if not selected_id or selected_decision.get("extract_allowed_by_policy") is not True:
        return {"candidate_count": 0, "candidates": []}

    selected_packet = next(
        (
            packet
            for packet in websearch_pipeline.get("candidate_packets") or []
            if str(packet.get("packet_id") or "").strip() == selected_id
        ),
        None,
    )
    if not isinstance(selected_packet, dict):
        return {"candidate_count": 0, "candidates": []}

    candidate = {
        "candidate_id": f"exact_card_candidate:{selected_id}",
        "evidence_role": "exact_card_candidate",
        "promotion_status": "review_candidate",
        "promotion_allowed": False,
        "runtime_truth_allowed": False,
        "packet_ready_truth_allowed": False,
        "exact_card_created": False,
        "approval_required_before_runtime_truth": True,
        "source_url": selected_packet.get("url"),
        "source_title": selected_packet.get("title"),
        "canonical_name": selected_packet.get("canonical_name"),
        "matched_name": selected_packet.get("matched_name"),
        "selected_search_packet_id": selected_id,
        "source_policy": {
            "source_type": selected_packet.get("source_type"),
            "source_class": selected_packet.get("source_class"),
            "source_quality_label": selected_packet.get("source_quality_label"),
            "officialness_hint": selected_packet.get("officialness_hint"),
            "license_status": selected_packet.get("license_status"),
            "robots_status": selected_packet.get("robots_status"),
            "identity_confidence": selected_packet.get("identity_confidence"),
            "serving_basis_candidate": selected_packet.get("serving_basis_candidate"),
            "nutrition_fields_present": list(selected_packet.get("nutrition_fields_present") or []),
        },
        "source_provenance": {
            "raw_ref": selected_packet.get("raw_ref"),
            "query": selected_packet.get("query"),
            "tavily_score": selected_packet.get("tavily_score"),
        },
        "approval_metadata": {
            "approval_mode": "none",
            "approval_scope": "review_candidate_only",
            "policy_version": "exact_evidence_lane_policy_v1",
            "runtime_truth_allowed": False,
        },
    }
    return {"candidate_count": 1, "candidates": [candidate]}


def _selected_extract_projection(decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "selected_search_packet_id": decision.get("selected_search_packet_id"),
        "extract_reason": decision.get("extract_reason"),
        "extract_allowed_by_policy": decision.get("extract_allowed_by_policy"),
        "max_extract_urls": decision.get("max_extract_urls"),
        "extract_count": decision.get("extract_count"),
        "source_policy_block_reasons": list(decision.get("source_policy_block_reasons") or []),
    }


def _candidate_packet_projection(packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "packet_id": packet.get("packet_id"),
        "packet_type": packet.get("packet_type"),
        "truth_level": packet.get("truth_level"),
        "source_type": packet.get("source_type"),
        "source_class": source_class_from_packet(packet),
        "source_quality_label": packet.get("source_quality_label"),
        "officialness_hint": packet.get("officialness_hint"),
        "license_status": packet.get("license_status"),
        "robots_status": packet.get("robots_status"),
        "identity_confidence": packet.get("identity_confidence"),
        "serving_basis_candidate": packet.get("serving_basis_candidate"),
        "nutrition_fields_present": list(packet.get("nutrition_fields_present") or []),
        "raw_ref": packet.get("raw_ref"),
        "title": packet.get("title"),
        "url": packet.get("url"),
        "tavily_score": packet.get("tavily_score"),
        "query": packet.get("query"),
        "matched_name": packet.get("matched_name"),
        "canonical_name": packet.get("canonical_name"),
        "match_type": packet.get("match_type"),
        "brand_match": packet.get("brand_match"),
        "size_or_serving_match": packet.get("size_or_serving_match"),
        "modifier_match": packet.get("modifier_match"),
        "hard_recheck_risks": list(packet.get("hard_recheck_risks") or []),
    }


def _classification_projection(classification: dict[str, Any]) -> dict[str, Any]:
    return {
        "packet_id": classification.get("packet_id"),
        "candidate_class": classification.get("candidate_class"),
        "extract_candidate_allowed": classification.get("extract_candidate_allowed"),
        "runtime_truth_allowed": classification.get("runtime_truth_allowed"),
        "packet_ready_truth_allowed": classification.get("packet_ready_truth_allowed"),
        "requires_later_promotion_path": classification.get("requires_later_promotion_path"),
        "source_quality_label": classification.get("source_quality_label"),
        "match_type": classification.get("match_type"),
        "size_or_serving_match": classification.get("size_or_serving_match"),
        "hard_recheck_risks": list(classification.get("hard_recheck_risks") or []),
        "source_policy_block_reasons": list(classification.get("source_policy_block_reasons") or []),
    }
