from __future__ import annotations

from scripts.live_diagnostic_decision_pack import (
    VERDICT_DIAGNOSTIC_OBSERVATION,
    VERDICT_PRODUCT_DECISION_REQUIRED,
    VERDICT_READINESS_BLOCKER,
    build_b2_live_llm_diagnostic_evidence,
    build_live_diagnostic_macro_report,
    build_product_semantic_decision_pack,
    classify_live_diagnostic_verdict,
)
from scripts.live_eval_readiness import PHASE_C_SAME_TRUTH_FAILURE


ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]


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


def test_product_semantic_decision_pack_entries_stay_pending_and_non_canonical() -> None:
    decision_pack = build_product_semantic_decision_pack(
        observations={
            "pearl_milk_tea_missing_sugar_size": {
                "observed_system_behavior": "draft_with_followup",
                "observed_live_llm_behavior": "logged_estimate_with_followup",
            }
        }
    )

    assert decision_pack["pack_status"] == "pending_user_decision"
    assert decision_pack["canonicalizes_product_semantics"] is False
    assert decision_pack["decision_count"] >= 10
    first = decision_pack["decisions"][0]
    assert first["decision_id"] == "pearl_milk_tea_missing_sugar_size"
    assert first["status"] == "pending"
    assert first["requires_user_approval"] is True
    assert first["observed_system_behavior"] == "draft_with_followup"
    assert first["observed_live_llm_behavior"] == "logged_estimate_with_followup"


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

    assert "Live Diagnostic Evidence And Product Semantics Decision Pack Lock" in spec
    assert "`diagnostic_observation`" in spec
    assert "`readiness_blocker`" in spec
    assert "`product_decision_required`" in spec
    assert "pending product decisions must not be written into canonical behavior" in spec
    assert "Product semantic decision pack status" in bootstrap
    assert "decision pack is not a canonical spec" in bootstrap
