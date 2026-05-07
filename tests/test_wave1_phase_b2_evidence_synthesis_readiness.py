from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import scripts.build_wave1_phase_b2_evidence_synthesis_smoke as phase_b2_builder
from scripts.build_wave1_phase_b2_evidence_synthesis_smoke import (
    build_phase_b2_synthetic_smoke_report,
    write_phase_b2_synthetic_smoke_report,
)
from scripts.verify_wave1_phase_b2_evidence_synthesis_readiness import verify_phase_b2_readiness


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


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _b1_green_handoff_snapshot() -> dict[str, object]:
    return {
        "b1_gate_scope": "Phase B-1 minimal tool-loop full natural-probe",
        "smoke_artifact": "artifacts/phase_b1_full_smoke.json",
        "readiness_artifact": "artifacts/phase_b1_readiness.json",
        "ready_for_phase_b1_implementation": True,
        "blockers": [],
        "not_claiming": "whole Wave 1 completion",
    }


def _cache() -> dict[str, object]:
    return {
        "cache_key": None,
        "cache_hit": None,
        "cache_policy": None,
        "unavailable_reason": "cache_not_implemented_in_b2_gate",
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


def _case(
    case_id: str,
    input_message: str,
    packets: list[dict[str, object]],
    item_results: list[dict[str, object]],
    *,
    mutation: dict[str, object] | None = None,
    final_response: str = "已根據 renderer input 回覆。",
    extract_policy: dict[str, object] | None = None,
) -> dict[str, object]:
    mutation = mutation or _mutation(
        attempted=True,
        reason="guard_approved_logging",
        result={"truth_level": "mutation_result", "ledger_item_ids": [f"item_{case_id}"]},
    )
    renderer_input = {
        "allowed_facts": ["估算", "先記一筆粗估", "資料顯示", "缺少滷味品項"],
        "forbidden_claims": ["facts outside item_results", "unsupported exact kcal"],
        "item_results": item_results,
        "ledger_mutation_result": mutation["mutation_result"],
    }
    return {
        "case_id": case_id,
        "input_message": input_message,
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


def valid_phase_b2_report_fixture(tmp_path: Path) -> Path:
    return _write_json(
        tmp_path / "phase_b2_report.json",
        build_phase_b2_synthetic_smoke_report(b1_green_handoff_snapshot=_b1_green_handoff_snapshot()),
    )


def invalid_phase_b2_report_fixture(tmp_path: Path, mutator) -> Path:
    path = valid_phase_b2_report_fixture(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    mutator(data)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _case_by_id(report: dict[str, object], case_id: str) -> dict[str, object]:
    return next(case for case in report["cases"] if case["case_id"] == case_id)


def test_valid_phase_b2_evidence_synthesis_fixture_is_ready_with_manager_semantics(tmp_path: Path) -> None:
    report = verify_phase_b2_readiness(phase_b2_report_path=valid_phase_b2_report_fixture(tmp_path))

    assert report["ready_for_phase_b2_implementation"] is True
    assert report["blockers"] == []
    assert report["recommended_next_steps_ordered"] == ["proceed_to_phase_b2_evidence_synthesis_implementation"]
    assert report["honesty_gate_status"] == {
        "snippet_final_truth_blocked": True,
        "wrong_item_blocked": True,
        "sibling_variant_blocked": True,
        "wrong_size_blocked": True,
        "wrong_modifier_blocked": True,
        "insufficient_evidence_blocked": True,
    }
    assert report["b1_green_handoff_check"]["passed"] is True
    assert report["semantic_owner_integrity"]["passed"] is True
    assert report["readiness_claim"]["producer_honesty"]["runner_inferred_semantics"] is False
    assert report["readiness_claim"]["semantic_authority_source"] == "synthetic_manager_structured_fixture"
    assert report["readiness_claim"]["producer_honesty"]["fake_provider_simulated_manager"] is False
    audit = report["artifact_completeness_audit"]
    assert audit["passed"] is True
    assert audit["chain_complete"] is True
    assert audit["required_chain_nodes"] == [
        "manager_semantic_fixture",
        "retrieval_intent_source",
        "source_selection",
        "candidate_packets",
        "exact_hard_recheck",
        "packet_consumption",
        "synthesis_item_results",
        "final_mapping",
        "readiness_summary",
    ]
    assert audit["rejected_packet_evidence_ref_violations"] == []
    assert audit["source_selection_semantic_owner_violations"] == []
    assert audit["packet_consumption_trace_violations"] == []
    assert audit["producer_final_mapping_owner_violations"] == []
    assert audit["strict_exact_estimability_violations"] == []
    assert audit["pending_policy_promotions"] == []


def test_semantic_owner_inversion_still_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        data["semantic_owner_integrity"] = {
            "status": "blocked",
            "failure_family": "semantic_owner_inversion",
            "detail": "raw user text drove retrieval intent",
        }

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert report["ready_for_phase_b2_implementation"] is False
    assert any(item["code"] == "semantic_owner_inversion" for item in report["blockers"])


def test_official_b2_producer_does_not_use_raw_text_retrieval_intent(monkeypatch) -> None:
    def fail_raw_builder(*args: object, **kwargs: object) -> None:
        raise AssertionError("official B2 producer must consume manager semantic decisions")

    if hasattr(phase_b2_builder, "build_retrieval_intent"):
        monkeypatch.setattr(phase_b2_builder, "build_retrieval_intent", fail_raw_builder)

    report = build_phase_b2_synthetic_smoke_report(b1_green_handoff_snapshot=_b1_green_handoff_snapshot())

    assert report["semantic_owner_integrity"] == {
        "status": "pass",
        "semantic_authority_source": "synthetic_manager_structured_fixture",
        "runner_inferred_semantics": False,
    }
    assert all(case["retrieval_intent_source"] == "manager_semantic_decision" for case in report["cases"])
    assert all(case["runner_inferred_semantics"] is False for case in report["cases"])
    assert all(
        case["manager_semantic_decision"]["semantic_authority_source"] == "synthetic_manager_structured_fixture"
        for case in report["cases"]
    )
    assert all(case["packet_consumption"]["owner"] == "evidence_packet_consumption" for case in report["cases"])
    assert all(
        set(case["packet_consumption"]["consumed_packet_ids"]).issubset({packet["packet_id"] for packet in case["packets"]})
        for case in report["cases"]
    )


def test_missing_manager_semantic_fixture_blocks_handoff_audit(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        _case_by_id(data, "B2-001").pop("manager_semantic_decision")

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "artifact_completeness_audit_failed" for item in report["blockers"])
    assert {"case_id": "B2-001", "node": "manager_semantic_fixture"} in report["artifact_completeness_audit"][
        "missing_chain_nodes"
    ]


def test_raw_text_retrieval_intent_source_blocks_handoff_audit(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        _case_by_id(data, "B2-001")["retrieval_intent_source"] = "raw_text"

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "artifact_completeness_audit_failed" for item in report["blockers"])
    assert {"case_id": "B2-001", "node": "retrieval_intent_source"} in report["artifact_completeness_audit"][
        "missing_chain_nodes"
    ]


def test_raw_text_retrieval_intent_builder_is_not_official_b2_readiness_truth() -> None:
    root = Path(__file__).resolve().parents[1]
    allowed_paths = {
        Path("app/nutrition/application/exact_brand_web_canary.py"),
        Path("app/nutrition/application/retrieval_intent.py"),
    }
    raw_builder_call = re.compile(r"\bbuild_retrieval_intent\(")
    findings: list[str] = []
    for folder in (root / "app", root / "scripts"):
        for path in folder.rglob("*.py"):
            relative = path.relative_to(root)
            if relative in allowed_paths:
                continue
            text = path.read_text(encoding="utf-8")
            for line_number, line in enumerate(text.splitlines(), start=1):
                if raw_builder_call.search(line):
                    findings.append(f"{relative.as_posix()}:{line_number}")

    assert findings == []


def test_missing_packet_consumption_trace_blocks_handoff_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        _case_by_id(data, "B2-001").pop("packet_consumption")

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert report["ready_for_phase_b2_implementation"] is False
    assert any(item["code"] == "packet_consumption_trace_missing" for item in report["blockers"])
    assert report["artifact_completeness_audit"]["packet_consumption_trace_violations"][0] == {
        "case_id": "B2-001",
        "reason": "missing",
    }


def test_artifact_completeness_audit_flags_rejected_packet_used_as_evidence(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        case = _case_by_id(data, "B2-009")
        packet = case["packets"][0]
        item = case["manager_pass_2"]["item_results"][0]
        item["evidence_used"] = [_evidence(packet, usage="fallback")]

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    audit = report["artifact_completeness_audit"]
    assert audit["passed"] is False
    assert audit["rejected_packet_evidence_ref_violations"][0]["case_id"] == "B2-009"


def test_artifact_completeness_audit_flags_strict_exact_as_estimability_blocker(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        rejected = _case_by_id(data, "B2-009")["manager_pass_2"]["item_results"][0]["rejected_candidates"][0]
        rejected["estimability_blocked"] = True

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    audit = report["artifact_completeness_audit"]
    assert audit["passed"] is False
    assert audit["strict_exact_estimability_violations"][0]["case_id"] == "B2-009"


def test_official_b2_producer_uses_runtime_path_for_runtime_backed_generic_cases() -> None:
    report = build_phase_b2_synthetic_smoke_report(b1_green_handoff_snapshot=_b1_green_handoff_snapshot())

    tea_egg = _case_by_id(report, "B2-001")
    assert tea_egg["source_selection"] == {
        "source_path": "generic_anchor",
        "evidence_required": "generic_anchor_packet",
        "reason": "generic_intent_uses_local_generic_anchor",
        "web_allowed": False,
        "read_only": False,
        "mutation_allowed": True,
        "decides_logged_or_draft": False,
        "product_policy_status": "source_selection_only",
    }
    assert tea_egg["producer_trace"] == {
        "backing_class": "runtime_backed",
        "support_basis": "generic_anchor",
        "compatibility_reason": None,
    }
    assert tea_egg["packets"][0]["raw_ref"].startswith("app/knowledge/small_anchor_store_tw.json#")
    assert tea_egg["packets"][0]["packet_id"].startswith("pkt_generic_anchor_")
    tea_egg_item = tea_egg["manager_pass_2"]["item_results"][0]
    assert tea_egg_item["food_name"] == "茶葉蛋"
    assert tea_egg_item["exactness_posture"] == "estimated"
    assert tea_egg_item["evidence_confidence"] == "strong"
    assert tea_egg_item["evidence_used"][0]["packet_id"] == tea_egg["packets"][0]["packet_id"]

    boba_query = _case_by_id(report, "B2-008")
    assert boba_query["source_selection"]["read_only"] is True
    assert boba_query["source_selection"]["mutation_allowed"] is False
    assert boba_query["source_selection"]["web_allowed"] is False
    assert boba_query["producer_trace"] == {
        "backing_class": "runtime_backed",
        "support_basis": "generic_anchor",
        "compatibility_reason": None,
    }
    assert boba_query["packets"][0]["raw_ref"].startswith("app/knowledge/small_anchor_store_tw.json#")
    assert boba_query["mutation"]["mutation_attempted"] is False
    boba_query_item = boba_query["manager_pass_2"]["item_results"][0]
    assert boba_query_item["food_name"] == "珍珠奶茶"
    assert boba_query_item["exactness_posture"] == "estimated"
    assert boba_query_item["evidence_confidence"] == "moderate"
    assert boba_query_item["evidence_used"][0]["packet_id"] == boba_query["packets"][0]["packet_id"]


def test_official_b2_producer_consumes_final_mapping_owner_for_ledger_status() -> None:
    report = build_phase_b2_synthetic_smoke_report(b1_green_handoff_snapshot=_b1_green_handoff_snapshot())

    boba = _case_by_id(report, "B2-002")["manager_pass_2"]["item_results"][0]
    assert boba["final_mapping"]["final_mapping_owner"] == "nutrition_final_mapping"
    assert boba["final_mapping"]["external_outcome"] == "logged"
    assert boba["final_mapping"]["followup_role"] == "precision_refinement"
    assert boba["ledger_status"] == boba["final_mapping"]["ledger_status"] == "included"

    luwei = _case_by_id(report, "B2-004")["manager_pass_2"]["item_results"][0]
    assert luwei["final_mapping"]["external_outcome"] == "draft"
    assert luwei["ledger_status"] == luwei["final_mapping"]["ledger_status"] == "excluded_pending_info"

    boba_query = _case_by_id(report, "B2-008")["manager_pass_2"]["item_results"][0]
    assert boba_query["final_mapping"]["external_outcome"] == "no_mutation_query"
    assert boba_query["ledger_status"] == boba_query["final_mapping"]["ledger_status"] == "not_applicable"


def test_official_b2_producer_keeps_taiwan_skill_compatibility_but_uses_runtime_clarify_output() -> None:
    report = build_phase_b2_synthetic_smoke_report(b1_green_handoff_snapshot=_b1_green_handoff_snapshot())

    luwei = _case_by_id(report, "B2-004")
    assert luwei["source_selection"]["source_path"] == "ask_user"
    assert luwei["source_selection"]["product_policy_status"] == "pending_or_provisional"
    assert luwei["source_selection"]["decides_logged_or_draft"] is False
    assert luwei["producer_trace"] == {
        "backing_class": "runtime_backed",
        "support_basis": "clarify_support",
        "compatibility_reason": None,
    }
    assert luwei["packets"][0]["source_type"] == "taiwan_skill"
    item = luwei["manager_pass_2"]["item_results"][0]
    assert item["food_name"] == "滷味"
    assert item["exactness_posture"] == "unresolved"
    assert item["evidence_confidence"] == "insufficient"
    assert item["kcal_range"] is None
    assert item["likely_kcal"] is None
    assert item["evidence_used"] == []
    assert item["ledger_status"] == "excluded_pending_info"


def test_official_b2_producer_uses_runtime_listed_item_fanout_for_b2_005() -> None:
    report = build_phase_b2_synthetic_smoke_report(b1_green_handoff_snapshot=_b1_green_handoff_snapshot())

    listed_items = _case_by_id(report, "B2-005")
    assert listed_items["producer_trace"] == {
        "backing_class": "runtime_backed",
        "support_basis": "listed_item_runtime_fanout",
        "compatibility_reason": None,
    }
    assert [item["food_name"] for item in listed_items["manager_pass_2"]["item_results"]] == ["豆干", "海帶", "貢丸"]
    assert all(str(packet["raw_ref"]).startswith("app/knowledge/small_anchor_store_tw.json#") for packet in listed_items["packets"])
    assert all(
        item["evidence_used"][0]["packet_id"] in {packet["packet_id"] for packet in listed_items["packets"]}
        for item in listed_items["manager_pass_2"]["item_results"]
    )
    assert listed_items["listed_item_fanout"]["resolutions"] == [
        {
            "listed_item": "豆干",
            "resolution_status": "resolved",
            "defer_reason": None,
            "clarify_support_present": False,
            "packet_ids": ["pkt_generic_anchor_listed_item_tofu_dried"],
        },
        {
            "listed_item": "海帶",
            "resolution_status": "resolved",
            "defer_reason": None,
            "clarify_support_present": False,
            "packet_ids": ["pkt_generic_anchor_listed_item_kelp"],
        },
        {
            "listed_item": "貢丸",
            "resolution_status": "resolved",
            "defer_reason": None,
            "clarify_support_present": False,
            "packet_ids": ["pkt_generic_anchor_listed_item_meatball"],
        },
    ]


def test_official_b2_producer_uses_runtime_selected_extract_lane_for_web_exact_positive_case() -> None:
    report = build_phase_b2_synthetic_smoke_report(b1_green_handoff_snapshot=_b1_green_handoff_snapshot())

    milkshop = _case_by_id(report, "B2-006")
    assert milkshop["producer_trace"] == {
        "backing_class": "runtime_backed",
        "support_basis": "selected_extract_exact_positive",
        "compatibility_reason": None,
    }
    search_packets = [packet for packet in milkshop["packets"] if packet["source_type"] == "web_search"]
    extract_packets = [packet for packet in milkshop["packets"] if packet["source_type"] == "web_extract"]
    assert len(search_packets) == 1
    assert len(extract_packets) == 1
    assert milkshop["extract_policy"] == {
        "selected_search_packet_id": search_packets[0]["packet_id"],
        "extract_reason": "selected_same_item_official_candidate",
        "extract_allowed_by_policy": True,
        "max_extract_urls": 1,
        "extract_count": 1,
    }
    item = milkshop["manager_pass_2"]["item_results"][0]
    assert item["food_name"] == "迷客夏 珍珠紅茶拿鐵"
    assert item["exactness_posture"] == "exact"
    assert item["evidence_used"][0]["usage"] == "exact"
    assert item["evidence_used"][0]["packet_id"] == extract_packets[0]["packet_id"]
    assert item["likely_kcal"] == 400.0
    assert item["rejected_candidates"] == []


def test_official_b2_producer_uses_exact_item_runtime_lane_for_matsuya_case() -> None:
    report = build_phase_b2_synthetic_smoke_report(b1_green_handoff_snapshot=_b1_green_handoff_snapshot())

    matsuya = _case_by_id(report, "B2-007")
    assert matsuya["producer_trace"] == {
        "backing_class": "runtime_backed",
        "support_basis": "exact_item_card",
        "compatibility_reason": None,
    }
    packet = matsuya["packets"][0]
    assert packet["raw_ref"].startswith("app/knowledge/exact_item_cards_tw.json#")
    assert packet["packet_id"].startswith("pkt_exact_item_")
    item = matsuya["manager_pass_2"]["item_results"][0]
    assert item["food_name"] == "松屋特盛牛丼"
    assert item["exactness_posture"] == "exact"
    assert item["evidence_used"][0]["usage"] == "exact"
    assert item["evidence_used"][0]["packet_id"] == packet["packet_id"]


def test_official_b2_producer_uses_runtime_web_rejection_for_sibling_case() -> None:
    report = build_phase_b2_synthetic_smoke_report(b1_green_handoff_snapshot=_b1_green_handoff_snapshot())

    sibling = _case_by_id(report, "B2-009")
    assert sibling["producer_trace"] == {
        "backing_class": "runtime_backed",
        "support_basis": "web_search_rejection",
        "compatibility_reason": None,
    }
    packet = sibling["packets"][0]
    assert packet["packet_id"].startswith("pkt_web_search_")
    item = sibling["manager_pass_2"]["item_results"][0]
    assert item["food_name"] == "迷客夏珍珠紅茶拿鐵"
    assert item["exactness_posture"] == "unresolved"
    assert item["likely_kcal"] is None
    assert item["evidence_used"] == []
    assert item["rejected_candidates"][0]["packet_id"] == packet["packet_id"]
    assert item["rejected_candidates"][0]["risk_type"] == "sibling_variant"


def test_official_b2_producer_uses_runtime_web_rejection_for_wrong_item_case() -> None:
    report = build_phase_b2_synthetic_smoke_report(b1_green_handoff_snapshot=_b1_green_handoff_snapshot())

    wrong_item = _case_by_id(report, "B2-010")
    assert wrong_item["producer_trace"] == {
        "backing_class": "runtime_backed",
        "support_basis": "web_search_rejection",
        "compatibility_reason": None,
    }
    packet = wrong_item["packets"][0]
    assert packet["packet_id"].startswith("pkt_web_search_")
    item = wrong_item["manager_pass_2"]["item_results"][0]
    assert item["food_name"] == "迷客夏珍珠紅茶拿鐵"
    assert item["exactness_posture"] == "unresolved"
    assert item["likely_kcal"] is None
    assert item["evidence_used"] == []
    assert item["rejected_candidates"][0]["packet_id"] == packet["packet_id"]
    assert item["rejected_candidates"][0]["risk_type"] == "wrong_item"


def test_packet_missing_packet_id_blocks_readiness(tmp_path: Path) -> None:
    phase_b2 = invalid_phase_b2_report_fixture(
        tmp_path,
        lambda data: _case_by_id(data, "B2-001")["packets"][0].pop("packet_id"),
    )

    report = verify_phase_b2_readiness(phase_b2_report_path=phase_b2)

    assert any(item["code"] == "packet_contract_missing_required_field" for item in report["blockers"])


def test_generic_db_marked_exact_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        _case_by_id(data, "B2-001")["packets"][0]["match_type"] = "exact"

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "generic_db_marked_exact" for item in report["blockers"])


def test_tavily_snippet_used_as_final_truth_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        _case_by_id(data, "B2-006")["packets"][0]["final_kcal"] = 650

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "packet_final_truth_present" for item in report["blockers"])


def test_sibling_variant_used_as_exact_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        case = _case_by_id(data, "B2-009")
        item = case["manager_pass_2"]["item_results"][0]
        packet = case["packets"][0]
        item["exactness_posture"] = "exact"
        item["evidence_confidence"] = "strong"
        item["evidence_used"] = [_evidence(packet, usage="exact")]
        item["rejected_candidates"] = []

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "sibling_variant_used_as_exact" for item in report["blockers"])


def test_wrong_item_used_as_exact_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        case = _case_by_id(data, "B2-010")
        item = case["manager_pass_2"]["item_results"][0]
        packet = case["packets"][0]
        item["exactness_posture"] = "exact"
        item["evidence_confidence"] = "strong"
        item["evidence_used"] = [_evidence(packet, usage="exact")]
        item["rejected_candidates"] = []

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "wrong_item_used_as_exact" for item in report["blockers"])


def test_wrong_size_used_as_exact_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        case = _case_by_id(data, "B2-007")
        item = case["manager_pass_2"]["item_results"][0]
        packet = case["packets"][0]
        packet["size_or_serving_match"] = "different"
        item["exactness_posture"] = "exact"
        item["evidence_confidence"] = "strong"
        item["evidence_used"] = [_evidence(packet, usage="exact")]

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "wrong_size_used_as_exact" for item in report["blockers"])


