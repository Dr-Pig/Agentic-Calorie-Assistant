from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .fooddb_retrieval_candidate_payload import (
    _ambiguity_reason,
    _candidate_payload,
    _rank_candidates,
    _ranking_policy,
    _vector_search_policy,
)
from .fooddb_retrieval_matching import _best_match
from .fooddb_retrieval_query import (
    ALIAS_EXPANSIONS,
    BASKET_TERMS,
    _bare_basket_match,
    _candidate_query_terms,
    _normalized_query,
)
from .fooddb_retrieval_records import (
    IndexedFoodRecord,
    build_runtime_retrieval_records_from_small_anchor_payload,
)


def retrieve_fooddb_candidates(
    query: str,
    *,
    retrieval_records: tuple[IndexedFoodRecord, ...],
    limit: int = 5,
    listed_components: list[str] | None = None,
) -> dict[str, Any]:
    normalized = _normalized_query(query)
    candidate_terms = _candidate_query_terms(normalized)
    normalized = {**normalized, "candidate_terms": candidate_terms}
    semantic_basket = _bare_basket_match(normalized["lookup_key"], retrieval_records)
    listed_components = _listed_components_from_manager(listed_components)

    if semantic_basket and not listed_components:
        return _result(
            normalized_query=normalized,
            accepted=[],
            rejected=[],
            retrieval_boundary="bare_basket_ask_followup_no_estimate",
            followup_hints=semantic_basket,
        )

    if listed_components:
        component_candidates = []
        rejected = []
        for component in listed_components:
            match = _best_match(component, retrieval_records)
            if match is None:
                rejected.append(
                    {
                        "query_component": component,
                        "reason": "no_runtime_anchor_match",
                    }
                )
                continue
            component_candidates.append(
                _candidate_payload(
                    match,
                    query_component=component,
                    modifier_hints=normalized["modifier_hints"],
                )
            )
        component_candidates.sort(key=lambda item: str(item["anchor_id"]))
        return _result(
            normalized_query=normalized,
            accepted=component_candidates[:limit],
            rejected=rejected,
            retrieval_boundary="listed_basket_component_recall",
            followup_hints=[],
        )

    candidates = []
    rejected = []
    for term in candidate_terms:
        match = _best_match(term, retrieval_records)
        if match is None:
            rejected.append({"query_term": term, "reason": "no_runtime_anchor_match"})
            continue
        payload = _candidate_payload(
            match,
            query_component=term,
            modifier_hints=normalized["modifier_hints"],
        )
        if payload not in candidates:
            candidates.append(payload)
    candidates = _dedupe_candidates_by_anchor(_rank_candidates(candidates))[:limit]

    return _result(
        normalized_query=normalized,
        accepted=candidates,
        rejected=rejected[:limit],
        retrieval_boundary="single_or_composite_candidate_recall",
        followup_hints=[],
    )


def build_fooddb_retrieval_policy_artifact(
    *,
    retrieval_records: tuple[IndexedFoodRecord, ...],
) -> dict[str, Any]:
    runtime_anchor_records = [
        record for record in retrieval_records if record.runtime_role == "common_serving_anchor"
    ]
    semantic_basket_records = [
        record for record in retrieval_records if record.runtime_role == "basket_family_semantic_only"
    ]
    return {
        "artifact_type": "accurate_intake_fooddb_retrieval_policy",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "claim_scope": "fooddb_retrieval_policy_report_only",
        "runtime_truth_changed": False,
        "product_loop_integration_claimed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "retrieval_architecture": {
            "dependency_inversion": {
                "policy_layer_depends_on": "FoodDB evidence records supplied by adapter",
                "forbidden_dependencies": [
                    "sqlite_file_path",
                    "supabase_client",
                    "webshell",
                    "manager_context_packet",
                ],
                "future_adapter_shape": "local_json_or_sqlite_or_supabase_can_supply_same_records",
            },
            "stages": [
                "text_normalization",
                "exact_alias_lookup",
                "alias_expansion_lookup",
                "fuzzy_lexical_lookup",
                "manager_owned_listed_component_lookup",
                "deterministic_candidate_ranking",
                "manager_disambiguation_later",
            ],
            "vector_search_policy": _vector_search_policy(),
        },
        "summary": {
            "runtime_anchor_indexed_count": len(runtime_anchor_records),
            "semantic_basket_indexed_count": len(semantic_basket_records),
            "source_lane_counts": _source_lane_counts(retrieval_records),
            "alias_expansion_count": len(ALIAS_EXPANSIONS),
            "basket_family_count": len(BASKET_TERMS),
        },
        "manager_retrieval_catalog": {
            "claim_scope": "compact_runtime_retrieval_catalog_not_raw_database",
            "raw_source_rows_included": False,
            "candidate_only_records_included": False,
            "full_fooddb_included": False,
            "anchors": [
                {
                    "anchor_id": record.anchor_id,
                    "canonical_name": record.canonical_name,
                    "aliases": list(record.aliases),
                    "dish_type": record.dish_type,
                    "source_lane": record.source_lane,
                    "runtime_usage_boundary": record.runtime_usage_boundary,
                }
                for record in retrieval_records
            ],
        },
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_product_loop_integration",
            "no_manager_context_change",
            "no_packetizer_format_change",
            "no_live_provider_call",
            "no_vector_truth_selection",
        ],
    }


def _result(
    *,
    normalized_query: dict[str, Any],
    accepted: list[dict[str, Any]],
    rejected: list[dict[str, Any]],
    retrieval_boundary: str,
    followup_hints: list[str],
) -> dict[str, Any]:
    return {
        "retrieval_scope": "candidate_recall_only",
        "truth_selection_forbidden": True,
        "runtime_mutation_allowed": False,
        "retrieval_boundary": retrieval_boundary,
        "normalized_query": normalized_query,
        "accepted_candidates": accepted,
        "rejected_candidates": rejected,
        "ambiguity_reason": _ambiguity_reason(accepted),
        "followup_hints": followup_hints,
        "vector_search_policy": _vector_search_policy(),
        "ranking_policy": _ranking_policy(),
    }


def _source_lane_counts(records: tuple[IndexedFoodRecord, ...]) -> dict[str, int]:
    counts = {
        "exact_item_card": 0,
        "generic_common_serving": 0,
        "listed_component": 0,
        "basket_family_semantic_only": 0,
    }
    for record in records:
        lane = record.source_lane
        if lane in counts:
            counts[lane] += 1
    return counts


def _dedupe_candidates_by_anchor(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidates:
        anchor_id = str(candidate.get("anchor_id") or "")
        if anchor_id in seen:
            continue
        seen.add(anchor_id)
        deduped.append(candidate)
    return deduped


def _listed_components_from_manager(listed_components: list[str] | None) -> list[str]:
    if not isinstance(listed_components, list):
        return []
    return [component for item in listed_components if (component := str(item or "").strip())]


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "IndexedFoodRecord",
    "build_fooddb_retrieval_policy_artifact",
    "build_runtime_retrieval_records_from_small_anchor_payload",
    "retrieve_fooddb_candidates",
]
