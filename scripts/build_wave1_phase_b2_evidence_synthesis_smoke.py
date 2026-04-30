from __future__ import annotations

import asyncio
import argparse
from dataclasses import asdict
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.nutrition.application.b2_candidate_packetizer import (
    add_hard_recheck_metadata_many,
    build_candidate_packets,
)
from app.nutrition.application.b2_final_mapping import map_b2_final_item_result
from app.nutrition.application.b2_local_synthesis import synthesize_b2_local_manager_pass2
from app.nutrition.application.b2_packet_consumption import B2PacketConsumptionResult, consume_rechecked_packets
from app.nutrition.application.b2_semantic_decision import (
    B2ManagerSemanticDecision,
    build_retrieval_intent_from_manager_decision,
)
from app.nutrition.application.b2_source_selection import select_b2_evidence_source
from app.nutrition.application.exact_item_card_lookup import lookup_exact_item_card_candidates
from app.nutrition.application.listed_item_fanout import fanout_listed_item_anchor_lookups
from app.nutrition.application.packetizer_input_seed import packetizer_input_seeds_from_anchor_lookup_result
from app.nutrition.application.packetizer_input_seed import packetizer_input_seeds_from_exact_item_lookup_result
from app.nutrition.application.retrieval_intent import RetrievalGoal, RetrievalIntent
from app.nutrition.application.selected_extract_policy import choose_selected_extract_packet
from app.nutrition.application.small_anchor_store import lookup_anchor_candidates
from app.nutrition.application.web_extract_packetizer import build_web_extract_packets
from app.nutrition.application.web_extract_port import WebExtractPort
from app.nutrition.application.web_search_candidate_producer import produce_web_search_candidates
from app.nutrition.application.web_search_packetizer import build_web_search_candidate_packets

DEFAULT_OUTPUT_DIR = ROOT / "artifacts"
DEFAULT_STABLE_OUTPUT = DEFAULT_OUTPUT_DIR / "wave1_phase_b2_evidence_synthesis_smoke.json"
DEFAULT_B1_READINESS_ARTIFACT = ROOT / "artifacts" / "wave1_phase_b_minimal_tool_loop_readiness.json"
DEFAULT_B1_GATE_SCOPE = "Phase B-1 minimal tool-loop full natural-probe"

SMOKE_CASES = [
    "我吃了一顆茶葉蛋",
    "我喝了一杯珍珠奶茶",
    "我吃了一個便當",
    "我吃了滷味",
    "我吃了豆干、海帶、貢丸的滷味",
    "迷客夏珍珠紅茶拿鐵",
    "松屋特盛牛丼",
    "珍珠奶茶多少熱量？",
    "sibling_negative_milkshop_black_tea_latte_matched_fresh_milk_tea",
    "official_wrong_item_negative",
]


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _project_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _cache() -> dict[str, object]:
    return {
        "cache_key": None,
        "cache_hit": None,
        "cache_policy": None,
        "unavailable_reason": "cache_not_implemented_in_b2_gate",
    }


def _producer_trace(
    backing_class: str,
    support_basis: str,
    compatibility_reason: str | None = None,
) -> dict[str, object]:
    return {
        "backing_class": backing_class,
        "support_basis": support_basis,
        "compatibility_reason": compatibility_reason,
    }


def _intent_from_manager_decision(decision: B2ManagerSemanticDecision) -> RetrievalIntent:
    return build_retrieval_intent_from_manager_decision(decision)


def _semantic_decision_trace(decision: B2ManagerSemanticDecision) -> dict[str, object]:
    return _json_safe(asdict(decision))


def _source_selection_trace(intent: RetrievalIntent) -> dict[str, object]:
    return _json_safe(asdict(select_b2_evidence_source(intent)))


def _packet_consumption_trace(consumption: B2PacketConsumptionResult) -> dict[str, object]:
    return {
        "owner": "b2_packet_consumption",
        "consumed_packet_ids": list(consumption.consumed_packet_ids),
        "accepted_packet_ids": [
            str(packet.get("packet_id"))
            for packet in consumption.accepted_packets
            if packet.get("packet_id")
        ],
        "rejected_candidate_packet_ids": [
            str(candidate.get("packet_id"))
            for candidate in consumption.rejected_candidates
            if candidate.get("packet_id")
        ],
        "accepted_packets_count": len(consumption.accepted_packets),
        "rejected_candidates_count": len(consumption.rejected_candidates),
    }


def _combine_packet_consumption_traces(traces: list[dict[str, object]]) -> dict[str, object]:
    consumed: list[str] = []
    accepted: list[str] = []
    rejected: list[str] = []
    for trace in traces:
        consumed.extend(str(item) for item in trace.get("consumed_packet_ids", []) if str(item).strip())
        accepted.extend(str(item) for item in trace.get("accepted_packet_ids", []) if str(item).strip())
        rejected.extend(str(item) for item in trace.get("rejected_candidate_packet_ids", []) if str(item).strip())
    return {
        "owner": "b2_packet_consumption",
        "consumed_packet_ids": consumed,
        "accepted_packet_ids": accepted,
        "rejected_candidate_packet_ids": rejected,
        "accepted_packets_count": len(accepted),
        "rejected_candidates_count": len(rejected),
    }


def _mutation(*, attempted: bool, reason: str, result: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "mutation_attempted": attempted,
        "reason": reason,
        "mutation_result": result,
    }


def _generic_packet(packet_id: str, food_name: str) -> dict[str, object]:
    return {
        "packet_id": packet_id,
        "packet_type": "GenericDbCandidatePacket",
        "truth_level": "candidate",
        "source_type": "generic_db",
        "source_quality_label": "internal_generic",
        "raw_ref": f"artifacts/raw/{packet_id}.json",
        "matched_name": food_name,
        "canonical_name": food_name,
        "match_type": "generic",
        "brand_match": "not_applicable",
        "size_or_serving_match": "generic_serving",
        "modifier_match": "not_applicable",
        "serving_basis": "common_serving",
        "sibling_variant_risk": {"present": False},
        "kcal_range": [70, 90],
        "likely_kcal": 80,
    }


