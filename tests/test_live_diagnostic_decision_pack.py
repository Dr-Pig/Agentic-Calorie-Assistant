from __future__ import annotations

from scripts.live_diagnostic_decision_pack import (
    B2_ASK_FIRST_POLICY_VIOLATION,
    B2_EMPTY_ITEM_RESULTS,
    VERDICT_DIAGNOSTIC_OBSERVATION,
    VERDICT_PRODUCT_DECISION_REQUIRED,
    VERDICT_READINESS_BLOCKER,
    build_b2_live_llm_diagnostic_contract_report,
    build_b2_live_llm_diagnostic_evidence,
    build_live_diagnostic_macro_report,
    build_product_semantic_decision_pack,
    classify_live_diagnostic_verdict,
)
from scripts.build_wave1_phase_b2_evidence_synthesis_smoke import build_phase_b2_synthetic_smoke_report
from scripts.live_eval_readiness import PHASE_C_SAME_TRUTH_FAILURE


ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]


def _b1_green_handoff_snapshot() -> dict[str, object]:
    return {
        "b1_gate_scope": "Phase B-1 minimal tool-loop full natural-probe",
        "smoke_artifact": "artifacts/phase_b1_full_smoke.json",
        "readiness_artifact": "artifacts/phase_b1_readiness.json",
        "ready_for_phase_b1_implementation": True,
        "blockers": [],
        "not_claiming": "whole Wave 1 completion",
    }


def _phase_b2_report() -> dict[str, object]:
    return build_phase_b2_synthetic_smoke_report(b1_green_handoff_snapshot=_b1_green_handoff_snapshot())


def _case_by_id(report: dict[str, object], case_id: str) -> dict[str, object]:
    return next(case for case in report["cases"] if case["case_id"] == case_id)


def _item_result(
    *,
    packet_id: str = "pkt_generic_anchor_boba_tea",
    exactness_posture: str = "estimated",
    likely_kcal: int | None = 420,
) -> dict[str, object]:
    return {
        "interpreted_food_identity": "diagnostic item",
        "exactness_posture": exactness_posture,
        "likely_kcal": likely_kcal,
        "kcal_range": [360, 480] if likely_kcal is not None else None,
        "uncertainty_reason": "fake provider contract output",
        "evidence_used": [{"packet_id": packet_id, "usage": "anchor"}],
        "suggested_followup_question": "補充份量可以提高精度。",
    }


def _provider_output(*items: dict[str, object], **extra: object) -> dict[str, object]:
    payload: dict[str, object] = {"item_results": list(items)}
    payload.update(extra)
    return payload


def test_live_diagnostic_verdict_separates_readiness_blocker_from_diagnostic_observation() -> None:
    phase_c_readiness = {
        "status": "hard_fail",
        "readiness_pass": False,
        "failure_family": PHASE_C_SAME_TRUTH_FAILURE,
    }

    verdict = classify_live_diagnostic_verdict(
        phase_c_live_readiness=phase_c_readiness,
        provider_schema_valid=True,
        product_decision_required=False,
    )

    assert verdict["category"] == VERDICT_READINESS_BLOCKER
    assert verdict["reason"] == "phase_c_same_truth_gate_not_ready"
    assert verdict["canonicalizes_product_semantics"] is False


def test_live_diagnostic_verdict_marks_pending_product_semantics_without_canonizing() -> None:
    verdict = classify_live_diagnostic_verdict(
        phase_c_live_readiness={"status": "pass", "readiness_pass": True},
        provider_schema_valid=True,
        product_decision_required=True,
    )

    assert verdict["category"] == VERDICT_PRODUCT_DECISION_REQUIRED
    assert verdict["reason"] == "pending_product_semantic_decision"
    assert verdict["canonicalizes_product_semantics"] is False