def test_wrong_modifier_used_as_exact_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        case = _case_by_id(data, "B2-006")
        item = case["manager_pass_2"]["item_results"][0]
        packet = case["packets"][0]
        packet["modifier_match"] = "different"
        item["exactness_posture"] = "exact"
        item["evidence_confidence"] = "strong"
        item["evidence_used"] = [_evidence(packet, usage="exact")]

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "wrong_modifier_used_as_exact" for item in report["blockers"])


def test_insufficient_evidence_used_as_exact_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        case = _case_by_id(data, "B2-007")
        item = case["manager_pass_2"]["item_results"][0]
        packet = case["packets"][0]
        packet["serving_basis"] = ""
        item["exactness_posture"] = "exact"
        item["evidence_confidence"] = "strong"
        item["evidence_used"] = [_evidence(packet, usage="exact")]

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "insufficient_evidence_used_as_exact" for item in report["blockers"])


def test_evidence_used_missing_packet_id_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        _case_by_id(data, "B2-001")["manager_pass_2"]["item_results"][0]["evidence_used"][0].pop("packet_id")

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "evidence_used_missing_packet_ref" for item in report["blockers"])


def test_missing_nutrition_final_mapping_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        _case_by_id(data, "B2-002")["manager_pass_2"]["item_results"][0].pop("final_mapping")

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "nutrition_final_mapping_missing" for item in report["blockers"])


