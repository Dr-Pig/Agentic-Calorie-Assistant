from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
from app.advanced_shadow_lab.product_lab_control_events import (
    build_new_control_entries,
)
from app.advanced_shadow_lab.product_lab_control_reducer import candidate_states
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.product_lab_control_state"
)

NON_CLAIMS = [
    "not_production_ledger",
    "not_scheduler_state",
    "not_durable_product_memory",
    "not_canonical_mutation",
    "not_mainline_user_control_activation",
]


def build_product_lab_control_state(
    *,
    session_id: str,
    turn_id: str,
    lab_now_minute: int,
    observed_material_signals: list[str],
    candidates: list[Mapping[str, Any]],
    prior_control_journal: list[Mapping[str, Any]] | None = None,
    control_events: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    candidate_rows = [_candidate_row(candidate) for candidate in candidates]
    candidate_ids = {row["candidate_id"] for row in candidate_rows}
    prior_entries = [
        dict(entry)
        for entry in prior_control_journal or []
        if isinstance(entry, Mapping)
    ]
    new_entries, blockers = build_new_control_entries(
        session_id=session_id,
        turn_id=turn_id,
        lab_now_minute=lab_now_minute,
        candidate_ids=candidate_ids,
        prior_entries=prior_entries,
        events=list(control_events or []),
    )
    journal = [*prior_entries, *new_entries]
    states = candidate_states(
        candidates=candidate_rows,
        journal=journal,
        lab_now_minute=lab_now_minute,
        observed_material_signals=observed_material_signals,
    )
    return {
        "artifact_type": "advanced_product_lab_control_state_artifact",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "owner": "app/advanced_shadow_lab/product_lab_control_state.py",
        "consumer": "advanced_product_lab_turn_runner",
        "retirement_trigger": "approved_advanced_product_lab_control_activation_plan",
        "session_id": session_id,
        "turn_id": turn_id,
        "lab_now_minute": lab_now_minute,
        "observed_material_signals": list(observed_material_signals),
        "journal_entry_count": len(journal),
        "journal_entries": journal,
        "candidate_states": states,
        "visible_candidate_count": sum(
            1 for state in states if state["visible_in_lab"] is True
        ),
        "suppressed_candidate_count": sum(
            1 for state in states if state["visible_in_lab"] is False
        ),
        "raw_user_text_semantic_inference_performed": False,
        "blockers": blockers,
        "non_claims": list(NON_CLAIMS),
        **dict(FALSE_FLAGS),
    }


def _candidate_row(candidate: Mapping[str, Any]) -> dict[str, str]:
    return {
        "candidate_id": str(candidate.get("packet_id") or ""),
        "trigger_type": str(candidate.get("trigger_type") or ""),
    }


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "build_product_lab_control_state"]
