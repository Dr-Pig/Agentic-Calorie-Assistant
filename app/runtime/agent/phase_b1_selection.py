from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .manager_branch_constraints import (
    B1_COMMON_FOOD_ITEM_CASE_FAMILY,
    B1_COMPOSITION_UNKNOWN_CASE_FAMILY,
    B1_LISTED_INGREDIENT_CASE_FAMILY,
)
from .phase_b1_profile_route_rules import select_phase_b1_local_diagnostic_route_rule
from .phase_b1_selection_specs import (
    FORCED_MODE,
    NATURAL_MODE,
    PASS1_DEFAULT_SELECTION_SPEC,
    PASS1_SELECTION_SPECS,
    PASS2_DEFAULT_SELECTION_SPEC,
    PASS2_SELECTION_SPECS,
    PHASE_B1_DEFAULT_ROUTE_RULE_ID,
    PHASE_B1_PASS_1_COMMON_COMMERCIAL_DRINK_ID,
    PHASE_B1_PASS_1_COMMON_COMMERCIAL_MEAL_ID,
    PHASE_B1_PASS_1_COMMON_FOOD_ITEM_ID,
    PHASE_B1_PASS_1_FORCED_ID,
    PHASE_B1_PASS_1_NATURAL_FALLBACK_ID,
    PHASE_B1_PASS_2_B1_004_CLARIFY_ONLY_ID,
    PHASE_B1_PASS_2_COMMON_COMMERCIAL_DRINK_ID,
    PHASE_B1_PASS_2_COMMON_COMMERCIAL_MEAL_ID,
    PHASE_B1_PASS_2_COMMON_FOOD_ITEM_ID,
    PHASE_B1_PASS_2_GENERIC_ID,
    PHASE_B1_PASS_2_LISTED_INGREDIENT_ID,
    PHASE_B1_ROUTE_SCOPE,
    PHASE_B1_TARGETED_OVERRIDE_RULE_ID,
)


@dataclass(frozen=True)
class PhaseB1SelectorInputs:
    case_family: str | None
    manager_role: str
    probe_mode: str
    case_id: str | None = None

    def to_trace_dict(self) -> dict[str, Any]:
        data = {
            "case_family": self.case_family,
            "manager_role": self.manager_role,
            "probe_mode": self.probe_mode,
        }
        if self.case_id:
            data["case_id"] = self.case_id
        return data


@dataclass(frozen=True)
class PhaseB1TaskPayloadSelection:
    task_payload_id: str
    constraint_id: str
    schema_branch: str
    guidance_fragment_id: str
    allowed_fields: tuple[str, ...]
    forbidden_fields: tuple[str, ...]
    selector_reason: str
    uses_case_id_local_debt: bool = False

    def to_trace_dict(self) -> dict[str, Any]:
        return {
            "payload_id": self.task_payload_id,
            "constraint_id": self.constraint_id,
            "schema_branch": self.schema_branch,
            "guidance_fragment_id": self.guidance_fragment_id,
            "allowed_fields": list(self.allowed_fields),
            "forbidden_fields": list(self.forbidden_fields),
            "selector_reason": self.selector_reason,
            "uses_case_id_local_debt": self.uses_case_id_local_debt,
        }


@dataclass(frozen=True)
class PhaseB1ProfileRouteSelection:
    profile_id: str
    route_mode: str
    route_reason: str
    route_rule_id: str
    route_scope: str
    artifact_basis: dict[str, Any] | None = None
    uses_case_id_local_debt: bool = False
    should_migrate_post_b1: bool = False

    def to_trace_dict(self) -> dict[str, Any]:
        return {
            "provider_profile_id": self.profile_id,
            "route_mode": self.route_mode,
            "route_reason": self.route_reason,
            "route_rule_id": self.route_rule_id,
            "route_scope": self.route_scope,
            "artifact_basis": self.artifact_basis,
            "uses_case_id_local_debt": self.uses_case_id_local_debt,
            "should_migrate_post_b1": self.should_migrate_post_b1,
        }


def build_phase_b1_selector_inputs(
    *,
    case_family: str | None,
    manager_role: str,
    probe_mode: str,
    case_id: str | None = None,
) -> PhaseB1SelectorInputs:
    return PhaseB1SelectorInputs(
        case_family=case_family,
        manager_role=manager_role,
        probe_mode=probe_mode,
        case_id=case_id,
    )


def _task_selection(spec: dict[str, Any]) -> PhaseB1TaskPayloadSelection:
    return PhaseB1TaskPayloadSelection(**spec)


def select_phase_b1_task_payload(
    *,
    manager_role: str,
    probe_mode: str,
    case_family: str | None,
) -> PhaseB1TaskPayloadSelection:
    if manager_role == "pass_1_tool_request":
        if probe_mode != NATURAL_MODE:
            return _task_selection(PASS1_SELECTION_SPECS["__forced__"])
        return _task_selection(PASS1_SELECTION_SPECS.get(case_family, PASS1_DEFAULT_SELECTION_SPEC))
    return _task_selection(PASS2_SELECTION_SPECS.get(case_family, PASS2_DEFAULT_SELECTION_SPEC))


def select_phase_b1_profile_route(
    *,
    case_set: str,
    requested_profile_id: str | None,
    probe_mode: str,
    manager_role: str,
    case_id: str | None,
    case_family: str | None,
    selected_profile_id: str,
    default_profile_id: str,
    profile_applies: bool,
) -> PhaseB1ProfileRouteSelection:
    local_rule = select_phase_b1_local_diagnostic_route_rule(
        case_set=case_set,
        requested_profile_id=requested_profile_id,
        probe_mode=probe_mode,
        manager_role=manager_role,
        case_id=case_id,
        case_family=case_family,
    )
    if local_rule is not None:
        return PhaseB1ProfileRouteSelection(
            local_rule.target_profile_id,
            "auto_branch_route",
            local_rule.route_reason,
            local_rule.route_rule_id,
            local_rule.route_scope,
            dict(local_rule.artifact_basis) if local_rule.artifact_basis is not None else None,
            uses_case_id_local_debt=local_rule.uses_case_id_local_debt,
            should_migrate_post_b1=local_rule.should_migrate_post_b1,
        )
    if requested_profile_id and selected_profile_id != default_profile_id and profile_applies:
        return PhaseB1ProfileRouteSelection(
            selected_profile_id,
            "explicit_targeted_override",
            "requested_targeted_profile_override",
            PHASE_B1_TARGETED_OVERRIDE_RULE_ID,
            PHASE_B1_ROUTE_SCOPE,
            should_migrate_post_b1=True,
        )
    active_profile_id = selected_profile_id if profile_applies else default_profile_id
    return PhaseB1ProfileRouteSelection(
        active_profile_id,
        "default_build_loop",
        "no_branch_specific_override",
        PHASE_B1_DEFAULT_ROUTE_RULE_ID,
        PHASE_B1_ROUTE_SCOPE,
    )
