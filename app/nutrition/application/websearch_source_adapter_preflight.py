from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .websearch_cache_rate_license_wall import (
    MAX_SEARCH_RESULTS,
    build_websearch_cache_key,
    build_websearch_cache_rate_license_wall,
    build_websearch_search_request_policy,
)


def build_websearch_source_adapter_preflight(
    *,
    websearch_status_packet: dict[str, Any] | None = None,
    cache_rate_license_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    websearch_gate = _compact_websearch_status(websearch_status_packet)
    cache_gate = _compact_cache_rate_license_wall(
        cache_rate_license_artifact or build_websearch_cache_rate_license_wall()
    )
    adapter_cases = _adapter_cases()
    case_blockers = [
        f"source_adapter_case_failed:{case['case_id']}"
        for case in adapter_cases
        if case["status"] != "pass"
    ]
    blockers = []
    if websearch_gate["blocked"]:
        blockers.append(
            f"websearch_status_not_clear:{websearch_gate['next_required_slice']}"
        )
    if cache_gate["blocked"]:
        blockers.append(
            f"cache_rate_license_wall_not_clear:{cache_gate['next_required_slice']}"
        )
    blockers.extend(case_blockers)
    clear = not blockers
    return {
        "artifact_type": "accurate_intake_websearch_source_adapter_preflight_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_websearch_source_adapter_preflight_only",
        "claim_scope": "websearch_source_adapter_preflight_without_live_call",
        "status": "pass" if clear else "blocked",
        "blockers": sorted(set(blockers)),
        "live_websearch_used": False,
        "live_provider_used": False,
        "runtime_truth_changed": False,
        "websearch_runtime_truth_allowed": False,
        "runtime_mutation_allowed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "readiness_claimed": False,
        "ready_for_live_search_diagnostic": clear,
        "ready_for_runtime_truth": False,
        "upstream_gates": {
            "websearch_status": websearch_gate,
            "cache_rate_license_wall": cache_gate,
        },
        "source_adapter_contract": {
            "dependency": "WebSearchPort",
            "port_method": "search_hits",
            "request_policy_source": "websearch_candidate_request_policy_v1",
            "candidate_normalizer": "produce_web_search_candidates",
            "manager_packet_role": "compact_candidate_packet_only",
            "raw_provider_payload_manager_allowed": False,
            "candidate_output_runtime_truth_allowed": False,
            "adapter_backend_swappable": True,
            "backend_examples": ["tavily", "openai_web_search", "cached_fixture"],
        },
        "diagnostic_contract": {
            "live_call_allowed_by_this_artifact": False,
            "requires_explicit_live_permission": True,
            "cache_required": True,
            "max_search_attempts": 2,
            "max_search_results": MAX_SEARCH_RESULTS,
            "include_answer": False,
            "include_raw_content": False,
            "raw_content_allowed_in_manager_context": False,
            "ledger_mutation_allowed": False,
            "exact_card_creation_allowed": False,
        },
        "adapter_cases": adapter_cases,
        "summary": {
            "adapter_case_count": len(adapter_cases),
            "pass_count": sum(1 for case in adapter_cases if case["status"] == "pass"),
            "fail_count": sum(1 for case in adapter_cases if case["status"] != "pass"),
            "ready_for_runtime_truth_count": 0,
        },
        "next_required_slice": (
            "websearch_live_search_diagnostic_canary"
            if clear
            else "inspect_websearch_source_adapter_preflight_blockers"
        ),
        "non_claims": [
            "no_live_websearch_call",
            "no_live_provider_call",
            "no_websearch_runtime_truth",
            "no_exact_card_truth_promotion",
            "no_runtime_mutation",
            "no_readiness_claim",
        ],
    }


def _compact_websearch_status(websearch_status_packet: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(websearch_status_packet, dict):
        return {
            "status": "not_provided",
            "next_required_slice": "inspect_websearch_status_packet",
            "blocked": True,
        }
    if (
        str(websearch_status_packet.get("artifact_type") or "")
        != "accurate_intake_websearch_candidate_lane_status_packet_v1"
    ):
        raise ValueError("unsupported_websearch_source_adapter_status_packet")
    next_required_slices = list(websearch_status_packet.get("next_required_slices") or [])
    next_required_slice = str(next_required_slices[0] or "").strip() if next_required_slices else None
    upstream_gate = (
        websearch_status_packet.get("upstream_gate")
        if isinstance(websearch_status_packet.get("upstream_gate"), dict)
        else {}
    )
    live_gate = (
        websearch_status_packet.get("live_diagnostic_gate")
        if isinstance(websearch_status_packet.get("live_diagnostic_gate"), dict)
        else {}
    )
    unsafe_top_level = any(
        websearch_status_packet.get(key) is True
        for key in (
            "live_websearch_used",
            "runtime_truth_changed",
            "mutation_changed",
            "shared_contract_changed",
            "readiness_claimed",
        )
    )
    aligned = (
        str(upstream_gate.get("status") or "") == "clear_for_websearch_lane"
        and upstream_gate.get("blocked") is False
        and str(live_gate.get("status") or "") == "live_diagnostic_pass"
        and live_gate.get("blocked") is False
        and live_gate.get("can_expand") is True
        and next_required_slice == "websearch_live_search_preflight_or_candidate_source_adapter"
        and not unsafe_top_level
    )
    return {
        "status": "clear_for_source_adapter_preflight" if aligned else "blocked",
        "next_required_slice": (
            "inspect_websearch_status_packet"
            if unsafe_top_level
            else next_required_slice
            if next_required_slice and not aligned
            else "websearch_live_search_preflight_or_candidate_source_adapter"
            if aligned
            else "inspect_websearch_status_packet"
        ),
        "blocked": not aligned,
    }


def _compact_cache_rate_license_wall(artifact: dict[str, Any]) -> dict[str, Any]:
    if (
        str(artifact.get("artifact_type") or "")
        != "accurate_intake_websearch_cache_rate_license_wall_v1"
    ):
        raise ValueError("unsupported_websearch_source_adapter_cache_wall")
    unsafe = any(
        artifact.get(key) is True
        for key in (
            "live_websearch_used",
            "live_provider_used",
            "runtime_truth_changed",
            "websearch_runtime_truth_allowed",
            "runtime_mutation_allowed",
            "manager_context_changed",
            "packetizer_format_changed",
            "readiness_claimed",
        )
    )
    summary = artifact.get("summary") if isinstance(artifact.get("summary"), dict) else {}
    blocked = (
        artifact.get("status") != "pass"
        or bool(artifact.get("blockers"))
        or unsafe
        or int(summary.get("max_search_results") or 0) > MAX_SEARCH_RESULTS
    )
    return {
        "status": "clear" if not blocked else "blocked",
        "next_required_slice": (
            "inspect_websearch_cache_rate_license_wall"
            if blocked
            else "websearch_source_adapter_preflight"
        ),
        "blocked": blocked,
    }


def _adapter_cases() -> list[dict[str, Any]]:
    exact_request = build_websearch_search_request_policy(
        normalized_query="Milksha pearl black tea latte",
        exact_phrase="Milksha pearl black tea latte",
    )
    fallback_request = build_websearch_search_request_policy(
        normalized_query="Milksha pearl black tea latte official menu nutrition",
    )
    cases = [
        _case_payload(
            case_id="exact_brand_request_uses_port_policy",
            request=exact_request,
            source_class_order=("official_brand_or_chain_page", "brand_menu_page"),
        ),
        _case_payload(
            case_id="fallback_request_stays_bounded_candidate_only",
            request=fallback_request,
            source_class_order=("official_brand_or_chain_page", "brand_menu_page"),
        ),
    ]
    return cases


def _case_payload(
    *,
    case_id: str,
    request: dict[str, Any],
    source_class_order: tuple[str, ...],
) -> dict[str, Any]:
    checks = {
        "basic_depth": request["search_depth"] == "basic",
        "auto_parameters_disabled": request["auto_parameters"] is False,
        "include_answer_disabled": request["include_answer"] is False,
        "include_raw_content_disabled": request["include_raw_content"] is False,
        "bounded_results": request["max_results"] == MAX_SEARCH_RESULTS,
        "no_runtime_truth": request["runtime_truth_allowed"] is False,
    }
    cache_key = build_websearch_cache_key(
        normalized_query=str(request["query"]),
        source_class_order=source_class_order,
        search_depth=str(request["search_depth"]),
        max_results=int(request["max_results"]),
        exact_match=bool(request["exact_match"]),
        include_raw_content=bool(request["include_raw_content"]),
    )
    return {
        "case_id": case_id,
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "request": request,
        "cache_key": cache_key,
    }


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_websearch_source_adapter_preflight"]
