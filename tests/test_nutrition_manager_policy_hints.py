from __future__ import annotations

from app.nutrition.application.manager_policy_hints import nutrition_manager_policy_hints


def test_nutrition_manager_policy_hints_expose_approved_case_law_without_runtime_authority() -> None:
    hints = nutrition_manager_policy_hints()

    assert hints["policy_source"] == "approved_nutrition_case_law"
    assert hints["policy_role"] == "manager_context_hint_not_deterministic_classifier"
    rules = {item["policy_id"]: item for item in hints["rules"]}
    assert "pearl_milk_tea_missing_sugar_size" in rules
    assert "logged estimate" in rules["pearl_milk_tea_missing_sugar_size"]["manager_behavior"]
    assert "refinement follow-up" in rules["pearl_milk_tea_missing_sugar_size"]["manager_behavior"]
    assert "self_selected_basket_without_listed_items" in rules
    assert "Do not estimate or canonical-write" in rules["self_selected_basket_without_listed_items"]["manager_behavior"]
    assert "listed_basket_followup_with_items" in rules
    listed_followup = rules["listed_basket_followup_with_items"]
    assert listed_followup["manager_behavior"].startswith("When the user provides concrete listed items")
    assert "call the nutrition evidence tool" in listed_followup["manager_behavior"]
    assert "do not repeat the same composition clarification" in listed_followup["manager_behavior"]
    assert listed_followup["runtime_authority"] == "validate_evidence_packet_and_final_mapping_only"
