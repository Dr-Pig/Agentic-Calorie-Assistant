from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any
from urllib.parse import urlparse

from .b2_candidate_packetizer import add_hard_recheck_metadata_many
from .b2_local_synthesis import synthesize_b2_local_manager_pass2
from .b2_packet_consumption import B2PacketConsumptionResult, consume_rechecked_packets
from .retrieval_intent import RetrievalIntent, build_retrieval_intent
from .selected_extract_policy import SelectedExtractDecision, choose_selected_extract_packet
from .web_extract_packetizer import build_web_extract_packets
from .web_extract_port import WebExtractPort
from .web_search_candidate_producer import collect_web_search_candidates
from .web_search_packetizer import build_web_search_candidate_packets
from .web_search_port import WebSearchPort

LANE_ID = "live_exact_brand_web_canary_v1"
_MULTI_ITEM_TOKENS = ("和", "、", ",", "，", "+", "還有")


@dataclass(frozen=True)
class ExactBrandWebLaneResult:
    intent: RetrievalIntent
    query: str
    search_packets: tuple[dict[str, object], ...]
    extract_packets: tuple[dict[str, object], ...]
    extract_policy: SelectedExtractDecision
    consumption: B2PacketConsumptionResult
    manager_pass_2: dict[str, object]


@dataclass(frozen=True)
class ExactBrandWebCanaryOutcome:
    result: ExactBrandWebLaneResult | None
    trace: dict[str, object]