def test_b2_live_llm_diagnostic_evidence_is_non_mutating_candidate_only() -> None:
    evidence = build_b2_live_llm_diagnostic_evidence(
        {
            "manager_role": "pass_2_synthesis",
            "payload_shape_valid": True,
            "item_results": [
                {
                    "interpreted_food_identity": "pearl milk tea",
                    "likely_kcal": 450,
                    "evidence_confidence": "moderate",
                    "suggested_followup_question": "What size and sugar level?",
                }
            ],
            "forbidden_mutation_fields_present": [],
            "mutation_attempted": False,
            "provider_params": {"provider": "builderspace", "model": "diagnostic-model"},
        }
    )

    assert evidence["diagnostic_lane"] == "b2_packet_synthesis"
    assert evidence["verdict_category"] == VERDICT_DIAGNOSTIC_OBSERVATION
    assert evidence["candidate_estimate_present"] is True
    assert evidence["mutation_authority"] is False
    assert evidence["canonical_truth_authority"] is False
    assert evidence["ledger_truth_authority"] is False
    assert evidence["provider_params"]["provider"] == "builderspace"


def test_b2_live_llm_diagnostic_flags_schema_or_mutation_fields_as_readiness_blocker() -> None:
    evidence = build_b2_live_llm_diagnostic_evidence(
        {
            "manager_role": "pass_2_synthesis",
            "payload_shape_valid": True,
            "item_results": [],
            "forbidden_mutation_fields_present": ["mutation_result"],
            "mutation_attempted": False,
        }
    )

    assert evidence["verdict_category"] == VERDICT_READINESS_BLOCKER
    assert evidence["failure_family"] == "b2_live_llm_diagnostic_contract_violation"
    assert evidence["mutation_authority"] is False


def test_b2_live_contract_harness_fake_mode_uses_deterministic_artifact_without_live_claim() -> None:
    report = build_b2_live_llm_diagnostic_contract_report(phase_b2_report=_phase_b2_report())

    assert report["diagnostic_lane"] == "b2_packet_synthesis"
    assert report["provider_mode"] == "fake"
    assert report["live_invoked"] is False
    assert report["readiness_claimed"] is False
    assert report["payload_artifact_id"] == "deterministic_b2_artifact"
    assert report["schema_mode"] == "json_schema"
    assert report["selected_case_ids"] == ["B2-002", "B2-007", "B2-001", "B2-009", "B2-004", "B2-008"]
    assert report["verdict_category"] == VERDICT_DIAGNOSTIC_OBSERVATION
    assert report["mutation_authority"] is False
    assert report["ledger_truth_authority"] is False
    assert report["source_priority_authority"] is False
    assert report["product_semantic_authority"] is False
    assert report["mutation_changed"] is False
    assert report["runtime_truth_changed"] is False
    assert report["user_facing_behavior_changed"] is False
    assert report["canonicalizes_product_semantics"] is False
    assert {case["case_id"] for case in report["case_results"]} == set(report["selected_case_ids"])


def test_b2_live_contract_harness_blocks_missing_item_results() -> None:
    report = build_b2_live_llm_diagnostic_contract_report(
        phase_b2_report=_phase_b2_report(),
        provider_outputs_by_case_id={"B2-002": {"payload_shape_valid": True}},
    )

    case = next(item for item in report["case_results"] if item["case_id"] == "B2-002")
    assert report["verdict_category"] == VERDICT_READINESS_BLOCKER
    assert case["verdict_category"] == VERDICT_READINESS_BLOCKER
    assert "missing_item_results" in case["blockers"]
    assert case["failure_family"] == B2_EMPTY_ITEM_RESULTS
    assert case["empty_item_results_root_cause"] == "prompt_contract_under_specified"


def test_b2_live_contract_harness_classifies_bridge_dropped_items() -> None:
    report = build_b2_live_llm_diagnostic_contract_report(
        phase_b2_report=_phase_b2_report(),
        provider_outputs_by_case_id={"B2-002": {"item_results": []}},
        provider_traces_by_case_id={
            "B2-002": {
                "raw_item_results_count": 1,
                "normalized_item_results_count": 0,
                "raw_top_level_keys": ["item_results"],
            }
        },
    )

    case = next(item for item in report["case_results"] if item["case_id"] == "B2-002")
    assert case["failure_family"] == B2_EMPTY_ITEM_RESULTS
    assert case["empty_item_results_root_cause"] == "provider_bridge_dropped_items"
    assert case["raw_provider_output_has_items"] is True
    assert case["normalized_output_has_items"] is False


