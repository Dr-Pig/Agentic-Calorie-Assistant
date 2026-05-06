from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Iterable, Mapping

from .web_search_candidate_producer import (
    MAX_WEBSEARCH_RESULTS_HARD_CAP,
    PROVIDER_TRUTH_MARKERS,
    bounded_websearch_max_results,
    produce_web_search_candidates,
)


FORBIDDEN_PROVIDER_TRUTH_FIELDS = frozenset(
    {
        "kcal",
        *PROVIDER_TRUTH_MARKERS,
    }
)


def build_websearch_source_adapter_guard() -> dict[str, Any]:
    cases = (
        _raw_truth_fields_ignored_case(),
        _malformed_optional_fields_degraded_case(),
        _candidate_count_capped_case(),
    )
    blockers = [
        blocker
        for case in cases
        for blocker in case["blockers"]
    ]
    clear = not blockers
    return {
        "artifact_type": "accurate_intake_websearch_source_adapter_guard_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_source_adapter_guard_only",
        "claim_scope": "websearch_provider_hit_to_candidate_boundary",
        "status": "pass" if clear else "blocked",
        "blockers": sorted(set(blockers)),
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "cases": list(cases),
        "summary": {
            "case_count": len(cases),
            "candidate_count": sum(case["candidate_count"] for case in cases),
            "truth_field_leak_count": sum(
                len(case["truth_field_violations"]) for case in cases
            ),
            "max_results_hard_cap": MAX_WEBSEARCH_RESULTS_HARD_CAP,
            "bounded_examples": {
                "-1": bounded_websearch_max_results(-1),
                "5": bounded_websearch_max_results(5),
                "999": bounded_websearch_max_results(999),
                "true": bounded_websearch_max_results(True),
            },
        },
        "best_practice_basis": [
            "Search API max_results should be explicitly bounded; documented range is 0..20.",
            "Raw-content inclusion and max_results affect response size and must not be adapter defaults.",
            "WebSearch results are candidate recall only; source snippets are not nutrition truth.",
        ],
        "next_required_slice": (
            "websearch_candidate_lane_status_packet"
            if clear
            else "inspect_websearch_source_adapter_guard_blockers"
        ),
        "non_claims": [
            "no_live_websearch_call",
            "no_live_provider_call",
            "no_websearch_runtime_truth",
            "no_exact_card_truth_promotion",
            "no_runtime_mutation",
            "no_readiness_claim",
        ],
    }


def _raw_truth_fields_ignored_case() -> dict[str, Any]:
    candidates = produce_web_search_candidates(
        query="Milksha pearl black tea latte",
        identity_target="Milksha pearl black tea latte",
        raw_hits=[
            {
                "url": "https://milksha.example/menu/pearl-black-tea-latte",
                "title": "Milksha pearl black tea latte",
                "snippet": "official menu candidate",
                "source_quality_hint": "high",
                "source_class_hint": "promotion_allowed",
                "officialness": "final_truth",
                "identity_confidence": "runtime_truth_allowed",
                "serving_basis": "likely_kcal",
                "nutrition_fields_present": ["kcal", "promotion_allowed"],
                "customization_slots_present": ["size", "runtime_truth_allowed"],
                "applicability_notes": "exact_card_created",
                "raw_ref": "raw/websearch/final_truth.json#0",
                "source_url": "https://milksha.example/menu/final_truth",
                "source_title": "Milksha final_truth",
                "content": "runtime_truth_allowed likely_kcal kcal_range",
                "runtime_truth_allowed": True,
                "final_truth": {"kcal": 400},
                "kcal_range": [380, 420],
                "promotion_allowed": True,
            }
        ],
    )
    return _case_result(
        case_id="raw_provider_truth_fields_ignored",
        candidates=candidates,
        extra_checks={
            "raw_fields_filtered_ok": _truth_field_violations(candidates) == [],
            "candidate_only_source_type": all(
                candidate.get("source_type") == "web_search" for candidate in candidates
            ),
        },
    )


def _malformed_optional_fields_degraded_case() -> dict[str, Any]:
    candidates = produce_web_search_candidates(
        query="Milksha pearl black tea latte",
        identity_target="Milksha pearl black tea latte",
        raw_hits=[
            {
                "url": "https://example.com/result",
                "title": 123,
                "snippet": None,
                "score": "bad-score",
                "officialness": 42,
                "source_quality_label": None,
                "serving_basis": 9,
                "nutrition_fields_present": "kcal",
                "customization_slots_present": None,
                "identity_confidence": 0.9,
                "applicability_confidence": {},
            }
        ],
    )
    candidate = candidates[0] if candidates else {}
    return _case_result(
        case_id="malformed_optional_fields_degraded",
        candidates=candidates,
        extra_checks={
            "source_title_degraded": candidate.get("source_title") == "",
            "score_degraded": candidate.get("score") is None,
            "quality_degraded": candidate.get("source_quality_hint") == "unknown",
            "identity_confidence_degraded": candidate.get("identity_confidence") == "unknown",
        },
    )


def _candidate_count_capped_case() -> dict[str, Any]:
    candidates = produce_web_search_candidates(
        query="Milksha pearl black tea latte",
        identity_target="Milksha pearl black tea latte",
        raw_hits=[
            {
                "url": f"https://example.com/menu/{index}",
                "title": f"candidate {index}",
                "snippet": "candidate",
            }
            for index in range(MAX_WEBSEARCH_RESULTS_HARD_CAP + 5)
        ],
    )
    return _case_result(
        case_id="candidate_count_capped",
        candidates=candidates,
        extra_checks={
            "candidate_count_capped": len(candidates) == MAX_WEBSEARCH_RESULTS_HARD_CAP,
            "hard_cap_matches_policy": bounded_websearch_max_results(999)
            == MAX_WEBSEARCH_RESULTS_HARD_CAP,
        },
    )


def _case_result(
    *,
    case_id: str,
    candidates: list[dict[str, Any]],
    extra_checks: Mapping[str, bool],
) -> dict[str, Any]:
    truth_violations = _truth_field_violations(candidates)
    checks = {
        "candidate_payload_present": bool(candidates),
        "raw_fields_filtered_ok": not truth_violations,
        **dict(extra_checks),
    }
    blockers = [
        f"{case_id}.{check_id}"
        for check_id, passed in checks.items()
        if passed is not True
    ]
    return {
        "case_id": case_id,
        "status": "pass" if not blockers else "blocked",
        "blockers": blockers,
        "candidate_count": len(candidates),
        "truth_field_violations": truth_violations,
        "checks": checks,
    }


def _truth_field_violations(candidates: Iterable[dict[str, Any]]) -> list[str]:
    violations: set[str] = set()
    for candidate in candidates:
        for key, value in candidate.items():
            if key in FORBIDDEN_PROVIDER_TRUTH_FIELDS:
                violations.add(f"key:{key}")
            for marker in _string_marker_violations(value):
                violations.add(f"string:{key}:{marker}")
    return sorted(violations)


def _string_marker_violations(value: object) -> list[str]:
    values = value if isinstance(value, list) else [value]
    markers: set[str] = set()
    for item in values:
        if not isinstance(item, str):
            continue
        normalized = item.lower()
        markers.update(marker for marker in PROVIDER_TRUTH_MARKERS if marker in normalized)
    return sorted(markers)


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "FORBIDDEN_PROVIDER_TRUTH_FIELDS",
    "build_websearch_source_adapter_guard",
]