async def run_exact_brand_web_canary(
    *,
    raw_user_input: str,
    search_port: WebSearchPort | None,
    extract_port: WebExtractPort | None,
    allow_search: bool,
    contextualized_query: str | None = None,
    exact_db_hit_present: bool = False,
) -> ExactBrandWebCanaryOutcome:
    trace = _default_trace()
    trace["raw_user_input"] = raw_user_input
    start = time.perf_counter()
    intent = build_retrieval_intent(raw_user_input)
    trace["retrieval_goal"] = intent.retrieval_goal
    trace["exact_db_miss_confirmed"] = not exact_db_hit_present
    trace["provider_profile"] = _provider_profile(search_port)

    skip_reason = _skip_reason(
        raw_user_input=raw_user_input,
        intent=intent,
        allow_search=allow_search,
        search_port=search_port,
        extract_port=extract_port,
        exact_db_hit_present=exact_db_hit_present,
    )
    if skip_reason is not None:
        trace["skip_reason"] = skip_reason
        trace["total_latency_ms"] = _elapsed_ms(start)
        return ExactBrandWebCanaryOutcome(result=None, trace=trace)

    trace["attempted"] = True
    query = _exact_brand_query(intent, contextualized_query=contextualized_query)
    trace["search_query"] = query
    trace["web_query"] = query

    search_start = time.perf_counter()
    try:
        candidates = await collect_web_search_candidates(
            search_port=search_port,
            query=query,
            identity_target=query,
            max_results=5,
        )
    except Exception as exc:
        trace["failure_reason"] = f"search_error:{type(exc).__name__}"
        trace["search_attempt_count"] = 1
        trace["search_latency_ms"] = _elapsed_ms(search_start)
        trace["total_latency_ms"] = _elapsed_ms(start)
        return ExactBrandWebCanaryOutcome(result=None, trace=trace)

    trace["search_attempt_count"] = 1
    trace["search_latency_ms"] = _elapsed_ms(search_start)
    search_packets = tuple(
        add_hard_recheck_metadata_many(
            build_web_search_candidate_packets(intent, candidates)
        )
    )
    trace["packetized_candidate_present"] = bool(search_packets)
    trace["candidate_traces"] = [_search_candidate_trace(packet) for packet in search_packets]

    extract_policy = choose_selected_extract_packet(search_packets)
    selected_search_packet = _selected_search_packet(
        search_packets,
        packet_id=extract_policy.selected_search_packet_id,
    )
    trace["selected_search_packet_id"] = extract_policy.selected_search_packet_id
    trace["selected_url"] = extract_policy.selected_urls[0] if extract_policy.selected_urls else None
    trace["manager_pass_2_saw_search_packet"] = selected_search_packet is not None
    if not extract_policy.extract_allowed_by_policy or selected_search_packet is None:
        trace["failure_reason"] = (
            "selected_search_packet_missing"
            if extract_policy.extract_allowed_by_policy and selected_search_packet is None
            else "selected_extract_policy_blocked"
        )
        trace["rejected_web_candidates_used_as_evidence"] = False
        trace["total_latency_ms"] = _elapsed_ms(start)
        return ExactBrandWebCanaryOutcome(result=None, trace=trace)

    extract_start = time.perf_counter()
    trace["extract_attempted"] = True
    try:
        extract_rows = await extract_port.extract_rows(
            urls=list(extract_policy.selected_urls),
            query=query,
        )
    except Exception as exc:
        trace["extract_attempt_count"] = 1
        trace["extract_latency_ms"] = _elapsed_ms(extract_start)
        trace["failure_reason"] = f"extract_error:{type(exc).__name__}"
        trace["total_latency_ms"] = _elapsed_ms(start)
        return ExactBrandWebCanaryOutcome(result=None, trace=trace)

    trace["extract_attempt_count"] = 1
    trace["extract_latency_ms"] = _elapsed_ms(extract_start)
    extract_packets = tuple(
        add_hard_recheck_metadata_many(
            build_web_extract_packets(
                intent,
                selected_search_packet=selected_search_packet,
                extract_rows=extract_rows,
            )
        )
    )
    consumption = consume_rechecked_packets(extract_packets)
    trace["packet_consumption_trace"] = _packet_consumption_trace(consumption)
    accepted_extract_packet = next(
        (
            packet
            for packet in consumption.accepted_packets
            if str(packet.get("source_type") or "").strip() == "web_extract"
            and str(packet.get("accepted_usage") or "").strip() == "exact"
        ),
        None,
    )
    trace["accepted_extract_packet_id"] = (
        str(accepted_extract_packet.get("packet_id") or "").strip()
        if isinstance(accepted_extract_packet, dict)
        else None
    )
    trace["total_latency_ms"] = _elapsed_ms(start)

    if accepted_extract_packet is None:
        trace["failure_reason"] = "no_accepted_web_extract_packet"
        trace["rejected_web_candidates_used_as_evidence"] = False
        return ExactBrandWebCanaryOutcome(result=None, trace=trace)

    manager_pass_2 = synthesize_b2_local_manager_pass2(intent, consumption)
    trace["synthesis_evidence_refs"] = _synthesis_evidence_refs(manager_pass_2)
    rejected_ids = {
        str(candidate.get("packet_id") or "").strip()
        for candidate in consumption.rejected_candidates
        if str(candidate.get("packet_id") or "").strip()
    }
    trace["rejected_web_candidates_used_as_evidence"] = bool(
        rejected_ids.intersection(set(trace["synthesis_evidence_refs"]))
    )
    result = ExactBrandWebLaneResult(
        intent=intent,
        query=query,
        search_packets=search_packets,
        extract_packets=extract_packets,
        extract_policy=extract_policy,
        consumption=consumption,
        manager_pass_2=manager_pass_2,
    )
    return ExactBrandWebCanaryOutcome(result=result, trace=trace)


def _skip_reason(
    *,
    raw_user_input: str,
    intent: RetrievalIntent,
    allow_search: bool,
    search_port: WebSearchPort | None,
    extract_port: WebExtractPort | None,
    exact_db_hit_present: bool,
) -> str | None:
    if exact_db_hit_present:
        return "exact_db_hit"
    if intent.listed_items:
        return "listed_items_not_supported"
    if any(token in str(raw_user_input or "") for token in _MULTI_ITEM_TOKENS):
        return "multi_item_not_supported"
    if intent.retrieval_goal != "exact_brand_lookup":
        return "retrieval_goal_not_exact_brand"
    if not allow_search:
        return "search_not_allowed"
    if search_port is None:
        return "search_port_unavailable"
    if extract_port is None:
        return "extract_port_unavailable"
    return None


