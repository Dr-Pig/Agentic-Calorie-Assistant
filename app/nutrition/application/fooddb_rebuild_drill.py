from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.application.food_evidence_auto_eligible_batch import (
    build_food_evidence_auto_eligible_batch,
)
from app.nutrition.application.food_evidence_candidate_normalization import (
    build_food_evidence_candidate_artifact,
)
from app.nutrition.application.food_evidence_candidate_validation import (
    build_food_evidence_candidate_validation_artifact,
)
from app.nutrition.application.food_evidence_tfda_promotion import (
    apply_selected_anchor_metadata_to_small_anchor_store,
    build_tfda_batch_promotion_artifact,
    build_tfda_per100g_source_evidence_artifact,
    build_tfda_selected_anchor_artifact,
)
from app.nutrition.infrastructure.exact_item_card_loader import load_exact_item_card_seed_records
from app.nutrition.infrastructure.small_anchor_store_loader import load_small_anchor_seed_records


def build_fooddb_rebuild_drill(
    *,
    scan_roots: Iterable[Path | str],
    exact_item_cards: Iterable[dict[str, Any]] | None = None,
    small_anchor_records: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    cards = list(exact_item_cards) if exact_item_cards is not None else load_exact_item_card_seed_records()
    anchors = list(small_anchor_records) if small_anchor_records is not None else load_small_anchor_seed_records()
    candidate_artifact = build_food_evidence_candidate_artifact(scan_roots=scan_roots)
    validation_artifact = build_food_evidence_candidate_validation_artifact(
        candidate_artifact=candidate_artifact,
        gap_register=None,
    )
    auto_eligible = build_food_evidence_auto_eligible_batch(
        validation_artifact=validation_artifact,
        sample_size_per_group=3,
    )
    promotion = build_tfda_batch_promotion_artifact(
        candidate_artifact=candidate_artifact,
        auto_eligible_artifact=auto_eligible,
    )
    selected_anchors = build_tfda_selected_anchor_artifact(promotion)
    source_evidence = build_tfda_per100g_source_evidence_artifact(promotion)
    updated_anchor_payload = apply_selected_anchor_metadata_to_small_anchor_store(
        {"anchors": anchors},
        selected_anchors,
    )
    packet_ready = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/accurate_intake_approved_packet_ready_fooddb_rebuild_drill.json",
        exact_item_cards=cards,
        small_anchor_records=updated_anchor_payload["anchors"],
    )
    checks = _rebuild_checks(
        candidate_artifact=candidate_artifact,
        validation_artifact=validation_artifact,
        auto_eligible=auto_eligible,
        promotion=promotion,
        source_evidence=source_evidence,
        selected_anchors=selected_anchors,
        packet_ready=packet_ready,
    )
    blockers = [name for name, status in checks.items() if status != "pass"]

    return {
        "artifact_type": "accurate_intake_fooddb_rebuild_drill",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "claim_scope": "fooddb_rebuild_drill_only",
        "status": "pass" if not blockers else "blocked",
        "runtime_truth_changed": False,
        "tracked_files_updated": False,
        "live_provider_used": False,
        "fooddb_truth_promotion_written": False,
        "summary": {
            "candidate_count": candidate_artifact["candidate_summary"]["candidate_count"],
            "validator_passed_count": validation_artifact["summary"]["validator_passed_count"],
            "auto_eligible_count": auto_eligible["summary"]["auto_eligible_count"],
            "source_evidence_count": promotion["summary"]["source_evidence_count"],
            "selected_runtime_anchor_count": promotion["summary"]["selected_runtime_anchor_count"],
            "packet_ready_status": packet_ready["status"],
            "packet_ready_lane_counts": packet_ready["summary"]["packet_ready_lane_counts"],
        },
        "rebuild_checks": checks,
        "blockers": blockers,
        "non_claims": [
            "no_broad_fooddb_expansion",
            "no_runtime_file_write",
            "no_websearch_truth",
            "no_live_provider_call",
            "no_product_readiness",
        ],
    }


def _rebuild_checks(
    *,
    candidate_artifact: dict[str, Any],
    validation_artifact: dict[str, Any],
    auto_eligible: dict[str, Any],
    promotion: dict[str, Any],
    source_evidence: dict[str, Any],
    selected_anchors: dict[str, Any],
    packet_ready: dict[str, Any],
) -> dict[str, str]:
    return {
        "raw_to_candidate": _pass_if(candidate_artifact["candidate_summary"]["candidate_count"] > 0),
        "candidate_to_validation": _pass_if(validation_artifact["summary"]["validator_passed_count"] > 0),
        "validation_to_auto_eligible": _pass_if(auto_eligible["summary"]["auto_eligible_count"] > 0),
        "promotion_to_selected_anchor": _pass_if(
            promotion["summary"]["selected_runtime_anchor_count"] > 0
            and bool(selected_anchors.get("anchors"))
        ),
        "selected_anchor_to_packet_ready": _pass_if(
            packet_ready["status"] == "approved_packet_ready_fooddb_artifact_ready"
        ),
        "macro_contract_preserved": _pass_if(
            _macro_contract_ok(packet_ready)
            and source_evidence["macro_contract"]["missing_macro_policy"]
            == "preserve_null_do_not_invent"
        ),
        "source_refs_preserved": _pass_if(_source_refs_ok(selected_anchors)),
    }


def _macro_contract_ok(packet_ready: dict[str, Any]) -> bool:
    contract = (
        packet_ready.get("approved_packet_ready_evidence_artifact", {}).get("macro_contract") or {}
    )
    fields = set(contract.get("packet_fields") or [])
    return {"protein_g", "carbs_g", "fat_g", "macro_visibility_status"}.issubset(fields)


def _source_refs_ok(selected_anchors: dict[str, Any]) -> bool:
    return all(anchor.get("source_refs") for anchor in selected_anchors.get("anchors") or [])


def _pass_if(value: bool) -> str:
    return "pass" if value else "fail"


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_fooddb_rebuild_drill"]
