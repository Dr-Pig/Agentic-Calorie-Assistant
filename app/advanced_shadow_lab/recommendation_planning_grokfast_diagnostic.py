from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.model_profiles import (
    ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
)
from app.recommendation.application.planning_fixture_provider import (
    planning_fixture_output_blockers,
)
from app.shared.infra.json_artifacts import write_json_artifact


ARTIFACT_TYPE = "advanced_product_lab_recommendation_planning_grokfast_diagnostic"
STAGE = "advanced_product_lab_recommendation_planning_diagnostic"
SYSTEM_PROMPT = (
    "Return JSON only for a recommendation planning diagnostic. Produce only "
    "recommendation_context_result, candidate_spec, non_serve_flags, and "
    "claim_scope. Do not rank candidates, filter candidates, select offers, "
    "mutate state, or infer from raw chat text."
)


def run_recommendation_planning_grokfast_diagnostic(
    *,
    planning_seed: Mapping[str, Any],
    provider: Any,
    provider_mode: str,
    live_invoked: bool,
    provider_profile_id: str = ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    output_path: Path | None = None,
) -> dict[str, Any]:
    input_blockers = planning_fixture_output_blockers(planning_seed)
    provider_result: dict[str, Any] = {}
    provider_trace: dict[str, Any] = {}
    provider_error: dict[str, Any] = {}
    provider_invoked = False
    if not input_blockers:
        provider_invoked = True
        try:
            provider_result, provider_trace = asyncio.run(
                _invoke_provider(provider, planning_seed)
            )
        except Exception as exc:
            provider_error = {"type": type(exc).__name__, "message": str(exc)[:300]}
    output_guard = (
        {"status": "not_run", "blockers": []}
        if input_blockers or provider_error
        else _output_guard(provider_result)
    )
    blockers = [*input_blockers, *output_guard["blockers"]]
    status = "provider_error" if provider_error else "blocked" if blockers else "pass"
    artifact = {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": status,
        "stage": STAGE,
        "provider_mode": provider_mode,
        "provider_profile_id": provider_profile_id,
        "diagnostic_evidence_class": _evidence_class(
            live_invoked=live_invoked,
            status=status,
        ),
        "live_invoked": live_invoked,
        "provider_invoked": provider_invoked,
        "provider_readiness": _readiness(provider),
        "provider_trace": provider_trace,
        "provider_error": provider_error,
        "planning_seed_summary": _seed_summary(planning_seed),
        "provider_result": provider_result,
        "output_guard": output_guard,
        "live_grokfast_diagnostic_pass": live_invoked and status == "pass",
        **_activation_flags(),
        "blockers": blockers,
    }
    if output_path is not None:
        write_json_artifact(output_path, artifact)
    return artifact


def blocked_not_invoked_recommendation_planning_grokfast_artifact(
    *,
    reason: str,
    provider_profile_id: str = ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    output_path: Path | None = None,
) -> dict[str, Any]:
    artifact = {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": "blocked",
        "stage": STAGE,
        "provider_mode": "not_invoked",
        "provider_profile_id": provider_profile_id,
        "diagnostic_evidence_class": "not_invoked",
        "live_invoked": False,
        "provider_invoked": False,
        "live_grokfast_diagnostic_pass": False,
        **_activation_flags(),
        "blockers": [reason],
    }
    if output_path is not None:
        write_json_artifact(output_path, artifact)
    return artifact


def recommendation_planning_live_provider_payload(
    planning_seed: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "stage": STAGE,
        "planning_seed_summary": _seed_summary(planning_seed),
        "constraints": {
            "claim_scope_required": "diagnostic_only",
            "planning_only": True,
            "candidate_retrieval_allowed": False,
            "offer_synthesis_allowed": False,
            "mutation_or_commit_allowed": False,
            "serve_to_mainline_allowed": False,
        },
    }


async def _invoke_provider(
    provider: Any,
    planning_seed: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    result, trace = await provider.complete_with_trace(
        system_prompt=SYSTEM_PROMPT,
        user_payload=recommendation_planning_live_provider_payload(planning_seed),
        stage=STAGE,
        max_tokens=700,
    )
    return _dict(result), _dict(trace)


def _output_guard(output: Mapping[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if output.get("claim_scope") != "diagnostic_only":
        blockers.append("claim_scope.not_diagnostic_only")
    pseudo_planning = {
        "recommendation_context_result": _mapping(
            output.get("recommendation_context_result")
        ),
        "candidate_spec": _mapping(output.get("candidate_spec")),
    }
    blockers.extend(planning_fixture_output_blockers(pseudo_planning))
    for key in ("allowed_candidate_ids", "selected_primary", "ranking_result"):
        if key in output:
            blockers.append(f"output.forbidden_field:{key}")
    flags = _mapping(output.get("non_serve_flags"))
    if flags.get("mainline_activation_enabled") is not False and flags.get("serve_to_mainline_allowed") is not False:
        blockers.append("non_serve_flags.mainline_activation_enabled_not_false")
    if flags.get("canonical_product_mutation_allowed") is not False and flags.get("mutation_or_commit_allowed") is not False:
        blockers.append("non_serve_flags.canonical_product_mutation_allowed_not_false")
    return {"status": "blocked" if blockers else "pass", "blockers": blockers}


def _seed_summary(planning_seed: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "artifact_type": str(planning_seed.get("artifact_type") or ""),
        "recommendation_context_result": dict(
            _mapping(planning_seed.get("recommendation_context_result"))
        ),
        "candidate_spec": dict(_mapping(planning_seed.get("candidate_spec"))),
    }


def _evidence_class(*, live_invoked: bool, status: str) -> str:
    if status != "pass":
        return "non_claim_diagnostic"
    return "live_grokfast" if live_invoked else "fixture_provider_contract"


def _readiness(provider: Any) -> dict[str, Any]:
    readiness = getattr(provider, "readiness", None)
    if callable(readiness):
        return _dict(readiness())
    return {}


def _activation_flags() -> dict[str, bool]:
    return {
        "mainline_activation_enabled": False,
        "served_to_mainline_user": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}
