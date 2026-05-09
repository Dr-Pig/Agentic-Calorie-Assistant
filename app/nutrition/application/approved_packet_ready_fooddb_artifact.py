from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Iterable

from app.nutrition.infrastructure.exact_item_card_loader import (
    load_exact_item_card_seed_records,
)
from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)
from app.nutrition.application.fooddb_macro_contract import (
    APPROVED_PACKET_READY_SCHEMA_VERSION as SCHEMA_VERSION,
    APPROVED_PACKET_READY_SOURCE_QUALITY as SOURCE_QUALITY,
    MACRO_CONTRACT,
)


def build_approved_packet_ready_fooddb_artifact(
    *,
    artifact_path: str,
    exact_item_cards: Iterable[dict[str, Any]] | None = None,
    small_anchor_records: Iterable[dict[str, Any]] | None = None,
    limit: int = 3,
) -> dict[str, Any]:
    cards = list(exact_item_cards) if exact_item_cards is not None else load_exact_item_card_seed_records()
    anchors = (
        list(small_anchor_records)
        if small_anchor_records is not None
        else load_small_anchor_seed_records()
    )
    exact_items = [_packet_ready_item(card) for card in cards if _card_has_complete_macro(card)]
    generic_items = [
        _packet_ready_anchor_item(anchor, source_lane="generic_common_serving")
        for anchor in anchors
        if _anchor_is_generic_common_serving(anchor)
    ]
    component_items = [
        _packet_ready_anchor_item(anchor, source_lane="listed_component")
        for anchor in anchors
        if _anchor_is_listed_component(anchor)
    ]
    packet_items = [
        *exact_items[:1],
        *generic_items[:1],
        *component_items[:1],
    ]
    packet_items = packet_items[: max(0, int(limit))]
    lane_counts = _packet_ready_lane_counts(packet_items)
    blockers = _missing_lane_blockers(lane_counts)
    ready = not blockers

    return {
        "artifact_type": "accurate_intake_approved_packet_ready_fooddb_artifact",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "claim_scope": "minimal_fooddb_packet_ready_macro_handoff",
        "producer_track": "FoodDB",
        "intended_consumers": ["ManagerRuntime", "AppShell"],
        "fixture_or_real": "real",
        "source_quality": SOURCE_QUALITY,
        "ready_for_other_tracks": ready,
        "status": (
            "approved_packet_ready_fooddb_artifact_ready"
            if ready
            else "blocked_missing_packet_ready_lane"
        ),
        "approved_packet_ready_evidence_artifact": {
            "path": str(artifact_path),
            "schema_version": SCHEMA_VERSION,
            "fixture_or_real": "real",
            "source_quality": SOURCE_QUALITY,
            "ready_for_product_loop": ready,
            "macro_contract": MACRO_CONTRACT,
        },
        "summary": {
            "source_file": "app/knowledge/exact_item_cards_tw.json",
            "small_anchor_source_file": "app/knowledge/small_anchor_store_tw.json",
            "source_card_count": len(cards),
            "source_anchor_count": len(anchors),
            "packet_ready_item_count": len(packet_items),
            "packet_ready_lane_counts": lane_counts,
            "macro_complete_item_count": sum(1 for card in cards if _card_has_complete_macro(card)),
        },
        "packet_ready_items": packet_items,
        "blockers": blockers,
        "runtime_truth_changed": False,
        "runtime_mutation_attempted": False,
        "fooddb_truth_updated": False,
        "websearch_evidence_used": False,
        "live_llm_invoked": False,
        "real_fooddb_pass_claimed": False,
        "dogfood_pass": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "non_claims": [
            "no_broad_fooddb_expansion",
            "no_websearch_truth",
            "no_runtime_mutation",
            "no_dogfood_pass",
            "no_product_readiness",
            "no_private_self_use_approval",
        ],
    }


def _packet_ready_lane_counts(packet_items: list[dict[str, Any]]) -> dict[str, int]:
    lanes = {
        "exact_item_card": 0,
        "generic_common_serving": 0,
        "listed_component": 0,
    }
    for item in packet_items:
        lane = _text(item.get("source_lane"))
        if lane in lanes:
            lanes[lane] += 1
    return lanes


def _missing_lane_blockers(lane_counts: dict[str, int]) -> list[str]:
    blockers: list[str] = []
    if lane_counts["exact_item_card"] < 1:
        blockers.append("no_macro_complete_exact_item_card")
    if lane_counts["generic_common_serving"] < 1:
        blockers.append("no_packet_ready_generic_common_serving")
    if lane_counts["listed_component"] < 1:
        blockers.append("no_packet_ready_listed_component")
    return blockers