def test_ledger_status_not_owned_by_nutrition_final_mapping_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        _case_by_id(data, "B2-002")["manager_pass_2"]["item_results"][0]["ledger_status"] = "excluded_pending_info"

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "nutrition_final_mapping_ledger_status_mismatch" for item in report["blockers"])


def test_unsupported_nutrition_final_mapping_external_outcome_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        _case_by_id(data, "B2-004")["manager_pass_2"]["item_results"][0]["final_mapping"][
            "external_outcome"
        ] = "unresolved"

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "nutrition_final_mapping_external_outcome_invalid" for item in report["blockers"])


def test_rejected_sibling_candidate_missing_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        _case_by_id(data, "B2-009")["manager_pass_2"]["item_results"][0]["rejected_candidates"] = []

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "sibling_candidate_not_rejected_or_downgraded" for item in report["blockers"])


def test_missing_producer_trace_blocks_readiness(tmp_path: Path) -> None:
    report = verify_phase_b2_readiness(
        phase_b2_report_path=invalid_phase_b2_report_fixture(
            tmp_path,
            lambda data: _case_by_id(data, "B2-001").pop("producer_trace"),
        )
    )

    assert any(item["code"] == "producer_trace_missing" for item in report["blockers"])


def test_missing_source_selection_blocks_readiness(tmp_path: Path) -> None:
    report = verify_phase_b2_readiness(
        phase_b2_report_path=invalid_phase_b2_report_fixture(
            tmp_path,
            lambda data: _case_by_id(data, "B2-001").pop("source_selection"),
        )
    )

    assert any(item["code"] == "source_selection_missing" for item in report["blockers"])


