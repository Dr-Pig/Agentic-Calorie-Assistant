from __future__ import annotations

"""B-1 local diagnostic profile-route registry.

This module is intentionally narrow. It is not a global provider route registry,
runtime model router, or manager profile router. It only quarantines the local
diagnostic auto-route rules still needed by the Phase B-1 smoke harness.
"""

from dataclasses import dataclass
from typing import Any

from .manager_branch_constraints import (
    B1_COMMON_COMMERCIAL_DRINK_CASE_FAMILY,
    B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY,
    B1_LISTED_INGREDIENT_CASE_FAMILY,
)
from .phase_b1_selection_specs import (
    NATURAL_MODE,
    PHASE_B1_FULL_SMOKE_B1003_GROK_ROUTE_RULE_ID,
    PHASE_B1_FULL_SMOKE_B1005_GROK_ROUTE_RULE_ID,
    PHASE_B1_FULL_SMOKE_B1006_GROK_ROUTE_RULE_ID,
    PHASE_B1_ROUTE_SCOPE,
)


@dataclass(frozen=True)
class PhaseB1LocalDiagnosticRouteRule:
    target_profile_id: str
    route_reason: str
    route_rule_id: str
    case_family: str
    case_id: str | None = None
    case_set: str = "full"
    probe_mode: str = NATURAL_MODE
    manager_role: str = "pass_1_tool_request"
    route_scope: str = PHASE_B1_ROUTE_SCOPE
    artifact_basis: dict[str, Any] | None = None
    uses_case_id_local_debt: bool = False
    should_migrate_post_b1: bool = True

    def matches(
        self,
        *,
        case_set: str,
        probe_mode: str,
        manager_role: str,
        case_id: str | None,
        case_family: str | None,
    ) -> bool:
        if case_set != self.case_set:
            return False
        if probe_mode != self.probe_mode:
            return False
        if manager_role != self.manager_role:
            return False
        if case_family != self.case_family:
            return False
        if self.case_id is not None and case_id != self.case_id:
            return False
        return True


PHASE_B1_LOCAL_DIAGNOSTIC_ROUTE_RULES: tuple[PhaseB1LocalDiagnosticRouteRule, ...] = (
    PhaseB1LocalDiagnosticRouteRule(
        target_profile_id="builderspace-grok-4-fast-b1003-probe",
        route_reason="known_deepseek_b1003_pass1_transport_breach",
        route_rule_id=PHASE_B1_FULL_SMOKE_B1003_GROK_ROUTE_RULE_ID,
        case_family=B1_COMMON_COMMERCIAL_MEAL_CASE_FAMILY,
        artifact_basis={
            "artifact_path": "artifacts/wave1_phase_b_minimal_tool_loop_smoke_20260427T155117.987328Z_natural-probe_targeted_B1-003_4ab12d.json",
            "observed_result": "B1-003_pass1_grok_legal_decision",
            "prior_default_failure": "B1-003_pass1_deepseek_tool_call_transport_contract_breach",
        },
    ),
    PhaseB1LocalDiagnosticRouteRule(
        target_profile_id="builderspace-grok-4-fast-b1005-probe",
        route_reason="known_deepseek_b1005_pass1_tool_policy_mismatch",
        route_rule_id=PHASE_B1_FULL_SMOKE_B1005_GROK_ROUTE_RULE_ID,
        case_family=B1_LISTED_INGREDIENT_CASE_FAMILY,
        case_id="B1-005",
        artifact_basis={
            "artifact_path": "artifacts/wave1_phase_b_minimal_tool_loop_smoke_20260427T180042.469158Z_natural-probe_targeted_B1-005_b176c8.json",
            "observed_result": "B1-005_pass1_grok_item_level_lookup_generic_food",
            "prior_default_failure": "B1-005_pass1_deepseek_search_tool_policy_mismatch",
        },
        uses_case_id_local_debt=True,
    ),
    PhaseB1LocalDiagnosticRouteRule(
        target_profile_id="builderspace-grok-4-fast-b1006-probe",
        route_reason="known_deepseek_b1006_pass1_non_json_output",
        route_rule_id=PHASE_B1_FULL_SMOKE_B1006_GROK_ROUTE_RULE_ID,
        case_family=B1_COMMON_COMMERCIAL_DRINK_CASE_FAMILY,
        case_id="B1-006",
        artifact_basis={
            "artifact_path": "artifacts/wave1_phase_b_minimal_tool_loop_smoke_20260427T172310.969052Z_natural-probe_targeted_B1-006_242ece.json",
            "observed_result": "B1-006_pass1_grok_legal_decision",
            "prior_default_failure": "B1-006_pass1_deepseek_non_json_model_output",
        },
        uses_case_id_local_debt=True,
    ),
)

