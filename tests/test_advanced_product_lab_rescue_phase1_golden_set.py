from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
GOLDEN_PATH = (
    ROOT / "docs" / "quality" / "advanced_product_lab_rescue_phase1_golden_set.yaml"
)
TRAIN_PATH = (
    ROOT / "docs" / "quality" / "advanced_product_lab_rescue_phase1_pr_train.yaml"
)
DOC_INDEX_PATH = ROOT / "docs" / "DOC_INDEX.md"
LAB_INDEX_PATH = ROOT / "docs" / "quality" / "ADVANCED_PRODUCT_LAB_INDEX.md"


def _golden() -> dict:
    return yaml.safe_load(GOLDEN_PATH.read_text(encoding="utf-8-sig"))


def _train() -> dict:
    return yaml.safe_load(TRAIN_PATH.read_text(encoding="utf-8-sig"))


def test_rescue_phase1_golden_set_records_fixture_only_contract() -> None:
    golden = _golden()

    assert golden["artifact_type"] == "advanced_product_lab_rescue_phase1_golden_set"
    assert golden["status"] == "active_fixture_contract"
    assert golden["capability_domain"] == "rescue_phase1_runtime_lab"
    assert golden["artifact_classification"] == "merge_safe"
    assert golden["runtime_connected"] is False
    assert golden["lab_isolated"] is True
    assert golden["mainline_activation_enabled"] is False
    assert golden["canonical_product_db_mutation_allowed"] is False
    assert golden["raw_keyword_semantic_oracle_allowed"] is False


def test_rescue_phase1_golden_set_covers_required_case_types_and_journeys() -> None:
    golden = _golden()
    contract = golden["suite_contract"]

    assert set(contract["required_journeys"]) == {"F", "F2", "T", "N-3"}
    assert set(contract["required_case_types"]) == {
        "same_day_overshoot_rescue",
        "planned_event_budget_allocation",
        "gathering_day_allocation",
        "intake_rescue_separation",
        "accept_rescue_plan",
        "dismiss_rescue_plan",
        "complaint_not_dismiss",
        "attachment_ambiguity",
        "guardrail_math",
        "proactive_rescue_nudge",
    }
    assert contract["required_split_counts"] == {
        "fixture": 10,
        "holdout": 3,
        "negative": 4,
    }

    case_types = {case["case_type"] for case in golden["cases"]}
    assert set(contract["required_case_types"]).issubset(case_types)
    journey_ids = {case["journey_id"] for case in golden["cases"]}
    assert set(contract["required_journeys"]).issubset(journey_ids)


def test_rescue_phase1_golden_set_locks_key_product_boundaries() -> None:
    golden = _golden()
    cases = {case["case_id"]: case for case in golden["cases"]}

    assert cases["f_intake_reply_overshoot_no_formal_rescue"]["expected_effects"] == {
        "overshoot_awareness_allowed": True,
        "formal_rescue_proposal_created": False,
        "ledger_overlay_created": False,
        "independent_rescue_message_required": True,
    }
    assert cases["f_complaint_not_dismiss"]["expected_attachment"] == {
        "proposal_action": "none",
        "disposition": "answer_only_or_negotiation",
        "proposal_status_changed": False,
    }
    assert cases["f_explicit_dismiss"]["expected_attachment"]["proposal_action"] == (
        "dismiss_rescue_plan"
    )
    assert cases["f_accept_from_chat"]["expected_commit"]["source"] == "chat"
    assert cases["f2_planned_hotpot_reserve"]["expected_effects"][
        "planned_event_budget_allocation"
    ] is True
    assert cases["t_gathering_informational_only"]["expected_effects"][
        "proposal_created"
    ] is False
    assert cases["n3_proactive_rescue_nudge_independent"]["expected_effects"][
        "message_independent"
    ] is True


def test_rescue_phase1_golden_set_declares_rubric_and_non_claims() -> None:
    golden = _golden()

    rubric_ids = {item["dimension_id"] for item in golden["rubric"]}
    assert {
        "trigger_legality",
        "guardrail_math_legality",
        "proposal_separation",
        "attachment_legality",
        "commit_boundary",
        "retrieval_context_scope",
        "proactive_control_boundary",
        "no_mainline_activation",
    }.issubset(rubric_ids)

    assert "not_runtime_activation_evidence" in golden["non_claims"]
    assert "not_mainline_user_facing_approval" in golden["non_claims"]
    assert "not_production_ledger_or_scheduler_approval" in golden["non_claims"]


def test_rescue_phase1_golden_cases_use_trace_fields_not_keyword_oracles() -> None:
    golden = _golden()

    for case in golden["cases"]:
        assert case["oracle"]["raw_keyword_route_allowed"] is False
        assert case["oracle"]["semantic_oracle_source"] == "product_rule_and_trace_fields"
        assert case["expected_trace_fields"]
        assert "product_contract_refs" in case
        assert case["product_contract_refs"]


def test_rescue_phase1_train_and_doc_index_point_to_golden_set() -> None:
    train = _train()
    doc_index = DOC_INDEX_PATH.read_text(encoding="utf-8-sig")
    lab_index = LAB_INDEX_PATH.read_text(encoding="utf-8-sig")

    assert (
        "docs/quality/advanced_product_lab_rescue_phase1_golden_set.yaml"
        in train["dynamic_estimate_protocol"]["persistent_truth_files"]
    )
    assert "ADVANCED_PRODUCT_LAB_INDEX.md" in doc_index
    assert "advanced_product_lab_rescue_phase1_golden_set.yaml" in lab_index
