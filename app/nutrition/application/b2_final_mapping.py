from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


ESTIMABLE_EXACTNESS_POSTURES = {"exact", "estimated", "provisional"}


def map_b2_final_item_result(
    item_result: Mapping[str, Any],
    *,
    canonical_write_decision: Mapping[str, Any] | None = None,
    interaction_type: str = "food_logging",
) -> dict[str, object]:
    write_allowed = _canonical_write_allowed(canonical_write_decision)
    exactness_posture = str(item_result.get("exactness_posture") or "").strip()
    has_estimate = item_result.get("likely_kcal") is not None or item_result.get("kcal_range") is not None
    followup_role = _followup_role(item_result, exactness_posture=exactness_posture)

    if str(interaction_type or "").strip() == "nutrition_info_query":
        return _mapping(
            external_outcome="no_mutation_query",
            ledger_status="not_applicable",
            mutation_allowed=False,
            followup_role=followup_role,
            reason="query_only_no_mutation",
        )

    if exactness_posture not in ESTIMABLE_EXACTNESS_POSTURES or not has_estimate:
        return _mapping(
            external_outcome="draft",
            ledger_status="excluded_pending_info",
            mutation_allowed=False,
            followup_role="clarification_required",
            reason="unresolved_or_non_estimable",
        )

    if not write_allowed:
        return _mapping(
            external_outcome="draft",
            ledger_status="excluded_pending_info",
            mutation_allowed=False,
            followup_role=followup_role,
            reason="canonical_write_owner_blocked",
        )

    return _mapping(
        external_outcome="logged",
        ledger_status="included",
        mutation_allowed=True,
        followup_role=followup_role,
        reason="estimable_and_write_owner_allowed",
    )


def map_b2_final_item_results(
    item_results: Iterable[Mapping[str, Any]],
    *,
    canonical_write_decision: Mapping[str, Any] | None = None,
    interaction_type: str = "food_logging",
) -> list[dict[str, object]]:
    return [
        map_b2_final_item_result(
            item,
            canonical_write_decision=canonical_write_decision,
            interaction_type=interaction_type,
        )
        for item in item_results
    ]


def _canonical_write_allowed(canonical_write_decision: Mapping[str, Any] | None) -> bool:
    if not isinstance(canonical_write_decision, Mapping):
        return True
    return canonical_write_decision.get("can_write_canonical", True) is not False


def _followup_role(item_result: Mapping[str, Any], *, exactness_posture: str) -> str:
    if exactness_posture not in ESTIMABLE_EXACTNESS_POSTURES:
        return "clarification_required"
    if item_result.get("suggested_followup_question"):
        return "precision_refinement"
    return "none"


def _mapping(
    *,
    external_outcome: str,
    ledger_status: str,
    mutation_allowed: bool,
    followup_role: str,
    reason: str,
) -> dict[str, object]:
    return {
        "final_mapping_owner": "b2_final_mapping",
        "external_outcome": external_outcome,
        "ledger_status": ledger_status,
        "mutation_allowed": mutation_allowed,
        "followup_role": followup_role,
        "reason": reason,
    }


__all__ = ["map_b2_final_item_result", "map_b2_final_item_results"]
