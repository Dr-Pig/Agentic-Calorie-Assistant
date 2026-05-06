from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .evidence_candidate_packetizer import add_hard_recheck_metadata
from .retrieval_intent import RetrievalIntent
from .web_search_packetizer import build_web_search_candidate_packet


WEBSEARCH_TRUTH_FIELD_DENYLIST = frozenset(
    {
        "accepted_usage",
        "exactness_posture",
        "final_truth",
        "kcal_range",
        "likely_kcal",
        "primary_source",
        "runtime_truth_allowed",
    }
)


@dataclass(frozen=True)
class WebSearchCandidateSmokeCase:
    case_id: str
    intent: RetrievalIntent
    candidate: dict[str, object]
    expected_boundary: str


def build_websearch_candidate_packet_smoke(
    cases: tuple[WebSearchCandidateSmokeCase, ...] = (),
) -> dict[str, Any]:
    smoke_cases = cases or _default_cases()
    case_results = [_case_result(case) for case in smoke_cases]
    return {
        "artifact_type": "accurate_intake_websearch_candidate_packet_smoke",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "claim_scope": "deterministic_websearch_candidate_packet_boundary",
        "live_websearch_used": False,
        "live_provider_used": False,
        "runtime_truth_changed": False,
        "websearch_runtime_truth_allowed": False,
        "manager_context_changed": False,
        "runtime_packetizer_contract_changed": False,
        "cases": case_results,
        "summary": {
            "case_count": len(case_results),
            "candidate_only_count": sum(
                1 for case in case_results if case["candidate_boundary"]["candidate_only"] is True
            ),
            "runtime_truth_allowed_count": sum(
                1 for case in case_results if case["candidate_boundary"]["runtime_truth_allowed"] is True
            ),
            "live_websearch_used": False,
            "snippet_truth_allowed": False,
        },
        "non_claims": [
            "no_live_websearch_call",
            "no_live_provider_call",
            "no_websearch_runtime_truth",
            "no_runtime_truth_promotion",
            "no_manager_context_change",
            "no_readiness_claim",
        ],
    }


def _case_result(case: WebSearchCandidateSmokeCase) -> dict[str, Any]:
    packet = build_web_search_candidate_packet(case.intent, case.candidate)
    rechecked = add_hard_recheck_metadata(packet)
    boundary = derive_websearch_candidate_boundary(packet)
    return {
        "case_id": case.case_id,
        "expected_boundary": case.expected_boundary,
        "websearch_candidate_packet": packet,
        "hard_recheck": {
            "supports_exact_claim": rechecked.get("supports_exact_claim") is True,
            "hard_recheck_risks": list(rechecked.get("hard_recheck_risks") or []),
        },
        "candidate_boundary": boundary,
    }


def derive_websearch_candidate_boundary(packet: dict[str, object]) -> dict[str, object]:
    truth_field_violations = sorted(key for key in WEBSEARCH_TRUTH_FIELD_DENYLIST if key in packet)
    truth_level = str(packet.get("truth_level") or "").strip()
    source_type = str(packet.get("source_type") or "").strip()
    candidate_only = (
        truth_level == "candidate"
        and source_type == "web_search"
        and not truth_field_violations
    )
    return {
        "candidate_only": candidate_only,
        "runtime_truth_allowed": False,
        "snippet_truth_allowed": False,
        "requires_later_promotion_path": True,
        "truth_field_violations": truth_field_violations,
    }


