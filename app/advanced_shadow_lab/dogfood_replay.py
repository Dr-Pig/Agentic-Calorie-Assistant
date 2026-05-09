from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain import (
    run_advanced_shadow_e2e_fixture_chain,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.dogfood_replay"
)
SUPPORTED_MEMORY_REPLAY = "runtime_lab_memory_dogfood_replay_review"
FALSE_FLAG_NAMES = (
    "runtime_effect_allowed", "mainline_runtime_connected", "delivery_attempted",
    "proactive_sent", "scheduler_enabled", "live_delivery_allowed",
    "push_or_line_delivery_connected", "durable_product_memory_written",
    "durable_memory_written", "manager_context_packet_changed",
    "manager_context_injected", "recommendation_served", "rescue_committed",
    "proposal_committed",
    "mutation_changed", "user_facing_behavior_changed", "live_provider_used",
    "product_readiness_claimed",
)
FALSE_FLAGS = dict.fromkeys(FALSE_FLAG_NAMES, False)
CLAIM_FLAGS = FALSE_FLAG_NAMES + (
    "canonical_mutation_changed", "memory_store_written", "day_budget_mutated",
    "body_plan_mutated", "meal_thread_mutated",
)
NON_CLAIMS = [
    "not_runtime_activation_evidence", "not_product_readiness_evidence",
    "not_user_facing_activation", "not_scheduler_delivery",
    "not_durable_product_memory", "not_mainline_manager_memory_context_injection",
]


def build_advanced_shadow_dogfood_replay_artifact(
    *,
    memory_dogfood_replay_review: Mapping[str, Any],
    chain_payload: Mapping[str, Any],
) -> dict[str, Any]:
    blockers = _memory_replay_blockers(memory_dogfood_replay_review)
    chain = _not_run_chain() if blockers else run_advanced_shadow_e2e_fixture_chain(
        memory_summary_projection=_mapping(chain_payload.get("memory_summary_projection")),
        recommendation_payload=_mapping(chain_payload.get("recommendation_payload")),
        derived_memory_views=_mapping(chain_payload.get("derived_memory_views")),
        current_budget_view=_mapping(chain_payload.get("current_budget_view")),
        active_body_plan_view=_mapping(chain_payload.get("active_body_plan_view")),
        open_proposals_view=_mapping(chain_payload.get("open_proposals_view")),
        proposal_candidate_output=_mapping(chain_payload.get("proposal_candidate_output")),
        user_control_models=_mapping(chain_payload.get("user_control_models")),
        interaction_plan=_sequence(chain_payload.get("interaction_plan")),
    )
    chain_blockers = [] if blockers else _chain_blockers(chain)
    all_blockers = [*blockers, *chain_blockers]
    return {
        "artifact_type": "advanced_shadow_dogfood_replay_artifact",
        "artifact_schema_version": "1.0",
        "status": "blocked" if all_blockers else "pass",
        "owner": "app/advanced_shadow_lab",
        "consumer": "future_advanced_shadow_live_diagnostic",
        "retirement_trigger": "approved_advanced_runtime_activation_plan",
        "source_memory_artifact_type": memory_dogfood_replay_review.get("artifact_type"),
        "reviewed_case_count": _int(memory_dogfood_replay_review.get("reviewed_case_count")),
        "dogfood_case_summaries": _case_summaries(memory_dogfood_replay_review),
        "advanced_fixture_chain_status": str(chain.get("status") or "not_run"),
        "chain_stage_trace": list(chain.get("stage_trace") or []),
        "terminal_review_sink_summary": _sink_summary(chain),
        "blockers": all_blockers,
        "runtime_connected": bool(memory_dogfood_replay_review.get("runtime_connected")),
        "lab_isolated": bool(memory_dogfood_replay_review.get("lab_isolated")),
        "dogfood_replay_used": True,
        "advanced_fixture_chain_used": not blockers,
        "non_claims": list(NON_CLAIMS),
        **dict(FALSE_FLAGS),
    }


def _memory_replay_blockers(artifact: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if artifact.get("artifact_type") != SUPPORTED_MEMORY_REPLAY:
        blockers.append("memory_dogfood_replay_review.unsupported_artifact_type")
    if artifact.get("status") != "pass":
        blockers.append("memory_dogfood_replay_review.status_blocked")
        blockers.extend(
            f"memory_dogfood_replay_review.{blocker}"
            for blocker in list(artifact.get("blockers") or [])
        )
    blockers.extend(_claim_blockers("memory_dogfood_replay_review", artifact))
    return blockers


def _chain_blockers(chain: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if chain.get("status") != "pass":
        blockers.append("advanced_fixture_chain.status_blocked")
        blockers.extend(f"advanced_fixture_chain.{b}" for b in list(chain.get("blockers") or []))
    blockers.extend(_claim_blockers("advanced_fixture_chain", chain))
    return blockers


def _claim_blockers(prefix: str, artifact: Mapping[str, Any]) -> list[str]:
    return [f"{prefix}.{flag}" for flag in CLAIM_FLAGS if artifact.get(flag) is True]


def _case_summaries(artifact: Mapping[str, Any]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for case in artifact.get("reviewed_case_proposals") or []:
        if isinstance(case, Mapping):
            expected = _mapping(case.get("expected_candidate"))
            trace = _mapping(case.get("trace_fields"))
            review = _mapping(case.get("review"))
            summaries.append({
                "case_id": str(case.get("case_id") or ""),
                "case_type": str(case.get("case_type") or ""),
                "split": str(case.get("split") or ""),
                "expected_outcome": str(review.get("expected_outcome") or ""),
                "candidate_type": str(expected.get("candidate_type") or ""),
                "source_ref_count": len(trace.get("source_refs") or []),
                "human_review_required": bool(expected.get("human_review_required")),
            })
    return summaries


def _sink_summary(chain: Mapping[str, Any]) -> dict[str, Any]:
    sink = _mapping(chain.get("terminal_review_sink"))
    return {"status": str(sink.get("status") or "not_run"), "record_count": _int(sink.get("record_count"))}


def _not_run_chain() -> dict[str, Any]:
    return {"status": "not_run", "stage_trace": [], "terminal_review_sink": {"status": "not_run", "record_count": 0}}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "build_advanced_shadow_dogfood_replay_artifact"]
