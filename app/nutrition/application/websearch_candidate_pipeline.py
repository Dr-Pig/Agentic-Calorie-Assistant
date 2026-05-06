from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Iterable, Mapping

from .evidence_candidate_packetizer import add_hard_recheck_metadata_many
from .retrieval_intent import RetrievalIntent
from .selected_extract_policy import choose_selected_extract_packet
from .web_search_candidate_producer import produce_web_search_candidates
from .web_search_packetizer import build_web_search_candidate_packets
from .websearch_candidate_classification import (
    classify_candidate_packet,
    source_policy_filtered_extract_decision_trace,
)
from .websearch_candidate_pipeline_expansion_fixtures import (
    build_expanded_websearch_pipeline_cases,
)
from .websearch_source_policy import build_websearch_source_policy_artifact

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
        "source_policy": build_websearch_source_policy_artifact(),
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
            "source_class_counts": _source_class_counts(classifications),
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
        classify_candidate_packet(
            packet,
            selected_extract_packet_id=extract_decision.selected_search_packet_id,
        )
        for packet in rechecked_packets
    ]
    extract_decision_trace = source_policy_filtered_extract_decision_trace(
        extract_decision_trace=extract_decision.to_trace(),
        classifications=classifications,
    )
    return {
        "case_id": case.case_id,
        "live_websearch_used": False,
        "runtime_truth_changed": False,
        "query_plan": query_plan,
        "candidate_packets": list(rechecked_packets),
        "candidate_classifications": classifications,
        "selected_extract_decision": extract_decision_trace,
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


def _classification_counts(classifications: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for classification in classifications:
        key = str(classification.get("candidate_class") or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _source_class_counts(classifications: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for classification in classifications:
        key = str(classification.get("source_class") or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _identity_target(intent: RetrievalIntent) -> str:
    for alias in intent.aliases:
        if str(alias or "").strip():
            return str(alias).strip()
    return str(intent.base_dish or "").strip()


def _default_cases() -> tuple[WebSearchPipelineCase, ...]:
    return build_expanded_websearch_pipeline_cases(case_factory=WebSearchPipelineCase)


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "WEBSEARCH_CANDIDATE_PIPELINE_NON_CLAIMS",
    "WebSearchPipelineCase",
    "build_websearch_candidate_pipeline_diagnostic",
    "build_websearch_query_plan",
]