def test_source_selection_cannot_activate_web_or_decide_logged_draft(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        selection = _case_by_id(data, "B2-001")["source_selection"]
        selection["web_allowed"] = True
        selection["decides_logged_or_draft"] = True

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "source_selection_web_activation_forbidden" for item in report["blockers"])
    assert any(item["code"] == "source_selection_semantic_owner_forbidden" for item in report["blockers"])


def test_synthetic_producer_trace_without_reason_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        case = _case_by_id(data, "B2-001")
        case["producer_trace"]["backing_class"] = "synthetic_compatibility"
        case["producer_trace"]["compatibility_reason"] = None

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "producer_trace_synthetic_missing_reason" for item in report["blockers"])


def test_runtime_backed_producer_trace_with_reason_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        _case_by_id(data, "B2-001")["producer_trace"]["compatibility_reason"] = "should_not_exist"

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "producer_trace_runtime_backed_has_reason" for item in report["blockers"])


def test_listed_item_runtime_fanout_trace_missing_resolutions_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        _case_by_id(data, "B2-005")["listed_item_fanout"] = {"resolutions": []}

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "listed_item_fanout_trace_incomplete" for item in report["blockers"])


def test_listed_item_runtime_fanout_resolved_entry_without_packets_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        _case_by_id(data, "B2-005")["listed_item_fanout"]["resolutions"][0]["packet_ids"] = []

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "listed_item_fanout_trace_incomplete" for item in report["blockers"])


