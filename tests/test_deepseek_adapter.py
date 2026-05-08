import pytest

from app.providers.deepseek_adapter import DeepSeekAdapter
from app.providers.deepseek_config import format_user_message
from app.runtime.agent.manager_branch_contract import (
    B1_COMMON_COMMERCIAL_DRINK_CASE_FAMILY,
    B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY,
    B1_COMMON_FOOD_ITEM_CASE_FAMILY,
    B1_COMPOSITION_UNKNOWN_CASE_FAMILY,
    B1_LISTED_INGREDIENT_CASE_FAMILY,
    ManagerPass1BranchContractError,
)


def test_readiness_exposes_only_single_manager_stage_models() -> None:
    adapter = DeepSeekAdapter()

    readiness = adapter.readiness()

    assert readiness["provider"] == "deepseek"
    assert readiness["manager_model"] == adapter.model
    assert readiness["stage_models"] == {
        "intake_manager_round": adapter.model,
    }
    assert readiness["timeout_seconds"] <= 15


def test_deepseek_format_user_message_uses_compact_json_for_prompt_payload() -> None:
    serialized = format_user_message(
        "intake_manager_round",
        {"b": [1, 2], "a": {"c": 3}},
    )

    assert serialized == '{"stage":"intake_manager_round","payload":{"b":[1,2],"a":{"c":3}}}'


def test_response_schema_only_exists_for_manager_stages() -> None:
    adapter = DeepSeekAdapter()

    assert adapter._response_schema_for_stage("intake_manager_round") is not None
    assert adapter._response_schema_for_stage("unknown_stage") is None


def test_extract_json_object_reads_fenced_manager_payload() -> None:
    adapter = DeepSeekAdapter()

    payload = adapter._extract_json_object("```json\n{\"workflow_effect\":\"ask_followup\"}\n```")

    assert payload["workflow_effect"] == "ask_followup"


def test_extract_json_object_rejects_non_json_content() -> None:
    adapter = DeepSeekAdapter()

    with pytest.raises(RuntimeError):
        adapter._extract_json_object("not-json")


def test_manager_response_schemas_are_closed_contracts() -> None:
    adapter = DeepSeekAdapter()

    for stage in ("intake_manager_round",):
        schema = adapter._response_schema_for_stage(stage)
        assert schema is not None
        assert schema["additionalProperties"] is False


def test_validate_manager_payload_rejects_missing_required_fields() -> None:
    adapter = DeepSeekAdapter()

    with pytest.raises(RuntimeError, match="missing required"):
        adapter._validate_manager_payload("intake_manager_round", {"workflow_effect": "commit"})


def test_validate_manager_payload_rejects_unknown_fields() -> None:
    adapter = DeepSeekAdapter()

    with pytest.raises(RuntimeError, match="unknown fields"):
        adapter._validate_manager_payload(
            "intake_manager_round",
            {
                "manager_action": "final",
                "intent": "log_meal",
                "final_action": "commit",
                "workflow_effect": "commit",
                "target_attachment": {},
                "exactness": "anchored",
                "confidence": "medium",
                "evidence_posture": "generic_with_uncertainty",
                "repair_ack": False,
                "answer_contract": {},
                "uncertainty_posture": "bounded",
                "evidence_honesty_posture": "generic",
                "unexpected": True,
            },
        )


def test_response_schema_narrows_for_b1_clarification_branch() -> None:
    adapter = DeepSeekAdapter()

    schema = adapter._response_schema_for_stage(
        "intake_manager_round",
        constraints={
            "phase_b1_manager_role": "pass_1_tool_request",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": B1_COMPOSITION_UNKNOWN_CASE_FAMILY,
        },
    )

    assert schema is not None
    assert schema["required"] == [
        "manager_action",
        "response_mode",
        "final_action",
        "operations",
        "answer_contract",
    ]
    assert schema["properties"]["manager_action"]["enum"] == ["final"]
    assert schema["properties"]["response_mode"]["enum"] == ["clarification"]
    assert schema["properties"]["final_action"]["enum"] == ["request_clarification"]


