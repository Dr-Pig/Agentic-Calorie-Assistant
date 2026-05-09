from __future__ import annotations

from typing import Any, Mapping

from app.rescue.application.proposal_shaping_output_validator_shadow import (
    validate_rescue_proposal_shaping_output_shadow,
)
from app.rescue.domain.shadow_status import RESCUE_SHADOW_NON_RUNTIME_FLAGS
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.proposal_shaping_fake_runner"
)


def run_rescue_proposal_shaping_fake(
    *,
    proposal_shaping_input_shadow_packet: Mapping[str, Any],
    candidate_output: Mapping[str, Any],
) -> dict[str, Any]:
    validation = validate_rescue_proposal_shaping_output_shadow(
        proposal_shaping_input_shadow_packet=proposal_shaping_input_shadow_packet,
        candidate_output=candidate_output,
    )
    status = str(validation.get("status") or "blocked")
    return {
        "artifact_type": "rescue_proposal_shaping_fake_runner_artifact",
        "artifact_schema_version": "1.0",
        "status": status,
        "owner": "app/rescue",
        "consumer": "rescue_proposal_shaping_edd_provider_prep",
        "retirement_trigger": "approved_rescue_proposal_shaping_live_diagnostic_runner",
        "runner_stage": "fake",
        "diagnostic_only": True,
        "candidate_output_supplied": True,
        "candidate_output_consumed": status != "blocked",
        "candidate_output_included": False,
        "raw_candidate_output_included": False,
        "validation_status": status,
        "validation": validation,
        "blockers": list(validation.get("blockers") or []),
        "live_llm_invoked": False,
        "provider_called": False,
        "runtime_effect_allowed": False,
        "manager_context_injected": False,
        "rescue_committed": False,
        "proposal_committed": False,
        "ledger_entry_created": False,
        "day_budget_mutated": False,
        "body_plan_mutated": False,
        "meal_thread_mutated": False,
        "durable_memory_written": False,
        "proactive_sent": False,
        "recommendation_served": False,
        "non_claims": [
            "not_live_llm_evidence",
            "not_user_facing_proposal",
            "not_rescue_proposal_commit",
            "not_runtime_activation",
        ],
        **dict(RESCUE_SHADOW_NON_RUNTIME_FLAGS),
    }


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "run_rescue_proposal_shaping_fake",
]
