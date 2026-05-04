from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from .exact_item_card_lookup import lookup_exact_item_card_candidates
from .retrieval_intent import RetrievalIntent
from .websearch_candidate_pipeline import (
    WebSearchPipelineCase,
    build_websearch_candidate_pipeline_diagnostic,
)


class _LocalExactSeedStore:
    def load_small_anchor_records(self) -> list[dict[str, object]]:
        return []

    def load_exact_item_card_records(self) -> list[dict[str, object]]:
        return [
            {
                "item_id": "exact_test_food_large",
                "title": "Test Brand Food Large",
                "aliases": ["Test Brand Food Large"],
                "brand": "Test Brand",
                "serving_basis": "large serving",
                "kcal": 123,
            }
        ]


def build_exact_evidence_lane_policy_artifact() -> dict[str, Any]:
    cases = [
        _local_exact_seed_case(),
        _websearch_candidate_review_case(),
        _no_exact_evidence_case(),
    ]
    return {
        "artifact_type": "accurate_intake_exact_evidence_lane_policy_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "offline_exact_lane_policy_only",
        "claim_scope": "deterministic_exact_lane_order_and_boundary",
        "runtime_truth_changed": False,
        "runtime_mutation_allowed": False,
        "packetizer_format_changed": False,
        "manager_context_changed": False,
        "live_websearch_used": False,
        "live_provider_used": False,
        "cases": cases,
        "summary": {
            "case_count": len(cases),
            "local_exact_preferred_count": sum(
                1 for case in cases if case["lane_decision"]["selected_lane"] == "local_exact_seed_support_only"
            ),
            "websearch_candidate_review_count": sum(
                1 for case in cases if case["lane_decision"]["selected_lane"] == "websearch_candidate_review"
            ),
            "no_exact_evidence_count": sum(
                1 for case in cases if case["lane_decision"]["selected_lane"] == "no_exact_evidence"
            ),
            "exact_card_staging_candidate_count": sum(
                case["exact_card_staging"]["candidate_count"] for case in cases
            ),
        },
        "lane_order": [
            "local_exact_seed_support_only",
            "websearch_candidate_review",
            "no_exact_evidence",
        ],
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_packet_ready_truth",
            "no_live_websearch_call",
            "no_live_provider_call",
            "no_runtime_mutation",
            "no_readiness_claim",
        ],
    }


def _local_exact_seed_case() -> dict[str, Any]:
    intent = RetrievalIntent(
        base_dish="Food",
        aliases=["Test Brand Food Large"],
        brand_hint="Test Brand",
        size_hint="Large",
        modifier_hints=[],
        listed_items=[],
        retrieval_goal="exact_brand_lookup",
    )
    local_exact = lookup_exact_item_card_candidates(intent, evidence_store=_LocalExactSeedStore())
    lane = "local_exact_seed_support_only" if local_exact.candidates else "no_exact_evidence"
    return _case_payload(
        case_id="local_exact_seed_preferred",
        intent=intent,
        local_exact=local_exact,
        websearch_case=None,
        selected_lane=lane,
        evidence_signal="local_exact_seed_support_available" if local_exact.candidates else "no_exact_evidence_available",
    )