def test_deepseek_response_format_uses_json_schema_for_b1_common_food_item() -> None:
    adapter = DeepSeekAdapter()

    response_format, transport_meta = adapter._response_format_request_for_stage(
        "intake_manager_round",
        constraints={
            "phase_b1_manager_role": "pass_1_tool_request",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": B1_COMMON_FOOD_ITEM_CASE_FAMILY,
        },
    )

    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    assert transport_meta["structured_output_transport_attempted"] is True
    assert transport_meta["structured_output_transport_mode"] == "json_schema"
    assert transport_meta["structured_output_transport_constraint_snapshot"]["phase_b1_case_family"] == "common_food_item"


def test_deepseek_response_format_uses_json_schema_for_b1_common_commercial_drink() -> None:
    adapter = DeepSeekAdapter()

    response_format, transport_meta = adapter._response_format_request_for_stage(
        "intake_manager_round",
        constraints={
            "phase_b1_manager_role": "pass_1_tool_request",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": B1_COMMON_COMMERCIAL_DRINK_CASE_FAMILY,
        },
    )

    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    assert response_format["json_schema"]["schema"]["required"] == [
        "manager_action",
        "response_mode",
        "operations",
        "answer_contract",
        "tool_calls",
    ]
    assert transport_meta["structured_output_transport_attempted"] is True
    assert transport_meta["structured_output_transport_mode"] == "json_schema"
    assert transport_meta["structured_output_transport_constraint_snapshot"]["phase_b1_case_family"] == "common_commercial_drink"


def test_deepseek_response_schema_forced_composition_unknown_is_tool_call_contract() -> None:
    adapter = DeepSeekAdapter()

    schema = adapter._response_schema_for_stage(
        "intake_manager_round",
        constraints={
            "phase_b1_manager_role": "pass_1_tool_request",
            "phase_b1_pass1_mode": "forced_tool_request_smoke",
            "phase_b1_case_family": B1_COMPOSITION_UNKNOWN_CASE_FAMILY,
        },
    )

    assert schema is not None
    assert schema["properties"]["manager_action"]["enum"] == ["call_tools"]
    assert schema["properties"]["tool_calls"]["minItems"] == 1
    assert schema["properties"]["tool_calls"]["items"]["properties"]["name"]["enum"] == [
        "lookup_generic_food",
        "retrieve_web_food_evidence",
        "load_taiwan_food_semantics_skill",
    ]
    assert schema["required"] == [
        "manager_action",
        "response_mode",
        "operations",
        "answer_contract",
        "tool_calls",
    ]


def test_deepseek_response_format_uses_json_schema_for_b1_pass2_contract() -> None:
    adapter = DeepSeekAdapter()

    response_format, transport_meta = adapter._response_format_request_for_stage(
        "intake_manager_round",
        constraints={
            "phase_b1_manager_role": "pass_2_synthesis",
            "phase_b1_pass1_mode": "forced_tool_request_smoke",
            "phase_b1_case_family": B1_COMMON_FOOD_ITEM_CASE_FAMILY,
        },
    )

    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    assert response_format["json_schema"]["schema"]["required"] == [
        "manager_action",
        "response_mode",
        "intent",
        "workflow_effect",
        "target_attachment",
        "exactness",
        "confidence",
        "evidence_posture",
        "repair_ack",
        "operations",
        "answer_contract",
    ]
    assert transport_meta["structured_output_transport_attempted"] is True
    assert transport_meta["structured_output_transport_mode"] == "json_schema"
    assert transport_meta["structured_output_transport_constraint_snapshot"]["phase_b1_manager_role"] == "pass_2_synthesis"


