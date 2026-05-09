from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.case_pairing import build_case_pairing
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract("advanced_shadow_lab.shadow_comparison")
FIXTURE_TYPE = "advanced_shadow_e2e_fixture_chain_artifact"
DOGFOOD_TYPE = "advanced_shadow_dogfood_replay_artifact"
LIVE_TYPE = "advanced_shadow_recommendation_copy_live_diagnostic_artifact"
RESCUE_LIVE_TYPE = "advanced_shadow_rescue_copy_live_diagnostic_artifact"
OPTIONAL_NOT_RUN_SOURCES = ("recommendation_copy_live_diagnostic", "rescue_copy_live_diagnostic")
FALSE_FLAG_NAMES = (
    "mainline_runtime_connected", "mainline_route_or_api_mount_allowed",
    "production_scheduler_delivery_allowed", "production_db_migration_allowed",
    "canonical_product_mutation_allowed", "delivery_attempted", "proactive_sent",
    "scheduler_enabled", "live_delivery_allowed", "push_or_line_delivery_connected",
    "manager_context_packet_changed", "manager_context_injected",
    "recommendation_served", "rescue_committed", "proposal_committed",
    "durable_product_memory_written", "durable_memory_written", "mutation_changed",
    "user_facing_behavior_changed", "product_readiness_claimed",
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
    baseline_case_artifacts: list[Mapping[str, Any]] | None = None,
    advanced_case_artifacts: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    source_inputs = {
        "fixture_chain": (FIXTURE_TYPE, fixture_chain_artifact),
        "dogfood_replay": (DOGFOOD_TYPE, dogfood_replay_artifact),
        "recommendation_copy_live_diagnostic": (LIVE_TYPE, recommendation_copy_live_diagnostic_artifact),
        "rescue_copy_live_diagnostic": (RESCUE_LIVE_TYPE, rescue_copy_live_diagnostic_artifact or _not_run(RESCUE_LIVE_TYPE)),
    }
    sources = {name: _typed(expected_type, artifact) for name, (expected_type, artifact) in source_inputs.items()}
    invariant = _activation_invariant_summary(sources.values())
    pairing_summary, paired_case_rows = build_case_pairing(
        baseline=list(baseline_case_artifacts or []),
        advanced=list(advanced_case_artifacts or []),
        false_flags=FALSE_FLAG_NAMES,
    )
    blockers = [
        *_source_type_blockers(source_inputs),
        *_source_status_blockers(sources),
        *[f"{row['source']}.{row['flag']}" for row in invariant["observed_true_flags"]],
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
        "source_statuses": {name: str(artifact.get("status") or "missing") for name, artifact in sources.items()},
        "surface_status_rows": [
            _terminal_sink_row(sources["fixture_chain"], sources["dogfood_replay"]),
            _live_copy_row("recommendation_prompt_reason_copy", sources["recommendation_copy_live_diagnostic"]),
            _live_copy_row("rescue_proposal_copy_posture", sources["rescue_copy_live_diagnostic"]),
        ],
        "activation_invariant_summary": invariant,
        "pairing_summary": pairing_summary,
        "paired_case_rows": paired_case_rows,
        "live_diagnostic_signals": {
            "recommendation_copy_live_diagnostic": _live_diagnostic_signal(sources["recommendation_copy_live_diagnostic"]),
            "rescue_copy_live_diagnostic": _live_diagnostic_signal(sources["rescue_copy_live_diagnostic"]),
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


def _terminal_sink_row(fixture: Mapping[str, Any], dogfood: Mapping[str, Any]) -> dict[str, str]:
    fixture_status = _sink_status(_mapping(fixture.get("terminal_review_sink")))
    dogfood_status = _sink_status(_mapping(dogfood.get("terminal_review_sink_summary")))
    return {
        "surface": "terminal_no_send_review_sink",
        "fixture_status": fixture_status,
        "dogfood_status": dogfood_status,
        "live_status": "not_applicable",
        "finding": "no_drift"
        if fixture_status == dogfood_status == "pass"
        else "terminal_sink_variance",
    }


def _live_copy_row(surface: str, live: Mapping[str, Any]) -> dict[str, str]:
    live_status = str(live.get("status") or "missing")
    guard_status = str(_mapping(live.get("output_guard")).get("status") or "")
    if live_status == "pass":
        finding = "live_diagnostic_passed"
    elif live_status == "not_run":
        finding = "live_diagnostic_not_run"
    elif guard_status == "blocked":
        finding = "live_diagnostic_model_output_blocked"
    else:
        finding = "live_diagnostic_unavailable"
    return {
        "surface": surface,
        "fixture_status": "not_applicable",
        "dogfood_status": "not_applicable",
        "live_status": live_status,
        "finding": finding,
    }


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


def _live_diagnostic_signal(live: Mapping[str, Any]) -> dict[str, Any]:
    if live.get("status") == "not_run":
        return _signal(False, False, "not_run", "not_run")
    return _signal(
        bool(live.get("live_invoked")),
        bool(live.get("live_provider_used")),
        str(live.get("provider_mode") or ""),
        str(_mapping(live.get("output_guard")).get("status") or ""),
    )


def _signal(invoked: bool, used: bool, mode: str, guard: str) -> dict[str, Any]:
    return {
        "live_invoked": invoked,
        "live_provider_used": used,
        "provider_mode": mode,
        "output_guard_status": guard,
    }


def _sink_status(sink: Mapping[str, Any]) -> str:
    return str(sink.get("status") or "missing")


def _not_run(artifact_type: str) -> dict[str, str]:
    return {"artifact_type": artifact_type, "status": "not_run"}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "build_advanced_shadow_comparison_artifact"]
