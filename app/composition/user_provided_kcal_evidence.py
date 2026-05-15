from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.composition.intake_manager_tool_batch import nutrition_tool_output
from app.composition.intake_read_tools import compare_against_budget_tool
from app.nutrition.application.estimate_artifact_types import EstimatedNutritionArtifact
from app.nutrition.application.user_provided_kcal_artifacts import build_user_provided_kcal_artifact


@dataclass(frozen=True)
class UserProvidedKcalEvidenceSeed:
    nutrition_artifact: EstimatedNutritionArtifact | None = None
    budget_summary: dict[str, Any] | None = None
    tool_results: list[dict[str, Any]] = field(default_factory=list)


def manager_owned_user_provided_kcal(manager_decision: Any) -> int | None:
    semantic_decision = dict(getattr(manager_decision, "semantic_decision", {}) or {})
    if str(semantic_decision.get("source") or "") != "user_provided_kcal":
        return None
    value = semantic_decision.get("user_provided_kcal")
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    kcal = int(value)
    if kcal != value or kcal <= 0 or kcal > 10000:
        return None
    return kcal


def build_user_provided_kcal_evidence_seed(
    db: Session,
    *,
    user_external_id: str,
    raw_user_input: str,
    local_date: str,
    state_before: Any,
    correction_target: dict[str, Any],
    manager_decision: Any,
) -> UserProvidedKcalEvidenceSeed:
    manager_owned_kcal = manager_owned_user_provided_kcal(manager_decision)
    if manager_owned_kcal is None:
        return UserProvidedKcalEvidenceSeed()
    nutrition_artifact = build_user_provided_kcal_artifact(
        db,
        user_external_id=user_external_id,
        raw_user_input=raw_user_input,
        local_date=local_date,
        user_provided_kcal=manager_owned_kcal,
    )
    budget_summary = None
    if getattr(state_before, "current_budget_view", None) is not None:
        budget_summary = compare_against_budget_tool(
            current_budget_view=state_before.current_budget_view,
            estimated_kcal=manager_owned_kcal,
            replaced_kcal=0,
        )
    user_tool_output = nutrition_tool_output(
        raw_user_input=raw_user_input,
        nutrition_artifact=nutrition_artifact,
        correction_target=correction_target,
        budget_summary=budget_summary,
    )
    user_tool_output["tool_name"] = "user_provided_kcal_evidence"
    user_tool_output["provenance"] = {
        **dict(user_tool_output.get("provenance") or {}),
        "canonical_tool_name": "user_provided_kcal_evidence",
        "truth_owner": "manager_semantic_decision.user_provided_kcal",
        "tool_kind": "manager_owned_user_fact_evidence",
        "mutation_authority": False,
    }
    return UserProvidedKcalEvidenceSeed(
        nutrition_artifact=nutrition_artifact,
        budget_summary=budget_summary,
        tool_results=[user_tool_output],
    )