def _search_packet(
    packet_id: str,
    *,
    matched_name: str,
    canonical_name: str,
    source_quality_label: str = "brand_menu",
    match_type: str = "exact",
    sibling_risk: bool = False,
) -> dict[str, object]:
    return {
        "packet_id": packet_id,
        "packet_type": "SearchCandidatePacket",
        "truth_level": "candidate",
        "source_type": "web_search",
        "source_quality_label": source_quality_label,
        "raw_ref": f"artifacts/raw/{packet_id}.json",
        "title": canonical_name,
        "url": f"https://example.test/{packet_id}",
        "snippet": f"{canonical_name} menu candidate",
        "tavily_score": 0.84,
        "query": matched_name,
        "matched_terms": [matched_name],
        "matched_name": matched_name,
        "canonical_name": canonical_name,
        "match_type": match_type,
        "brand_match": "same" if "迷客夏" in matched_name or "松屋" in matched_name else "unknown",
        "size_or_serving_match": "same",
        "modifier_match": "same",
        "serving_basis": "menu_serving",
        "sibling_variant_risk": {"present": sibling_risk, "reason": "nearby menu variant" if sibling_risk else None},
    }


def _taiwan_skill_packet(packet_id: str) -> dict[str, object]:
    return {
        "packet_id": packet_id,
        "packet_type": "TaiwanSkillPacket",
        "truth_level": "rule_hint",
        "source_type": "taiwan_skill",
        "source_quality_label": "semantic_hint",
        "raw_ref": f"artifacts/raw/{packet_id}.json",
        "rule_id": "self_selected_basket_without_ingredients",
        "semantic_problem": "composition_unknown",
        "default_behavior_hint": "ask for listed ingredients before estimate tools",
    }


def _evidence(packet: dict[str, object], *, usage: str = "fallback", reason: str = "packet supports synthesis") -> dict[str, object]:
    return {
        "packet_id": packet["packet_id"],
        "source_type": packet["source_type"],
        "source_quality_label": packet["source_quality_label"],
        "usage": usage,
        "reason": reason,
    }


def _item_result(
    food_name: str,
    packet: dict[str, object] | None,
    *,
    exactness_posture: str,
    evidence_confidence: str,
    ledger_status: str = "included",
    usage: str = "fallback",
    rejected: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "food_name": food_name,
        "interpreted_food_identity": food_name,
        "assumed_composition": "single item" if ledger_status == "included" else "unknown composition",
        "kcal_range": [70, 90] if ledger_status == "included" else None,
        "likely_kcal": 80 if ledger_status == "included" else None,
        "uncertainty_level": "low" if exactness_posture == "exact" else "moderate",
        "evidence_confidence": evidence_confidence,
        "exactness_posture": exactness_posture,
        "evidence_used": [_evidence(packet, usage=usage)] if packet else [],
        "rejected_candidates": rejected or [],
        "uncertainty_reason": "B-2 gate synthetic packet",
        "suggested_followup_question": None if ledger_status == "included" else "請列出滷味品項。",
        "ledger_status": ledger_status,
    }


def _compat_uncertainty_level_from_exactness_posture(exactness_posture: str) -> str:
    return "low" if exactness_posture == "exact" else "moderate"


def _bridge_runtime_item_result_for_readiness(item: dict[str, object]) -> dict[str, object]:
    interpreted_food_identity = str(item.get("interpreted_food_identity") or "").strip()
    exactness_posture = str(item.get("exactness_posture") or "").strip()
    return {
        "food_name": interpreted_food_identity,
        "interpreted_food_identity": item.get("interpreted_food_identity"),
        "assumed_composition": item.get("assumed_composition"),
        "kcal_range": item.get("kcal_range"),
        "likely_kcal": item.get("likely_kcal"),
        "uncertainty_level": _compat_uncertainty_level_from_exactness_posture(exactness_posture),
        "evidence_confidence": item.get("evidence_confidence"),
        "exactness_posture": item.get("exactness_posture"),
        "evidence_used": list(item.get("evidence_used") or []),
        "rejected_candidates": list(item.get("rejected_candidates") or []),
        "uncertainty_reason": item.get("uncertainty_reason"),
        "suggested_followup_question": item.get("suggested_followup_question"),
    }


def _apply_final_mapping(
    item_results: list[dict[str, object]],
    *,
    mutation: dict[str, object],
) -> list[dict[str, object]]:
    interaction_type = _interaction_type_from_mutation(mutation)
    canonical_write_decision = {
        "can_write_canonical": bool(mutation.get("mutation_attempted") and mutation.get("mutation_result") is not None)
    }
    mapped_results: list[dict[str, object]] = []
    for item in item_results:
        mapped = dict(item)
        final_mapping = map_b2_final_item_result(
            mapped,
            canonical_write_decision=canonical_write_decision,
            interaction_type=interaction_type,
        )
        mapped["final_mapping"] = final_mapping
        mapped["ledger_status"] = final_mapping["ledger_status"]
        mapped_results.append(mapped)
    return mapped_results


def _interaction_type_from_mutation(mutation: dict[str, object]) -> str:
    if mutation.get("mutation_attempted") is False and mutation.get("reason") == "no_mutation_intent":
        return "nutrition_info_query"
    return "food_logging"


