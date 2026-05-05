from __future__ import annotations

import time
from urllib.parse import urlparse

from app.shared.contracts.readiness_claim import build_readiness_claim

from .evidence_packet_consumption import EvidencePacketConsumptionResult
from .web_search_port import WebSearchPort

LANE_ID = "live_exact_brand_web_canary_v1"


def default_trace() -> dict[str, object]:
    return {
        "lane_id": LANE_ID,
        "attempted": False,
        "readiness_claimed": False,
        "readiness_claim": build_readiness_claim(
            claim_scope="unit_contract",
            activation_stage="contract",
            semantic_authority_source="deterministic_validator",
            producer_honesty={
                "runner_inferred_semantics": False,
                "fake_provider_simulated_manager": False,
                "final_mapping_fabricated": False,
                "mutation_fabricated": False,
            },
            evidence_lineage={
                "artifacts": [],
                "producers": ["app/nutrition/application/exact_brand_web_canary_trace.py"],
                "trace_only": True,
                "legacy_oracle_used": False,
            },
            allowed_next_stage=None,
            forbidden_claims=["product_ready", "user_facing_ready", "mutation_ready", "production_ready"],
            readiness_claimed=False,
        ),
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
        "raw_text_retrieval_hint_goal": None,
        "semantic_authority_source": None,
        "exact_db_miss_confirmed": False,
        "truth_boundary": {
            "trace_only": True,
            "runtime_web_diagnostic_enabled": False,
            "web_candidate_truth_authority": False,
            "accepted_extract_packet_truth_authority": False,
            "requires_packetizer_hard_recheck_consumption": True,
            "requires_synthesis_verifier": True,
            "runtime_web_activation_recommended": False,
        },
    }


def provider_profile(search_port: WebSearchPort | None) -> dict[str, object]:
    if search_port is None:
        return {"search_port": None, "trace_only": True}
    readiness = getattr(search_port, "readiness", None)
    profile = readiness() if callable(readiness) else {}
    return {
        "search_port": type(search_port).__name__,
        "trace_only": True,
        **(profile if isinstance(profile, dict) else {}),
    }


def search_candidate_trace(packet: dict[str, object]) -> dict[str, object]:
    risks = [str(risk).strip() for risk in packet.get("hard_recheck_risks", []) if str(risk).strip()]
    accepted_for_recheck = packet.get("supports_exact_claim") is True and not risks
    return {
        "packet_id": packet.get("packet_id"),
        "candidate_identity": packet.get("canonical_name"),
        "source_url": packet.get("url"),
        "source_domain": urlparse(str(packet.get("url") or "")).netloc.lower(),
        "source_title": packet.get("title"),
        "source_snippet": packet.get("snippet"),
        "source_quality_label": packet.get("source_quality_label"),
        "officialness_hint": packet.get("officialness_hint"),
        "license_status": packet.get("license_status"),
        "robots_status": packet.get("robots_status"),
        "identity_confidence": packet.get("identity_confidence"),
        "serving_basis_candidate": packet.get("serving_basis_candidate"),
        "nutrition_fields_present": list(packet.get("nutrition_fields_present") or []),
        "match_type": packet.get("match_type"),
        "brand_match": packet.get("brand_match"),
        "size_or_serving_match": packet.get("size_or_serving_match"),
        "modifier_match": packet.get("modifier_match"),
        "sibling_variant_risk": packet.get("sibling_variant_risk"),
        "hard_recheck_verdict": "accepted_for_exact_recheck" if accepted_for_recheck else "rejected_by_hard_recheck",
        "accepted_usage": None,
        "rejected_risk": risks[0] if risks else None,
    }


def packet_consumption_trace(consumption: EvidencePacketConsumptionResult) -> dict[str, object]:
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


def synthesis_evidence_refs(manager_pass_2: dict[str, object]) -> list[str]:
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


def elapsed_ms(start: float) -> int:
    return int(round((time.perf_counter() - start) * 1000))


__all__ = [
    "LANE_ID",
    "default_trace",
    "elapsed_ms",
    "packet_consumption_trace",
    "provider_profile",
    "search_candidate_trace",
    "synthesis_evidence_refs",
]
