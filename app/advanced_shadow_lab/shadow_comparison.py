from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.shadow_comparison"
)
FIXTURE_TYPE = "advanced_shadow_e2e_fixture_chain_artifact"
DOGFOOD_TYPE = "advanced_shadow_dogfood_replay_artifact"
LIVE_TYPE = "advanced_shadow_recommendation_copy_live_diagnostic_artifact"
FALSE_FLAG_NAMES = (
    "mainline_runtime_connected",
    "mainline_route_or_api_mount_allowed",
    "production_scheduler_delivery_allowed",
    "production_db_migration_allowed",
    "canonical_product_mutation_allowed",
    "delivery_attempted",
    "proactive_sent",
    "scheduler_enabled",
    "live_delivery_allowed",
    "push_or_line_delivery_connected",
    "manager_context_packet_changed",
    "manager_context_injected",
    "recommendation_served",
    "rescue_committed",
    "proposal_committed",
    "durable_product_memory_written",
    "durable_memory_written",
    "mutation_changed",
    "user_facing_behavior_changed",
    "product_readiness_claimed",
)
FALSE_FLAGS = dict.fromkeys(FALSE_FLAG_NAMES, False)
NON_CLAIMS = [
    "not_runtime_activation_evidence",
    "not_product_readiness_evidence",
    "not_user_facing_activation",
    "not_scheduler_delivery",
    "not_canonical_mutation_authority",
    "not_shadow_or_canary_approval",
]


def build_advanced_shadow_comparison_artifact(
    *,
    fixture_chain_artifact: Mapping[str, Any],
    dogfood_replay_artifact: Mapping[str, Any],
    recommendation_copy_live_diagnostic_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    source_inputs = {
        "fixture_chain": (FIXTURE_TYPE, fixture_chain_artifact),
        "dogfood_replay": (DOGFOOD_TYPE, dogfood_replay_artifact),
        "recommendation_copy_live_diagnostic": (
            LIVE_TYPE,
            recommendation_copy_live_diagnostic_artifact,
        ),
    }
    sources = {
        name: _typed(expected_type, artifact)
        for name, (expected_type, artifact) in source_inputs.items()
    }
    invariant = _activation_invariant_summary(sources.values())
    blockers = [
        *_source_type_blockers(source_inputs),
        *[
            f"{row['source']}.{row['flag']}"
            for row in invariant["observed_true_flags"]
        ],
    ]
    return {
        "artifact_type": "advanced_shadow_comparison_artifact",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "owner": "app/advanced_shadow_lab",
        "consumer": "future_advanced_shadow_lab_quality_gate_or_manual_review",
        "retirement_trigger": "approved_advanced_runtime_activation_plan",
        "source_statuses": {
            name: str(artifact.get("status") or "missing")
            for name, artifact in sources.items()
        },
        "surface_status_rows": [
            _terminal_sink_row(sources["fixture_chain"], sources["dogfood_replay"]),
            _live_recommendation_copy_row(
                sources["recommendation_copy_live_diagnostic"]
            ),
        ],
        "activation_invariant_summary": invariant,
        "live_diagnostic_signal": _live_diagnostic_signal(
            sources["recommendation_copy_live_diagnostic"]
        ),
        "blockers": blockers,
        "non_claims": list(NON_CLAIMS),
        **dict(FALSE_FLAGS),
    }


def _typed(expected_type: str, artifact: Mapping[str, Any]) -> Mapping[str, Any]:
    if artifact.get("artifact_type") == expected_type:
        return artifact
    return {"artifact_type": expected_type, "status": "unsupported"}


def _source_type_blockers(
    sources: Mapping[str, tuple[str, Mapping[str, Any]]],
) -> list[str]:
    blockers: list[str] = []
    for name, (expected_type, artifact) in sources.items():
        actual_type = str(artifact.get("artifact_type") or "")
        if actual_type != expected_type:
            blockers.append(
                f"{name}.unsupported_artifact_type:{actual_type or 'missing'}"
            )
    return blockers


def _terminal_sink_row(
    fixture: Mapping[str, Any],
    dogfood: Mapping[str, Any],
) -> dict[str, str]:
    fixture_status = _sink_status(_mapping(fixture.get("terminal_review_sink")))
    dogfood_status = _sink_status(
        _mapping(dogfood.get("terminal_review_sink_summary"))
    )
    return {
        "surface": "terminal_no_send_review_sink",
        "fixture_status": fixture_status,
        "dogfood_status": dogfood_status,
        "live_status": "not_applicable",
        "finding": "no_drift"
        if fixture_status == dogfood_status == "pass"
        else "terminal_sink_variance",
    }


def _live_recommendation_copy_row(live: Mapping[str, Any]) -> dict[str, str]:
    live_status = str(live.get("status") or "missing")
    guard_status = str(_mapping(live.get("output_guard")).get("status") or "")
    if live_status == "pass":
        finding = "live_diagnostic_passed"
    elif guard_status == "blocked":
        finding = "live_diagnostic_model_output_blocked"
    else:
        finding = "live_diagnostic_unavailable"
    return {
        "surface": "recommendation_prompt_reason_copy",
        "fixture_status": "not_applicable",
        "dogfood_status": "not_applicable",
        "live_status": live_status,
        "finding": finding,
    }


def _activation_invariant_summary(
    artifacts: list[Mapping[str, Any]] | Any,
) -> dict[str, Any]:
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
    return {
        "live_invoked": bool(live.get("live_invoked")),
        "live_provider_used": bool(live.get("live_provider_used")),
        "provider_mode": str(live.get("provider_mode") or ""),
        "output_guard_status": str(
            _mapping(live.get("output_guard")).get("status") or ""
        ),
    }


def _sink_status(sink: Mapping[str, Any]) -> str:
    return str(sink.get("status") or "missing")


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_advanced_shadow_comparison_artifact",
]
