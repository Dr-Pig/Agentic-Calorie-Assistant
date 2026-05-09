from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "recommendation.application.three_node_shadow_support"
)


def build_fixture_recommendation_three_node_input() -> dict[str, Any]:
    return {
        "current_budget_view": {"remaining_kcal": 700},
        "negative_preference_summary": {
            "items": [{"pattern": "cilantro", "status": "confirmed_negative_preference"}]
        },
        "open_rescue_context": {"accepted_conflict_patterns": ["fried_chicken"]},
        "manager_recommendation_decision_fixture": {
            "decision_mode": "llm_fixture",
            "top_candidate_id": "golden-1",
            "decision_summary": "fixture LLM chose a budget-fitting golden order",
        },
        "candidate_source_fixture": [
            _candidate(
                "golden-1",
                "FamilyMart salad chicken and sweet potato",
                520,
                ["salad_chicken", "sweet_potato"],
                source_type="golden_order",
            ),
            _candidate("over-1", "large pork cutlet rice", 920, ["pork"]),
            _candidate("cilantro-1", "cilantro chicken salad", 430, ["cilantro"]),
            _candidate("fried-1", "fried chicken bento", 580, ["fried_chicken"]),
            _candidate(
                "closed-1",
                "closed store tofu bowl",
                480,
                ["tofu"],
                hard_avoid_flags=["unavailable"],
            ),
        ],
        "shadow_offer_packet_fixture": {
            "decision_mode": "llm_fixture",
            "candidate_id": "golden-1",
            "recommendation_served": False,
            "is_canonical_truth": False,
            "intake_commit_requested": False,
        },
    }


def candidate_guard(payload: Mapping[str, Any]) -> dict[str, Any]:
    allowed: list[str] = []
    filtered: list[dict[str, Any]] = []
    for candidate in candidates(payload):
        candidate_id = str(candidate.get("candidate_id", ""))
        reasons = filter_reason_codes(candidate, payload)
        if reasons:
            filtered.append({"candidate_id": candidate_id, "reason_codes": reasons})
        else:
            allowed.append(candidate_id)
    return {
        "allowed_candidate_ids": allowed,
        "filtered_candidates": filtered,
        "deterministic_guard_only": True,
    }


def filter_reason_codes(
    candidate: Mapping[str, Any], payload: Mapping[str, Any]
) -> list[str]:
    reasons: list[str] = []
    remaining = _int_field(_mapping(payload.get("current_budget_view")), "remaining_kcal")
    kcal_max = _int_field(_mapping(candidate.get("estimated_kcal_range")), "max")
    if remaining is not None and kcal_max is not None and kcal_max > remaining:
        reasons.append("over_budget")
    if _matches_any(candidate, _negative_patterns(payload)):
        reasons.append("confirmed_negative_preference")
    if _matches_any(candidate, _rescue_conflict_patterns(payload)):
        reasons.append("accepted_rescue_conflict")
    reasons.extend(sorted({str(flag) for flag in candidate.get("hard_avoid_flags", [])}))
    return list(dict.fromkeys(reasons))


def offer_blockers(offer: Mapping[str, Any], allowed_ids: set[str]) -> list[str]:
    blockers: list[str] = []
    candidate_id = str(offer.get("candidate_id", ""))
    if candidate_id not in allowed_ids:
        blockers.append(f"shadow_offer_packet_fixture.candidate_not_allowed:{candidate_id}")
    if offer.get("recommendation_served") is True:
        blockers.append("shadow_offer_packet_fixture.recommendation_served_not_allowed")
    if offer.get("is_canonical_truth") is True:
        blockers.append("shadow_offer_packet_fixture.is_canonical_truth_not_allowed")
    if offer.get("intake_commit_requested") is True:
        blockers.append("shadow_offer_packet_fixture.intake_commit_requested_not_allowed")
    return blockers


def source_refs(payload: Mapping[str, Any], candidate_id: str) -> list[str]:
    for candidate in candidates(payload):
        if candidate.get("candidate_id") == candidate_id:
            return [str(ref) for ref in candidate.get("source_refs", [])]
    return []


def candidates(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    values = payload.get("candidate_source_fixture")
    return [item for item in values if isinstance(item, Mapping)] if isinstance(values, list) else []


def empty_candidate_guard() -> dict[str, Any]:
    return {
        "allowed_candidate_ids": [],
        "filtered_candidates": [],
        "deterministic_guard_only": True,
    }


def _negative_patterns(payload: Mapping[str, Any]) -> list[str]:
    summary = _mapping(payload.get("negative_preference_summary"))
    patterns: list[str] = []
    for item in summary.get("items", []):
        if isinstance(item, Mapping) and item.get("status") in {
            "confirmed_negative_preference",
            "allergy",
            "diet_constraint",
        }:
            patterns.append(str(item.get("pattern", "")))
    return patterns


def _rescue_conflict_patterns(payload: Mapping[str, Any]) -> list[str]:
    context = _mapping(payload.get("open_rescue_context"))
    return [str(item) for item in context.get("accepted_conflict_patterns", [])]


def _matches_any(candidate: Mapping[str, Any], patterns: list[str]) -> bool:
    title = _normalize(str(candidate.get("title", "")))
    tokens = {_normalize(str(item)) for item in candidate.get("item_patterns", [])}
    for pattern in patterns:
        normalized = _normalize(pattern)
        if normalized and (normalized in tokens or normalized in title):
            return True
    return False


def _candidate(
    candidate_id: str,
    title: str,
    kcal_max: int,
    item_patterns: list[str],
    *,
    source_type: str = "nearby_fixture",
    hard_avoid_flags: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "title": title,
        "source_type": source_type,
        "estimated_kcal_range": {"min": max(kcal_max - 120, 0), "max": kcal_max},
        "item_patterns": item_patterns,
        "hard_avoid_flags": hard_avoid_flags or [],
        "source_refs": [f"fixture:{candidate_id}"],
    }


def _int_field(mapping: Mapping[str, Any], key: str) -> int | None:
    value = mapping.get(key)
    return value if isinstance(value, int) else None


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _normalize(value: str) -> str:
    return value.lower().replace(" ", "_").replace("-", "_")


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_fixture_recommendation_three_node_input",
    "candidate_guard",
    "empty_candidate_guard",
    "offer_blockers",
    "source_refs",
]