def _runtime_generic_case(
    case_id: str,
    input_message: str,
    *,
    semantic_decision: B2ManagerSemanticDecision,
    mutation: dict[str, object] | None = None,
    final_response: str = "已根據 renderer input 回覆。",
) -> dict[str, object]:
    intent = _intent_from_manager_decision(semantic_decision)
    anchor_result = lookup_anchor_candidates(intent)
    seeds = packetizer_input_seeds_from_anchor_lookup_result(anchor_result)
    packets = list(add_hard_recheck_metadata_many(build_candidate_packets(seeds)))
    consumption = consume_rechecked_packets(packets)
    manager_pass_2 = synthesize_b2_local_manager_pass2(intent, consumption)
    item_results = [
        _bridge_runtime_item_result_for_readiness(item)
        for item in manager_pass_2.get("item_results", [])
        if isinstance(item, dict)
    ]
    return _case(
        case_id,
        input_message,
        packets,
        item_results,
        producer_trace=_producer_trace("runtime_backed", "generic_anchor"),
        source_selection=_source_selection_trace(intent),
        packet_consumption=_packet_consumption_trace(consumption),
        semantic_decision=semantic_decision,
        mutation=mutation,
        final_response=final_response,
    )


def _runtime_clarify_case_with_taiwan_skill_compat(
    case_id: str,
    input_message: str,
    *,
    semantic_decision: B2ManagerSemanticDecision,
    compatibility_packet: dict[str, object],
    mutation: dict[str, object] | None = None,
    final_response: str = "已根據 renderer input 回覆。",
) -> dict[str, object]:
    intent = _intent_from_manager_decision(semantic_decision)
    anchor_result = lookup_anchor_candidates(intent)
    consumption = consume_rechecked_packets((compatibility_packet,))
    synthesis_consumption = consume_rechecked_packets(())
    manager_pass_2 = synthesize_b2_local_manager_pass2(
        intent,
        synthesis_consumption,
        clarify_support=anchor_result.clarify_support,
    )
    item_results = [
        _bridge_runtime_item_result_for_readiness(item)
        for item in manager_pass_2.get("item_results", [])
        if isinstance(item, dict)
    ]
    return _case(
        case_id,
        input_message,
        [compatibility_packet],
        item_results,
        producer_trace=_producer_trace("runtime_backed", "clarify_support"),
        source_selection=_source_selection_trace(intent),
        packet_consumption=_packet_consumption_trace(consumption),
        semantic_decision=semantic_decision,
        mutation=mutation,
        final_response=final_response,
    )


def _runtime_exact_item_case(
    case_id: str,
    input_message: str,
    *,
    semantic_decision: B2ManagerSemanticDecision,
    mutation: dict[str, object] | None = None,
    final_response: str = "已根據 renderer input 回覆。",
) -> dict[str, object]:
    intent = _intent_from_manager_decision(semantic_decision)
    exact_lookup = lookup_exact_item_card_candidates(intent)
    seeds = packetizer_input_seeds_from_exact_item_lookup_result(exact_lookup)
    packets = list(add_hard_recheck_metadata_many(build_candidate_packets(seeds)))
    consumption = consume_rechecked_packets(packets)
    manager_pass_2 = synthesize_b2_local_manager_pass2(intent, consumption)
    item_results = [
        _bridge_runtime_item_result_for_readiness(item)
        for item in manager_pass_2.get("item_results", [])
        if isinstance(item, dict)
    ]
    return _case(
        case_id,
        input_message,
        packets,
        item_results,
        producer_trace=_producer_trace("runtime_backed", "exact_item_card"),
        source_selection=_source_selection_trace(intent),
        packet_consumption=_packet_consumption_trace(consumption),
        semantic_decision=semantic_decision,
        mutation=mutation,
        final_response=final_response,
    )


def _runtime_web_rejection_case(
    case_id: str,
    input_message: str,
    *,
    semantic_decision: B2ManagerSemanticDecision,
    query: str,
    raw_hits: list[dict[str, object]],
    mutation: dict[str, object] | None = None,
    final_response: str = "已根據 renderer input 回覆。",
) -> dict[str, object]:
    intent = _intent_from_manager_decision(semantic_decision)
    candidates = produce_web_search_candidates(
        query=query,
        identity_target=query,
        raw_hits=raw_hits,
    )
    packets = list(add_hard_recheck_metadata_many(build_web_search_candidate_packets(intent, candidates)))
    consumption = consume_rechecked_packets(packets)
    manager_pass_2 = synthesize_b2_local_manager_pass2(intent, consumption)
    item_results = [
        _bridge_runtime_item_result_for_readiness(item)
        for item in manager_pass_2.get("item_results", [])
        if isinstance(item, dict)
    ]
    return _case(
        case_id,
        input_message,
        packets,
        item_results,
        producer_trace=_producer_trace("runtime_backed", "web_search_rejection"),
        source_selection=_source_selection_trace(intent),
        packet_consumption=_packet_consumption_trace(consumption),
        semantic_decision=semantic_decision,
        mutation=mutation,
        final_response=final_response,
    )


class _FixtureExtractPort:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    async def extract_rows(
        self,
        *,
        urls: list[str],
        query: str,
    ) -> list[dict[str, object]]:
        allowed = set(urls)
        return [row for row in self._rows if str(row.get("url") or "") in allowed]