def _exact_brand_query(intent: RetrievalIntent, *, contextualized_query: str | None) -> str:
    if str(contextualized_query or "").strip():
        return str(contextualized_query or "").strip()
    if intent.brand_hint and intent.base_dish:
        size_hint = str(intent.size_hint or "").strip()
        parts = [intent.brand_hint]
        if size_hint:
            parts.append(size_hint)
        parts.append(intent.base_dish)
        return "".join(part.strip() for part in parts if str(part).strip())
    if intent.aliases:
        return str(intent.aliases[0] or "").strip()
    return str(intent.base_dish or "").strip()


def _selected_search_packet(
    packets: tuple[dict[str, object], ...],
    *,
    packet_id: str | None,
) -> dict[str, object] | None:
    if not packet_id:
        return None
    return next((packet for packet in packets if packet.get("packet_id") == packet_id), None)


def _default_trace() -> dict[str, object]:
    return {
        "lane_id": LANE_ID,
        "attempted": False,
        "readiness_claimed": False,
        "skip_reason": None,
        "failure_reason": None,
        "search_query": None,
        "web_query": None,
        "provider_profile": None,
        "selected_search_packet_id": None,
        "accepted_extract_packet_id": None,
        "selected_url": None,
        "candidate_traces": [],
        "packet_consumption_trace": {"accepted_packets": [], "rejected_candidates": []},
        "synthesis_evidence_refs": [],
        "rejected_web_candidates_used_as_evidence": False,
        "search_attempt_count": 0,
        "extract_attempt_count": 0,
        "search_latency_ms": 0,
        "extract_latency_ms": 0,
        "total_latency_ms": 0,
        "cost": None,
        "packetized_candidate_present": False,
        "manager_pass_2_saw_search_packet": False,
        "extract_attempted": False,
        "retrieval_goal": None,
        "exact_db_miss_confirmed": False,
    }


def _provider_profile(search_port: WebSearchPort | None) -> dict[str, object]:
    if search_port is None:
        return {"search_port": None, "trace_only": True}
    readiness = getattr(search_port, "readiness", None)
    profile = readiness() if callable(readiness) else {}
    return {
        "search_port": type(search_port).__name__,
        "trace_only": True,
        **(profile if isinstance(profile, dict) else {}),
    }


def _search_candidate_trace(packet: dict[str, object]) -> dict[str, object]:
    risks = [str(risk).strip() for risk in packet.get("hard_recheck_risks", []) if str(risk).strip()]
    accepted_for_recheck = packet.get("supports_exact_claim") is True and not risks
    return {
        "packet_id": packet.get("packet_id"),
        "candidate_identity": packet.get("canonical_name"),
        "source_url": packet.get("url"),
        "source_domain": urlparse(str(packet.get("url") or "")).netloc.lower(),
        "source_title": packet.get("title"),
        "source_snippet": packet.get("snippet"),
        "hard_recheck_verdict": "accepted_for_exact_recheck" if accepted_for_recheck else "rejected_by_hard_recheck",
        "accepted_usage": None,
        "rejected_risk": risks[0] if risks else None,
    }


def _packet_consumption_trace(consumption: B2PacketConsumptionResult) -> dict[str, object]:
    return {
        "accepted_packets": [
            {
                "packet_id": packet.get("packet_id"),
                "accepted_usage": packet.get("accepted_usage"),
                "source_type": packet.get("source_type"),
            }
            for packet in consumption.accepted_packets
        ],
        "rejected_candidates": [
            {
                "packet_id": candidate.get("packet_id"),
                "risk_type": candidate.get("risk_type"),
                "usable_as_evidence": candidate.get("usable_as_evidence"),
            }
            for candidate in consumption.rejected_candidates
        ],
    }


def _synthesis_evidence_refs(manager_pass_2: dict[str, object]) -> list[str]:
    refs: list[str] = []
    for item in manager_pass_2.get("item_results", []):
        if not isinstance(item, dict):
            continue
        for evidence in item.get("evidence_used", []):
            if not isinstance(evidence, dict):
                continue
            packet_id = str(evidence.get("packet_id") or "").strip()
            if packet_id and packet_id not in refs:
                refs.append(packet_id)
    return refs


def _elapsed_ms(start: float) -> int:
    return int(round((time.perf_counter() - start) * 1000))


__all__ = [
    "ExactBrandWebCanaryOutcome",
    "ExactBrandWebLaneResult",
    "LANE_ID",
    "run_exact_brand_web_canary",
]
