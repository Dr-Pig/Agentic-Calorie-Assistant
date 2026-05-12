from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_rescue import run_product_lab_rescue


def build_rescue_memory_context_case_reports() -> list[dict[str, Any]]:
    return [
        _case_report(
            case_id="scoped_memory_context_used_for_rescue",
            fixture_inputs=_fixture_inputs(),
            expect_blocked=False,
        ),
        _case_report(
            case_id="claim_drift_memory_context_rejected",
            fixture_inputs=_claim_drift_inputs(),
            expect_blocked=True,
        ),
    ]


def _case_report(
    *,
    case_id: str,
    fixture_inputs: Mapping[str, Any],
    expect_blocked: bool,
) -> dict[str, Any]:
    artifact = run_product_lab_rescue(fixture_inputs=fixture_inputs)
    context = _context_stage(artifact)
    claim_boundary_blocked = any(
        "consumer_summary_projection." in str(blocker)
        for blocker in artifact.get("blockers") or []
    )
    no_mutation = not any(
        artifact.get(flag) is True
        for flag in (
            "canonical_commit_requested",
            "proposal_committed",
            "rescue_committed",
            "ledger_entry_created",
            "day_budget_mutated",
            "body_plan_mutated",
            "meal_thread_mutated",
            "durable_product_memory_written",
        )
    )
    return {
        "case_id": case_id,
        "status": "pass"
        if _passes(artifact, expect_blocked, claim_boundary_blocked, no_mutation)
        else "blocked",
        "source_rescue_status": str(artifact.get("status") or ""),
        "memory_summary_projection_used": context.get("memory_summary_projection_used")
        is True,
        "memory_signal_summary": dict(_mapping(context.get("memory_signal_summary"))),
        "rescue_history_context_present": bool(
            _mapping(context.get("rescue_history_context"))
        ),
        "adherence_context_present": bool(_mapping(context.get("adherence_context"))),
        "proposal_presented_to_lab": artifact.get("proposal_presented_to_lab") is True,
        "rescue_intent_state_created": artifact.get("rescue_intent_state_created")
        is True,
        "claim_boundary_blocked": claim_boundary_blocked,
        "canonical_commit_requested": artifact.get("canonical_commit_requested") is True,
        "ledger_entry_created": artifact.get("ledger_entry_created") is True,
        "day_budget_mutated": artifact.get("day_budget_mutated") is True,
        "body_plan_mutated": artifact.get("body_plan_mutated") is True,
        "meal_thread_mutated": artifact.get("meal_thread_mutated") is True,
        "durable_product_memory_written": artifact.get(
            "durable_product_memory_written"
        )
        is True,
        "blockers": list(artifact.get("blockers") or []),
    }


def _fixture_inputs() -> dict[str, Any]:
    inputs = build_product_lab_fixture_inputs()
    projection = dict(inputs["memory_summary_projection"])
    projection["preference_profile_summary"] = {
        "freshness_posture": "fresh",
        "accepted_shadow_candidate_ids": ["pref-ramen", "pref-hotpot"],
        "negative_preference_blockers": ["negative-spicy"],
    }
    projection["suppression_summary"] = {
        "suppression_blockers": [
            {
                "candidate_id": "rescue-too-frequent",
                "trigger_type": "rescue_nudge",
                "summary": "User dismissed repeated rescue nudges today.",
            }
        ]
    }
    inputs["memory_summary_projection"] = projection
    inputs["derived_memory_views"] = {
        "rescue_history_summary": {
            "is_durable_memory_truth": False,
            "recent_rescue_count": 2,
            "summary": "User accepted gentler plans after large ramen meals.",
            "rescue_viability_posture": "gentler_plan_preferred",
        },
        "adherence_summary": {
            "is_durable_memory_truth": False,
            "adherence_posture": "responds_to_chat_first_rescue",
        },
    }
    return inputs


def _claim_drift_inputs() -> dict[str, Any]:
    inputs = _fixture_inputs()
    projection = dict(inputs["memory_summary_projection"])
    projection["recommendation_served"] = True
    inputs["memory_summary_projection"] = projection
    return inputs


def _context_stage(artifact: Mapping[str, Any]) -> Mapping[str, Any]:
    for stage in _chain(artifact).get("stage_artifacts") or []:
        if (
            isinstance(stage, Mapping)
            and stage.get("artifact_type") == "rescue_shadow_summary_context_projection"
        ):
            return stage
    return {}


def _chain(artifact: Mapping[str, Any]) -> Mapping[str, Any]:
    for key in ("source_shadow_chain_artifact", "source_chain_artifact", "rescue_chain"):
        value = artifact.get(key)
        if isinstance(value, Mapping):
            return value
    return {}


def _passes(
    artifact: Mapping[str, Any],
    expect_blocked: bool,
    claim_boundary_blocked: bool,
    no_mutation: bool,
) -> bool:
    expected_status = "blocked" if expect_blocked else "pass"
    if artifact.get("status") != expected_status:
        return False
    if expect_blocked != claim_boundary_blocked:
        return False
    return no_mutation


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["build_rescue_memory_context_case_reports"]