def _runtime_selected_extract_exact_positive_case(
    case_id: str,
    input_message: str,
    *,
    semantic_decision: B2ManagerSemanticDecision,
    query: str,
    raw_hits: list[dict[str, object]],
    extract_rows: list[dict[str, object]],
    extract_port: WebExtractPort | None = None,
    mutation: dict[str, object] | None = None,
    final_response: str = "撌脫??renderer input ????,",
) -> dict[str, object]:
    intent = _intent_from_manager_decision(semantic_decision)
    candidates = produce_web_search_candidates(
        query=query,
        identity_target=query,
        raw_hits=raw_hits,
    )
    search_packets = list(add_hard_recheck_metadata_many(build_web_search_candidate_packets(intent, candidates)))
    extract_policy = choose_selected_extract_packet(search_packets)
    extract_packets: list[dict[str, object]] = []
    if extract_policy.extract_allowed_by_policy and extract_policy.selected_search_packet_id:
        selected_search_packet = next(
            packet for packet in search_packets if packet.get("packet_id") == extract_policy.selected_search_packet_id
        )
        port = extract_port or _FixtureExtractPort(extract_rows)
        extracted_rows = asyncio.run(port.extract_rows(urls=extract_policy.selected_urls, query=query))
        extract_packets = list(
            add_hard_recheck_metadata_many(
                build_web_extract_packets(
                    intent,
                    selected_search_packet=selected_search_packet,
                    extract_rows=extracted_rows,
                )
            )
        )
    consumption = consume_rechecked_packets(extract_packets)
    manager_pass_2 = synthesize_b2_local_manager_pass2(intent, consumption)
    item_results = [
        _bridge_runtime_item_result_for_readiness(item)
        for item in manager_pass_2.get("item_results", [])
        if isinstance(item, dict)
    ]
    return _case(
        case_id,
        input_message,
        [*search_packets, *extract_packets],
        item_results,
        producer_trace=_producer_trace("runtime_backed", "selected_extract_exact_positive"),
        source_selection=_source_selection_trace(intent),
        packet_consumption=_packet_consumption_trace(consumption),
        semantic_decision=semantic_decision,
        mutation=mutation,
        final_response=final_response,
        extract_policy=extract_policy.to_trace(),
    )


def _runtime_listed_item_fanout_case(
    case_id: str,
    input_message: str,
    *,
    semantic_decision: B2ManagerSemanticDecision,
    mutation: dict[str, object] | None = None,
    final_response: str = "已根據 renderer input 回覆。",
) -> dict[str, object]:
    intent = _intent_from_manager_decision(semantic_decision)
    resolutions = fanout_listed_item_anchor_lookups(intent)

    packets: list[dict[str, object]] = []
    item_results: list[dict[str, object]] = []
    resolution_trace: list[dict[str, object]] = []
    consumption_traces: list[dict[str, object]] = []

    for resolution in resolutions:
        seeds = packetizer_input_seeds_from_anchor_lookup_result(resolution.lookup_result)
        if not seeds:
            resolution_trace.append(
                {
                    "listed_item": resolution.listed_item,
                    "resolution_status": "unresolved",
                    "defer_reason": resolution.lookup_result.defer_reason,
                    "clarify_support_present": resolution.lookup_result.clarify_support is not None,
                    "packet_ids": [],
                }
            )
            continue
        sub_packets = list(add_hard_recheck_metadata_many(build_candidate_packets(seeds)))
        consumption = consume_rechecked_packets(sub_packets)
        consumption_traces.append(_packet_consumption_trace(consumption))
        manager_pass_2 = synthesize_b2_local_manager_pass2(resolution.sub_intent, consumption)
        resolution_trace.append(
            {
                "listed_item": resolution.listed_item,
                "resolution_status": "resolved",
                "defer_reason": None,
                "clarify_support_present": False,
                "packet_ids": [packet.get("packet_id") for packet in sub_packets],
            }
        )
        packets.extend(sub_packets)
        item_results.extend(
            _bridge_runtime_item_result_for_readiness(item)
            for item in manager_pass_2.get("item_results", [])
            if isinstance(item, dict)
        )

    return _case(
        case_id,
        input_message,
        packets,
        item_results,
        producer_trace=_producer_trace("runtime_backed", "listed_item_runtime_fanout"),
        source_selection=_source_selection_trace(intent),
        packet_consumption=_combine_packet_consumption_traces(consumption_traces),
        semantic_decision=semantic_decision,
        mutation=mutation,
        final_response=final_response,
        extra_case_trace={"listed_item_fanout": {"resolutions": resolution_trace}},
    )


def _case(
    case_id: str,
    input_message: str,
    packets: list[dict[str, object]],
    item_results: list[dict[str, object]],
    *,
    producer_trace: dict[str, object] | None = None,
    source_selection: dict[str, object] | None = None,
    packet_consumption: dict[str, object] | None = None,
    semantic_decision: B2ManagerSemanticDecision | None = None,
    mutation: dict[str, object] | None = None,
    final_response: str = "已根據 renderer input 回覆。",
    extract_policy: dict[str, object] | None = None,
    extra_case_trace: dict[str, object] | None = None,
) -> dict[str, object]:
    mutation = mutation or _mutation(
        attempted=True,
        reason="guard_approved_logging",
        result={"truth_level": "mutation_result", "ledger_item_ids": [f"item_{case_id}"]},
    )
    item_results = _apply_final_mapping(item_results, mutation=mutation)
    renderer_input = {
        "allowed_facts": ["估算", "先記一筆粗估", "資料顯示", "缺少滷味品項"],
        "forbidden_claims": ["facts outside item_results", "unsupported exact kcal"],
        "item_results": item_results,
        "ledger_mutation_result": mutation["mutation_result"],
    }
    case_payload = {
        "case_id": case_id,
        "input_message": input_message,
        "producer_trace": producer_trace,
        "manager_semantic_decision": _semantic_decision_trace(semantic_decision) if semantic_decision else None,
        "retrieval_intent_source": "manager_semantic_decision" if semantic_decision else None,
        "runner_inferred_semantics": False if semantic_decision else None,
        "source_selection": source_selection,
        "packet_consumption": packet_consumption,
        "packets": packets,
        "manager_pass_2": {"item_results": item_results},
        "extract_policy": extract_policy
        or {
            "selected_search_packet_id": None,
            "extract_reason": None,
            "extract_allowed_by_policy": False,
            "max_extract_urls": 1,
            "extract_count": 0,
        },
        "mutation": mutation,
        "renderer": {"input": renderer_input, "final_response": final_response},
        "cache": _cache(),
    }
    if extra_case_trace:
        case_payload.update(extra_case_trace)
    return case_payload


