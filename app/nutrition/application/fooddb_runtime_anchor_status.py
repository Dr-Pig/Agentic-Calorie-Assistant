from __future__ import annotations

from typing import Any


def runtime_visible_anchor_ids(small_anchor_payload: dict[str, Any]) -> list[str]:
    return [
        item["anchor_id"]
        for item in small_anchor_payload.get("anchors") or []
        if item.get("record_kind") == "generic_anchor"
        and item.get("runtime_role") == "common_serving_anchor"
        and item.get("runtime_truth_allowed") is True
    ]


def build_status_packet(
    *,
    small_anchor_payload: dict[str, Any],
    coverage_matrix: dict[str, Any],
    runtime_batch: dict[str, Any],
    generated_at_utc: str,
) -> dict[str, Any]:
    runtime_anchor_ids = runtime_visible_anchor_ids(small_anchor_payload)
    return {
        "artifact_type": "accurate_intake_fooddb_status_packet",
        "artifact_schema_version": "1.0",
        "generated_at_utc": generated_at_utc,
        "track": "FDB",
        "claim_scope": "fooddb_status_for_future_downstream_consumption",
        "pl_ce_files_changed": False,
        "product_loop_integration_claimed": False,
        "web_readiness_claimed": False,
        "private_self_use_approved": False,
        "live_provider_used": False,
        "real_fooddb_evidence_available": bool(runtime_anchor_ids),
        "runtime_visible_anchor_count": len(runtime_anchor_ids),
        "runtime_visible_anchor_ids": runtime_anchor_ids,
        "coverage_summary": coverage_matrix.get("summary", {}),
        "runtime_batch_summary": runtime_batch.get("summary", {}),
        "non_claims": [
            "no_product_loop_integration",
            "no_web_readiness",
            "no_private_self_use_approval",
            "no_live_provider_call",
            "no_kimi_or_grokfast",
        ],
    }


__all__ = ["build_status_packet", "runtime_visible_anchor_ids"]