def test_deepseek_decision_transport_request_for_b1_common_commercial_meal() -> None:
    adapter = DeepSeekAdapter()

    transport_request, transport_meta = adapter._decision_transport_request_for_stage(
        "intake_manager_round",
        constraints={
            "phase_b1_manager_role": "pass_1_tool_request",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY,
        },
    )

    assert transport_request is not None
    assert transport_request["mode"] == "tool_call_decision_transport"
    assert transport_request["tool_choice"]["type"] == "function"
    assert transport_request["tool_choice"]["function"]["name"] == "manager_call_tools_decision"
    assert transport_request["tools"][0]["type"] == "function"
    assert transport_request["tools"][0]["function"]["name"] == "manager_call_tools_decision"
    schema = transport_request["tools"][0]["function"]["parameters"]
    assert schema["required"] == [
        "manager_action",
        "response_mode",
        "operations",
        "answer_contract",
        "tool_calls",
    ]
    assert schema["properties"]["manager_action"]["enum"] == ["call_tools"]
    assert transport_meta["decision_transport_attempted"] is True
    assert transport_meta["decision_transport_mode"] == "tool_call_decision_transport"
    assert transport_meta["decision_transport_constraint_snapshot"]["phase_b1_case_family"] == "common_commercial_meal"


def test_validate_manager_payload_rejects_b1_mixed_branch_contract() -> None:
    adapter = DeepSeekAdapter()

    with pytest.raises(ManagerPass1BranchContractError, match="conflicting fields"):
        adapter._validate_manager_payload(
            "intake_manager_round",
            {
                "manager_action": "call_tools",
                "interaction_family": "food_logging",
                "response_mode": "intake_result",
                "final_action": "request_clarification",
                "operations": [],
                "answer_contract": {},
                "tool_calls": [{"name": "lookup_generic_food", "arguments": {"food_name": "滷味"}}],
            },
            constraints={
                "phase_b1_manager_role": "pass_1_tool_request",
                "phase_b1_pass1_mode": "natural_tool_selection_probe",
                "phase_b1_case_family": B1_COMPOSITION_UNKNOWN_CASE_FAMILY,
            },
        )


def test_validate_manager_payload_accepts_b1_clarification_branch() -> None:
    adapter = DeepSeekAdapter()

    adapter._validate_manager_payload(
        "intake_manager_round",
        {
            "manager_action": "final",
            "interaction_family": "food_logging",
            "response_mode": "clarification",
            "final_action": "request_clarification",
            "operations": [],
            "answer_contract": {"text": "Please list the specific items in the basket."},
        },
        constraints={
            "phase_b1_manager_role": "pass_1_tool_request",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": B1_COMPOSITION_UNKNOWN_CASE_FAMILY,
        },
    )


def test_validate_manager_payload_accepts_b1_clarification_branch_none_sentinels() -> None:
    adapter = DeepSeekAdapter()

    adapter._validate_manager_payload(
        "intake_manager_round",
        {
            "manager_action": "final",
            "interaction_family": "food_logging",
            "response_mode": "clarification",
            "final_action": "request_clarification",
            "workflow_effect": "none",
            "uncertainty_posture": "none",
            "operations": [],
            "answer_contract": {"text": "Please list the specific items in the basket."},
            "exactness": "none",
            "confidence": "none",
            "evidence_posture": "no_evidence",
            "evidence_honesty_posture": "none",
            "repair_ack": None,
        },
        constraints={
            "phase_b1_manager_role": "pass_1_tool_request",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": B1_COMPOSITION_UNKNOWN_CASE_FAMILY,
        },
    )


