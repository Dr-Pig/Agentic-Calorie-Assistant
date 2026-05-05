from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from typing import Any

from .websearch_source_policy import build_websearch_source_policy_artifact


MAX_SEARCH_RESULTS = 5
MAX_SEARCH_RESULTS_HARD_CAP = 20
MAX_CHUNKS_PER_SOURCE = 3


def build_websearch_cache_rate_license_wall() -> dict[str, Any]:
    source_policy = build_websearch_source_policy_artifact()
    cases = _policy_cases()
    blockers = [
        f"websearch_policy_case_failed:{case['case_id']}"
        for case in cases
        if case["status"] != "pass"
    ]
    clear = not blockers
    return {
        "artifact_type": "accurate_intake_websearch_cache_rate_license_wall_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_websearch_governance_only",
        "claim_scope": "websearch_cache_rate_license_wall",
        "status": "pass" if clear else "blocked",
        "blockers": blockers,
        "live_websearch_used": False,
        "live_provider_used": False,
        "runtime_truth_changed": False,
        "websearch_runtime_truth_allowed": False,
        "runtime_mutation_allowed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "readiness_claimed": False,
        "source_policy_artifact_type": source_policy["artifact_type"],
        "best_practice_basis": {
            "tavily_search": [
                "auto_parameters can change search_depth and consume more credits",
                "max_results should be manually bounded because it controls response size",
                "exact_match is explicit and must be query-planned for exact item lookup",
            ],
            "tavily_extract": [
                "chunks_per_source should bound extracted content",
                "advanced extraction costs more and is not the default diagnostic path",
            ],
        },
        "cases": cases,
        "summary": {
            "case_count": len(cases),
            "pass_count": sum(1 for case in cases if case["status"] == "pass"),
            "fail_count": sum(1 for case in cases if case["status"] != "pass"),
            "max_search_results": MAX_SEARCH_RESULTS,
            "max_search_results_hard_cap": MAX_SEARCH_RESULTS_HARD_CAP,
            "max_chunks_per_source": MAX_CHUNKS_PER_SOURCE,
        },
        "next_required_slice": (
            "websearch_candidate_packet_smoke"
            if clear
            else "inspect_websearch_cache_rate_license_wall_blockers"
        ),
        "non_claims": [
            "no_live_websearch_call",
            "no_live_provider_call",
            "no_websearch_runtime_truth",
            "no_runtime_truth_promotion",
            "no_exact_card_truth_promotion",
            "no_runtime_mutation",
            "no_readiness_claim",
        ],
    }


def build_websearch_search_request_policy(
    *,
    normalized_query: str,
    exact_phrase: str | None = None,
    max_results: int = MAX_SEARCH_RESULTS,
    search_depth: str = "basic",
    diagnostic_advanced_allowed: bool = False,
) -> dict[str, Any]:
    depth = str(search_depth or "basic").lower()
    advanced_downgraded = depth == "advanced" and not diagnostic_advanced_allowed
    if advanced_downgraded:
        depth = "basic"
    exact = str(exact_phrase or "").strip()
    query = f'"{exact}"' if exact else str(normalized_query or "").strip()
    return {
        "policy_version": "websearch_candidate_request_policy_v1",
        "query": query,
        "search_depth": depth,
        "advanced_depth_downgraded": advanced_downgraded,
        "max_results": min(max(int(max_results or 1), 1), MAX_SEARCH_RESULTS),
        "max_results_hard_cap": MAX_SEARCH_RESULTS_HARD_CAP,
        "auto_parameters": False,
        "include_answer": False,
        "include_raw_content": False,
        "exact_match": bool(exact),
        "runtime_truth_allowed": False,
    }


