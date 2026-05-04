from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


REQUIRED_RUNTIME_ANCHOR_FIELDS = (
    "runtime_role",
    "runtime_estimate_allowed",
    "runtime_truth_allowed",
    "serving_basis",
    "portion_basis",
    "kcal_point",
    "kcal_range",
    "source_provenance",
    "approval_metadata",
)

NON_CLAIMS = [
    "no_product_loop_integration",
    "no_manager_context_change",
    "no_packetizer_format_change",
    "no_live_provider_call",
    "no_readiness_claim",
]


def build_fooddb_guarded_afk_truth_audit(
    *,
    small_anchor_payload: dict[str, Any],
    tfda_source_payload: dict[str, Any],
    exact_card_payload: dict[str, Any],
) -> dict[str, Any]:
    runtime_anchors = _runtime_common_serving_anchors(small_anchor_payload)
    runtime_anchor_audit = _audit_runtime_anchors(runtime_anchors)
    source_evidence_audit = _audit_tfda_source_evidence(tfda_source_payload)
    blockers = _blockers(
        runtime_anchor_audit=runtime_anchor_audit,
        source_evidence_audit=source_evidence_audit,
    )
    semantic_only_baskets = _semantic_only_baskets(small_anchor_payload)
    exact_cards = [card for card in exact_card_payload.get("cards") or [] if isinstance(card, dict)]

    return {
        "artifact_type": "accurate_intake_fooddb_guarded_afk_truth_audit",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "claim_scope": "fooddb_guarded_afk_truth_audit_no_runtime_change",
        "runtime_truth_changed": False,
        "product_loop_integration_claimed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "live_provider_used": False,
        "stop_gate_status": "blocked" if blockers else "pass",
        "blockers": blockers,
        "summary": {
            "runtime_common_serving_anchor_count": len(runtime_anchor_audit),
            "tfda_source_evidence_only_count": source_evidence_audit["tfda_source_evidence_only_count"],
            "semantic_only_basket_count": len(semantic_only_baskets),
            "exact_card_count": len(exact_cards),
            "blocker_count": len(blockers),
        },
        "runtime_anchor_audit": runtime_anchor_audit,
        "source_evidence_audit": source_evidence_audit,
        "exact_card_audit": {
            "exact_card_count": len(exact_cards),
            "promotion_scope": "existing_exact_card_store_report_only",
            "new_exact_card_promoted": False,
        },
        "semantic_only_basket_audit": {
            "basket_count": len(semantic_only_baskets),
            "bare_basket_runtime_estimate_allowed": False,
            "usage_boundary": "bare_basket_ask_followup_listed_components_only",
            "basket_ids": [item.get("anchor_id") for item in semantic_only_baskets],
        },
        "manager_evidence_catalog": _manager_evidence_catalog(runtime_anchors, runtime_anchor_audit),
        "non_claims": NON_CLAIMS,
    }