def test_validate_manager_payload_accepts_b1_clarification_branch_composition_unknown_posture() -> None:
    adapter = DeepSeekAdapter()

    adapter._validate_manager_payload(
        "intake_manager_round",
        {
            "manager_action": "final",
            "interaction_family": "food_logging",
            "response_mode": "clarification",
            "final_action": "request_clarification",
            "operations": [],
            "answer_contract": {"text": "Please list the specific items in the basket."},
            "exactness": "low",
            "confidence": "low",
            "evidence_posture": "no_evidence",
            "repair_ack": None,
            "workflow_effect": "none",
            "uncertainty_posture": "composition_unknown_basket",
            "evidence_honesty_posture": "honest",
        },
        constraints={
            "phase_b1_manager_role": "pass_1_tool_request",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": B1_COMPOSITION_UNKNOWN_CASE_FAMILY,
        },
    )


def test_response_schema_narrows_for_b1_listed_ingredient_tool_call_branch() -> None:
    adapter = DeepSeekAdapter()

    schema = adapter._response_schema_for_stage(
        "intake_manager_round",
        constraints={
            "phase_b1_manager_role": "pass_1_tool_request",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": B1_LISTED_INGREDIENT_CASE_FAMILY,
        },
    )

    assert schema is not None
    assert schema["required"] == [
        "manager_action",
        "response_mode",
        "operations",
        "answer_contract",
        "tool_calls",
    ]
    assert schema["properties"]["manager_action"]["enum"] == ["call_tools"]


def test_validate_manager_payload_accepts_b1_listed_ingredient_tool_call_branch() -> None:
    adapter = DeepSeekAdapter()

    adapter._validate_manager_payload(
        "intake_manager_round",
        {
            "manager_action": "call_tools",
            "interaction_family": "food_logging",
            "response_mode": "intake_result",
            "operations": [],
            "answer_contract": {},
            "tool_calls": [
                {"name": "lookup_generic_food", "arguments": {"food_name": "豆干"}},
                {"name": "lookup_generic_food", "arguments": {"food_name": "海帶"}},
            ],
        },
        constraints={
            "phase_b1_manager_role": "pass_1_tool_request",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": B1_LISTED_INGREDIENT_CASE_FAMILY,
        },
    )


def test_validate_manager_payload_rejects_b1_listed_ingredient_final_branch() -> None:
    adapter = DeepSeekAdapter()

    with pytest.raises(ManagerPass1BranchContractError, match="tool-call branch"):
        adapter._validate_manager_payload(
            "intake_manager_round",
            {
                "manager_action": "final",
                "interaction_family": "food_logging",
                "response_mode": "clarification",
                "final_action": "request_clarification",
                "operations": [],
                "answer_contract": {},
                "tool_calls": [],
            },
            constraints={
                "phase_b1_manager_role": "pass_1_tool_request",
                "phase_b1_pass1_mode": "natural_tool_selection_probe",
                "phase_b1_case_family": B1_LISTED_INGREDIENT_CASE_FAMILY,
            },
        )


def test_response_schema_narrows_for_b1_listed_ingredient_pass2_branch() -> None:
    adapter = DeepSeekAdapter()

    schema = adapter._response_schema_for_stage(
        "intake_manager_round",
        constraints={
            "phase_b1_manager_role": "pass_2_synthesis",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": B1_LISTED_INGREDIENT_CASE_FAMILY,
        },
    )

    assert schema is not None
    assert schema["required"] == [
        "manager_action",
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
    ]
    assert schema["properties"]["manager_action"]["enum"] == ["final"]
    assert "tool_calls" not in schema["properties"]
    assert schema["properties"]["item_results"]["type"] == "array"


def test_validate_manager_payload_accepts_b1_listed_ingredient_pass2_branch() -> None:
    adapter = DeepSeekAdapter()

    adapter._validate_manager_payload(
        "intake_manager_round",
        {
            "manager_action": "final",
            "interaction_family": "food_logging",
            "response_mode": "intake_result",
            "intent": "estimate_calories",
            "workflow_effect": "complete",
            "target_attachment": {"kind": "food_logging_estimate"},
            "exactness": "approximate",
            "confidence": "medium",
            "evidence_posture": "packetized_generic_db",
            "repair_ack": False,
            "item_results": [
                {
                    "food_name": "豆干",
                    "kcal_range": [70, 90],
                    "likely_kcal": 80,
                    "uncertainty": "medium",
                    "evidence_used": ["generic_food_db:豆干"],
                }
            ],
            "operations": [],
            "answer_contract": {},
        },
        constraints={
            "phase_b1_manager_role": "pass_2_synthesis",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": B1_LISTED_INGREDIENT_CASE_FAMILY,
        },
    )


