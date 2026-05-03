from __future__ import annotations

import json
from pathlib import Path

from scripts.build_accurate_intake_contract_hardening_guard import (
    build_accurate_intake_contract_hardening_guard,
)


ROOT = Path(__file__).resolve().parents[1]
HOLDOUT_REGISTER_PATH = ROOT / "docs" / "quality" / "accurate_intake_basket_holdout_cases.json"
CHANGE_MANIFEST_PATH = ROOT / "docs" / "quality" / "accurate_intake_contract_change_manifest_pr84.json"
LEGAL_FLOW_MATRIX_PATH = ROOT / "docs" / "quality" / "accurate_intake_contract_legal_flow_matrix.json"
DRIFT_AUDIT_PATH = ROOT / "docs" / "quality" / "accurate_intake_pr74_84_semantic_drift_audit.json"

FORBIDDEN_ORACLE_FIELDS = {
    "keyword",
    "input_contains",
    "raw_text_route",
    "raw_text_intent",
    "deterministic_route",
    "deterministic_intent",
}


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_basket_holdout_register_covers_bare_listed_and_stable_classes_without_raw_text_oracles() -> None:
    register = _load(HOLDOUT_REGISTER_PATH)
    cases = register["cases"]
    classes = {case["holdout_class"] for case in cases}

    assert register["register_id"] == "accurate_intake_basket_holdout_cases_v1"
    assert register["runner_inferred_semantics"] is False
    assert register["food_seed_rule"]["can_decide_logged_draft_no_mutation"] is False
    assert classes == {"bare_basket", "listed_basket", "stable_common_item"}
    assert len([case for case in cases if case["holdout_class"] == "bare_basket"]) >= 6
    assert len([case for case in cases if case["holdout_class"] == "listed_basket"]) >= 4
    assert len([case for case in cases if case["holdout_class"] == "stable_common_item"]) >= 4

    for case in cases:
        manager_fixture = case["manager_decision_fixture"]
        runtime_validation = case["expected_runtime_validation"]
        assert case["runner_inferred_semantics"] is False
        assert manager_fixture["semantic_owner"] == "manager"
        assert manager_fixture["source"] == "fixture_manager_structured_decision"
        assert runtime_validation["runner_may_infer_semantics_from_raw_text"] is False
        assert runtime_validation["food_seed_may_decide_logged_draft_no_mutation"] is False
        assert not (FORBIDDEN_ORACLE_FIELDS & set(case))
        assert not (FORBIDDEN_ORACLE_FIELDS & set(manager_fixture))


def test_bare_basket_holdouts_ask_followup_without_estimate_or_mutation() -> None:
    register = _load(HOLDOUT_REGISTER_PATH)
    bare_cases = [case for case in register["cases"] if case["holdout_class"] == "bare_basket"]
    raw_inputs = {case["raw_user_input"] for case in bare_cases}

    assert {"我吃了滷味", "我吃了麻辣燙", "我去買鹽酥雞", "我吃自助餐"} <= raw_inputs
    for case in bare_cases:
        fixture = case["manager_decision_fixture"]
        state = case["expected_state"]
        assert fixture["manager_action"] == "final"
        assert fixture["final_action"] == "ask_followup"
        assert fixture["workflow_effect"] == "draft_clarify_no_mutation"
        assert fixture["tool_calls"] == []
        assert state["estimate_nutrition_called"] is False
        assert state["ledger_mutation_allowed"] is False
        assert state["logged_or_committed"] is False


def test_listed_basket_holdouts_use_estimate_path_without_repeating_bare_basket_block() -> None:
    register = _load(HOLDOUT_REGISTER_PATH)
    listed_cases = [case for case in register["cases"] if case["holdout_class"] == "listed_basket"]
    raw_inputs = {case["raw_user_input"] for case in listed_cases}

    assert "滷味，有豆干、海帶、貢丸" in raw_inputs
    assert "麻辣燙，有王子麵、青菜、貢丸" in raw_inputs
    for case in listed_cases:
        fixture = case["manager_decision_fixture"]
        state = case["expected_state"]
        assert fixture["manager_action"] == "call_tools"
        assert fixture["final_action"] == "commit"
        assert fixture["workflow_effect"] == "listed_basket_commit"
        assert "estimate_nutrition" in fixture["tool_calls"]
        assert state["estimate_nutrition_called"] is True
        assert state["ledger_mutation_allowed"] is True
        assert state["logged_or_committed"] is True


def test_stable_common_item_holdouts_remain_estimable_with_optional_refinement() -> None:
    register = _load(HOLDOUT_REGISTER_PATH)
    stable_cases = [case for case in register["cases"] if case["holdout_class"] == "stable_common_item"]
    raw_inputs = {case["raw_user_input"] for case in stable_cases}

    assert {"珍珠奶茶半糖大杯", "雞腿便當", "茶葉蛋", "牛肉麵"} <= raw_inputs
    for case in stable_cases:
        fixture = case["manager_decision_fixture"]
        state = case["expected_state"]
        assert fixture["manager_action"] == "call_tools"
        assert fixture["final_action"] == "commit"
        assert fixture["workflow_effect"] == "stable_item_commit_with_optional_refinement"
        assert "estimate_nutrition" in fixture["tool_calls"]
        assert fixture["followup_posture"] == "refinement_optional"
        assert state["estimate_nutrition_called"] is True
        assert state["ledger_mutation_allowed"] is True
        assert state["logged_or_committed"] is True


def test_pr84_contract_hardening_guard_debt_is_cleared_by_basket_holdout() -> None:
    guard = build_accurate_intake_contract_hardening_guard(
        _load(CHANGE_MANIFEST_PATH),
        legal_flow_matrix_artifact=_load(LEGAL_FLOW_MATRIX_PATH),
        semantic_drift_audit_artifact=_load(DRIFT_AUDIT_PATH),
    )

    assert guard["merge_allowed"] is True
    assert guard["contract_hardening_debt"]["present"] is False
    assert "holdout_tests_missing" not in guard["blockers"]
