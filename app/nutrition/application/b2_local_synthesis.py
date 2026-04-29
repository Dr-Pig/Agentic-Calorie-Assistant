from __future__ import annotations

from typing import Any

from .b2_packet_consumption import B2PacketConsumptionResult
from .retrieval_intent import RetrievalIntent
from .small_anchor_store import GenericClarifySupport


def synthesize_b2_local_manager_pass2(
    intent: RetrievalIntent,
    consumption: B2PacketConsumptionResult,
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
    rule = _anchor_rule_from_semantic_metadata(packet)
    if rule is None:
        dish_type = str(packet.get("dish_type") or "").strip()
        rule = _anchor_rule_for_dish_type(dish_type)
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
        "suggested_followup_question": _question_from_followup_hints(clarify_support.followup_hints),
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


def _anchor_rule_for_dish_type(dish_type: str) -> dict[str, Any]:
    if dish_type in {"single_item", "listed_item"}:
        return {
            "assumed_composition": "single item" if dish_type == "single_item" else "listed item",
            "exactness_posture": "estimated",
            "evidence_confidence": "strong",
            "include_kcal": True,
            "include_evidence_used": True,
            "evidence_reason": "generic_anchor_used_as_anchor_evidence",
            "uncertainty_reason": "generic_anchor_support",
            "suggested_followup_question": None,
        }
    if dish_type == "customizable_drink":
        return {
            "assumed_composition": "customizable drink",
            "exactness_posture": "estimated",
            "evidence_confidence": "moderate",
            "include_kcal": True,
            "include_evidence_used": True,
            "evidence_reason": "generic_anchor_drink_used_as_anchor_evidence",
            "uncertainty_reason": "generic_anchor_drink_requires_modifier_refinement",
            "suggested_followup_question": "\u8acb\u88dc\u5145\u7cd6\u5ea6\u548c\u676f\u578b\u3002",
        }
    if dish_type == "generic_meal":
        return {
            "assumed_composition": "generic meal",
            "exactness_posture": "provisional",
            "evidence_confidence": "moderate",
            "include_kcal": True,
            "include_evidence_used": True,
            "evidence_reason": "generic_anchor_meal_used_as_anchor_evidence",
            "uncertainty_reason": "generic_anchor_meal_requires_soft_refinement",
            "suggested_followup_question": "\u8acb\u88dc\u5145\u4e3b\u83dc\u505a\u6cd5\u6216\u767d\u98ef\u4efd\u91cf\u3002",
        }
    if dish_type == "stable_base_variable_dish":
        return {
            "assumed_composition": "stable-base dish",
            "exactness_posture": "estimated",
            "evidence_confidence": "moderate",
            "include_kcal": True,
            "include_evidence_used": True,
            "evidence_reason": "generic_anchor_stable_base_used_as_anchor_evidence",
            "uncertainty_reason": "generic_anchor_stable_base_requires_refinement",
            "suggested_followup_question": "\u8acb\u88dc\u5145\u9eb5\u91cf\u3001\u52a0\u6599\u6216\u4efd\u91cf\u3002",
        }
    return {
        "assumed_composition": None,
        "exactness_posture": "estimated",
        "evidence_confidence": "moderate",
        "include_kcal": True,
        "include_evidence_used": True,
        "evidence_reason": "generic_anchor_used_as_anchor_evidence",
        "uncertainty_reason": "generic_anchor_support",
        "suggested_followup_question": None,
    }


def _anchor_rule_from_semantic_metadata(packet: dict[str, object]) -> dict[str, Any] | None:
    clarify_required = packet.get("clarify_required") is True
    composition_posture = _optional_packet_text(packet.get("composition_posture"))
    variance_level = _optional_packet_text(packet.get("variance_level"))
    followup_hints = _packet_hint_tuple(packet.get("followup_hints"))
    followup_question = _question_from_followup_hints(followup_hints)
    assumed_composition = _assumed_composition_for_composition_posture(composition_posture)

    if clarify_required:
        return {
            "assumed_composition": assumed_composition,
            "exactness_posture": "unresolved",
            "evidence_confidence": "insufficient",
            "include_kcal": False,
            "include_evidence_used": False,
            "evidence_reason": "generic_anchor_requires_clarification",
            "uncertainty_reason": "generic_anchor_requires_clarification",
            "suggested_followup_question": followup_question,
        }

    if composition_posture == "composition_unknown_basket":
        return {
            "assumed_composition": assumed_composition,
            "exactness_posture": "unresolved",
            "evidence_confidence": "insufficient",
            "include_kcal": False,
            "include_evidence_used": False,
            "evidence_reason": "generic_anchor_requires_clarification",
            "uncertainty_reason": "generic_anchor_requires_clarification",
            "suggested_followup_question": followup_question,
        }

    if composition_posture in {"single_item", "listed_item_component"}:
        return {
            "assumed_composition": assumed_composition,
            "exactness_posture": "estimated",
            "evidence_confidence": "strong" if variance_level == "low" else "moderate",
            "include_kcal": True,
            "include_evidence_used": True,
            "evidence_reason": "generic_anchor_used_as_anchor_evidence",
            "uncertainty_reason": "generic_anchor_support",
            "suggested_followup_question": followup_question,
        }

    if composition_posture == "estimable_with_modifier_refinement":
        return {
            "assumed_composition": assumed_composition,
            "exactness_posture": "estimated",
            "evidence_confidence": "moderate",
            "include_kcal": True,
            "include_evidence_used": True,
            "evidence_reason": "generic_anchor_modifier_sensitive_used_as_anchor_evidence",
            "uncertainty_reason": "generic_anchor_modifier_requires_refinement",
            "suggested_followup_question": followup_question,
        }

    if composition_posture == "estimable_generic_meal":
        return {
            "assumed_composition": assumed_composition,
            "exactness_posture": "provisional",
            "evidence_confidence": "moderate",
            "include_kcal": True,
            "include_evidence_used": True,
            "evidence_reason": "generic_anchor_meal_used_as_anchor_evidence",
            "uncertainty_reason": "generic_anchor_meal_requires_soft_refinement",
            "suggested_followup_question": followup_question,
        }

    if composition_posture == "estimable_with_refinement":
        return {
            "assumed_composition": assumed_composition,
            "exactness_posture": "estimated",
            "evidence_confidence": "moderate",
            "include_kcal": True,
            "include_evidence_used": True,
            "evidence_reason": "generic_anchor_refinement_used_as_anchor_evidence",
            "uncertainty_reason": "generic_anchor_requires_refinement",
            "suggested_followup_question": followup_question,
        }

    return None


def _evidence_used(packet: dict[str, object], *, usage: str, reason: str) -> dict[str, object]:
    return {
        "packet_id": packet.get("packet_id"),
        "source_type": packet.get("source_type"),
        "source_quality_label": packet.get("source_quality_label"),
        "usage": usage,
        "reason": reason,
    }


def _question_from_followup_hints(followup_hints: tuple[str, ...]) -> str | None:
    hint_set = set(followup_hints)
    if {"ask_listed_items", "ask_portion"}.issubset(hint_set):
        return "\u8acb\u5217\u51fa\u54c1\u9805\u8207\u5927\u81f4\u4efd\u91cf\u3002"
    if {"ask_sugar_level", "ask_cup_size"}.issubset(hint_set):
        return "\u8acb\u88dc\u5145\u7cd6\u5ea6\u548c\u676f\u578b\u3002"
    if {"ask_main_style", "ask_rice_portion"}.issubset(hint_set):
        return "\u8acb\u88dc\u5145\u4e3b\u83dc\u505a\u6cd5\u6216\u767d\u98ef\u4efd\u91cf\u3002"
    if {"ask_noodle_portion", "ask_add_ons", "ask_portion"} & hint_set:
        return "\u8acb\u88dc\u5145\u9eb5\u91cf\u3001\u52a0\u6599\u6216\u4efd\u91cf\u3002"
    return None


def _optional_packet_text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _packet_hint_tuple(value: object) -> tuple[str, ...]:
    return tuple(str(item).strip() for item in value or [] if str(item).strip())


def _assumed_composition_for_composition_posture(composition_posture: str | None) -> str | None:
    if composition_posture == "single_item":
        return "single item"
    if composition_posture == "listed_item_component":
        return "listed item"
    if composition_posture == "estimable_with_modifier_refinement":
        return "customizable drink"
    if composition_posture == "estimable_generic_meal":
        return "generic meal"
    if composition_posture == "estimable_with_refinement":
        return "stable-base dish"
    if composition_posture == "composition_unknown_basket":
        return "composition unknown basket"
    return None


__all__ = ["synthesize_b2_local_manager_pass2"]