@pytest.mark.parametrize(
    ("case_family", "expected_required"),
    (
        (
            B1_COMMON_FOOD_ITEM_CASE_FAMILY,
            [
                "manager_action",
                "response_mode",
                "intent",
                "workflow_effect",
                "target_attachment",
                "exactness",
                "confidence",
                "evidence_posture",
                "repair_ack",
                "operations",
                "answer_contract",
            ],
        ),
        (
            B1_COMMON_COMMERCIAL_DRINK_CASE_FAMILY,
            [
                "manager_action",
                "response_mode",
                "intent",
                "workflow_effect",
                "target_attachment",
                "exactness",
                "confidence",
                "evidence_posture",
                "repair_ack",
                "operations",
                "answer_contract",
            ],
        ),
        (
            B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY,
            [
                "manager_action",
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
            ],
        ),
    ),
)
def test_response_schema_narrows_for_b1_generic_pass2_branch(
    case_family: str,
    expected_required: list[str],
) -> None:
    adapter = DeepSeekAdapter()

    schema = adapter._response_schema_for_stage(
        "intake_manager_round",
        constraints={
            "phase_b1_manager_role": "pass_2_synthesis",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": case_family,
        },
    )

    assert schema is not None
    assert schema["required"] == expected_required
    assert schema["properties"]["manager_action"]["enum"] == ["final"]
    assert schema["properties"]["item_results"]["type"] == "array"
    assert schema["properties"]["evidence_used"]["type"] == "array"


def test_validate_manager_payload_accepts_b1_generic_common_food_pass2_without_broad_wrapper_fields() -> None:
    adapter = DeepSeekAdapter()

    adapter._validate_manager_payload(
        "intake_manager_round",
        {
            "manager_action": "final",
            "interaction_family": "food_logging",
            "response_mode": "intake_result",
            "intent": "log_food_item",
            "workflow_effect": "item_logged",
            "target_attachment": "茶葉蛋",
            "exactness": "approximate",
            "confidence": "medium",
            "evidence_posture": "packetized_generic_db",
            "repair_ack": False,
            "operations": [],
            "answer_contract": {
                "item_results": [
                    {
                        "item_name": "茶葉蛋",
                        "kcal_range": [70, 90],
                        "likely_kcal": 80,
                    }
                ]
            },
        },
        constraints={
            "phase_b1_manager_role": "pass_2_synthesis",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": B1_COMMON_FOOD_ITEM_CASE_FAMILY,
        },
    )


def test_validate_manager_payload_accepts_b1_generic_common_drink_pass2_with_top_level_item_results() -> None:
    adapter = DeepSeekAdapter()

    adapter._validate_manager_payload(
        "intake_manager_round",
        {
            "manager_action": "final",
            "interaction_family": "nutrition_info_query",
            "response_mode": "info_answer",
            "intent": "query_food_calories",
            "workflow_effect": "complete",
            "target_attachment": "food_item",
            "exactness": "approximate",
            "confidence": "medium",
            "evidence_posture": "packetized_generic_db",
            "repair_ack": False,
            "item_results": [
                {
                    "food_name": "珍珠奶茶",
                    "kcal_range": [350, 450],
                    "likely_kcal": 400,
                    "uncertainty": "medium",
                    "evidence_used": ["generic_food_db:珍珠奶茶"],
                }
            ],
            "evidence_used": ["generic_food_db:珍珠奶茶"],
            "operations": [],
            "answer_contract": {},
        },
        constraints={
            "phase_b1_manager_role": "pass_2_synthesis",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": B1_COMMON_COMMERCIAL_DRINK_CASE_FAMILY,
        },
    )