def test_web_search_mismatch_used_as_anchor_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        case = _case_by_id(data, "B2-010")
        packet = case["packets"][0]
        item = case["manager_pass_2"]["item_results"][0]
        item["exactness_posture"] = "estimated"
        item["evidence_confidence"] = "weak"
        item["evidence_used"] = [_evidence(packet, usage="anchor")]
        item["rejected_candidates"] = []

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "web_search_mismatch_used_as_anchor" for item in report["blockers"])


def test_runtime_selected_extract_case_missing_extract_policy_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        _case_by_id(data, "B2-006").pop("extract_policy")

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "extract_policy_trace_incomplete" for item in report["blockers"])


def test_runtime_selected_extract_case_citing_web_search_packet_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        case = _case_by_id(data, "B2-006")
        web_search_packet = next(packet for packet in case["packets"] if packet["source_type"] == "web_search")
        item = case["manager_pass_2"]["item_results"][0]
        item["evidence_used"][0]["packet_id"] = web_search_packet["packet_id"]
        item["evidence_used"][0]["source_type"] = "web_search"
        item["evidence_used"][0]["source_quality_label"] = web_search_packet["source_quality_label"]

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "selected_extract_exact_result_not_backed_by_web_extract" for item in report["blockers"])


def test_runtime_selected_extract_case_without_web_extract_packet_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        case = _case_by_id(data, "B2-006")
        case["packets"] = [packet for packet in case["packets"] if packet["source_type"] != "web_extract"]
        item = case["manager_pass_2"]["item_results"][0]
        item["evidence_used"] = []
        item["rejected_candidates"] = []

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "selected_extract_exact_positive_missing_web_extract_packet" for item in report["blockers"])


