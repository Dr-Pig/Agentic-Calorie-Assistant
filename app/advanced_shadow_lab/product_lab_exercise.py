from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
from app.advanced_shadow_lab.product_lab_exercise_builders import (
    build_lab_exercise_chat_reply,
    build_lab_exercise_event,
    build_lab_exercise_ledger_entry,
    build_lab_exercise_today_projection,
    estimate_exercise_packet,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.product_lab_exercise"
)
ARTIFACT_TYPE = "advanced_product_lab_exercise_budget_artifact"


def run_product_lab_exercise_budget(
    *,
    fixture_inputs: Mapping[str, Any],
    enabled: bool = False,
) -> dict[str, Any]:
    if not enabled:
        return _not_applicable()
    context = _mapping(fixture_inputs.get("exercise_context"))
    extraction = dict(_mapping(context.get("semantic_extraction")))
    if extraction.get("exercise_action") != "create_exercise":
        return _clarification_artifact(extraction, fixture_inputs)

    estimate_packet = estimate_exercise_packet(extraction, fixture_inputs)
    exercise_event = build_lab_exercise_event(extraction, estimate_packet, context)
    ledger_entry = build_lab_exercise_ledger_entry(exercise_event)
    projection = build_lab_exercise_today_projection(
        fixture_inputs, int(ledger_entry["delta_kcal"])
    )
    chat_reply = build_lab_exercise_chat_reply(exercise_event, projection)
    return {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": "pass",
        "workflow_family": "exercise",
        "chat_first": True,
        "semantic_extraction": extraction,
        "estimate": estimate_packet,
        "lab_exercise_event": exercise_event,
        "lab_ledger_entry": ledger_entry,
        "lab_ledger_entry_created": True,
        "lab_today_budget_projection": projection,
        "chat_reply_packet": chat_reply,
        "lab_today_surface_updated": True,
        "mainline_activation_enabled": False,
        "canonical_product_mutation_allowed": False,
        "production_db_migration_allowed": False,
        "body_plan_mutated": False,
        "day_budget_mutated": False,
        "ledger_entry_created": False,
        "durable_product_memory_written": False,
        "served_to_mainline_user": False,
        "blockers": [],
        "best_practice_evidence": _best_practice_evidence(),
        **dict(FALSE_FLAGS),
    }


def _clarification_artifact(
    extraction: Mapping[str, Any],
    fixture_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    projection = build_lab_exercise_today_projection(fixture_inputs, 0)
    return {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": "needs_clarification",
        "workflow_family": "exercise",
        "semantic_extraction": dict(extraction),
        "estimate": {},
        "lab_exercise_event": {},
        "lab_ledger_entry": {},
        "lab_ledger_entry_created": False,
        "lab_today_budget_projection": projection,
        "chat_reply_packet": {
            "message_kind": "clarifying_question",
            "copy": str(
                extraction.get("clarification_question")
                or "可以告訴我運動類型和大概多久嗎？"
            ),
            "canonical_commit_requested": False,
        },
        "mainline_activation_enabled": False,
        "canonical_product_mutation_allowed": False,
        "production_db_migration_allowed": False,
        "body_plan_mutated": False,
        "day_budget_mutated": False,
        "ledger_entry_created": False,
        "durable_product_memory_written": False,
        "blockers": [],
        "best_practice_evidence": _best_practice_evidence(),
        **dict(FALSE_FLAGS),
    }


def _not_applicable() -> dict[str, Any]:
    return {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": "not_applicable",
        "workflow_family": "exercise",
        "blockers": [],
        **dict(FALSE_FLAGS),
    }


def _best_practice_evidence() -> dict[str, Any]:
    return {
        "required": True,
        "sources_checked": [
            "CDC physical-activity MET intensity guidance",
            "Compendium of Physical Activities MET tables",
            "OpenAI Agents SDK guardrails and workflow guidance",
        ],
        "adopted_guidance": [
            "semantic extraction remains an LLM-owned fixture output",
            "calorie math is deterministic after extraction",
            "lab-local action artifacts stay behind an activation wall",
        ],
        "rejected_guidance": [
            "production persistence before exercise writeback activation",
            "raw user text keyword parsing as semantic truth",
        ],
        "how_the_design_changed": (
            "U is implemented as a lab-local complete product slice with "
            "artifact-only event and ledger records."
        ),
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "run_product_lab_exercise_budget"]