def test_b2_live_contract_harness_classifies_payload_missing_evidence() -> None:
    phase_b2_report = _phase_b2_report()
    _case_by_id(phase_b2_report, "B2-002")["manager_pass_2"]["item_results"][0]["evidence_used"] = []

    report = build_b2_live_llm_diagnostic_contract_report(
        phase_b2_report=phase_b2_report,
        provider_outputs_by_case_id={"B2-002": {"item_results": []}},
    )

    case = next(item for item in report["case_results"] if item["case_id"] == "B2-002")
    assert case["failure_family"] == B2_EMPTY_ITEM_RESULTS
    assert case["empty_item_results_root_cause"] == "payload_missing_evidence"


def test_b2_live_contract_harness_blocks_forbidden_authority_fields() -> None:
    report = build_b2_live_llm_diagnostic_contract_report(
        phase_b2_report=_phase_b2_report(),
        provider_outputs_by_case_id={
            "B2-002": _provider_output(
                _item_result(),
                ledger_update={"ledger_item_ids": ["bad"]},
                product_semantic_decision="logged_estimate_with_followup",
                source_priority_decision="generic_db_first",
            )
        },
    )

    case = next(item for item in report["case_results"] if item["case_id"] == "B2-002")
    assert report["verdict_category"] == VERDICT_READINESS_BLOCKER
    assert "forbidden_authority_fields" in case["blockers"]
    assert set(case["forbidden_fields_present"]) == {
        "ledger_update",
        "product_semantic_decision",
        "source_priority_decision",
    }


def test_b2_live_contract_harness_blocks_rejected_packet_used_as_evidence() -> None:
    phase_b2_report = _phase_b2_report()
    rejected_packet_id = _case_by_id(phase_b2_report, "B2-009")["packets"][0]["packet_id"]

    report = build_b2_live_llm_diagnostic_contract_report(
        phase_b2_report=phase_b2_report,
        provider_outputs_by_case_id={"B2-009": _provider_output(_item_result(packet_id=rejected_packet_id))},
    )

    case = next(item for item in report["case_results"] if item["case_id"] == "B2-009")
    assert report["verdict_category"] == VERDICT_READINESS_BLOCKER
    assert "rejected_packet_used_as_evidence" in case["blockers"]
    assert case["rejected_packet_evidence_refs"] == [rejected_packet_id]


def test_b2_live_contract_harness_blocks_exactness_above_packet_permission() -> None:
    phase_b2_report = _phase_b2_report()
    generic_packet_id = _case_by_id(phase_b2_report, "B2-001")["packets"][0]["packet_id"]

    report = build_b2_live_llm_diagnostic_contract_report(
        phase_b2_report=phase_b2_report,
        provider_outputs_by_case_id={
            "B2-001": _provider_output(_item_result(packet_id=generic_packet_id, exactness_posture="exact"))
        },
    )

    case = next(item for item in report["case_results"] if item["case_id"] == "B2-001")
    assert report["verdict_category"] == VERDICT_READINESS_BLOCKER
    assert "generic_anchor_returned_exact" in case["blockers"]
    assert "exactness_exceeds_packet_permission" in case["blockers"]


def test_b2_live_contract_harness_marks_unknown_composition_estimate_as_product_decision_required() -> None:
    report = build_b2_live_llm_diagnostic_contract_report(
        phase_b2_report=_phase_b2_report(),
        provider_outputs_by_case_id={"B2-004": _provider_output(_item_result(packet_id="", likely_kcal=520))},
    )

    case = next(item for item in report["case_results"] if item["case_id"] == "B2-004")
    assert report["verdict_category"] == VERDICT_PRODUCT_DECISION_REQUIRED
    assert case["verdict_category"] == VERDICT_PRODUCT_DECISION_REQUIRED
    assert "unknown_composition_estimated" in case["product_decisions_required"]


