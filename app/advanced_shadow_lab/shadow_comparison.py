from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.case_pairing import build_case_pairing
from app.advanced_shadow_lab.no_send_control_comparison import (
    compare_no_send_control_paths,
    control_blockers_if_comparable,
    terminal_sink_row,
)
from app.advanced_shadow_lab.chat_ux_copy_alignment import (
    chat_packet_copy_alignment_blockers,
    chat_packet_copy_alignment_row,
)
from app.advanced_shadow_lab.shadow_comparison_live_rows import (
    live_copy_row,
    live_diagnostic_signal,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract("advanced_shadow_lab.shadow_comparison")
FIXTURE_TYPE = "advanced_shadow_e2e_fixture_chain_artifact"
DOGFOOD_TYPE = "advanced_shadow_dogfood_replay_artifact"
LIVE_TYPE = "advanced_shadow_recommendation_copy_live_diagnostic_artifact"
RESCUE_LIVE_TYPE = "advanced_shadow_rescue_copy_live_diagnostic_artifact"
PROACTIVE_LIVE_TYPE = "advanced_shadow_proactive_copy_live_diagnostic_artifact"
OPTIONAL_NOT_RUN_SOURCES = (
    "recommendation_copy_live_diagnostic", "rescue_copy_live_diagnostic",
    "proactive_copy_live_diagnostic",
)
FALSE_FLAG_NAMES = (
    "mainline_runtime_connected", "mainline_route_or_api_mount_allowed",
    "production_scheduler_delivery_allowed", "production_db_migration_allowed",
    "canonical_product_mutation_allowed", "delivery_attempted", "proactive_sent",
    "scheduler_enabled", "scheduler_enqueued", "live_delivery_allowed", "push_or_line_delivery_connected",
    "manager_context_packet_changed", "manager_context_injected",
    "recommendation_served", "rescue_committed", "proposal_committed",
    "durable_product_memory_written", "durable_memory_written", "durable_snooze_written",
    "mutation_changed", "user_facing_behavior_changed", "product_readiness_claimed",
)
FALSE_FLAGS = dict.fromkeys(FALSE_FLAG_NAMES, False)
NON_CLAIMS = [
    "not_runtime_activation_evidence", "not_product_readiness_evidence",
    "not_user_facing_activation", "not_scheduler_delivery",
    "not_canonical_mutation_authority", "not_shadow_or_canary_approval",
]


def build_advanced_shadow_comparison_artifact(
    *,
    fixture_chain_artifact: Mapping[str, Any],
    dogfood_replay_artifact: Mapping[str, Any],
    recommendation_copy_live_diagnostic_artifact: Mapping[str, Any],
    rescue_copy_live_diagnostic_artifact: Mapping[str, Any] | None = None,
    proactive_copy_live_diagnostic_artifact: Mapping[str, Any] | None = None,
    baseline_case_artifacts: list[Mapping[str, Any]] | None = None,
    advanced_case_artifacts: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    source_inputs = {
        "fixture_chain": (FIXTURE_TYPE, fixture_chain_artifact),
        "dogfood_replay": (DOGFOOD_TYPE, dogfood_replay_artifact),
        "recommendation_copy_live_diagnostic": (LIVE_TYPE, recommendation_copy_live_diagnostic_artifact),
        "rescue_copy_live_diagnostic": (RESCUE_LIVE_TYPE, rescue_copy_live_diagnostic_artifact or _not_run(RESCUE_LIVE_TYPE)),
        "proactive_copy_live_diagnostic": (PROACTIVE_LIVE_TYPE, proactive_copy_live_diagnostic_artifact or _not_run(PROACTIVE_LIVE_TYPE)),
    }
    sources = {name: _typed(expected_type, artifact) for name, (expected_type, artifact) in source_inputs.items()}
    source_statuses = {name: str(artifact.get("status") or "missing") for name, artifact in sources.items()}
    invariant = _activation_invariant_summary(sources.values())
    control_comparison, control_row, control_blockers = compare_no_send_control_paths(
        fixture_sink=_mapping(sources["fixture_chain"].get("terminal_review_sink")),
        dogfood_sink=_mapping(sources["dogfood_replay"].get("terminal_review_sink_summary")))
    pairing_summary, paired_case_rows = build_case_pairing(
        baseline=list(baseline_case_artifacts or []), advanced=list(advanced_case_artifacts or []),
        false_flags=FALSE_FLAG_NAMES)
    blockers = [
        *_source_type_blockers(source_inputs),
        *_source_status_blockers(sources),
        *chat_packet_copy_alignment_blockers(sources["fixture_chain"]),
        *[f"{row['source']}.{row['flag']}" for row in invariant["observed_true_flags"]],
        *control_blockers_if_comparable(source_statuses=source_statuses, blockers=control_blockers),
        *pairing_summary["schema_gaps"],
        *pairing_summary["activation_violations"],
    ]
    return {
        "artifact_type": "advanced_shadow_comparison_artifact",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "owner": "app/advanced_shadow_lab",
        "consumer": "future_advanced_shadow_lab_quality_gate_or_manual_review",
        "retirement_trigger": "approved_advanced_runtime_activation_plan",
        "source_statuses": source_statuses,
        "surface_status_rows": [
            terminal_sink_row(fixture_chain=sources["fixture_chain"], dogfood_replay=sources["dogfood_replay"]),
            control_row,
            chat_packet_copy_alignment_row(sources["fixture_chain"]),
            live_copy_row("recommendation_prompt_reason_copy", sources["recommendation_copy_live_diagnostic"]),
            live_copy_row("rescue_proposal_copy_posture", sources["rescue_copy_live_diagnostic"]),
            live_copy_row("proactive_chat_copy_posture", sources["proactive_copy_live_diagnostic"]),
        ],
        "no_send_control_path_comparison": control_comparison,
        "activation_invariant_summary": invariant,
        "pairing_summary": pairing_summary,
        "paired_case_rows": paired_case_rows,
        "live_diagnostic_signals": {
            "recommendation_copy_live_diagnostic": live_diagnostic_signal(sources["recommendation_copy_live_diagnostic"]),
            "rescue_copy_live_diagnostic": live_diagnostic_signal(sources["rescue_copy_live_diagnostic"]),
            "proactive_copy_live_diagnostic": live_diagnostic_signal(sources["proactive_copy_live_diagnostic"]),
        },
        "blockers": blockers,
        "runtime_connected": False,
        "non_claims": list(NON_CLAIMS),
        **dict(FALSE_FLAGS),
    }


def _typed(expected_type: str, artifact: Mapping[str, Any]) -> Mapping[str, Any]:
    if artifact.get("status") == "not_run" and artifact.get("artifact_type") == expected_type:
        return artifact
    if artifact.get("artifact_type") == expected_type:
        return artifact
    return {"artifact_type": expected_type, "status": "unsupported"}


def _source_type_blockers(sources: Mapping[str, tuple[str, Mapping[str, Any]]]) -> list[str]:
    blockers: list[str] = []
    for name, (expected_type, artifact) in sources.items():
        actual_type = str(artifact.get("artifact_type") or "")
        if artifact.get("status") == "not_run" and actual_type == expected_type:
            continue
        if actual_type != expected_type:
            blockers.append(f"{name}.unsupported_artifact_type:{actual_type or 'missing'}")
    return blockers


def _source_status_blockers(sources: Mapping[str, Mapping[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for name, artifact in sources.items():
        status = str(artifact.get("status") or "missing")
        if status == "pass" or status == "unsupported":
            continue
        if status == "not_run" and name in OPTIONAL_NOT_RUN_SOURCES:
            continue
        blockers.append(f"{name}.status_{status}")
    return blockers


def _activation_invariant_summary(artifacts: list[Mapping[str, Any]] | Any) -> dict[str, Any]:
    observed: list[dict[str, str]] = []
    for artifact in artifacts:
        artifact_type = str(artifact.get("artifact_type") or "unknown_artifact")
        for flag in FALSE_FLAG_NAMES:
            if artifact.get(flag) is True:
                observed.append({"source": artifact_type, "flag": flag})
    return {
        "expected_false_flags": list(FALSE_FLAG_NAMES),
        "observed_true_flags": observed,
    }


def _not_run(artifact_type: str) -> dict[str, str]:
    return {"artifact_type": artifact_type, "status": "not_run"}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "build_advanced_shadow_comparison_artifact"]
