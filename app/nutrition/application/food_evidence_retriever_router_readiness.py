from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .food_evidence_retriever_router import (
    RetrieverBackendAvailability,
    build_food_evidence_retriever_route_plan,
    build_food_evidence_retriever_route_plan_for_request,
)
from .retrieval_intent import RetrievalIntent
from .retrieval_request import build_retrieval_request_from_raw_text_hint

_EXPECTED_WEBSEARCH_STATUS = "accurate_intake_websearch_evidence_status_packet_v1"
_WEBSEARCH_LANE_READY_SLICE = "inspect_websearch_status_packet"


def apply_websearch_status_gate_to_availability(
    base_availability: RetrieverBackendAvailability,
    *,
    websearch_status_packet: dict[str, Any] | None = None,
) -> RetrieverBackendAvailability:
    if not base_availability.websearch_candidate_lane:
        return base_availability
    if not _websearch_candidate_lane_ready(websearch_status_packet):
        return RetrieverBackendAvailability(
            local_fooddb_index=base_availability.local_fooddb_index,
            sqlite_fts_index=base_availability.sqlite_fts_index,
            websearch_candidate_lane=False,
            supabase_index=base_availability.supabase_index,
        )
    return base_availability


def build_food_evidence_retriever_router_readiness(
    *,
    base_availability: RetrieverBackendAvailability,
    websearch_status_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gated = apply_websearch_status_gate_to_availability(
        base_availability,
        websearch_status_packet=websearch_status_packet,
    )
    cases = [
        _generic_case(gated),
        _exact_brand_ready_case(gated),
        _exact_brand_blocked_case(base_availability, websearch_status_packet),
        _raw_hint_case(gated),
    ]
    fail_count = sum(1 for case in cases if case["status"] != "pass")
    return {
        "artifact_type": "accurate_intake_food_evidence_retriever_router_readiness_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_retriever_router_readiness_only",
        "claim_scope": "router_alignment_to_fooddb_and_websearch_status",
        "status": "pass" if fail_count == 0 else "blocked",
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "shared_contract_changed": False,
        "manager_context_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "cases": cases,
        "summary": {
            "case_count": len(cases),
            "fail_count": fail_count,
            "exact_brand_websearch_ready": gated.websearch_candidate_lane is True,
            "websearch_status_gate_present": isinstance(websearch_status_packet, dict),
            "next_required_slice": _WEBSEARCH_LANE_READY_SLICE,
        },
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_runtime_mutation",
            "no_shared_contract_change",
            "no_manager_context_change",
            "no_readiness_claim",
        ],
    }


def _generic_case(availability: RetrieverBackendAvailability) -> dict[str, Any]:
    plan = build_food_evidence_retriever_route_plan(
        RetrievalIntent(
            base_dish="tea egg",
            aliases=["tea egg"],
            brand_hint=None,
            size_hint=None,
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="generic_anchor_lookup",
        ),
        availability=availability,
    )
    return {
        "case_id": "generic_fooddb_only",
        "status": "pass" if plan.websearch_candidate_enabled is False else "blocked",
        "primary_backend": plan.primary_backend,
        "backend_sequence": list(plan.backend_sequence),
        "websearch_candidate_enabled": plan.websearch_candidate_enabled,
    }


def _exact_brand_ready_case(availability: RetrieverBackendAvailability) -> dict[str, Any]:
    plan = build_food_evidence_retriever_route_plan(_exact_brand_intent(), availability=availability)
    enabled = plan.websearch_candidate_enabled is True
    return {
        "case_id": "exact_brand_websearch_ready_when_status_clear",
        "status": "pass" if enabled == availability.websearch_candidate_lane else "blocked",
        "primary_backend": plan.primary_backend,
        "backend_sequence": list(plan.backend_sequence),
        "websearch_candidate_enabled": plan.websearch_candidate_enabled,
    }


def _exact_brand_blocked_case(
    base_availability: RetrieverBackendAvailability,
    websearch_status_packet: dict[str, Any] | None,
) -> dict[str, Any]:
    blocked_availability = apply_websearch_status_gate_to_availability(
        base_availability,
        websearch_status_packet=_force_blocked_status(websearch_status_packet),
    )
    plan = build_food_evidence_retriever_route_plan(
        _exact_brand_intent(),
        availability=blocked_availability,
    )
    return {
        "case_id": "exact_brand_websearch_stays_blocked_without_clear_status",
        "status": "pass" if plan.websearch_candidate_enabled is False else "blocked",
        "primary_backend": plan.primary_backend,
        "backend_sequence": list(plan.backend_sequence),
        "websearch_candidate_enabled": plan.websearch_candidate_enabled,
    }


def _raw_hint_case(availability: RetrieverBackendAvailability) -> dict[str, Any]:
    plan = build_food_evidence_retriever_route_plan_for_request(
        build_retrieval_request_from_raw_text_hint("Milksha pearl black tea latte"),
        availability=availability,
    )
    return {
        "case_id": "raw_text_hint_stays_blocked",
        "status": "pass" if plan.primary_backend == "blocked_no_execution" else "blocked",
        "primary_backend": plan.primary_backend,
        "backend_sequence": list(plan.backend_sequence),
        "websearch_candidate_enabled": plan.websearch_candidate_enabled,
    }


def _websearch_candidate_lane_ready(websearch_status_packet: dict[str, Any] | None) -> bool:
    if not isinstance(websearch_status_packet, dict):
        return False
    if str(websearch_status_packet.get("artifact_type") or "") != _EXPECTED_WEBSEARCH_STATUS:
        raise ValueError("unsupported_retriever_router_readiness_websearch_status_packet")
    if websearch_status_packet.get("status") != "pass":
        return False
    if websearch_status_packet.get("runtime_truth_changed") is not False:
        return False
    if websearch_status_packet.get("mutation_changed") is not False:
        return False
    if websearch_status_packet.get("shared_contract_changed") is not False:
        return False
    if websearch_status_packet.get("manager_context_changed") is not False:
        return False
    if websearch_status_packet.get("live_provider_used") is not False:
        return False
    if websearch_status_packet.get("live_websearch_used") is not False:
        return False
    if websearch_status_packet.get("readiness_claimed") is not False:
        return False
    summary = dict(websearch_status_packet.get("summary") or {})
    return summary.get("candidate_lane_next_required_slice") == _WEBSEARCH_LANE_READY_SLICE


def _force_blocked_status(websearch_status_packet: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(websearch_status_packet, dict):
        return {
            "artifact_type": _EXPECTED_WEBSEARCH_STATUS,
            "status": "blocked_on_candidate_lane",
            "summary": {"candidate_lane_next_required_slice": "grokfast_fooddb_packet_live_diagnostic"},
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "shared_contract_changed": False,
            "manager_context_changed": False,
            "live_provider_used": False,
            "live_websearch_used": False,
            "readiness_claimed": False,
        }
    blocked = dict(websearch_status_packet)
    blocked["status"] = "blocked_on_candidate_lane"
    blocked["summary"] = {
        **dict(websearch_status_packet.get("summary") or {}),
        "candidate_lane_next_required_slice": "grokfast_fooddb_packet_live_diagnostic",
    }
    return blocked


def _exact_brand_intent() -> RetrievalIntent:
    return RetrievalIntent(
        base_dish="pearl black tea latte",
        aliases=["Milksha pearl black tea latte"],
        brand_hint="Milksha",
        size_hint="large",
        modifier_hints=[],
        listed_items=[],
        retrieval_goal="exact_brand_lookup",
    )


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "apply_websearch_status_gate_to_availability",
    "build_food_evidence_retriever_router_readiness",
]
