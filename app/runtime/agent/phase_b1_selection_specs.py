from __future__ import annotations

from .manager_branch_constraints import (
    B1_COMMON_COMMERCIAL_DRINK_CASE_FAMILY,
    B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY,
    B1_COMMON_FOOD_ITEM_CASE_FAMILY,
    B1_COMPOSITION_UNKNOWN_CASE_FAMILY,
    B1_LISTED_INGREDIENT_CASE_FAMILY,
)

FORCED_MODE = "forced_tool_request_smoke"
NATURAL_MODE = "natural_tool_selection_probe"

PHASE_B1_ROUTE_SCOPE = "b1_local_diagnostic"
PHASE_B1_DEFAULT_ROUTE_RULE_ID = "phase_b1_default_build_loop_v1"
PHASE_B1_TARGETED_OVERRIDE_RULE_ID = "phase_b1_targeted_profile_override_v1"
PHASE_B1_FULL_DIAGNOSTIC_OVERRIDE_RULE_ID = "phase_b1_full_diagnostic_profile_override_v1"
PHASE_B1_FULL_SMOKE_B1003_GROK_ROUTE_RULE_ID = "phase_b1_full_smoke_b1003_pass1_grok_route_v1"
PHASE_B1_FULL_SMOKE_B1005_GROK_ROUTE_RULE_ID = "phase_b1_full_smoke_b1005_pass1_grok_route_v1"
PHASE_B1_FULL_SMOKE_B1006_GROK_ROUTE_RULE_ID = "phase_b1_full_smoke_b1006_pass1_grok_route_v1"

PHASE_B1_PASS_1_FORCED_ID = "phase_b1_pass_1_forced_tool_request_v1"
PHASE_B1_PASS_1_COMMON_FOOD_ITEM_ID = "phase_b1_pass_1_common_food_item_anti_final_v1"
PHASE_B1_PASS_1_COMMON_COMMERCIAL_DRINK_ID = "phase_b1_pass_1_common_commercial_drink_anti_final_v1"
PHASE_B1_PASS_1_COMMON_COMMERCIAL_MEAL_ID = "phase_b1_pass_1_common_commercial_meal_anti_final_v1"
PHASE_B1_PASS_1_NATURAL_FALLBACK_ID = "phase_b1_pass_1_natural_tool_selection_guidance_v5"
PHASE_B1_PASS_2_B1_004_CLARIFY_ONLY_ID = "phase_b1_pass_2_b1_004_clarify_only_v1"
PHASE_B1_PASS_2_COMMON_FOOD_ITEM_ID = "phase_b1_pass_2_common_food_item_compact_json_first_v1"
PHASE_B1_PASS_2_COMMON_COMMERCIAL_DRINK_ID = "phase_b1_pass_2_common_commercial_drink_compact_json_first_v1"
PHASE_B1_PASS_2_COMMON_COMMERCIAL_MEAL_ID = "phase_b1_pass_2_common_commercial_meal_compact_json_first_v1"
PHASE_B1_PASS_2_LISTED_INGREDIENT_ID = "phase_b1_pass_2_listed_ingredient_compact_json_first_v1"
PHASE_B1_PASS_2_GENERIC_ID = "phase_b1_pass_2_synthesis_v1"

PASS1_TOOL_CALL_ALLOWED_FIELDS = (
    "manager_action",
    "interaction_family",
    "response_mode",
    "operations",
    "answer_contract",
    "tool_calls",
)
PASS1_TOOL_CALL_FORBIDDEN_FIELDS = (
    "item_results",
    "likely_kcal",
    "kcal_range",
    "final_response",
    "mutation_result",
    "ledger_delta",
    "canonical_ledger_entry",
)
PASS1_CLARIFICATION_ALLOWED_FIELDS = (
    "manager_action",
    "interaction_family",
    "response_mode",
    "final_action",
    "operations",
    "answer_contract",
)
PASS1_CLARIFICATION_FORBIDDEN_FIELDS = (
    "tool_calls",
    "item_results",
    "likely_kcal",
    "kcal_range",
    "mutation_result",
    "ledger_delta",
    "canonical_ledger_entry",
)
PASS2_CLARIFICATION_ALLOWED_FIELDS = (
    "manager_action",
    "interaction_family",
    "response_mode",
    "intent",
    "workflow_effect",
    "target_attachment",
    "final_action",
    "exactness",
    "confidence",
    "evidence_posture",
    "repair_ack",
    "response_summary",
    "pending_followup",
    "operations",
    "answer_contract",
    "item_results",
    "evidence_used",
    "uncertainty_posture",
    "evidence_honesty_posture",
)
PASS2_GENERIC_ALLOWED_FIELDS = (
    "manager_action",
    "interaction_family",
    "response_mode",
    "intent",
    "workflow_effect",
    "target_attachment",
    "final_action",
    "exactness",
    "confidence",
    "evidence_posture",
    "repair_ack",
    "response_summary",
    "pending_followup",
    "operations",
    "answer_contract",
    "item_results",
    "evidence_used",
    "uncertainty_posture",
    "evidence_honesty_posture",
)
PASS2_LISTED_INGREDIENT_ALLOWED_FIELDS = (
    "manager_action",
    "interaction_family",
    "response_mode",
    "intent",
    "workflow_effect",
    "target_attachment",
    "exactness",
    "confidence",
    "evidence_posture",
    "repair_ack",
    "item_results",
    "operations",
    "answer_contract",
)
PASS2_FORBIDDEN_MUTATION_FIELDS = (
    "mutation_result",
    "ledger_delta",
    "canonical_ledger_entry",
)