def test_taiwan_skill_kcal_macro_portion_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        _case_by_id(data, "B2-004")["packets"][0]["kcal_range"] = [300, 900]

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "taiwan_skill_contains_nutrition_truth" for item in report["blockers"])


def test_all_web_extract_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        _case_by_id(data, "B2-006")["extract_policy"] = {
            "selected_search_packet_id": "*",
            "extract_reason": "extract all search results",
            "extract_allowed_by_policy": True,
            "max_extract_urls": 1,
            "extract_count": 5,
        }

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "extract_policy_all_web_extract" for item in report["blockers"])


def test_renderer_exactness_wording_exceeds_renderer_input_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        case = _case_by_id(data, "B2-002")
        case["renderer"]["input"]["allowed_facts"] = ["估算"]
        case["renderer"]["final_response"] = "資料顯示這杯是 999 大卡。"

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "renderer_exactness_wording_exceeds_input" for item in report["blockers"])


def test_missing_smoke_case_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        data["smoke_cases_run"].remove("official_wrong_item_negative")

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "phase_b2_smoke_case_missing" for item in report["blockers"])


def test_spec_declares_b2_not_accuracy_ready() -> None:
    spec = Path("docs/specs/WAVE_1_PHASE_B2_EVIDENCE_AND_SYNTHESIS_GATE.md").read_text(encoding="utf-8-sig")

    assert "does not mean nutrition accuracy is production-ready" in spec


