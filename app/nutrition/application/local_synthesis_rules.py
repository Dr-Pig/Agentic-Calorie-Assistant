from __future__ import annotations

from typing import Any


def anchor_rule_for_dish_type(dish_type: str) -> dict[str, Any]:
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


def anchor_rule_from_packet(packet: dict[str, object]) -> dict[str, Any] | None:
    clarify_required = packet.get("clarify_required") is True
    composition_posture = _optional_packet_text(packet.get("composition_posture"))
    variance_level = _optional_packet_text(packet.get("variance_level"))
    followup_hints = _packet_hint_tuple(packet.get("followup_hints"))
    followup_question = question_from_followup_hints(followup_hints)
    assumed_composition = _assumed_composition_for_composition_posture(composition_posture)

    if clarify_required or composition_posture == "composition_unknown_basket":
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


def question_from_followup_hints(followup_hints: tuple[str, ...]) -> str | None:
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


__all__ = [
    "anchor_rule_for_dish_type",
    "anchor_rule_from_packet",
    "question_from_followup_hints",
]