def build_websearch_extract_request_policy(
    *,
    urls: tuple[str, ...],
    query: str,
    chunks_per_source: int = MAX_CHUNKS_PER_SOURCE,
    extract_depth: str = "basic",
    diagnostic_advanced_allowed: bool = False,
) -> dict[str, Any]:
    depth = str(extract_depth or "basic").lower()
    advanced_downgraded = depth == "advanced" and not diagnostic_advanced_allowed
    if advanced_downgraded:
        depth = "basic"
    return {
        "policy_version": "websearch_candidate_extract_policy_v1",
        "urls": list(urls),
        "query": str(query or "").strip(),
        "extract_depth": depth,
        "advanced_depth_downgraded": advanced_downgraded,
        "chunks_per_source": min(max(int(chunks_per_source or 1), 1), MAX_CHUNKS_PER_SOURCE),
        "include_images": False,
        "raw_content_truth_allowed": False,
        "runtime_truth_allowed": False,
    }


def build_websearch_cache_key(
    *,
    normalized_query: str,
    source_class_order: tuple[str, ...],
    search_depth: str,
    max_results: int,
    exact_match: bool,
    include_raw_content: bool,
    raw_snippet: str | None = None,
) -> str:
    del raw_snippet
    payload = {
        "normalized_query": str(normalized_query or "").strip().lower(),
        "source_class_order": list(source_class_order),
        "search_depth": str(search_depth or "basic").lower(),
        "max_results": min(max(int(max_results or 1), 1), MAX_SEARCH_RESULTS_HARD_CAP),
        "exact_match": bool(exact_match),
        "include_raw_content": bool(include_raw_content),
        "policy_version": "websearch_candidate_request_policy_v1",
    }
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]
    return f"websearch_candidate_v1:{digest}"


def _policy_cases() -> list[dict[str, Any]]:
    search_request = build_websearch_search_request_policy(
        normalized_query="Milksha pearl black tea latte",
        exact_phrase="Milksha pearl black tea latte",
    )
    advanced_search = build_websearch_search_request_policy(
        normalized_query="Starbucks latte",
        max_results=999,
        search_depth="advanced",
    )
    extract_request = build_websearch_extract_request_policy(
        urls=("https://brand.example/menu/item",),
        query="Milksha pearl black tea latte calories",
        chunks_per_source=99,
        extract_depth="advanced",
    )
    cache_key = build_websearch_cache_key(
        normalized_query="Milksha pearl black tea latte",
        source_class_order=("official_brand_or_chain_page", "brand_menu_page"),
        search_depth="basic",
        max_results=5,
        exact_match=True,
        include_raw_content=False,
    )
    return [
        {
            "case_id": "exact_brand_search_request_bounded",
            "status": _status(
                {
                    "basic_depth": search_request["search_depth"] == "basic",
                    "exact_match": search_request["exact_match"] is True,
                    "auto_parameters_disabled": search_request["auto_parameters"] is False,
                    "raw_content_disabled": search_request["include_raw_content"] is False,
                }
            ),
            "request": search_request,
        },
        {
            "case_id": "advanced_search_downgraded_without_exception",
            "status": _status(
                {
                    "downgraded": advanced_search["advanced_depth_downgraded"] is True,
                    "bounded_results": advanced_search["max_results"] == MAX_SEARCH_RESULTS,
                }
            ),
            "request": advanced_search,
        },
        {
            "case_id": "extract_chunks_bounded",
            "status": _status(
                {
                    "basic_depth": extract_request["extract_depth"] == "basic",
                    "bounded_chunks": extract_request["chunks_per_source"] == MAX_CHUNKS_PER_SOURCE,
                    "raw_content_not_truth": extract_request["raw_content_truth_allowed"] is False,
                }
            ),
            "request": extract_request,
        },
        {
            "case_id": "cache_key_policy_inputs_only",
            "status": _status(
                {
                    "cache_key_prefix": cache_key.startswith("websearch_candidate_v1:"),
                    "no_raw_snippet": "raw" not in cache_key,
                }
            ),
            "cache_key": cache_key,
        },
    ]


def _status(checks: dict[str, bool]) -> str:
    return "pass" if checks and all(checks.values()) else "fail"


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "build_websearch_cache_key",
    "build_websearch_cache_rate_license_wall",
    "build_websearch_extract_request_policy",
    "build_websearch_search_request_policy",
]
