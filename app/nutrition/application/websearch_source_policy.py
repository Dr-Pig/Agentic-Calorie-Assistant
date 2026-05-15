from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Mapping


TRUSTED_SOURCE_CLASSES = {
    "official_brand_or_chain_page",
    "brand_menu_page",
    "brand_menu_component_page",
    "official_nutrition_pdf",
}

EXTRACT_ALLOWED_LICENSE_STATUSES = {
    "public_menu_page",
    "official_public_page",
    "open_license",
    "licensed_for_cache",
}


def build_websearch_source_policy_artifact() -> dict[str, Any]:
    return {
        "artifact_type": "accurate_intake_websearch_source_policy_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "track": "FDB",
        "claim_scope": "websearch_source_cache_rate_license_policy_only",
        "live_websearch_used": False,
        "runtime_truth_changed": False,
        "websearch_runtime_truth_allowed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "max_search_attempts": 2,
        "search_depth_policy": {
            "default": "basic",
            "advanced_allowed": "diagnostic_exception_only",
            "reason": "Tavily advanced depth costs more and should not be default for candidate recall",
        },
        "cache_policy": {
            "cache_key_fields": [
                "normalized_query",
                "source_class_order",
                "search_depth",
                "max_results",
            ],
            "ttl_policy": "diagnostic_cache_can_expire_without_truth_effect",
            "cache_hit_truth_allowed": False,
        },
        "rate_policy": {
            "max_search_attempts": 2,
            "max_results": 5,
            "max_results_hard_cap": 20,
            "auto_parameters": False,
        },
        "license_policy": {
            "unknown_license_behavior": "candidate_only_requires_review",
            "unknown_robots_behavior": "candidate_only_requires_review",
            "extract_allowed_license_statuses": sorted(EXTRACT_ALLOWED_LICENSE_STATUSES),
            "allowed_source_classes": sorted(TRUSTED_SOURCE_CLASSES),
        },
        "best_practice_basis": [
            "Tavily Search API search_depth cost differs by depth",
            "Tavily Search API max_results is bounded",
            "Tavily exact_match is explicit and should be query-planned, not assumed",
        ],
        "non_claims": [
            "no_live_websearch_call",
            "no_websearch_runtime_truth",
            "no_runtime_truth_promotion",
            "no_exact_card_truth_promotion",
            "no_runtime_mutation",
            "no_readiness_claim",
        ],
    }


def classify_websearch_source_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    source_class = _normalized_token(candidate.get("source_class"))
    license_status = _normalized_token(candidate.get("license_status") or "unknown")
    robots_status = _normalized_token(candidate.get("robots_status") or "unknown")
    identity_confidence = _normalized_token(candidate.get("identity_confidence"))
    serving_basis = str(candidate.get("serving_basis_candidate") or "").strip()
    nutrition_fields = [
        _normalized_token(field)
        for field in candidate.get("nutrition_fields_present") or []
    ]
    block_reasons = _source_block_reasons(
        source_class=source_class,
        license_status=license_status,
        robots_status=robots_status,
        identity_confidence=identity_confidence,
        serving_basis=serving_basis,
        nutrition_fields=nutrition_fields,
    )

    if source_class not in TRUSTED_SOURCE_CLASSES:
        candidate_class = "weak_or_unusable_candidate"
        extract_candidate_allowed = False
    elif block_reasons:
        candidate_class = "blocked_source_policy_candidate"
        extract_candidate_allowed = False
    else:
        candidate_class = "exact_candidate_for_extract_review"
        extract_candidate_allowed = True

    return {
        "source_url": candidate.get("source_url"),
        "source_class": source_class,
        "candidate_class": candidate_class,
        "extract_candidate_allowed": extract_candidate_allowed,
        "runtime_truth_allowed": False,
        "packet_ready_truth_allowed": False,
        "cache_allowed": (
            license_status in EXTRACT_ALLOWED_LICENSE_STATUSES
            and robots_status == "allowed"
        ),
        "requires_later_promotion_path": True,
        "block_reasons": block_reasons,
    }


def _normalized_token(value: object) -> str:
    return str(value or "").strip().lower()


def _source_block_reasons(
    *,
    source_class: str,
    license_status: str,
    robots_status: str,
    identity_confidence: str,
    serving_basis: str,
    nutrition_fields: list[str],
) -> list[str]:
    reasons = []
    if source_class not in TRUSTED_SOURCE_CLASSES:
        reasons.append("source_class_not_trusted")
    if license_status == "unknown":
        reasons.append("license_unknown")
    elif license_status not in EXTRACT_ALLOWED_LICENSE_STATUSES:
        reasons.append("license_not_allowed")
    if robots_status != "allowed":
        reasons.append("robots_unknown" if robots_status == "unknown" else "robots_blocked")
    if identity_confidence != "high":
        reasons.append("identity_confidence_not_high")
    if not serving_basis or serving_basis.lower() == "unknown":
        reasons.append("serving_basis_missing")
    if "kcal" not in nutrition_fields:
        reasons.append("kcal_missing")
    return reasons


__all__ = [
    "TRUSTED_SOURCE_CLASSES",
    "EXTRACT_ALLOWED_LICENSE_STATUSES",
    "build_websearch_source_policy_artifact",
    "classify_websearch_source_candidate",
]