def test_b2_live_contract_harness_blocks_bare_self_selected_basket_estimate_when_policy_approved() -> None:
    report = build_b2_live_llm_diagnostic_contract_report(
        phase_b2_report=_phase_b2_report(),
        provider_outputs_by_case_id={"B2-004": _provider_output(_item_result(packet_id="", likely_kcal=520))},
        approved_ask_first_policy_ids=("self_selected_basket_without_listed_items",),
    )

    case = next(item for item in report["case_results"] if item["case_id"] == "B2-004")
    assert report["verdict_category"] == VERDICT_READINESS_BLOCKER
    assert case["verdict_category"] == VERDICT_READINESS_BLOCKER
    assert case["failure_family"] == B2_ASK_FIRST_POLICY_VIOLATION
    assert "ask_first_item_results_present" in case["blockers"]
    assert "ask_first_estimate_present" in case["blockers"]
    assert case["product_decisions_required"] == []


def test_b2_live_contract_harness_allows_clarify_only_output_for_bare_self_selected_basket() -> None:
    report = build_b2_live_llm_diagnostic_contract_report(
        phase_b2_report=_phase_b2_report(),
        provider_outputs_by_case_id={
            "B2-004": {
                "clarification_question": "請列出滷味品項與大概份量。",
                "followup_question": "你吃了哪些滷味？例如豆干、海帶、貢丸各多少？",
            }
        },
        approved_ask_first_policy_ids=("self_selected_basket_without_listed_items",),
        selected_case_ids=("B2-004",),
    )

    case = report["case_results"][0]
    assert report["verdict_category"] == VERDICT_DIAGNOSTIC_OBSERVATION
    assert case["verdict_category"] == VERDICT_DIAGNOSTIC_OBSERVATION
    assert case["blockers"] == []
    assert case["item_result_count"] == 0


def test_b2_live_contract_harness_does_not_apply_ask_first_policy_to_pearl_milk_tea() -> None:
    report = build_b2_live_llm_diagnostic_contract_report(
        phase_b2_report=_phase_b2_report(),
        provider_outputs_by_case_id={"B2-002": _provider_output(_item_result(likely_kcal=420))},
        approved_ask_first_policy_ids=("self_selected_basket_without_listed_items",),
        selected_case_ids=("B2-002",),
    )

    case = report["case_results"][0]
    assert report["verdict_category"] == VERDICT_DIAGNOSTIC_OBSERVATION
    assert case["verdict_category"] == VERDICT_DIAGNOSTIC_OBSERVATION
    assert case["item_result_count"] == 1


def test_b2_live_contract_harness_blocks_query_only_mutation_intent() -> None:
    report = build_b2_live_llm_diagnostic_contract_report(
        phase_b2_report=_phase_b2_report(),
        provider_outputs_by_case_id={"B2-008": _provider_output(_item_result(), mutation_intent="log_this")},
    )

    case = next(item for item in report["case_results"] if item["case_id"] == "B2-008")
    assert report["verdict_category"] == VERDICT_READINESS_BLOCKER
    assert "query_only_mutation_intent" in case["blockers"]
    assert "forbidden_authority_fields" in case["blockers"]


def test_b2_live_contract_harness_does_not_import_final_mapping_or_semantic_register() -> None:
    source = (ROOT / "scripts/live_diagnostic_decision_pack.py").read_text(encoding="utf-8")

    assert "b2_final_mapping" not in source
    assert "WAVE_1_PHASE_B2_SEMANTIC_DECISION_REGISTER" not in source


