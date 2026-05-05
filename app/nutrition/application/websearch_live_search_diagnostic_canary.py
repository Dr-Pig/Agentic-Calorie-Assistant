from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .exact_brand_web_canary import run_exact_brand_web_canary
from .retrieval_semantic_decision import B2ManagerSemanticDecision
from .web_extract_port import WebExtractPort
from .web_search_port import WebSearchPort


async def build_websearch_live_search_diagnostic_canary(
    *,
    preflight_artifact: dict[str, Any] | None,
    live_permission_granted: bool,
    search_port: WebSearchPort | None,
    extract_port: WebExtractPort | None,
) -> dict[str, Any]:
    preflight_gate = _compact_preflight(preflight_artifact)
    port_gate = _compact_port_presence(search_port=search_port, extract_port=extract_port)
    blockers = []
    if preflight_gate["blocked"]:
        blockers.append(f"preflight_not_clear:{preflight_gate['next_required_slice']}")
    if not live_permission_granted:
        blockers.append("live_search_permission_required")
    if port_gate["blocked"]:
        blockers.extend(port_gate["blockers"])
    cases: list[dict[str, Any]] = []
    search_port_call_count = 0
    extract_port_call_count = 0
    search_port_profile = {"provider": None, "configured": False}
    extract_port_profile = {"provider": None, "configured": False}
    if not blockers:
        metered_search_port = _MeteredSearchPort(search_port)
        metered_extract_port = _MeteredExtractPort(extract_port)
        outcome = await run_exact_brand_web_canary(
            raw_user_input="I drank a Test Brand Matcha Latte",
            manager_decision=_manager_decision_fixture(),
            search_port=metered_search_port,
            extract_port=metered_extract_port,
            allow_search=True,
            exact_db_hit_present=False,
        )
        cases.append(_case_result(outcome.trace))
        search_port_call_count = metered_search_port.call_count
        extract_port_call_count = metered_extract_port.call_count
        search_port_profile = metered_search_port.readiness()
        extract_port_profile = metered_extract_port.readiness()
        if cases[-1]["status"] != "pass":
            blockers.append(f"canary_case_failed:{cases[-1]['case_id']}")
    clear = not blockers
    return {
        "artifact_type": "accurate_intake_websearch_live_search_diagnostic_canary_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "diagnostic_canary_harness_only",
        "claim_scope": "websearch_live_search_diagnostic_canary_without_runtime_truth",
        "status": "pass" if clear else "blocked",
        "blockers": sorted(set(blockers)),
        "live_permission_granted": live_permission_granted,
        "search_port_used": search_port_call_count > 0,
        "extract_port_used": extract_port_call_count > 0,
        "live_provider_used": False,
        "live_websearch_used": _external_search_port_used(
            search_port=search_port,
            search_port_call_count=search_port_call_count,
        ),
        "runtime_truth_changed": False,
        "websearch_runtime_truth_allowed": False,
        "runtime_mutation_allowed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "readiness_claimed": False,
        "ready_for_runtime_truth": False,
        "ready_for_runtime_mutation": False,
        "preflight_gate": preflight_gate,
        "port_gate": {
            **port_gate,
            "search_port_profile": search_port_profile,
            "extract_port_profile": extract_port_profile,
        },
        "cases": cases,
        "summary": {
            "case_count": len(cases),
            "pass_count": sum(1 for case in cases if case["status"] == "pass"),
            "fail_count": sum(1 for case in cases if case["status"] != "pass"),
            "search_port_call_count": search_port_call_count,
            "extract_port_call_count": extract_port_call_count,
            "runtime_truth_allowed_count": 0,
        },
        "next_required_slice": (
            "websearch_live_search_diagnostic_report"
            if clear
            else "inspect_websearch_live_search_diagnostic_canary_blockers"
        ),
        "non_claims": [
            "no_live_provider_call",
            "no_websearch_runtime_truth",
            "no_exact_card_truth_promotion",
            "no_runtime_mutation",
            "no_readiness_claim",
        ],
    }