PASS1_DEFAULT_SELECTION_SPEC = {
    "task_payload_id": PHASE_B1_PASS_1_NATURAL_FALLBACK_ID,
    "constraint_id": "phase_b1_pass1_generic_tool_call_contract_v1",
    "schema_branch": "pass1_generic_tool_call",
    "guidance_fragment_id": "generic_json_first_tool_request_v1",
    "allowed_fields": PASS1_TOOL_CALL_ALLOWED_FIELDS,
    "forbidden_fields": PASS1_TOOL_CALL_FORBIDDEN_FIELDS,
    "selector_reason": "natural_probe_generic_pass1_selector",
}

PASS1_SELECTION_SPECS = {
    "__forced__": {
        "task_payload_id": PHASE_B1_PASS_1_FORCED_ID,
        "constraint_id": "phase_b1_pass1_forced_tool_request_contract_v1",
        "schema_branch": "pass1_call_tools_forced",
        "guidance_fragment_id": "forced_tool_request_json_contract_v1",
        "allowed_fields": PASS1_TOOL_CALL_ALLOWED_FIELDS,
        "forbidden_fields": PASS1_TOOL_CALL_FORBIDDEN_FIELDS,
        "selector_reason": "forced_tool_request_contract",
    },
    B1_COMPOSITION_UNKNOWN_CASE_FAMILY: {
        "task_payload_id": PHASE_B1_PASS_1_NATURAL_FALLBACK_ID,
        "constraint_id": "phase_b1_pass1_clarification_contract_v1",
        "schema_branch": "pass1_clarification",
        "guidance_fragment_id": "b1_004_pass1_clarification_guard_v1",
        "allowed_fields": PASS1_CLARIFICATION_ALLOWED_FIELDS,
        "forbidden_fields": PASS1_CLARIFICATION_FORBIDDEN_FIELDS,
        "selector_reason": "composition_unknown_pass1_clarification_selector",
    },
    B1_LISTED_INGREDIENT_CASE_FAMILY: {
        "task_payload_id": PHASE_B1_PASS_1_NATURAL_FALLBACK_ID,
        "constraint_id": "phase_b1_pass1_listed_ingredient_tool_call_contract_v1",
        "schema_branch": "pass1_listed_ingredient_tool_call",
        "guidance_fragment_id": "listed_ingredient_json_first_tool_request_v1",
        "allowed_fields": PASS1_TOOL_CALL_ALLOWED_FIELDS,
        "forbidden_fields": PASS1_TOOL_CALL_FORBIDDEN_FIELDS,
        "selector_reason": "listed_ingredient_pass1_selector",
    },
    B1_COMMON_FOOD_ITEM_CASE_FAMILY: {
        "task_payload_id": PHASE_B1_PASS_1_COMMON_FOOD_ITEM_ID,
        "constraint_id": "phase_b1_pass1_generic_tool_call_contract_v1",
        "schema_branch": "pass1_generic_tool_call",
        "guidance_fragment_id": "common_food_item_json_first_tool_request_v1",
        "allowed_fields": PASS1_TOOL_CALL_ALLOWED_FIELDS,
        "forbidden_fields": PASS1_TOOL_CALL_FORBIDDEN_FIELDS,
        "selector_reason": "common_food_item_pass1_selector",
    },
    B1_COMMON_COMMERCIAL_DRINK_CASE_FAMILY: {
        "task_payload_id": PHASE_B1_PASS_1_COMMON_COMMERCIAL_DRINK_ID,
        "constraint_id": "phase_b1_pass1_generic_tool_call_contract_v1",
        "schema_branch": "pass1_generic_tool_call",
        "guidance_fragment_id": "common_commercial_drink_json_first_tool_request_v1",
        "allowed_fields": PASS1_TOOL_CALL_ALLOWED_FIELDS,
        "forbidden_fields": PASS1_TOOL_CALL_FORBIDDEN_FIELDS,
        "selector_reason": "common_commercial_drink_pass1_selector",
    },
    B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY: {
        "task_payload_id": PHASE_B1_PASS_1_COMMON_COMMERCIAL_MEAL_ID,
        "constraint_id": "phase_b1_pass1_generic_tool_call_contract_v1",
        "schema_branch": "pass1_generic_tool_call",
        "guidance_fragment_id": "common_commercial_meal_json_first_tool_request_v1",
        "allowed_fields": PASS1_TOOL_CALL_ALLOWED_FIELDS,
        "forbidden_fields": PASS1_TOOL_CALL_FORBIDDEN_FIELDS,
        "selector_reason": "common_commercial_meal_pass1_selector",
    },
}

