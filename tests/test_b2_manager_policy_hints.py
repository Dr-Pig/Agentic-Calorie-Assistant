from __future__ import annotations

from app.nutrition.application.b2_manager_policy_hints import b2_manager_policy_hints


def test_b2_manager_policy_hints_expose_approved_case_law_without_runtime_authority() -> None:
    hints = b2_manager_policy_hints()

    assert hints["policy_source"] == "approved_b2_case_law"
    assert hints["policy_role"] == "manager_context_hint_not_deterministic_classifier"
    rules = {item["policy_id"]: item for item in hints["rules"]}
    assert "pearl_milk_tea_missing_sugar_size" in rules
    assert "logged estimate" in rules["pearl_milk_tea_missing_sugar_size"]["manager_behavior"]
    assert "refinement follow-up" in rules["pearl_milk_tea_missing_sugar_size"]["manager_behavior"]
    assert "self_selected_basket_without_listed_items" in rules
    assert "Do not estimate or canonical-write" in rules["self_selected_basket_without_listed_items"]["manager_behavior"]
