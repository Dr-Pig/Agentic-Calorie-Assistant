from __future__ import annotations

from typing import Any

from app.nutrition.application.fooddb_modifier_priority import (
    build_modifier_activation_posture,
    build_modifier_limitation_labels,
)


def build_fooddb_activation_gap_report(
    *,
    small_anchor_payload: dict[str, Any],
    tfda_source_payload: dict[str, Any],
    exact_card_payload: dict[str, Any],
) -> dict[str, Any]:
    runtime_anchors = _runtime_common_serving_anchors(small_anchor_payload)
    semantic_only_baskets = _semantic_only_baskets(small_anchor_payload)
    exact_candidate_cases = _exact_candidate_cases(exact_card_payload)
    activation_gap_report = {
        "known_unsupported_food_families": [item["canonical_name"] for item in semantic_only_baskets],
        "known_ask_followup_cases": [
            "bare_basket_followup",
            "listed_basket_component_followup",
            "portion_refinement",
        ],
        "known_candidate_only_exact_cases": [item["item_id"] for item in exact_candidate_cases],
        "known_modifier_limitations": build_modifier_limitation_labels(),
        "modifier_activation_posture": build_modifier_activation_posture(),
        "known_basket_limitations": [
            "bare_basket:ask_followup_no_estimate",
            "listed_basket:estimate_component_anchors_only",
        ],
    }
    return {
        "artifact_type": "accurate_intake_fooddb_activation_gap_report",
        "artifact_schema_version": "1.0",
        # This audit is deterministic over tracked repo truth; avoid wall-clock variance.
        "generated_at_utc": None,
        "track": "FDB",
        "claim_scope": "fooddb_activation_gap_report_only",
        "runtime_truth_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "live_provider_used": False,
        "activation_can_proceed_with_known_bounded_gaps": True,
        "activation_gap_note": "Activation can proceed with known bounded gaps.",
        "summary": {
            "runtime_visible_common_serving_anchor_count": len(runtime_anchors),
            "source_evidence_only_count": _source_evidence_only_count(tfda_source_payload),
            "semantic_only_basket_family_count": len(semantic_only_baskets),
            "listed_component_anchor_count": _listed_component_anchor_count(runtime_anchors),
            "exact_candidate_only_posture": "candidate_only",
        },
        "activation_gap_report": activation_gap_report,
        "non_claims": [
            "no_product_loop_integration",
            "no_manager_context_change",
            "no_packetizer_format_change",
            "no_live_provider_call",
            "no_readiness_claim",
        ],
    }


def _runtime_common_serving_anchors(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        anchor
        for anchor in payload.get("anchors") or []
        if isinstance(anchor, dict)
        and anchor.get("record_kind") == "generic_anchor"
        and anchor.get("runtime_role") == "common_serving_anchor"
        and anchor.get("runtime_truth_allowed") is True
    ]


def _semantic_only_baskets(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        anchor
        for anchor in payload.get("anchors") or []
        if isinstance(anchor, dict) and anchor.get("record_kind") == "generic_semantic_only"
    ]


def _exact_candidate_cases(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "item_id": str(card.get("item_id") or ""),
            "title": str(card.get("title") or ""),
        }
        for card in payload.get("cards") or []
        if isinstance(card, dict) and str(card.get("item_id") or "").strip()
    ]


def _source_evidence_only_count(payload: dict[str, Any]) -> int:
    return sum(1 for record in payload.get("records") or [] if isinstance(record, dict))


def _listed_component_anchor_count(runtime_anchors: list[dict[str, Any]]) -> int:
    return sum(1 for anchor in runtime_anchors if str(anchor.get("dish_type") or "") == "listed_item")


__all__ = ["build_fooddb_activation_gap_report"]