def test_trusted_database_without_resolvable_source_or_justification_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        packet = _case_by_id(data, "B2-001")["packets"][0]
        packet["source_quality_label"] = "trusted_database"
        packet["source_id"] = "unresolved_trusted_source"
        data["trusted_database_policy"] = {"allowlist": [], "approved": True}

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "trusted_database_source_unresolved" for item in report["blockers"])


def test_trusted_database_with_approved_manifest_entry_passes(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        packet = _case_by_id(data, "B2-001")["packets"][0]
        packet["source_quality_label"] = "trusted_database"
        packet["source_id"] = "taiwan_food_trusted_reference"

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert report["ready_for_phase_b2_implementation"] is True
    assert not any(item["code"] == "trusted_database_source_unresolved" for item in report["blockers"])
    assert not any(item["code"] == "semantic_owner_inversion" for item in report["blockers"])


def test_llm_prior_without_last_resort_rationale_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        llm_packet = {
            "packet_id": "pkt_llm_prior_boba",
            "packet_type": "LlmPriorPacket",
            "truth_level": "hint",
            "source_type": "llm_prior",
            "source_quality_label": "llm_prior",
            "raw_ref": "artifacts/raw/llm_prior_boba.json",
        }
        case = _case_by_id(data, "B2-002")
        case["packets"].append(llm_packet)
        case["manager_pass_2"]["item_results"][0]["evidence_used"].append(_evidence(llm_packet, usage="fallback"))

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "llm_prior_trace_missing" for item in report["blockers"])