def test_validate_manager_payload_accepts_b1_common_commercial_meal_pass2_with_top_level_item_results() -> None:
    adapter = DeepSeekAdapter()

    adapter._validate_manager_payload(
        "intake_manager_round",
        {
            "manager_action": "final",
            "interaction_family": "food_logging",
            "response_mode": "intake_result",
            "intent": "estimate_calories",
            "workflow_effect": "complete",
            "target_attachment": "generic_taiwanese_bento",
            "exactness": "approximate",
            "confidence": "medium",
            "evidence_posture": "packetized_generic_db",
            "repair_ack": False,
            "item_results": [
                {
                    "food_name": "taiwanese_bento",
                    "kcal_range": [550, 960],
                    "likely_kcal": 750,
                    "uncertainty": "medium",
                    "evidence_used": ["generic_food_db:taiwanese_bento"],
                }
            ],
            "evidence_used": ["generic_food_db:taiwanese_bento"],
            "operations": [],
            "answer_contract": {},
        },
        constraints={
            "phase_b1_manager_role": "pass_2_synthesis",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY,
        },
    )


def test_validate_manager_payload_rejects_b1_common_commercial_meal_pass2_bridge_only_item_results() -> None:
    adapter = DeepSeekAdapter()

    with pytest.raises(RuntimeError, match="item_results"):
        adapter._validate_manager_payload(
            "intake_manager_round",
            {
                "manager_action": "final",
                "interaction_family": "food_logging",
                "response_mode": "intake_result",
                "intent": "estimate_calories",
                "workflow_effect": "complete",
                "target_attachment": "generic_taiwanese_bento",
                "exactness": "approximate",
                "confidence": "medium",
                "evidence_posture": "packetized_generic_db",
                "repair_ack": False,
                "answer_contract": {
                    "item_results": [
                        {
                            "item_name": "taiwanese_bento",
                            "item_quantity": 1,
                            "item_unit": "serving",
                        }
                    ],
                    "kcal_range": [550, 960],
                    "likely_kcal": 750,
                    "uncertainty": "medium",
                    "evidence_used": ["generic_food_db:taiwanese_bento"],
                },
                "operations": [],
            },
            constraints={
                "phase_b1_manager_role": "pass_2_synthesis",
                "phase_b1_pass1_mode": "natural_tool_selection_probe",
                "phase_b1_case_family": B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY,
            },
        )


def test_validate_manager_payload_rejects_pass1_item_results_even_for_listed_ingredient_case() -> None:
    adapter = DeepSeekAdapter()

    with pytest.raises(RuntimeError, match="unknown fields"):
        adapter._validate_manager_payload(
            "intake_manager_round",
            {
                "manager_action": "call_tools",
                "interaction_family": "food_logging",
                "response_mode": "intake_result",
                "operations": [],
                "answer_contract": {},
                "tool_calls": [{"name": "lookup_generic_food", "arguments": {"food_name": "豆干"}}],
                "item_results": [],
            },
            constraints={
                "phase_b1_manager_role": "pass_1_tool_request",
                "phase_b1_pass1_mode": "natural_tool_selection_probe",
                "phase_b1_case_family": B1_LISTED_INGREDIENT_CASE_FAMILY,
            },
        )