def build_b1_green_handoff_snapshot(*, readiness_artifact_path: Path | None = None) -> dict[str, Any]:
    readiness_path = readiness_artifact_path or DEFAULT_B1_READINESS_ARTIFACT
    if not readiness_path.exists():
        raise FileNotFoundError(f"B-1 readiness artifact not found: {readiness_path}")

    readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
    ready = readiness.get("ready_for_phase_b1_implementation") is True
    blockers = list(readiness.get("blockers") or [])
    if not ready or blockers:
        raise ValueError("B-1 handoff requires ready_for_phase_b1_implementation=true and blockers=[].")

    smoke_artifact = readiness.get("phase_b_report_path")
    if not isinstance(smoke_artifact, str) or not smoke_artifact.strip():
        raise ValueError("B-1 readiness artifact must expose phase_b_report_path for handoff tracing.")

    return {
        "b1_gate_scope": DEFAULT_B1_GATE_SCOPE,
        "smoke_artifact": smoke_artifact,
        "readiness_artifact": _project_relative(readiness_path),
        "ready_for_phase_b1_implementation": True,
        "blockers": [],
        "not_claiming": "whole Wave 1 completion",
    }


def _synthetic_manager_decision_fixture(
    *,
    base_dish: str | None,
    aliases: list[str] | None = None,
    brand_hint: str | None = None,
    size_hint: str | None = None,
    modifier_hints: list[str] | None = None,
    listed_items: list[str] | None = None,
    retrieval_goal: RetrievalGoal,
) -> B2ManagerSemanticDecision:
    return B2ManagerSemanticDecision(
        base_dish=base_dish,
        aliases=aliases or [],
        brand_hint=brand_hint,
        size_hint=size_hint,
        modifier_hints=modifier_hints or [],
        listed_items=listed_items or [],
        retrieval_goal=retrieval_goal,
        semantic_authority_source="synthetic_manager_structured_fixture",
    )


