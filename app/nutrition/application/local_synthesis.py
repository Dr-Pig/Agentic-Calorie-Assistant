from __future__ import annotations

from .evidence_packet_consumption import EvidencePacketConsumptionResult
from .local_synthesis_rules import (
    anchor_rule_for_dish_type,
    anchor_rule_from_packet,
    question_from_followup_hints,
)
from .retrieval_intent import RetrievalIntent
from .small_anchor_store import GenericClarifySupport


def synthesize_local_manager_pass(
    intent: RetrievalIntent,
    consumption: EvidencePacketConsumptionResult,
    *,
    clarify_support: GenericClarifySupport | None = None,
) -> dict[str, object]:
    item_results: list[dict[str, object]] = []
    for packet in consumption.accepted_packets:
        if str(packet.get("accepted_usage") or "") == "exact":
            item_results.append(_build_exact_item_result(packet, rejected_candidates=()))
            continue
        item_results.append(
            _build_anchor_item_result(
                packet,
                rejected_candidates=_matching_rejected_candidates(packet, consumption.rejected_candidates),
            )
        )
    if not item_results and clarify_support is not None:
        item_results.append(_build_clarify_support_item_result(clarify_support))
    elif not item_results and consumption.rejected_candidates:
        item_results.append(_build_unresolved_item_result(intent, consumption.rejected_candidates))
    return {"item_results": item_results}


def _build_exact_item_result(
    packet: dict[str, object],
    *,
    rejected_candidates: tuple[dict[str, object], ...],
) -> dict[str, object]:
    kcal_value = packet.get("kcal")
    kcal = float(kcal_value) if isinstance(kcal_value, (int, float)) else None
    return {
        "interpreted_food_identity": packet.get("canonical_name"),
        "assumed_composition": None,
        "kcal_range": [kcal, kcal] if kcal is not None else None,
        "likely_kcal": kcal,
        "exactness_posture": "exact",
        "evidence_confidence": "exact",
        "evidence_used": [_evidence_used(packet, usage="exact", reason="exact_packet_passed_deterministic_recheck")],
        "rejected_candidates": list(rejected_candidates),
        "uncertainty_reason": "exact_item_card_passed_deterministic_recheck",
        "suggested_followup_question": None,
    }


def _build_anchor_item_result(
    packet: dict[str, object],
    *,
    rejected_candidates: tuple[dict[str, object], ...],
) -> dict[str, object]:
    rule = anchor_rule_from_packet(packet)
    if rule is None:
        dish_type = str(packet.get("dish_type") or "").strip()
        rule = anchor_rule_for_dish_type(dish_type)
    kcal_range = packet.get("kcal_range")
    if isinstance(kcal_range, tuple):
        kcal_range = list(kcal_range)
    likely_kcal = packet.get("likely_kcal")
    if not rule["include_kcal"]:
        kcal_range = None
        likely_kcal = None
    evidence_used = []
    if rule["include_evidence_used"]:
        evidence_used = [_evidence_used(packet, usage="anchor", reason=rule["evidence_reason"])]
    return {
        "interpreted_food_identity": packet.get("canonical_name"),
        "assumed_composition": rule["assumed_composition"],
        "kcal_range": kcal_range,
        "likely_kcal": likely_kcal,
        "exactness_posture": rule["exactness_posture"],
        "evidence_confidence": rule["evidence_confidence"],
        "evidence_used": evidence_used,
        "rejected_candidates": list(rejected_candidates),
        "uncertainty_reason": rule["uncertainty_reason"],
        "suggested_followup_question": rule["suggested_followup_question"],
    }


def _build_unresolved_item_result(
    intent: RetrievalIntent,
    rejected_candidates: tuple[dict[str, object], ...],
) -> dict[str, object]:
    identity = _unresolved_identity(intent, rejected_candidates)
    return {
        "interpreted_food_identity": identity,
        "assumed_composition": None,
        "kcal_range": None,
        "likely_kcal": None,
        "exactness_posture": "unresolved",
        "evidence_confidence": "insufficient",
        "evidence_used": [],
        "rejected_candidates": list(rejected_candidates),
        "uncertainty_reason": "deterministic_hard_recheck_rejected_exact_item_evidence",
        "suggested_followup_question": "\u8acb\u78ba\u8a8d\u5177\u9ad4\u54c1\u9805\u8207\u5c3a\u5bf8\u6216\u4efd\u91cf\u3002",
    }


def _unresolved_identity(
    intent: RetrievalIntent,
    rejected_candidates: tuple[dict[str, object], ...],
) -> object:
    requested_identity = intent.aliases[0] if intent.aliases else intent.base_dish
    if rejected_candidates and _all_web_search_mismatch_rejections(rejected_candidates) and requested_identity:
        return requested_identity
    if rejected_candidates:
        return rejected_candidates[0].get("canonical_name")
    return requested_identity


def _all_web_search_mismatch_rejections(
    rejected_candidates: tuple[dict[str, object], ...],
) -> bool:
    if not rejected_candidates:
        return False
    mismatch_risk_types = {"wrong_item", "sibling_variant", "wrong_size", "wrong_modifier", "insufficient_evidence"}
    return all(
        candidate.get("source_type") == "web_search"
        and candidate.get("risk_type") in mismatch_risk_types
        for candidate in rejected_candidates
    )


def _build_clarify_support_item_result(clarify_support: GenericClarifySupport) -> dict[str, object]:
    return {
        "interpreted_food_identity": clarify_support.canonical_name,
        "assumed_composition": "composition unknown basket",
        "kcal_range": None,
        "likely_kcal": None,
        "exactness_posture": "unresolved",
        "evidence_confidence": "insufficient",
        "evidence_used": [],
        "rejected_candidates": [],
        "uncertainty_reason": clarify_support.unresolved_reason
        or "generic_semantic_only_requires_clarification",
        "suggested_followup_question": question_from_followup_hints(clarify_support.followup_hints),
    }


def _matching_rejected_candidates(
    packet: dict[str, object],
    rejected_candidates: tuple[dict[str, object], ...],
) -> tuple[dict[str, object], ...]:
    canonical_name = packet.get("canonical_name")
    matched = [
        candidate for candidate in rejected_candidates if candidate.get("canonical_name") == canonical_name
    ]
    return tuple(matched)


def _evidence_used(packet: dict[str, object], *, usage: str, reason: str) -> dict[str, object]:
    return {
        "packet_id": packet.get("packet_id"),
        "source_type": packet.get("source_type"),
        "source_quality_label": packet.get("source_quality_label"),
        "usage": usage,
        "reason": reason,
    }


__all__ = ["synthesize_local_manager_pass"]
