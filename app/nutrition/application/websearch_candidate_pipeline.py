from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Iterable, Mapping

from .evidence_candidate_packetizer import add_hard_recheck_metadata_many
from .retrieval_intent import RetrievalIntent
from .selected_extract_policy import choose_selected_extract_packet
from .web_search_candidate_producer import produce_web_search_candidates
from .web_search_packetizer import build_web_search_candidate_packets


WEBSEARCH_CANDIDATE_PIPELINE_NON_CLAIMS = [
    "no_live_websearch_call",
    "no_live_provider_call",
    "no_websearch_runtime_truth",
    "no_runtime_truth_promotion",
    "no_exact_card_truth_promotion",
    "no_runtime_mutation",
    "no_readiness_claim",
]


@dataclass(frozen=True)
class WebSearchPipelineCase:
    case_id: str
    intent: RetrievalIntent
    raw_hits: tuple[Mapping[str, Any], ...]


def build_websearch_candidate_pipeline_diagnostic(
    cases: tuple[WebSearchPipelineCase, ...] = (),
) -> dict[str, Any]:
    pipeline_cases = cases or _default_cases()
    case_results = [_case_result(case) for case in pipeline_cases]
    classifications = [
        classification
        for case in case_results
        for classification in case["candidate_classifications"]
    ]
    return {
        "artifact_type": "accurate_intake_websearch_candidate_pipeline_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "offline_candidate_pipeline_only",
        "claim_scope": "deterministic_websearch_candidate_query_and_classification",
        "source_policy_version": "websearch_candidate_pipeline_v1",
        "max_search_attempts": 2,
        "live_websearch_used": False,
        "live_provider_used": False,
        "runtime_truth_changed": False,
        "websearch_runtime_truth_allowed": False,
        "manager_context_changed": False,
        "runtime_packetizer_contract_changed": False,
        "cases": case_results,
        "summary": {
            "case_count": len(case_results),
            "candidate_packet_count": sum(len(case["candidate_packets"]) for case in case_results),
            "runtime_truth_allowed_count": sum(
                1 for classification in classifications if classification["runtime_truth_allowed"] is True
            ),
            "extract_candidate_allowed_count": sum(
                1
                for classification in classifications
                if classification["extract_candidate_allowed"] is True
            ),
            "classification_counts": _classification_counts(classifications),
        },
        "non_claims": list(WEBSEARCH_CANDIDATE_PIPELINE_NON_CLAIMS),
    }


def _case_result(case: WebSearchPipelineCase) -> dict[str, Any]:
    query_plan = build_websearch_query_plan(case.intent)
    query = query_plan["search_attempts"][0]["query"]
    identity_target = _identity_target(case.intent)
    candidates = produce_web_search_candidates(
        query=query,
        identity_target=identity_target,
        raw_hits=case.raw_hits,
    )
    packets = build_web_search_candidate_packets(case.intent, candidates)
    rechecked_packets = add_hard_recheck_metadata_many(packets)
    extract_decision = choose_selected_extract_packet(rechecked_packets)
    classifications = [
        _classify_candidate_packet(
            packet,
            selected_extract_packet_id=extract_decision.selected_search_packet_id,
        )
        for packet in rechecked_packets
    ]
    return {
        "case_id": case.case_id,
        "live_websearch_used": False,
        "runtime_truth_changed": False,
        "query_plan": query_plan,
        "candidate_packets": list(rechecked_packets),
        "candidate_classifications": classifications,
        "selected_extract_decision": extract_decision.to_trace(),
    }


def build_websearch_query_plan(intent: RetrievalIntent) -> dict[str, Any]:
    identity = _identity_target(intent)
    exact_query = " ".join(part for part in (intent.brand_hint, identity, intent.size_hint) if part)
    exact_query = exact_query or identity
    return {
        "policy_version": "websearch_candidate_pipeline_v1",
        "retrieval_goal": intent.retrieval_goal,
        "max_search_attempts": 2,
        "source_class_order": [
            "official_brand_or_chain_page",
            "brand_menu_page",
            "high_quality_search_candidate",
        ],
        "semantic_search_role": "candidate_recall_only",
        "search_attempts": [
            {
                "attempt": 1,
                "purpose": "exact_brand_or_menu_candidate",
                "query": exact_query,
                "metadata_first": True,
            },
            {
                "attempt": 2,
                "purpose": "fallback_official_menu_nutrition_candidate",
                "query": f"{exact_query} official menu nutrition",
                "metadata_first": True,
            },
        ],
    }