def _default_cases() -> tuple[WebSearchCandidateSmokeCase, ...]:
    exact_intent = _intent(
        base_dish="pearl black tea latte",
        alias="Milksha pearl black tea latte",
        brand_hint="Milksha",
    )
    starbucks_intent = _intent(
        base_dish="iced latte",
        alias="Starbucks iced latte large",
        brand_hint="Starbucks",
        size_hint="large",
    )
    convenience_store_intent = _intent(
        base_dish="salmon rice ball",
        alias="7-Eleven salmon rice ball",
        brand_hint="7-Eleven",
    )
    chain_restaurant_intent = _intent(
        base_dish="gyudon",
        alias="Matsuya gyudon large",
        brand_hint="Matsuya",
        size_hint="large",
    )
    return (
        WebSearchCandidateSmokeCase(
            case_id="official_exact_candidate",
            intent=exact_intent,
            candidate=_candidate(
                candidate_id="web_search_candidate:milksha_exact",
                title="Milksha pearl black tea latte",
                url="https://milksha.example/menu/pearl-black-tea-latte",
                query="Milksha pearl black tea latte",
                brand_detected="Milksha",
                identity_confidence="high",
                raw_ref="raw/websearch/milksha_exact.json#0",
            ),
            expected_boundary="candidate_only_even_if_exact_support",
        ),
        WebSearchCandidateSmokeCase(
            case_id="same_brand_sibling_candidate",
            intent=exact_intent,
            candidate=_candidate(
                candidate_id="web_search_candidate:milksha_sibling",
                title="Milksha pearl fresh milk tea",
                url="https://milksha.example/menu/pearl-fresh-milk-tea",
                query="Milksha pearl black tea latte",
                brand_detected="Milksha",
                identity_confidence="medium",
                raw_ref="raw/websearch/milksha_sibling.json#0",
            ),
            expected_boundary="candidate_only_sibling_rejected_by_hard_recheck",
        ),
        WebSearchCandidateSmokeCase(
            case_id="third_party_weak_candidate",
            intent=exact_intent,
            candidate=_candidate(
                candidate_id="web_search_candidate:third_party_weak",
                title="Milksha pearl black tea latte calories",
                url="https://third-party.example/milksha",
                query="Milksha pearl black tea latte",
                brand_detected="Milksha",
                officialness_hint="unknown",
                source_quality_hint="low",
                identity_confidence="high",
                raw_ref="raw/websearch/third_party_weak.json#0",
            ),
            expected_boundary="candidate_only_third_party_not_truth",
        ),
        WebSearchCandidateSmokeCase(
            case_id="wrong_size_candidate",
            intent=starbucks_intent,
            candidate=_candidate(
                candidate_id="web_search_candidate:starbucks_wrong_size",
                title="Starbucks iced latte medium",
                url="https://starbucks.example/menu/iced-latte-medium",
                query="Starbucks iced latte large",
                brand_detected="Starbucks",
                identity_confidence="high",
                raw_ref="raw/websearch/starbucks_wrong_size.json#0",
            ),
            expected_boundary="candidate_only_wrong_size_rejected_by_hard_recheck",
        ),
        WebSearchCandidateSmokeCase(
            case_id="convenience_store_exact_candidate",
            intent=convenience_store_intent,
            candidate=_candidate(
                candidate_id="web_search_candidate:seven_eleven_salmon_rice_ball",
                title="7-Eleven salmon rice ball",
                url="https://7-11.example/products/salmon-rice-ball",
                query="7-Eleven salmon rice ball",
                brand_detected="7-Eleven",
                serving_basis_candidate="per_piece",
                identity_confidence="high",
                raw_ref="raw/websearch/seven_eleven_salmon_rice_ball.json#0",
            ),
            expected_boundary="candidate_only_packaged_exact_support",
        ),
        WebSearchCandidateSmokeCase(
            case_id="chain_restaurant_exact_candidate",
            intent=chain_restaurant_intent,
            candidate=_candidate(
                candidate_id="web_search_candidate:matsuya_gyudon_large",
                title="Matsuya gyudon large",
                url="https://matsuya.example/menu/gyudon-large",
                query="Matsuya gyudon large",
                brand_detected="Matsuya",
                serving_basis_candidate="per_bowl",
                identity_confidence="high",
                raw_ref="raw/websearch/matsuya_gyudon_large.json#0",
            ),
            expected_boundary="candidate_only_chain_menu_exact_support",
        ),
    )


def _intent(
    *,
    base_dish: str,
    alias: str,
    brand_hint: str | None = None,
    size_hint: str | None = None,
) -> RetrievalIntent:
    return RetrievalIntent(
        base_dish=base_dish,
        aliases=[alias],
        brand_hint=brand_hint,
        size_hint=size_hint,
        modifier_hints=[],
        listed_items=[],
        retrieval_goal="exact_brand_lookup",
    )


def _candidate(
    *,
    candidate_id: str,
    title: str,
    url: str,
    query: str,
    brand_detected: str = "",
    officialness_hint: str = "official",
    source_quality_hint: str = "high",
    snippet: str = "official menu result",
    score: float = 0.93,
    serving_basis_candidate: str = "per_cup",
    identity_confidence: str = "medium",
    applicability_confidence: str = "medium",
    raw_ref: str = "raw/websearch/test.json#0",
) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "source_type": "web_search",
        "source_url": url,
        "source_domain": "example.test",
        "source_title": title,
        "snippet": snippet,
        "query": query,
        "identity_target": query,
        "score": score,
        "source_quality_hint": source_quality_hint,
        "officialness_hint": officialness_hint,
        "brand_detected": brand_detected,
        "channel_detected": "handmade_foodservice",
        "serving_basis_candidate": serving_basis_candidate,
        "nutrition_fields_present": ["kcal"],
        "customization_slots_present": ["size"],
        "identity_confidence": identity_confidence,
        "applicability_confidence": applicability_confidence,
        "applicability_notes": "fixture candidate",
        "raw_ref": raw_ref,
    }


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "WEBSEARCH_TRUTH_FIELD_DENYLIST",
    "WebSearchCandidateSmokeCase",
    "build_websearch_candidate_packet_smoke",
    "derive_websearch_candidate_boundary",
]
