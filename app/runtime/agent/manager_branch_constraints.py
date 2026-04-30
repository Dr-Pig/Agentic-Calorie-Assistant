from __future__ import annotations

from typing import Any


B1_COMPOSITION_UNKNOWN_CASE_FAMILY = "composition_unknown_self_selected_basket"
B1_COMMON_FOOD_ITEM_CASE_FAMILY = "common_food_item"
B1_COMMON_COMMERCIAL_DRINK_CASE_FAMILY = "common_commercial_drink"
B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY = "common_commercial_meal"
B1_LISTED_INGREDIENT_CASE_FAMILY = "listed_ingredient_basket"
FORCED_TOOL_REQUEST_MODE = "forced_tool_request_smoke"
NATURAL_TOOL_SELECTION_MODE = "natural_tool_selection_probe"


def is_b1_clarification_branch_constraint(constraints: dict[str, Any] | None) -> bool:
    return _is_phase_case(constraints, role="pass_1_tool_request", case_families={B1_COMPOSITION_UNKNOWN_CASE_FAMILY})


def is_b1_listed_ingredient_tool_call_constraint(constraints: dict[str, Any] | None) -> bool:
    return _is_phase_case(
        constraints,
        role="pass_1_tool_request",
        case_families={B1_LISTED_INGREDIENT_CASE_FAMILY},
        pass1_modes={FORCED_TOOL_REQUEST_MODE, NATURAL_TOOL_SELECTION_MODE},
    )


def is_b1_generic_tool_call_constraint(constraints: dict[str, Any] | None) -> bool:
    return _is_phase_case(
        constraints,
        role="pass_1_tool_request",
        case_families={
            B1_COMMON_FOOD_ITEM_CASE_FAMILY,
            B1_COMMON_COMMERCIAL_DRINK_CASE_FAMILY,
            B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY,
        },
        pass1_modes={FORCED_TOOL_REQUEST_MODE, NATURAL_TOOL_SELECTION_MODE},
    )


def should_attempt_b1_generic_pass1_structured_output_transport(constraints: dict[str, Any] | None) -> bool:
    return _is_phase_case(
        constraints,
        role="pass_1_tool_request",
        case_families={B1_COMMON_FOOD_ITEM_CASE_FAMILY, B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY},
    )


def should_attempt_b1_common_commercial_meal_pass1_decision_transport(constraints: dict[str, Any] | None) -> bool:
    return _is_phase_case(constraints, role="pass_1_tool_request", case_families={B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY})


def is_b1_generic_pass2_constraint(constraints: dict[str, Any] | None) -> bool:
    return _is_phase_case(
        constraints,
        role="pass_2_synthesis",
        case_families={B1_COMMON_FOOD_ITEM_CASE_FAMILY, B1_COMMON_COMMERCIAL_DRINK_CASE_FAMILY},
    )


def is_b1_clarification_pass2_constraint(constraints: dict[str, Any] | None) -> bool:
    return _is_phase_case(constraints, role="pass_2_synthesis", case_families={B1_COMPOSITION_UNKNOWN_CASE_FAMILY})


def is_b1_common_commercial_meal_pass2_constraint(constraints: dict[str, Any] | None) -> bool:
    return _is_phase_case(constraints, role="pass_2_synthesis", case_families={B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY})


def is_b1_listed_ingredient_pass2_constraint(constraints: dict[str, Any] | None) -> bool:
    return _is_phase_case(constraints, role="pass_2_synthesis", case_families={B1_LISTED_INGREDIENT_CASE_FAMILY})


def _is_phase_case(
    constraints: dict[str, Any] | None,
    *,
    role: str,
    case_families: set[str],
    pass1_modes: set[str] | None = None,
) -> bool:
    if not isinstance(constraints, dict):
        return False
    allowed_modes = pass1_modes or {NATURAL_TOOL_SELECTION_MODE}
    return (
        str(constraints.get("phase_b1_manager_role") or "") == role
        and str(constraints.get("phase_b1_pass1_mode") or "") in allowed_modes
        and str(constraints.get("phase_b1_case_family") or "") in case_families
    )