def _websearch_candidate_review_case() -> dict[str, Any]:
    intent = RetrievalIntent(
        base_dish="pearl black tea latte",
        aliases=["Milksha pearl black tea latte"],
        brand_hint="Milksha",
        size_hint=None,
        modifier_hints=[],
        listed_items=[],
        retrieval_goal="exact_brand_lookup",
    )
    local_exact = lookup_exact_item_card_candidates(intent)
    web_case = WebSearchPipelineCase(
        case_id="pipeline_milksha_exact",
        intent=intent,
        raw_hits=(
            {
                "url": "https://milksha.example/menu/pearl-black-tea-latte",
                "domain": "example.test",
                "title": "Milksha pearl black tea latte",
                "snippet": "deterministic search candidate",
                "score": 0.93,
                "officialness": "official",
                "source_quality_label": "high",
                "brand_detected": "Milksha",
                "channel_detected": "handmade_foodservice",
                "serving_basis": "per_cup",
                "nutrition_fields_present": ["kcal"],
                "license_status": "public_menu_page",
                "robots_status": "allowed",
                "customization_slots_present": ["size"],
                "identity_confidence": "high",
                "applicability_confidence": "medium",
                "applicability_notes": "deterministic fixture candidate",
                "raw_ref": "raw/websearch/pipeline_milksha_exact.json#0",
            },
        ),
    )
    return _case_payload(
        case_id="websearch_candidate_review_fallback",
        intent=intent,
        local_exact=local_exact,
        websearch_case=web_case,
        selected_lane="websearch_candidate_review",
        evidence_signal="exact_card_candidate_review_available",
    )


def _no_exact_evidence_case() -> dict[str, Any]:
    intent = RetrievalIntent(
        base_dish="super matcha au lait",
        aliases=["Super Matcha Au Lait"],
        brand_hint="Unknown Brand",
        size_hint=None,
        modifier_hints=[],
        listed_items=[],
        retrieval_goal="exact_brand_lookup",
    )
    local_exact = lookup_exact_item_card_candidates(intent)
    web_case = WebSearchPipelineCase(
        case_id="pipeline_no_exact_evidence",
        intent=intent,
        raw_hits=(
            {
                "url": "https://third-party.example/super-matcha",
                "domain": "example.test",
                "title": "Super Matcha Au Lait calories",
                "snippet": "third-party calorie blog",
                "score": 0.70,
                "officialness": "unknown",
                "source_quality_label": "low",
                "brand_detected": "Unknown Brand",
                "channel_detected": "handmade_foodservice",
                "serving_basis": "unknown",
                "nutrition_fields_present": ["kcal"],
                "customization_slots_present": [],
                "identity_confidence": "low",
                "applicability_confidence": "low",
                "applicability_notes": "weak third-party candidate",
                "raw_ref": "raw/websearch/pipeline_no_exact_evidence.json#0",
            },
        ),
    )
    return _case_payload(
        case_id="no_exact_evidence_available",
        intent=intent,
        local_exact=local_exact,
        websearch_case=web_case,
        selected_lane="no_exact_evidence",
        evidence_signal="no_exact_evidence_available",
    )


def _case_payload(
    *,
    case_id: str,
    intent: RetrievalIntent,
    local_exact: Any,
    websearch_case: WebSearchPipelineCase | None,
    selected_lane: str,
    evidence_signal: str,
) -> dict[str, Any]:
    local_candidates = [asdict(candidate) for candidate in local_exact.candidates]
    websearch_pipeline = _build_websearch_case_summary(websearch_case)
    exact_card_staging = _build_exact_card_staging(websearch_pipeline)
    return {
        "case_id": case_id,
        "intent": {
            "base_dish": intent.base_dish,
            "aliases": list(intent.aliases),
            "brand_hint": intent.brand_hint,
            "size_hint": intent.size_hint,
            "retrieval_goal": intent.retrieval_goal,
        },
        "runtime_truth_allowed": False,
        "packet_ready_truth_allowed": False,
        "runtime_mutation_allowed": False,
        "live_websearch_used": False,
        "local_exact": {
            "candidate_count": len(local_candidates),
            "defer_reason": local_exact.defer_reason,
            "candidates": local_candidates,
        },
        "websearch_pipeline": websearch_pipeline,
        "exact_card_staging": exact_card_staging,
        "lane_decision": {
            "selected_lane": selected_lane,
            "websearch_required": selected_lane == "websearch_candidate_review",
            "evidence_signal": evidence_signal,
        },
    }


def _build_websearch_case_summary(websearch_case: WebSearchPipelineCase | None) -> dict[str, Any]:
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


def _build_exact_card_staging(websearch_pipeline: dict[str, Any]) -> dict[str, Any]:
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


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_exact_evidence_lane_policy_artifact"]