def _compact_preflight(preflight_artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(preflight_artifact, dict):
        return {
            "status": "not_provided",
            "next_required_slice": "inspect_websearch_source_adapter_preflight",
            "blocked": True,
        }
    if (
        str(preflight_artifact.get("artifact_type") or "")
        != "accurate_intake_websearch_source_adapter_preflight_v1"
    ):
        raise ValueError("unsupported_websearch_live_search_canary_preflight")
    unsafe = any(
        preflight_artifact.get(key) is True
        for key in (
            "live_websearch_used",
            "runtime_truth_changed",
            "websearch_runtime_truth_allowed",
            "runtime_mutation_allowed",
            "manager_context_changed",
            "packetizer_format_changed",
            "readiness_claimed",
        )
    )
    clear = (
        preflight_artifact.get("status") == "pass"
        and preflight_artifact.get("ready_for_live_search_diagnostic") is True
        and preflight_artifact.get("ready_for_runtime_truth") is False
        and not preflight_artifact.get("blockers")
        and not unsafe
    )
    return {
        "status": "clear" if clear else "blocked",
        "next_required_slice": (
            "websearch_live_search_diagnostic_canary"
            if clear
            else "inspect_websearch_source_adapter_preflight"
        ),
        "blocked": not clear,
    }


def _compact_port_presence(
    *,
    search_port: WebSearchPort | None,
    extract_port: WebExtractPort | None,
) -> dict[str, Any]:
    blockers = []
    if search_port is None:
        blockers.append("search_port_unavailable")
    if extract_port is None:
        blockers.append("extract_port_unavailable")
    return {
        "status": "clear" if not blockers else "blocked",
        "blockers": sorted(blockers),
        "blocked": bool(blockers),
    }


def _safe_readiness(port: object | None) -> dict[str, Any]:
    if port is None:
        return {"provider": None, "configured": False}
    readiness = getattr(port, "readiness", None)
    profile = readiness() if callable(readiness) else {}
    return {
        "port_type": type(port).__name__,
        **(profile if isinstance(profile, dict) else {}),
    }


class _MeteredSearchPort:
    def __init__(self, inner: WebSearchPort) -> None:
        self._inner = inner
        self.call_count = 0

    def readiness(self) -> dict[str, Any]:
        return _safe_readiness(self._inner)

    async def search_hits(self, *, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        self.call_count += 1
        return await self._inner.search_hits(query=query, max_results=max_results)


class _MeteredExtractPort:
    def __init__(self, inner: WebExtractPort) -> None:
        self._inner = inner
        self.call_count = 0

    def readiness(self) -> dict[str, Any]:
        return _safe_readiness(self._inner)

    async def extract_rows(self, *, urls: list[str], query: str) -> list[dict[str, Any]]:
        self.call_count += 1
        return await self._inner.extract_rows(urls=urls, query=query)


def _external_search_port_used(
    *,
    search_port: WebSearchPort | None,
    search_port_call_count: int,
) -> bool:
    if search_port is None or search_port_call_count <= 0:
        return False
    profile = _safe_readiness(search_port)
    provider = str(profile.get("provider") or "").strip().lower()
    return provider not in {"", "fixture", "fake", "stub"}


def _manager_decision_fixture() -> B2ManagerSemanticDecision:
    return B2ManagerSemanticDecision(
        base_dish="Matcha Latte",
        aliases=["Test Brand Matcha Latte"],
        brand_hint="Test Brand",
        size_hint=None,
        modifier_hints=[],
        listed_items=[],
        retrieval_goal="exact_brand_lookup",
        semantic_authority_source="synthetic_manager_structured_fixture",
    )


def _case_result(trace: dict[str, Any]) -> dict[str, Any]:
    trace_payload = dict(trace)
    accepted_extract_packet_id = str(trace_payload.get("accepted_extract_packet_id") or "").strip()
    attempted = trace_payload.get("attempted") is True
    unsafe = trace_payload.get("rejected_web_candidates_used_as_evidence") is True
    status = "pass" if attempted and accepted_extract_packet_id and not unsafe else "fail"
    return {
        "case_id": "websearch_exact_brand_fixture_canary",
        "status": status,
        "runtime_truth_allowed": False,
        "runtime_mutation_allowed": False,
        "exact_card_created": False,
        "trace": trace_payload,
    }


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_websearch_live_search_diagnostic_canary"]
