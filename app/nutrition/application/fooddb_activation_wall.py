from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .fooddb_activation_wall_checks import (
    coverage_checks,
    modifier_checks,
    next_required_slice,
    p0_supported_modifier_count,
    packet_checks,
    upstream_next_required_slices,
)
from .fooddb_evidence_status_packet import build_fooddb_evidence_status_packet
from .fooddb_manager_packet_smoke import build_fooddb_manager_packet_smoke
from .fooddb_modifier_catalog import build_fooddb_modifier_catalog
from .fooddb_retrieval_policy import IndexedFoodRecord


def build_fooddb_activation_wall(
    *,
    small_anchor_payload: dict[str, Any],
    tfda_source_payload: dict[str, Any],
    exact_card_payload: dict[str, Any],
    retrieval_records: tuple[IndexedFoodRecord, ...],
) -> dict[str, Any]:
    status_packet = build_fooddb_evidence_status_packet(
        small_anchor_payload=small_anchor_payload,
        tfda_source_payload=tfda_source_payload,
        exact_card_payload=exact_card_payload,
    )
    modifier_catalog = build_fooddb_modifier_catalog(small_anchor_payload=small_anchor_payload)
    packet_smoke = build_fooddb_manager_packet_smoke(retrieval_records=retrieval_records)
    checks = [
        *coverage_checks(status_packet),
        *modifier_checks(modifier_catalog),
        *packet_checks(packet_smoke),
    ]
    blockers = [
        check["check_id"]
        for check in checks
        if check["status"] != "pass"
    ]
    upstream_next_required = upstream_next_required_slices(status_packet)
    status = "pass" if not blockers else "blocked"
    return {
        "artifact_type": "accurate_intake_fooddb_activation_wall_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_fooddb_activation_wall_only",
        "claim_scope": "fooddb_activation_minimum_packet_wall",
        "status": status,
        "blockers": blockers,
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "summary": {
            "runtime_common_serving_anchor_count": status_packet["summary"][
                "runtime_common_serving_anchor_count"
            ],
            "listed_component_anchor_count": status_packet["summary"][
                "listed_component_anchor_count"
            ],
            "p0_modifier_count": modifier_catalog["summary"]["p0_modifier_count"],
            "p0_supported_modifier_count": p0_supported_modifier_count(modifier_catalog),
            "packet_case_count": packet_smoke["summary"]["case_count"],
            "manager_packet_check_pass_count": sum(
                1 for check in checks if check["check_group"] == "manager_packet" and check["status"] == "pass"
            ),
            "upstream_next_required_slice_count": len(upstream_next_required),
        },
        "upstream_next_required_slices": upstream_next_required,
        "checks": checks,
        "next_required_slice": next_required_slice(
            status=status,
            upstream_next_required=upstream_next_required,
        ),
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_runtime_mutation",
            "no_manager_context_change",
            "no_packetizer_format_change",
            "no_live_provider_call",
            "no_live_websearch_call",
            "no_readiness_claim",
        ],
    }


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_fooddb_activation_wall"]