PASS2_DEFAULT_SELECTION_SPEC = {
    "task_payload_id": PHASE_B1_PASS_2_GENERIC_ID,
    "constraint_id": "phase_b1_pass2_generic_synthesis_contract_v1",
    "schema_branch": "pass2_generic_synthesis",
    "guidance_fragment_id": "generic_compact_json_first_v1",
    "allowed_fields": PASS2_GENERIC_ALLOWED_FIELDS,
    "forbidden_fields": PASS2_FORBIDDEN_MUTATION_FIELDS,
    "selector_reason": "generic_pass2_selector",
}

PASS2_SELECTION_SPECS = {
    B1_COMPOSITION_UNKNOWN_CASE_FAMILY: {
        "task_payload_id": PHASE_B1_PASS_2_B1_004_CLARIFY_ONLY_ID,
        "constraint_id": "phase_b1_pass2_clarify_only_contract_v1",
        "schema_branch": "pass2_clarify_only",
        "guidance_fragment_id": "b1_004_clarify_only_json_first_v1",
        "allowed_fields": PASS2_CLARIFICATION_ALLOWED_FIELDS,
        "forbidden_fields": PASS2_FORBIDDEN_MUTATION_FIELDS,
        "selector_reason": "b1_004_clarify_only_pass2_selector",
    },
    B1_COMMON_FOOD_ITEM_CASE_FAMILY: {
        "task_payload_id": PHASE_B1_PASS_2_COMMON_FOOD_ITEM_ID,
        "constraint_id": "phase_b1_pass2_generic_synthesis_contract_v1",
        "schema_branch": "pass2_generic_synthesis",
        "guidance_fragment_id": "common_food_item_compact_json_first_v1",
        "allowed_fields": PASS2_GENERIC_ALLOWED_FIELDS,
        "forbidden_fields": PASS2_FORBIDDEN_MUTATION_FIELDS,
        "selector_reason": "common_food_item_pass2_selector",
    },
    B1_COMMON_COMMERCIAL_DRINK_CASE_FAMILY: {
        "task_payload_id": PHASE_B1_PASS_2_COMMON_COMMERCIAL_DRINK_ID,
        "constraint_id": "phase_b1_pass2_generic_synthesis_contract_v1",
        "schema_branch": "pass2_generic_synthesis",
        "guidance_fragment_id": "common_commercial_drink_compact_json_first_v1",
        "allowed_fields": PASS2_GENERIC_ALLOWED_FIELDS,
        "forbidden_fields": PASS2_FORBIDDEN_MUTATION_FIELDS,
        "selector_reason": "common_commercial_drink_pass2_selector",
    },
    B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY: {
        "task_payload_id": PHASE_B1_PASS_2_COMMON_COMMERCIAL_MEAL_ID,
        "constraint_id": "phase_b1_pass2_common_commercial_meal_contract_v1",
        "schema_branch": "pass2_common_commercial_meal",
        "guidance_fragment_id": "common_commercial_meal_compact_json_first_v1",
        "allowed_fields": PASS2_GENERIC_ALLOWED_FIELDS,
        "forbidden_fields": PASS2_FORBIDDEN_MUTATION_FIELDS,
        "selector_reason": "common_commercial_meal_pass2_selector",
    },
    B1_LISTED_INGREDIENT_CASE_FAMILY: {
        "task_payload_id": PHASE_B1_PASS_2_LISTED_INGREDIENT_ID,
        "constraint_id": "phase_b1_pass2_listed_ingredient_contract_v1",
        "schema_branch": "pass2_listed_ingredient",
        "guidance_fragment_id": "listed_ingredient_compact_json_first_v1",
        "allowed_fields": PASS2_LISTED_INGREDIENT_ALLOWED_FIELDS,
        "forbidden_fields": PASS2_FORBIDDEN_MUTATION_FIELDS,
        "selector_reason": "listed_ingredient_pass2_selector",
    },
}