@pytest.mark.parametrize(
    "case_family",
    (
        B1_COMMON_FOOD_ITEM_CASE_FAMILY,
        B1_COMMON_COMMERCIAL_DRINK_CASE_FAMILY,
        B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY,
    ),
)
def test_response_schema_narrows_for_b1_generic_pass1_tool_call_branch(case_family: str) -> None:
    adapter = DeepSeekAdapter()

    schema = adapter._response_schema_for_stage(
        "intake_manager_round",
        constraints={
            "phase_b1_manager_role": "pass_1_tool_request",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": case_family,
        },
    )

    assert schema is not None
    assert schema["required"] == [
        "manager_action",
        "response_mode",
        "operations",
        "answer_contract",
        "tool_calls",
    ]
    assert schema["properties"]["manager_action"]["enum"] == ["call_tools"]


@pytest.mark.parametrize(
    ("case_family", "food_name"),
    (
        (B1_COMMON_FOOD_ITEM_CASE_FAMILY, "茶葉蛋"),
        (B1_COMMON_COMMERCIAL_DRINK_CASE_FAMILY, "珍珠奶茶"),
        (B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY, "便當"),
    ),
)
def test_validate_manager_payload_accepts_b1_generic_pass1_tool_call_branch(
    case_family: str,
    food_name: str,
) -> None:
    adapter = DeepSeekAdapter()

    adapter._validate_manager_payload(
        "intake_manager_round",
        {
            "manager_action": "call_tools",
            "interaction_family": "food_logging",
            "response_mode": "intake_result",
            "operations": [],
            "answer_contract": {},
            "tool_calls": [{"name": "lookup_generic_food", "arguments": {"food_name": food_name}}],
        },
        constraints={
            "phase_b1_manager_role": "pass_1_tool_request",
            "phase_b1_pass1_mode": "natural_tool_selection_probe",
            "phase_b1_case_family": case_family,
        },
    )


def test_validate_manager_payload_rejects_b1_generic_pass1_empty_tool_calls() -> None:
    adapter = DeepSeekAdapter()

    with pytest.raises(ManagerPass1BranchContractError, match="tool-call branch"):
        adapter._validate_manager_payload(
            "intake_manager_round",
            {
                "manager_action": "call_tools",
                "interaction_family": "food_logging",
                "response_mode": "intake_result",
                "operations": [],
                "answer_contract": {},
                "tool_calls": [],
            },
            constraints={
                "phase_b1_manager_role": "pass_1_tool_request",
                "phase_b1_pass1_mode": "natural_tool_selection_probe",
                "phase_b1_case_family": B1_COMMON_FOOD_ITEM_CASE_FAMILY,
            },
        )


def test_validate_manager_payload_rejects_b1_generic_pass1_final_truth_fields() -> None:
    adapter = DeepSeekAdapter()

    with pytest.raises(RuntimeError, match="unknown fields"):
        adapter._validate_manager_payload(
            "intake_manager_round",
            {
                "manager_action": "call_tools",
                "interaction_family": "food_logging",
                "response_mode": "intake_result",
                "operations": [],
                "answer_contract": {},
                "tool_calls": [{"name": "lookup_generic_food", "arguments": {"food_name": "茶葉蛋"}}],
                "item_results": [],
            },
            constraints={
                "phase_b1_manager_role": "pass_1_tool_request",
                "phase_b1_pass1_mode": "natural_tool_selection_probe",
                "phase_b1_case_family": B1_COMMON_FOOD_ITEM_CASE_FAMILY,
            },
        )


def test_manager_schema_exposes_semantic_contract_fields_without_reasoning_dump() -> None:
    adapter = DeepSeekAdapter()
    schema = adapter._response_schema_for_stage("intake_manager_round")

    assert schema is not None
    assert "intent" in schema["properties"]
    assert "target_attachment" in schema["properties"]
    assert "exactness" in schema["properties"]
    assert "confidence" in schema["properties"]
    assert "evidence_posture" in schema["properties"]
    assert "repair_ack" in schema["properties"]
    assert "thoughts" not in schema["properties"]
    assert "reasoning" not in schema["properties"]
    assert "interaction_family" in schema["properties"]
    assert "response_mode" in schema["properties"]
    assert "operations" in schema["properties"]
