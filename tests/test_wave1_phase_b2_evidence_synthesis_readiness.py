from __future__ import annotations

import copy
import json
from pathlib import Path

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
    return _write_json(
        tmp_path / "phase_b2_report.json",
        {
            "phase": "B2",
            "mode": "evidence_synthesis_gate",
            "smoke_cases_run": SMOKE_CASES,
            "cases": cases,
            "trusted_source_manifest": {
                "entries": [
                    {
                        "source_id": "taiwan_food_trusted_reference",
                        "source_quality_label": "trusted_database",
                        "approved": True,
                        "scope": "B-2 synthetic trusted database fixture",
                    }
                ]
            },
            "trusted_database_policy": {
                "allowlist": ["taiwan_food_trusted_reference"],
                "approved": True,
            },
            "minimal_db_seed_manifest": {
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
        },
    )


def invalid_phase_b2_report_fixture(tmp_path: Path, mutator) -> Path:
    path = valid_phase_b2_report_fixture(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    mutator(data)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def test_valid_phase_b2_evidence_synthesis_fixture_is_ready(tmp_path: Path) -> None:
    report = verify_phase_b2_readiness(phase_b2_report_path=valid_phase_b2_report_fixture(tmp_path))

    assert report["ready_for_phase_b2_implementation"] is True
    assert report["blockers"] == []
    assert report["recommended_next_steps_ordered"] == ["proceed_to_phase_b2_evidence_synthesis_implementation"]


def test_packet_missing_packet_id_blocks_readiness(tmp_path: Path) -> None:
    phase_b2 = invalid_phase_b2_report_fixture(tmp_path, lambda data: data["cases"][0]["packets"][0].pop("packet_id"))

    report = verify_phase_b2_readiness(phase_b2_report_path=phase_b2)

    assert any(item["code"] == "packet_contract_missing_required_field" for item in report["blockers"])


def test_generic_db_marked_exact_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        data["cases"][0]["packets"][0]["match_type"] = "exact"

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "generic_db_marked_exact" for item in report["blockers"])


def test_tavily_snippet_used_as_final_truth_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        data["cases"][5]["packets"][0]["final_kcal"] = 650

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "packet_final_truth_present" for item in report["blockers"])


def test_sibling_variant_used_as_exact_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        item = data["cases"][8]["manager_pass_2"]["item_results"][0]
        packet = data["cases"][8]["packets"][0]
        item["exactness_posture"] = "exact"
        item["evidence_confidence"] = "strong"
        item["evidence_used"] = [_evidence(packet, usage="exact")]
        item["rejected_candidates"] = []

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "sibling_variant_used_as_exact" for item in report["blockers"])


def test_evidence_used_missing_packet_id_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        data["cases"][0]["manager_pass_2"]["item_results"][0]["evidence_used"][0].pop("packet_id")

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "evidence_used_missing_packet_ref" for item in report["blockers"])


def test_rejected_sibling_candidate_missing_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        data["cases"][8]["manager_pass_2"]["item_results"][0]["rejected_candidates"] = []

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "sibling_candidate_not_rejected_or_downgraded" for item in report["blockers"])


def test_taiwan_skill_kcal_macro_portion_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        data["cases"][3]["packets"][0]["kcal_range"] = [300, 900]

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "taiwan_skill_contains_nutrition_truth" for item in report["blockers"])


def test_all_web_extract_blocks_readiness(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        data["cases"][5]["extract_policy"] = {
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
        data["cases"][1]["renderer"]["input"]["allowed_facts"] = ["估算"]
        data["cases"][1]["renderer"]["final_response"] = "資料顯示這杯是 999 大卡。"

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
        packet = data["cases"][0]["packets"][0]
        packet["source_quality_label"] = "trusted_database"
        packet["source_id"] = "unresolved_trusted_source"
        data["trusted_database_policy"] = {"allowlist": [], "approved": True}

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert any(item["code"] == "trusted_database_source_unresolved" for item in report["blockers"])


def test_trusted_database_with_approved_manifest_entry_passes(tmp_path: Path) -> None:
    def mutate(data: dict[str, object]) -> None:
        packet = data["cases"][0]["packets"][0]
        packet["source_quality_label"] = "trusted_database"
        packet["source_id"] = "taiwan_food_trusted_reference"

    report = verify_phase_b2_readiness(phase_b2_report_path=invalid_phase_b2_report_fixture(tmp_path, mutate))

    assert report["ready_for_phase_b2_implementation"] is True
    assert not any(item["code"] == "trusted_database_source_unresolved" for item in report["blockers"])


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
        data["cases"][1]["packets"].append(llm_packet)
        data["cases"][1]["manager_pass_2"]["item_results"][0]["evidence_used"].append(_evidence(llm_packet, usage="fallback"))

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
        data["cases"][1]["packets"].append(llm_packet)
        item = data["cases"][1]["manager_pass_2"]["item_results"][0]
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

    assert report["ready_for_phase_b2_implementation"] is True


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