def test_product_semantic_decision_pack_marks_approved_pearl_milk_tea_policy() -> None:
    decision_pack = build_product_semantic_decision_pack(
        observations={
            "pearl_milk_tea_missing_sugar_size": {
                "observed_system_behavior": "logged_estimate_with_followup",
                "observed_live_llm_behavior": "logged_estimate_with_followup",
            }
        }
    )

    assert decision_pack["pack_status"] == "pending_user_decision"
    assert decision_pack["canonicalizes_product_semantics"] is False
    assert decision_pack["decision_count"] >= 10
    first = decision_pack["decisions"][0]
    assert first["decision_id"] == "pearl_milk_tea_missing_sugar_size"
    assert first["status"] == "approved"
    assert first["selected_policy"] == "logged_estimate_with_followup"
    assert first["requires_user_approval"] is False
    assert first["observed_system_behavior"] == "logged_estimate_with_followup"
    assert first["observed_live_llm_behavior"] == "logged_estimate_with_followup"
    assert "superseded_c001_draft_expectation" in first["supersedes_stale_expectations"]
    assert any(decision["status"] == "pending" for decision in decision_pack["decisions"][1:])


def test_macro_report_keeps_three_outputs_separate() -> None:
    decision_pack = build_product_semantic_decision_pack()
    b2_evidence = build_b2_live_llm_diagnostic_evidence(
        {
            "manager_role": "pass_2_synthesis",
            "payload_shape_valid": True,
            "item_results": [],
            "forbidden_mutation_fields_present": [],
            "mutation_attempted": False,
        }
    )

    report = build_live_diagnostic_macro_report(
        live_preflight={"live_test_mode": "diagnostic", "readiness_claim_scope": "diagnostic_live_smoke"},
        phase_c_gate_status="pass",
        b2_live_llm_diagnostic=b2_evidence,
        product_semantic_decision_pack=decision_pack,
    )

    assert report["outputs"] == [
        "live_diagnostic_report",
        "b2_live_llm_diagnostic_lane",
        "product_semantic_decision_pack",
    ]
    assert report["canonicalizes_product_semantics"] is False
    assert report["mutation_changed"] is False
    assert report["user_facing_behavior_changed"] is False


def test_docs_lock_live_diagnostic_macro_batch_without_canonizing_decisions() -> None:
    spec = (ROOT / "docs/specs/V2_WAVE_1_MINIMAL_IMPLEMENTATION_CONTRACTS.md").read_text(encoding="utf-8-sig")
    bootstrap = (ROOT / "docs/specs/V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md").read_text(encoding="utf-8-sig")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8-sig")
    register_path = ROOT / "docs/specs/WAVE_1_PHASE_B2_SEMANTIC_DECISION_REGISTER.md"

    assert "Live Diagnostic Evidence And Product Semantics Decision Pack Lock" in spec
    assert "`diagnostic_observation`" in spec
    assert "`readiness_blocker`" in spec
    assert "`product_decision_required`" in spec
    assert "pending product decisions must not be written into canonical behavior" in spec
    assert "User-approved product semantic decisions supersede stale eval expectations" in bootstrap
    assert "pearl milk tea missing sugar/size is approved as logged estimate plus follow-up" in bootstrap
    assert "Product semantic decision pack status" in bootstrap
    assert "decision pack is not a canonical spec" in bootstrap
    assert "Current Wave 1 mainline is B2 / Phase B semantic closure" in bootstrap
    assert "baseline guardrail support, not the current mainline" in bootstrap
    assert "Strategic Sequencing Gate" in agents
    assert "current_mainline" in agents
    assert "strategic_verdict" in agents
    assert register_path.exists()
    register = register_path.read_text(encoding="utf-8-sig")
    assert "pearl_milk_tea_missing_sugar_size" in register
    assert "logged_estimate_with_followup" in register
    assert "follow_up_for_estimable_items" in register
    assert "precision_refinement_not_commit_gate" in register
    assert "self_selected_basket_without_listed_items" in register
    assert "ask_first_unresolved_no_logged_estimate" in register
    assert "homemade_dish_minimum_estimability" in register
    assert "homemade_dish_minimum_estimability:\n    status: pending" in register
    assert "Decision pack artifacts remain diagnostic" in register