def _classify_candidate_packet(
    packet: dict[str, Any],
    *,
    selected_extract_packet_id: str | None,
) -> dict[str, Any]:
    risks = [str(risk) for risk in packet.get("hard_recheck_risks", [])]
    packet_id = str(packet.get("packet_id") or "")
    source_quality = str(packet.get("source_quality_label") or "")
    match_type = str(packet.get("match_type") or "")
    size_match = str(packet.get("size_or_serving_match") or "")
    sibling_risk = bool((packet.get("sibling_variant_risk") or {}).get("present"))
    if source_quality == "third_party":
        candidate_class = "weak_or_unusable_candidate"
        manager_expected_behavior = "reject_or_request_better_source"
    elif "wrong_size" in risks or size_match == "different":
        candidate_class = "near_exact_wrong_size_candidate"
        manager_expected_behavior = "ask_followup"
    elif sibling_risk or "sibling_variant" in risks or match_type == "related":
        candidate_class = "near_exact_sibling_candidate"
        manager_expected_behavior = "ask_followup"
    elif packet_id == selected_extract_packet_id:
        candidate_class = "exact_candidate_for_extract_review"
        manager_expected_behavior = "candidate_review_no_commit"
    elif match_type == "exact":
        candidate_class = "exact_candidate_blocked_by_policy"
        manager_expected_behavior = "candidate_review_no_commit"
    else:
        candidate_class = "weak_or_unusable_candidate"
        manager_expected_behavior = "reject_or_request_better_source"

    return {
        "packet_id": packet_id,
        "candidate_class": candidate_class,
        "manager_expected_behavior": manager_expected_behavior,
        "extract_candidate_allowed": packet_id == selected_extract_packet_id,
        "runtime_truth_allowed": False,
        "packet_ready_truth_allowed": False,
        "requires_later_promotion_path": True,
        "source_quality_label": source_quality,
        "match_type": match_type,
        "size_or_serving_match": size_match,
        "hard_recheck_risks": risks,
    }


def _classification_counts(classifications: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for classification in classifications:
        key = str(classification.get("candidate_class") or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _identity_target(intent: RetrievalIntent) -> str:
    for alias in intent.aliases:
        if str(alias or "").strip():
            return str(alias).strip()
    return str(intent.base_dish or "").strip()


def _default_cases() -> tuple[WebSearchPipelineCase, ...]:
    milksha_intent = _intent(
        base_dish="pearl black tea latte",
        alias="Milksha pearl black tea latte",
        brand_hint="Milksha",
    )
    starbucks_intent = _intent(
        base_dish="iced latte",
        alias="Starbucks iced latte large",
        brand_hint="Starbucks",
        size_hint="large",
    )
    return (
        WebSearchPipelineCase(
            case_id="pipeline_milksha_exact",
            intent=milksha_intent,
            raw_hits=(
                _hit(
                    title="Milksha pearl black tea latte",
                    url="https://milksha.example/menu/pearl-black-tea-latte",
                    brand_detected="Milksha",
                    identity_confidence="high",
                    raw_ref="raw/websearch/pipeline_milksha_exact.json#0",
                ),
            ),
        ),
        WebSearchPipelineCase(
            case_id="pipeline_milksha_sibling",
            intent=milksha_intent,
            raw_hits=(
                _hit(
                    title="Milksha pearl fresh milk tea",
                    url="https://milksha.example/menu/pearl-fresh-milk-tea",
                    brand_detected="Milksha",
                    identity_confidence="medium",
                    raw_ref="raw/websearch/pipeline_milksha_sibling.json#0",
                ),
            ),
        ),
        WebSearchPipelineCase(
            case_id="pipeline_third_party_weak",
            intent=milksha_intent,
            raw_hits=(
                _hit(
                    title="Milksha pearl black tea latte calories",
                    url="https://third-party.example/milksha",
                    brand_detected="Milksha",
                    officialness="unknown",
                    source_quality_label="low",
                    identity_confidence="high",
                    raw_ref="raw/websearch/pipeline_third_party_weak.json#0",
                ),
            ),
        ),
        WebSearchPipelineCase(
            case_id="pipeline_starbucks_wrong_size",
            intent=starbucks_intent,
            raw_hits=(
                _hit(
                    title="Starbucks iced latte medium",
                    url="https://starbucks.example/menu/iced-latte-medium",
                    brand_detected="Starbucks",
                    identity_confidence="high",
                    raw_ref="raw/websearch/pipeline_starbucks_wrong_size.json#0",
                ),
            ),
        ),
    )


def _intent(
    *,
    base_dish: str,
    alias: str,
    brand_hint: str,
    size_hint: str | None = None,
) -> RetrievalIntent:
    return RetrievalIntent(
        base_dish=base_dish,
        aliases=[alias],
        brand_hint=brand_hint,
        size_hint=size_hint,
        modifier_hints=[],
        listed_items=[],
        retrieval_goal="exact_brand_lookup",
    )


def _hit(
    *,
    title: str,
    url: str,
    brand_detected: str,
    officialness: str = "official",
    source_quality_label: str = "high",
    identity_confidence: str = "medium",
    raw_ref: str,
) -> dict[str, Any]:
    return {
        "url": url,
        "domain": "example.test",
        "title": title,
        "snippet": "deterministic search candidate",
        "score": 0.93,
        "officialness": officialness,
        "source_quality_label": source_quality_label,
        "brand_detected": brand_detected,
        "channel_detected": "handmade_foodservice",
        "serving_basis": "per_cup",
        "nutrition_fields_present": ["kcal"],
        "customization_slots_present": ["size"],
        "identity_confidence": identity_confidence,
        "applicability_confidence": "medium",
        "applicability_notes": "deterministic fixture candidate",
        "raw_ref": raw_ref,
    }


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "WEBSEARCH_CANDIDATE_PIPELINE_NON_CLAIMS",
    "WebSearchPipelineCase",
    "build_websearch_candidate_pipeline_diagnostic",
    "build_websearch_query_plan",
]