def _build_phase_b2_synthetic_smoke_report_legacy(
    *,
    b1_green_handoff_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    raise RuntimeError("Legacy static B2 smoke producer is disabled; use build_phase_b2_synthetic_smoke_report.")

    handoff_snapshot = _json_safe(b1_green_handoff_snapshot or build_b1_green_handoff_snapshot())

    tea_egg = _generic_packet("pkt_generic_tea_egg", "茶葉蛋")
    boba = _generic_packet("pkt_generic_boba", "珍珠奶茶")
    bento = _generic_packet("pkt_generic_bento", "便當")
    luwei_skill = _taiwan_skill_packet("pkt_skill_luwei")
    dougan = _generic_packet("pkt_generic_dougan", "豆干")
    haidai = _generic_packet("pkt_generic_haidai", "海帶")
    gongwan = _generic_packet("pkt_generic_gongwan", "貢丸")
    milkshop_search = _search_packet(
        "pkt_search_milkshop_black_tea_latte",
        matched_name="迷客夏珍珠紅茶拿鐵",
        canonical_name="迷客夏珍珠紅茶拿鐵",
        source_quality_label="brand_menu",
        match_type="exact",
    )
    matsuya = _search_packet(
        "pkt_search_matsuya_tokumori",
        matched_name="松屋特盛牛丼",
        canonical_name="松屋特盛牛丼",
        source_quality_label="official",
        match_type="exact",
    )
    sibling = _search_packet(
        "pkt_sibling_milkshop_fresh_milk_tea",
        matched_name="迷客夏珍珠紅茶拿鐵",
        canonical_name="迷客夏珍珠鮮奶茶",
        source_quality_label="brand_menu",
        match_type="related",
        sibling_risk=True,
    )
    wrong_official = _search_packet(
        "pkt_official_wrong_item",
        matched_name="迷客夏珍珠紅茶拿鐵",
        canonical_name="迷客夏伯爵紅茶拿鐵",
        source_quality_label="official",
        match_type="related",
        sibling_risk=True,
    )

    cases = [
        _case("B2-001", "我吃了一顆茶葉蛋", [tea_egg], [_item_result("茶葉蛋", tea_egg, exactness_posture="estimated", evidence_confidence="moderate")], final_response="這是一筆估算。"),
        _case("B2-002", "我喝了一杯珍珠奶茶", [boba], [_item_result("珍珠奶茶", boba, exactness_posture="estimated", evidence_confidence="moderate")], final_response="這是一筆估算，糖度與杯型可再補。"),
        _case("B2-003", "我吃了一個便當", [bento], [_item_result("便當", bento, exactness_posture="provisional", evidence_confidence="weak")], final_response="先記一筆粗估。"),
        _case(
            "B2-004",
            "我吃了滷味",
            [luwei_skill],
            [_item_result("滷味", None, exactness_posture="unresolved", evidence_confidence="insufficient", ledger_status="excluded_pending_info")],
            mutation=_mutation(attempted=False, reason="needs_info_guard", result=None),
            final_response="缺少滷味品項，請列出組成。",
        ),
        _case(
            "B2-005",
            "我吃了豆干、海帶、貢丸的滷味",
            [dougan, haidai, gongwan],
            [
                _item_result("豆干", dougan, exactness_posture="estimated", evidence_confidence="moderate"),
                _item_result("海帶", haidai, exactness_posture="estimated", evidence_confidence="moderate"),
                _item_result("貢丸", gongwan, exactness_posture="estimated", evidence_confidence="moderate"),
            ],
            final_response="已拆成豆干、海帶、貢丸並估算。",
        ),
        _case(
            "B2-006",
            "迷客夏珍珠紅茶拿鐵",
            [milkshop_search],
            [_item_result("迷客夏珍珠紅茶拿鐵", milkshop_search, exactness_posture="exact", evidence_confidence="strong", usage="exact")],
            final_response="資料顯示這是同品項品牌候選。",
            extract_policy={
                "selected_search_packet_id": "pkt_search_milkshop_black_tea_latte",
                "extract_reason": "selected brand-menu same-item candidate",
                "extract_allowed_by_policy": True,
                "max_extract_urls": 1,
                "extract_count": 1,
            },
        ),
        _case(
            "B2-007",
            "松屋特盛牛丼",
            [matsuya],
            [_item_result("松屋特盛牛丼", matsuya, exactness_posture="exact", evidence_confidence="strong", usage="exact")],
            final_response="資料顯示這是官方同品項候選。",
        ),
        _case(
            "B2-008",
            "珍珠奶茶多少熱量？",
            [boba],
            [_item_result("珍珠奶茶", boba, exactness_posture="estimated", evidence_confidence="moderate")],
            mutation=_mutation(attempted=False, reason="no_mutation_intent", result=None),
            final_response="這是估算查詢，不會記帳。",
        ),
        _case(
            "B2-009",
            "sibling_negative_milkshop_black_tea_latte_matched_fresh_milk_tea",
            [sibling],
            [
                _item_result(
                    "迷客夏珍珠紅茶拿鐵",
                    None,
                    exactness_posture="estimated",
                    evidence_confidence="weak",
                    rejected=[
                        {
                            "packet_id": "pkt_sibling_milkshop_fresh_milk_tea",
                            "risk_type": "sibling_variant",
                            "reason": "candidate is 珍珠鮮奶茶, not 珍珠紅茶拿鐵",
                        }
                    ],
                )
            ],
            final_response="候選是相近品項，只能作參考。",
        ),
        _case(
            "B2-010",
            "official_wrong_item_negative",
            [wrong_official],
            [
                _item_result(
                    "迷客夏珍珠紅茶拿鐵",
                    wrong_official,
                    exactness_posture="estimated",
                    evidence_confidence="weak",
                    usage="anchor",
                    rejected=[
                        {
                            "packet_id": "pkt_official_wrong_item",
                            "risk_type": "wrong_item",
                            "reason": "official source is authoritative but item name differs",
                        }
                    ],
                )
            ],
            final_response="官方來源品項不同，只能作參考。",
        ),
    ]

    return {
        "phase": "B2",
        "mode": "evidence_synthesis_gate",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "semantic_owner_integrity": {
            "status": "pass",
            "semantic_authority_source": "synthetic_manager_structured_fixture",
            "runner_inferred_semantics": False,
        },
        "b1_green_handoff_snapshot": handoff_snapshot,
        "smoke_cases_run": SMOKE_CASES,
        "cases": cases,
        "trusted_source_manifest": {
            "entries": [
                {
                    "source_id": "taiwan_food_trusted_reference",
                    "source_quality_label": "trusted_database",
                    "approved": True,
                    "scope": "B-2 local app-owned fixture/store evidence",
                    "evidence_authority": "local_app_owned_store",
                    "semantic_authority": "none",
                    "runtime_web_activation": False,
                }
            ]
        },
        "trusted_database_policy": {
            "allowlist": ["taiwan_food_trusted_reference"],
            "approved": True,
        },
        "minimal_db_seed_manifest": {
            "store_backing": "local_app_owned_test_aligned_store",
            "semantic_authority": "none",
            "provenance_note": "Seeds exercise app-owned local lookup and packetizer paths; manager semantics come from the synthetic manager structured fixture.",
            "seeds": [
                {
                    "food_name": "茶葉蛋",
                    "seed_type": "generic",
                    "used_by_smoke_case": "我吃了一顆茶葉蛋",
                    "fixture_only": False,
                    "allowed_fields": ["kcal_range", "likely_kcal", "macro_candidate"],
                },
                {
                    "food_name": "珍珠奶茶",
                    "seed_type": "generic",
                    "used_by_smoke_case": "我喝了一杯珍珠奶茶",
                    "fixture_only": False,
                    "allowed_fields": ["kcal_range", "likely_kcal", "macro_candidate"],
                },
                {
                    "food_name": "便當",
                    "seed_type": "generic",
                    "used_by_smoke_case": "我吃了一個便當",
                    "fixture_only": False,
                    "allowed_fields": ["kcal_range", "likely_kcal", "macro_candidate"],
                },
                {
                    "food_name": "豆干",
                    "seed_type": "generic",
                    "used_by_smoke_case": "我吃了豆干、海帶、貢丸的滷味",
                    "fixture_only": False,
                    "allowed_fields": ["kcal_range", "likely_kcal", "macro_candidate"],
                },
                {
                    "food_name": "海帶",
                    "seed_type": "generic",
                    "used_by_smoke_case": "我吃了豆干、海帶、貢丸的滷味",
                    "fixture_only": False,
                    "allowed_fields": ["kcal_range", "likely_kcal", "macro_candidate"],
                },
                {
                    "food_name": "貢丸",
                    "seed_type": "generic",
                    "used_by_smoke_case": "我吃了豆干、海帶、貢丸的滷味",
                    "fixture_only": False,
                    "allowed_fields": ["kcal_range", "likely_kcal", "macro_candidate"],
                },
            ],
            "exact_seed_policy": "empty_for_real_runtime_in_this_slice",
        },
        "runtime_trace_parity": {
            "status": "not_applicable",
            "required_core_fields_match": True,
            "extra_fields_allowed": True,
            "renamed_core_fields_allowed": False,
            "missing_core_fields_allowed": False,
        },
        "non_scope": {
            "autonomous_nutrition_subagent": False,
            "independent_llm_evidence_normalizer": False,
            "full_macro_engine": False,
            "nutrition_accuracy_production_ready_claim": False,
        },
    }


def build_phase_b2_synthetic_smoke_report(
    *,
    b1_green_handoff_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    handoff_snapshot = _json_safe(b1_green_handoff_snapshot or build_b1_green_handoff_snapshot())
    matsuya_decision = _synthetic_manager_decision_fixture(
        base_dish="牛丼",
        aliases=["松屋特盛牛丼"],
        brand_hint="松屋",
        size_hint="特盛",
        retrieval_goal="exact_brand_lookup",
    )
    milkshop_exact_decision = _synthetic_manager_decision_fixture(
        base_dish="珍珠紅茶拿鐵",
        aliases=["迷客夏珍珠紅茶拿鐵"],
        brand_hint="迷客夏",
        size_hint=None,
        retrieval_goal="exact_brand_lookup",
    )

    luwei_skill = _taiwan_skill_packet("pkt_skill_luwei")
    dougan = _generic_packet("pkt_generic_dougan", "豆干")
    haidai = _generic_packet("pkt_generic_haidai", "海帶")
    gongwan = _generic_packet("pkt_generic_gongwan", "貢丸")
    milkshop_search = _search_packet(
        "pkt_search_milkshop_black_tea_latte",
        matched_name="迷客夏珍珠紅茶拿鐵",
        canonical_name="迷客夏珍珠紅茶拿鐵",
        source_quality_label="brand_menu",
        match_type="exact",
    )
    cases = [
        _runtime_generic_case(
            "B2-001",
            "我吃了一顆茶葉蛋",
            semantic_decision=_synthetic_manager_decision_fixture(
                base_dish="茶葉蛋",
                aliases=["茶葉蛋"],
                retrieval_goal="generic_anchor_lookup",
            ),
        ),
        _runtime_generic_case(
            "B2-002",
            "我喝了一杯珍珠奶茶",
            semantic_decision=_synthetic_manager_decision_fixture(
                base_dish="珍珠奶茶",
                aliases=["珍珠奶茶"],
                retrieval_goal="generic_anchor_lookup",
            ),
        ),
        _runtime_generic_case(
            "B2-003",
            "我吃了一個便當",
            semantic_decision=_synthetic_manager_decision_fixture(
                base_dish="便當",
                aliases=["便當"],
                retrieval_goal="generic_anchor_lookup",
            ),
        ),
        _runtime_clarify_case_with_taiwan_skill_compat(
            "B2-004",
            "我吃了滷味",
            semantic_decision=_synthetic_manager_decision_fixture(
                base_dish="滷味",
                aliases=["滷味"],
                retrieval_goal="composition_clarification",
            ),
            compatibility_packet=luwei_skill,
            mutation=_mutation(attempted=False, reason="needs_info_guard", result=None),
        ),
        _runtime_listed_item_fanout_case(
            "B2-005",
            "我吃了豆干、海帶、貢丸的滷味",
            semantic_decision=_synthetic_manager_decision_fixture(
                base_dish="滷味",
                aliases=["滷味"],
                listed_items=["豆干", "海帶", "貢丸"],
                retrieval_goal="listed_item_lookup",
            ),
        ),
        _runtime_selected_extract_exact_positive_case(
            "B2-006",
            "迷客夏珍珠紅茶拿鐵",
            semantic_decision=milkshop_exact_decision,
            query="迷客夏珍珠紅茶拿鐵",
            raw_hits=[
                {
                    "title": "迷客夏 珍珠紅茶拿鐵",
                    "url": "https://milksha.example/menu/pearl-black-tea-latte",
                    "snippet": "official menu result",
                    "score": 0.94,
                    "officialness": "official",
                    "brand_detected": "迷客夏",
                    "identity_confidence": "high",
                    "source_quality_label": "high",
                    "serving_basis": "per_cup",
                    "nutrition_fields_present": ["kcal"],
                }
            ],
            extract_rows=[
                {
                    "url": "https://milksha.example/menu/pearl-black-tea-latte",
                    "title": "迷客夏 珍珠紅茶拿鐵",
                    "source_type": "official",
                    "officialness": "official",
                    "serving_basis": "per_cup",
                    "brand_detected": "milksha",
                    "raw_content": "每杯 400 kcal",
                }
            ],
        ),
        _runtime_exact_item_case(
            "B2-007",
            "松屋特盛牛丼",
            semantic_decision=matsuya_decision,
        ),
        _runtime_generic_case(
            "B2-008",
            "珍珠奶茶多少熱量？",
            semantic_decision=_synthetic_manager_decision_fixture(
                base_dish="珍珠奶茶",
                aliases=["珍珠奶茶"],
                retrieval_goal="query_only_answer",
            ),
            mutation=_mutation(attempted=False, reason="no_mutation_intent", result=None),
        ),
        _runtime_web_rejection_case(
            "B2-009",
            "sibling_negative_milkshop_black_tea_latte_matched_fresh_milk_tea",
            semantic_decision=milkshop_exact_decision,
            query="迷客夏珍珠紅茶拿鐵",
            raw_hits=[
                {
                    "title": "迷客夏珍珠鮮奶茶",
                    "url": "https://example.test/milkshop-fresh-milk-tea",
                    "snippet": "迷客夏珍珠鮮奶茶 menu candidate",
                    "score": 0.91,
                    "officialness": "official",
                    "brand_detected": "迷客夏",
                    "identity_confidence": "high",
                    "source_quality_label": "high",
                }
            ],
        ),
        _runtime_web_rejection_case(
            "B2-010",
            "official_wrong_item_negative",
            semantic_decision=milkshop_exact_decision,
            query="迷客夏珍珠紅茶拿鐵",
            raw_hits=[
                {
                    "title": "迷客夏布丁紅茶拿鐵",
                    "url": "https://example.test/milkshop-pudding-latte",
                    "snippet": "迷客夏布丁紅茶拿鐵 menu candidate",
                    "score": 0.87,
                    "officialness": "official",
                    "brand_detected": "迷客夏",
                    "identity_confidence": "low",
                    "source_quality_label": "high",
                }
            ],
        ),
    ]

    return {
        "phase": "B2",
        "mode": "evidence_synthesis_gate",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "semantic_owner_integrity": {
            "status": "pass",
            "semantic_authority_source": "synthetic_manager_structured_fixture",
            "runner_inferred_semantics": False,
        },
        "b1_green_handoff_snapshot": handoff_snapshot,
        "smoke_cases_run": SMOKE_CASES,
        "cases": cases,
        "trusted_source_manifest": {
            "entries": [
                {
                    "source_id": "taiwan_food_trusted_reference",
                    "source_quality_label": "trusted_database",
                    "approved": True,
                    "scope": "B-2 local app-owned fixture/store evidence",
                    "evidence_authority": "local_app_owned_store",
                    "semantic_authority": "none",
                    "runtime_web_activation": False,
                }
            ]
        },
        "trusted_database_policy": {
            "allowlist": ["taiwan_food_trusted_reference"],
            "approved": True,
        },
        "minimal_db_seed_manifest": {
            "store_backing": "local_app_owned_test_aligned_store",
            "semantic_authority": "none",
            "provenance_note": "Seeds exercise app-owned local lookup and packetizer paths; manager semantics come from the synthetic manager structured fixture.",
            "seeds": [
                {
                    "food_name": "茶葉蛋",
                    "seed_type": "generic",
                    "used_by_smoke_case": "我吃了一顆茶葉蛋",
                    "fixture_only": False,
                    "allowed_fields": ["kcal_range", "likely_kcal", "macro_candidate"],
                },
                {
                    "food_name": "珍珠奶茶",
                    "seed_type": "generic",
                    "used_by_smoke_case": "我喝了一杯珍珠奶茶",
                    "fixture_only": False,
                    "allowed_fields": ["kcal_range", "likely_kcal", "macro_candidate"],
                },
                {
                    "food_name": "便當",
                    "seed_type": "generic",
                    "used_by_smoke_case": "我吃了一個便當",
                    "fixture_only": False,
                    "allowed_fields": ["kcal_range", "likely_kcal", "macro_candidate"],
                },
                {
                    "food_name": "豆干",
                    "seed_type": "generic",
                    "used_by_smoke_case": "我吃了豆干、海帶、貢丸的滷味",
                    "fixture_only": False,
                    "allowed_fields": ["kcal_range", "likely_kcal", "macro_candidate"],
                },
                {
                    "food_name": "海帶",
                    "seed_type": "generic",
                    "used_by_smoke_case": "我吃了豆干、海帶、貢丸的滷味",
                    "fixture_only": False,
                    "allowed_fields": ["kcal_range", "likely_kcal", "macro_candidate"],
                },
                {
                    "food_name": "貢丸",
                    "seed_type": "generic",
                    "used_by_smoke_case": "我吃了豆干、海帶、貢丸的滷味",
                    "fixture_only": False,
                    "allowed_fields": ["kcal_range", "likely_kcal", "macro_candidate"],
                },
            ],
            "exact_seed_policy": "empty_for_real_runtime_in_this_slice",
        },
        "runtime_trace_parity": {
            "status": "not_applicable",
            "required_core_fields_match": True,
            "extra_fields_allowed": True,
            "renamed_core_fields_allowed": False,
            "missing_core_fields_allowed": False,
        },
        "non_scope": {
            "autonomous_nutrition_subagent": False,
            "independent_llm_evidence_normalizer": False,
            "full_macro_engine": False,
            "nutrition_accuracy_production_ready_claim": False,
        },
    }


def write_phase_b2_synthetic_smoke_report(
    *,
    output_dir: Path | None = None,
    stable_output_path: Path | None = None,
    b1_readiness_artifact_path: Path | None = None,
) -> dict[str, str]:
    output_dir = output_dir or DEFAULT_OUTPUT_DIR
    stable_path = stable_output_path or DEFAULT_STABLE_OUTPUT
    timestamped_path = output_dir / f"wave1_phase_b2_evidence_synthesis_smoke_{_utc_stamp()}.json"

    report = build_phase_b2_synthetic_smoke_report(
        b1_green_handoff_snapshot=build_b1_green_handoff_snapshot(readiness_artifact_path=b1_readiness_artifact_path)
    )
    report["artifact_paths"] = {
        "stable_latest": _project_relative(stable_path),
        "timestamped": _project_relative(timestamped_path),
    }

    _write_json(timestamped_path, report)
    _write_json(stable_path, report)
    return {
        "stable_output_path": str(stable_path),
        "timestamped_output_path": str(timestamped_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the official Wave 1 Phase B-2 synthetic smoke artifact.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--stable-output", default=str(DEFAULT_STABLE_OUTPUT))
    parser.add_argument("--b1-readiness-artifact", default=str(DEFAULT_B1_READINESS_ARTIFACT))
    args = parser.parse_args()

    outputs = write_phase_b2_synthetic_smoke_report(
        output_dir=Path(args.output_dir),
        stable_output_path=Path(args.stable_output),
        b1_readiness_artifact_path=Path(args.b1_readiness_artifact),
    )
    print(json.dumps(_json_safe(outputs), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
