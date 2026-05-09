from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Iterable

from app.nutrition.infrastructure.exact_item_card_loader import (
    load_exact_item_card_seed_records,
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
    limit: int = 1,
) -> dict[str, Any]:
    cards = list(exact_item_cards) if exact_item_cards is not None else load_exact_item_card_seed_records()
    packet_items = [_packet_ready_item(card) for card in cards if _card_has_complete_macro(card)]
    packet_items = packet_items[: max(0, int(limit))]
    ready = bool(packet_items)
    blockers = [] if ready else ["no_macro_complete_exact_item_card"]

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
            else "blocked_no_macro_complete_exact_item"
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
            "source_card_count": len(cards),
            "packet_ready_item_count": len(packet_items),
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


def _card_has_complete_macro(card: dict[str, Any]) -> bool:
    return (
        _whole_number(card.get("kcal") or card.get("label_kcal")) > 0
        and _whole_number(card.get("protein_g")) > 0
        and _whole_number(card.get("carb_g") or card.get("carbs_g")) > 0
        and _whole_number(card.get("fat_g")) > 0
    )


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