PHASE_B1_LOCAL_DIAGNOSTIC_TARGETED_PROFILE_CASE_ALLOWLIST: dict[str, list[str]] = {
    "builderspace-grok-4-fast-b1003-probe": ["B1-003"],
    "builderspace-grok-4-fast-b1004-probe": ["B1-004"],
    "builderspace-grok-4-fast-b1005-probe": ["B1-005"],
    "builderspace-grok-4-fast-b1006-probe": ["B1-006"],
}

PHASE_B1_LOCAL_DIAGNOSTIC_TARGETED_PROFILE_SUBSET_ALLOWLIST: dict[str, list[str]] = {
    "builderspace-grok-4-fast-b1-pass2-probe": ["B1-001", "B1-002", "B1-004", "B1-005"],
}

PHASE_B1_LOCAL_DIAGNOSTIC_FULL_PROFILE_ALLOWLIST: set[str] = {
    "builderspace-grok-4-fast-b1-pass1-tool-choice",
    "builderspace-grok-4-fast-b1-full-tool-loop-diagnostic",
}


def select_phase_b1_local_diagnostic_route_rule(
    *,
    case_set: str,
    requested_profile_id: str | None,
    probe_mode: str,
    manager_role: str,
    case_id: str | None,
    case_family: str | None,
) -> PhaseB1LocalDiagnosticRouteRule | None:
    if requested_profile_id:
        return None
    for rule in PHASE_B1_LOCAL_DIAGNOSTIC_ROUTE_RULES:
        if rule.matches(
            case_set=case_set,
            probe_mode=probe_mode,
            manager_role=manager_role,
            case_id=case_id,
            case_family=case_family,
        ):
            return rule
    return None


def phase_b1_local_diagnostic_requested_profile_allowed(
    *,
    requested_profile_id: str | None,
    case_set: str,
    requested_case_ids: list[str],
) -> bool:
    if not requested_profile_id:
        return False
    if case_set == "full" and requested_profile_id in PHASE_B1_LOCAL_DIAGNOSTIC_FULL_PROFILE_ALLOWLIST:
        return True
    subset_allowed_case_ids = PHASE_B1_LOCAL_DIAGNOSTIC_TARGETED_PROFILE_SUBSET_ALLOWLIST.get(requested_profile_id)
    if case_set == "targeted" and subset_allowed_case_ids is not None:
        return bool(requested_case_ids) and set(requested_case_ids).issubset(set(subset_allowed_case_ids))
    allowed_case_ids = PHASE_B1_LOCAL_DIAGNOSTIC_TARGETED_PROFILE_CASE_ALLOWLIST.get(requested_profile_id)
    if case_set != "targeted" or allowed_case_ids is None:
        return False
    return requested_case_ids == allowed_case_ids


def resolve_phase_b1_local_diagnostic_cli_defaults(
    *,
    requested_case_ids: list[str] | None,
    mode: str,
    provider_profile_id: str | None,
    used_legacy_targeting: bool,
) -> tuple[str, str | None]:
    if not used_legacy_targeting or requested_case_ids != ["B1-004"]:
        return mode, provider_profile_id
    effective_mode = "natural-probe" if mode == "forced" else mode
    effective_profile_id = provider_profile_id or "builderspace-grok-4-fast-b1004-probe"
    return effective_mode, effective_profile_id


__all__ = [
    "PHASE_B1_LOCAL_DIAGNOSTIC_FULL_PROFILE_ALLOWLIST",
    "PHASE_B1_LOCAL_DIAGNOSTIC_TARGETED_PROFILE_CASE_ALLOWLIST",
    "PHASE_B1_LOCAL_DIAGNOSTIC_TARGETED_PROFILE_SUBSET_ALLOWLIST",
    "PHASE_B1_LOCAL_DIAGNOSTIC_ROUTE_RULES",
    "PhaseB1LocalDiagnosticRouteRule",
    "phase_b1_local_diagnostic_requested_profile_allowed",
    "resolve_phase_b1_local_diagnostic_cli_defaults",
    "select_phase_b1_local_diagnostic_route_rule",
]