def _audit_runtime_anchors(runtime_anchors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    audited = []
    for anchor in runtime_anchors:
        missing = [
            field
            for field in REQUIRED_RUNTIME_ANCHOR_FIELDS
            if anchor.get(field) in (None, "", [])
        ]
        invalid = []
        if anchor.get("runtime_role") != "common_serving_anchor":
            invalid.append("runtime_role_not_common_serving_anchor")
        if anchor.get("runtime_truth_allowed") is not True:
            invalid.append("runtime_truth_not_allowed")
        if anchor.get("runtime_estimate_allowed") is not True:
            invalid.append("runtime_estimate_not_allowed")
        if anchor.get("serving_basis") == "per_100g":
            invalid.append("per_100g_runtime_anchor")
        for source_ref in anchor.get("source_refs") or []:
            if not isinstance(source_ref, dict):
                continue
            source_id = str(source_ref.get("source_id") or "")
            source_evidence_id = str(source_ref.get("source_evidence_id") or "")
            is_tfda_per100g_ref = (
                source_id == "taiwan_tfda_open_data"
                or source_id.startswith("tfda_")
                or source_evidence_id.startswith("tfda_")
            )
            if is_tfda_per100g_ref and (
                source_ref.get("runtime_role") != "source_evidence_only"
                or source_ref.get("serving_basis") != "per_100g"
                or source_ref.get("external_source_role") == "common_serving_anchor"
            ):
                invalid.append("tfda_source_ref_role_leakage")
        audited.append(
            {
                "anchor_id": anchor.get("anchor_id"),
                "canonical_name": anchor.get("canonical_name"),
                "status": "blocked" if missing or invalid else "pass",
                "missing_required_fields": missing,
                "invalid_runtime_fields": invalid,
                "runtime_role": anchor.get("runtime_role"),
                "serving_basis": anchor.get("serving_basis"),
                "runtime_truth_allowed": anchor.get("runtime_truth_allowed"),
                "kcal_point": anchor.get("kcal_point"),
                "kcal_range": anchor.get("kcal_range"),
                "approval_mode": (anchor.get("approval_metadata") or {}).get("approval_mode"),
                "source_id": (anchor.get("source_provenance") or {}).get("source_id"),
            }
        )
    return audited


def _audit_tfda_source_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    records = [record for record in payload.get("records") or [] if isinstance(record, dict)]
    violations = []
    for index, record in enumerate(records):
        reasons = []
        if record.get("runtime_role") != "source_evidence_only":
            reasons.append("runtime_role_not_source_evidence_only")
        if record.get("runtime_estimate_allowed") is not False:
            reasons.append("runtime_estimate_allowed_not_false")
        if record.get("packetizer_common_serving_allowed") is not False:
            reasons.append("packetizer_common_serving_allowed_not_false")
        if reasons:
            violations.append(
                {
                    "row_index": index,
                    "source_evidence_id": record.get("source_evidence_id"),
                    "canonical_name": record.get("canonical_name"),
                    "reasons": reasons,
                }
            )
    return {
        "source_artifact_type": payload.get("artifact_type"),
        "runtime_role": payload.get("runtime_role"),
        "runtime_estimate_allowed": payload.get("runtime_estimate_allowed"),
        "packetizer_common_serving_allowed": payload.get("packetizer_common_serving_allowed"),
        "tfda_source_evidence_only_count": len(records),
        "tfda_per100g_violation_count": len(violations),
        "violations": violations[:20],
    }


def _manager_evidence_catalog(
    runtime_anchors: list[dict[str, Any]],
    runtime_anchor_audit: list[dict[str, Any]],
) -> dict[str, Any]:
    passed_ids = {
        item["anchor_id"]
        for item in runtime_anchor_audit
        if item["status"] == "pass"
    }
    compact = []
    for anchor in runtime_anchors:
        if anchor.get("anchor_id") not in passed_ids:
            continue
        compact.append(
            {
                "anchor_id": anchor.get("anchor_id"),
                "canonical_name": anchor.get("canonical_name"),
                "aliases": list(anchor.get("aliases") or []),
                "dish_type": anchor.get("dish_type"),
                "kcal_point": anchor.get("kcal_point"),
                "kcal_range": anchor.get("kcal_range"),
                "serving_basis": anchor.get("serving_basis"),
                "portion_basis": anchor.get("portion_basis"),
                "variance_level": anchor.get("variance_level"),
                "followup_hints": list(anchor.get("followup_hints") or []),
                "runtime_usage_boundary": anchor.get("runtime_usage_boundary"),
            }
        )
    return {
        "claim_scope": "compact_runtime_evidence_catalog_not_raw_source",
        "raw_source_rows_included": False,
        "candidate_only_records_included": False,
        "runtime_common_serving_anchors": compact,
    }


def _blockers(
    *,
    runtime_anchor_audit: list[dict[str, Any]],
    source_evidence_audit: dict[str, Any],
) -> list[str]:
    blockers = []
    if any(item["status"] == "blocked" for item in runtime_anchor_audit):
        blockers.append("runtime_anchor_missing_required_metadata")
    if source_evidence_audit["tfda_per100g_violation_count"]:
        blockers.append("tfda_per100g_runtime_estimate_leakage")
    if any(
        "tfda_source_ref_role_leakage" in item["invalid_runtime_fields"]
        for item in runtime_anchor_audit
    ):
        blockers.append("runtime_anchor_source_ref_role_leakage")
    return blockers


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


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "build_fooddb_guarded_afk_truth_audit",
]