def test_llm_prior_supporting_exact_claim_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        llm_packet = {
            "packet_id": "pkt_llm_prior_exact",
            "packet_type": "LlmPriorPacket",
            "truth_level": "hint",
            "source_type": "llm_prior",
            "source_quality_label": "llm_prior",
            "raw_ref": "artifacts/raw/llm_prior_exact.json",
        }
        data["llm_prior_trace"] = {
            "llm_prior_used": True,
            "why_no_better_evidence_available": "synthetic negative case",
            "exact_claim_allowed": True,
            "evidence_confidence": "strong",
        }
        case = _case_by_id(data, "B2-002")
        case["packets"].append(llm_packet)
        item = case["manager_pass_2"]["item_results"][0]
        item["exactness_posture"] = "exact"
        item["evidence_confidence"] = "strong"
        item["evidence_used"] = [_evidence(llm_packet, usage="exact")]

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "llm_prior_exact_claim_allowed" for item in report["blockers"])


def test_missing_minimal_db_seed_manifest_blocks_readiness(tmp_path: Path) -> None:
    phase_b2 = invalid_phase_b2_report_fixture(tmp_path, lambda data: data.pop("minimal_db_seed_manifest"))

    report = verify_phase_b2_readiness(phase_b2_report_path=phase_b2)

    assert any(item["code"] == "minimal_db_seed_manifest_missing" for item in report["blockers"])


def test_generic_seed_containing_brand_exact_fields_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        data["minimal_db_seed_manifest"]["seeds"][0]["allowed_fields"].append("brand_name")
        data["minimal_db_seed_manifest"]["seeds"][0]["source_quality_label"] = "internal_exact"

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "minimal_db_seed_contains_exact_truth" for item in report["blockers"])


def test_extra_non_smoke_seed_blocks_unless_fixture_only_or_out_of_scope(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        data["minimal_db_seed_manifest"]["seeds"].append(
            {
                "food_name": "品牌限定雞腿便當",
                "seed_type": "generic",
                "used_by_smoke_case": "not_a_smoke_case",
                "fixture_only": False,
                "allowed_fields": ["kcal_range", "likely_kcal"],
            }
        )

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "minimal_db_seed_outside_smoke_scope" for item in report["blockers"])


def test_runtime_trace_parity_allows_extra_metadata_fields(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        data["runtime_trace_parity"] = {
            "status": "checked",
            "required_core_fields_match": True,
            "extra_fields_allowed": True,
            "renamed_core_fields_allowed": False,
            "missing_core_fields_allowed": False,
            "runtime_extra_fields": ["provider_latency_ms", "tool_call_count"],
        }

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert report["runtime_trace_parity"]["passed"] is True
    assert report["ready_for_phase_b2_implementation"] is True
    assert not any(item["code"] == "semantic_owner_inversion" for item in report["blockers"])


def test_runtime_trace_parity_renamed_or_missing_core_fields_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        data["runtime_trace_parity"] = {
            "status": "checked",
            "required_core_fields_match": False,
            "extra_fields_allowed": True,
            "renamed_core_fields_allowed": True,
            "missing_core_fields_allowed": True,
        }

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "runtime_trace_parity_failed" for item in report["blockers"])


def test_b1_green_handoff_snapshot_missing_blocks_readiness(tmp_path: Path) -> None:
    report = verify_phase_b2_readiness(
        phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, lambda data: data.pop("b1_green_handoff_snapshot"))
    )

    assert any(item["code"] == "b1_green_handoff_snapshot_missing" for item in report["blockers"])


def test_official_phase_b2_synthetic_producer_writes_latest_and_timestamped_artifacts(tmp_path: Path) -> None:
    b1_readiness = _write_json(
        tmp_path / "wave1_phase_b_minimal_tool_loop_readiness.json",
        {
            "ready_for_phase_b1_implementation": True,
            "blockers": [],
            "phase_b_report_path": "artifacts/phase_b1_full_smoke.json",
        },
    )
    outputs = write_phase_b2_synthetic_smoke_report(
        output_dir=tmp_path,
        stable_output_path=tmp_path / "wave1_phase_b2_evidence_synthesis_smoke.json",
        b1_readiness_artifact_path=b1_readiness,
    )

    stable_path = Path(outputs["stable_output_path"])
    timestamped_path = Path(outputs["timestamped_output_path"])
    assert stable_path.exists()
    assert timestamped_path.exists()
    assert stable_path.read_text(encoding="utf-8") == timestamped_path.read_text(encoding="utf-8")

    report = verify_phase_b2_readiness(phase_b2_report_path=stable_path)
    assert report["ready_for_phase_b2_implementation"] is True
    assert report["blockers"] == []