def _packet_ready_item(card: dict[str, Any]) -> dict[str, Any]:
    item_id = _text(card.get("item_id") or card.get("card_id") or card.get("id"))
    title = _text(card.get("title"))
    protein = _whole_number(card.get("protein_g"))
    carbs = _whole_number(card.get("carb_g") or card.get("carbs_g"))
    fat = _whole_number(card.get("fat_g"))
    kcal = _whole_number(card.get("kcal") or card.get("label_kcal"))
    source_file = "app/knowledge/exact_item_cards_tw.json"
    return {
        "source_lane": "exact_item_card",
        "item_id": item_id,
        "canonical_name": title,
        "aliases": [_text(alias) for alias in card.get("aliases", []) if _text(alias)],
        "brand": _text(card.get("brand")),
        "runtime_role": "exact_item_card",
        "runtime_truth_allowed": True,
        "runtime_usage_boundary": "exact_item_seed_label_macro_present",
        "serving_basis": _text(card.get("serving_basis") or card.get("serving_size")),
        "portion_basis": {
            "basis": _text(card.get("macro_basis")) or "per_package",
            "label": _text(card.get("serving_basis") or card.get("serving_size")),
        },
        "kcal_point": kcal,
        "kcal_range": [kcal, kcal],
        "protein_g": protein,
        "carbs_g": carbs,
        "fat_g": fat,
        "macro_visibility_status": "visible",
        "macro_source_basis": "exact_item_seed_label",
        "macro_confidence": _text(card.get("macro_confidence")) or "high",
        "source_provenance": {
            "source_id": "exact_item_cards_tw",
            "source_file": source_file,
            "record_id": item_id,
        },
        "approval_metadata": {
            "approval_mode": "tracked_exact_item_seed_packet_ready",
            "approval_scope": "minimal_current_shell_macro_present_exact_item",
            "policy_version": SCHEMA_VERSION,
            "runtime_truth_allowed": True,
        },
    }


def _packet_ready_anchor_item(
    anchor: dict[str, Any],
    *,
    source_lane: str,
) -> dict[str, Any]:
    anchor_id = _text(anchor.get("anchor_id"))
    source_provenance = anchor.get("source_provenance")
    approval_metadata = dict(anchor.get("approval_metadata") or {})
    approval_scope = (
        "minimal_current_shell_listed_component_macro_unknown"
        if source_lane == "listed_component"
        else "minimal_current_shell_generic_common_serving_macro_unknown"
    )
    return {
        "source_lane": source_lane,
        "item_id": anchor_id,
        "canonical_name": _text(anchor.get("canonical_name")),
        "aliases": [_text(alias) for alias in anchor.get("aliases", []) if _text(alias)],
        "runtime_role": _text(anchor.get("runtime_role")) or "common_serving_anchor",
        "runtime_truth_allowed": True,
        "runtime_usage_boundary": _text(anchor.get("runtime_usage_boundary")),
        "serving_basis": _text(anchor.get("serving_basis")) or "common_serving",
        "portion_basis": anchor.get("portion_basis") or {},
        "kcal_point": _whole_number(anchor.get("kcal_point") or anchor.get("baseline_likely_kcal")),
        "kcal_range": _kcal_range(anchor.get("kcal_range") or anchor.get("baseline_kcal_range")),
        "protein_g": None,
        "carbs_g": None,
        "fat_g": None,
        "macro_visibility_status": "hidden_missing_source",
        "macro_source_basis": "unknown",
        "macro_confidence": "unknown",
        "source_provenance": source_provenance if isinstance(source_provenance, dict) else {},
        "source_refs": anchor.get("source_refs") or [],
        "approval_metadata": {
            "approval_mode": _text(approval_metadata.get("approval_mode")),
            "approval_scope": approval_scope,
            "policy_version": SCHEMA_VERSION,
            "runtime_truth_allowed": True,
        },
    }


def _card_has_complete_macro(card: dict[str, Any]) -> bool:
    return (
        _whole_number(card.get("kcal") or card.get("label_kcal")) > 0
        and _whole_number(card.get("protein_g")) > 0
        and _whole_number(card.get("carb_g") or card.get("carbs_g")) > 0
        and _whole_number(card.get("fat_g")) > 0
    )


def _anchor_is_generic_common_serving(anchor: dict[str, Any]) -> bool:
    return (
        _anchor_is_packet_ready(anchor)
        and _text(anchor.get("runtime_role")) == "common_serving_anchor"
        and _text(anchor.get("composition_posture")) != "listed_item_component"
        and "listed_component" not in _text(anchor.get("runtime_usage_boundary"))
        and _text(anchor.get("runtime_usage_boundary")).startswith("generic_range")
    )


def _anchor_is_listed_component(anchor: dict[str, Any]) -> bool:
    return (
        _anchor_is_packet_ready(anchor)
        and (
            _text(anchor.get("composition_posture")) == "listed_item_component"
            or _text(anchor.get("runtime_usage_boundary")).startswith("listed_component")
        )
    )


def _anchor_is_packet_ready(anchor: dict[str, Any]) -> bool:
    approval = anchor.get("approval_metadata") or {}
    return (
        _text(anchor.get("record_kind") or "generic_anchor") == "generic_anchor"
        and bool(anchor.get("runtime_truth_allowed") is True)
        and bool(approval.get("runtime_truth_allowed") is True)
        and _whole_number(anchor.get("kcal_point") or anchor.get("baseline_likely_kcal")) > 0
        and bool(_kcal_range(anchor.get("kcal_range") or anchor.get("baseline_kcal_range")))
    )


def _kcal_range(value: Any) -> list[int]:
    if not isinstance(value, list | tuple) or not value:
        return []
    low = _whole_number(value[0])
    high = _whole_number(value[1] if len(value) > 1 else value[0])
    if low <= 0 or high <= 0:
        return []
    return [min(low, high), max(low, high)]


def _whole_number(value: Any) -> int:
    try:
        return max(0, int(round(float(value))))
    except (TypeError, ValueError):
        return 0


def _text(value: Any) -> str:
    return str(value or "").strip()


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_approved_packet_ready_fooddb_artifact"]
