from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import os
import random
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
import sys
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_debug_routes import build_accurate_intake_debug_payload
from app.composition.canonical_persistence import commit_meal_payload_to_canonical
from app.composition.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date
from app.database import get_or_create_user
from app.intake.infrastructure.models import MealItemRecord
from app.models import Base
from app.runtime.agent.founder_live_manager_contract import (
    FOUNDER_LIVE_MANAGER_SCHEMA_NAME,
    FOUNDER_LIVE_MANAGER_SCHEMA_VERSION,
    FOUNDER_LIVE_MANAGER_REQUIRED_FIELDS,
    FOUNDER_LIVE_MANAGER_TRANSPORT_POLICY,
    founder_live_manager_contract_constraints,
)
from app.runtime.contracts.trace import MANAGER_LOOP_STAGE
from app.shared.contracts.readiness_claim import build_readiness_claim
from app.shared.contracts.intake_payloads import CommitRequestCandidate, MealItemPayload


ARTIFACT_PATH = ROOT / "artifacts" / "accurate_intake_mvp_live_diagnostic.json"
DEFAULT_DB_PATH = ROOT / "artifacts" / "accurate_intake_mvp_live_diagnostic.sqlite3"
DEFAULT_OFFLINE_REPLAY_ARTIFACT = ROOT / "artifacts" / "accurate_intake_mvp_offline_shadow_replay.json"
DEFAULT_LOCAL_DATE = "2026-05-02"
DEFAULT_ACCURATE_INTAKE_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID = (
    "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic"
)
ACTIVE_ENTRYPOINT = "app.composition.intake_turn_orchestrator.execute_intake_turn"
STAGE_PROVIDER_HEALTH_SMOKE = "provider_health_smoke"
STAGE_SCHEMA_CONTRACT_PROBE = "schema_contract_probe"
STAGE_FAKE_PROVIDER_ACTIVE_RUNTIME_GATE = "fake_provider_active_runtime_gate"
STAGE_SINGLE_CASE_LIVE_PROBE = "single_case_live_probe"
STAGE_FULL_SUITE_LIVE_DIAGNOSTIC = "full_suite_live_diagnostic"
STAGE_ALL = "all"
ORDERED_STAGE_IDS = (
    STAGE_PROVIDER_HEALTH_SMOKE,
    STAGE_SCHEMA_CONTRACT_PROBE,
    STAGE_FAKE_PROVIDER_ACTIVE_RUNTIME_GATE,
    STAGE_SINGLE_CASE_LIVE_PROBE,
    STAGE_FULL_SUITE_LIVE_DIAGNOSTIC,
)

_FORBIDDEN_CLAIMS = [
    "product_ready",
    "self_use_ready",
    "live_ready",
    "user_facing_ready",
    "mutation_ready",
    "production_ready",
    "runtime_web_activation_ready",
]

_PROVIDER_PROFILES: dict[str, dict[str, Any]] = {
    DEFAULT_ACCURATE_INTAKE_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID: {
        "provider_profile_id": DEFAULT_ACCURATE_INTAKE_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID,
        "provider": "builderspace",
        "model": "grok-4-fast",
        "provider_profile_role": "accurate_intake_mvp_live_diagnostic",
        "cost_tier": "low",
        "production_selected": False,
        "not_production_selection": True,
        "readiness_owner": False,
        "temperature": 0.0,
        "schema_name": FOUNDER_LIVE_MANAGER_SCHEMA_NAME,
        "schema_version": FOUNDER_LIVE_MANAGER_SCHEMA_VERSION,
        "transport_policy": {
            "primary": FOUNDER_LIVE_MANAGER_TRANSPORT_POLICY,
            "fallback": "json_schema",
            "forbidden_as_success": ["plain_json_object_without_schema_validation"],
        },
    },
}


@dataclass(frozen=True)
class LiveStep:
    turn: int
    kind: str
    text: str
    script: dict[str, Any]


@dataclass(frozen=True)
class LiveCase:
    case_id: str
    description: str
    user_external_id: str
    body_plan_seeded: bool
    steps: tuple[LiveStep, ...]
    seed_kind: str | None = None
    turn_limit_max_turn: int | None = None
    original_turn_count: int | None = None


class AccurateIntakeLiveDiagnosticProvider:
    """Adds diagnostic profile metadata and shared manager contract constraints."""

    def __init__(
        self,
        provider: Any,
        *,
        profile: dict[str, Any],
        live_invoked: bool,
        provider_request_timeout_ms: int = 180000,
        provider_request_retry_count: int = 0,
        provider_request_retry_backoff_ms: int = 0,
        provider_request_retry_jitter_ms: int = 0,
    ) -> None:
        self._provider = provider
        self.profile = dict(profile)
        self.live_invoked = live_invoked
        self.invocations: list[dict[str, Any]] = []
        self.provider_request_timeout_ms = max(1, int(provider_request_timeout_ms))
        self.provider_request_retry_count = max(0, int(provider_request_retry_count))
        self.provider_request_retry_backoff_ms = max(0, int(provider_request_retry_backoff_ms))
        self.provider_request_retry_jitter_ms = max(0, int(provider_request_retry_jitter_ms))

    def begin_step(self, step_script: dict[str, Any]) -> None:
        if hasattr(self._provider, "begin_step"):
            self._provider.begin_step(step_script)

    def readiness(self) -> dict[str, Any]:
        readiness = self._provider.readiness() if hasattr(self._provider, "readiness") else {}
        return {
            **(readiness if isinstance(readiness, dict) else {}),
            "provider_profile_id": self.profile["provider_profile_id"],
            "provider_profile_model": self.profile["model"],
            "provider_profile_role": self.profile["provider_profile_role"],
            "production_selected": False,
            "not_production_selection": True,
            "readiness_owner": False,
        }

    async def complete_with_trace(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        stage = str(kwargs.get("stage") or "")
        kwargs = _with_accurate_intake_live_contract_constraints(kwargs, profile=self.profile)
        max_attempts = self.provider_request_retry_count + 1
        retry_attempts: list[dict[str, Any]] = []
        for attempt_index in range(1, max_attempts + 1):
            started = datetime.now(UTC)
            try:
                payload, trace = await asyncio.wait_for(
                    self._provider.complete_with_trace(**kwargs),
                    timeout=max(0.001, self.provider_request_timeout_ms / 1000),
                )
            except Exception as exc:
                elapsed_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
                retryable = _is_retryable_provider_exception(exc)
                error_trace = _provider_error_trace(exc, stage=stage, profile=self.profile)
                error_trace.update(
                    {
                        "attempt_index": attempt_index,
                        "attempt_count": attempt_index,
                        "max_attempt_count": max_attempts,
                        "latency_ms": elapsed_ms,
                        "timeout_budget_ms": self.provider_request_timeout_ms,
                        "retryable": retryable,
                        "retry_policy_applied": attempt_index > 1,
                        "result_kind": "timeout_after_retry"
                        if retryable and attempt_index == max_attempts and max_attempts > 1
                        else "timeout_first_attempt",
                    }
                )
                retry_attempts.append(error_trace)
                self.invocations.append(error_trace)
                if retryable and attempt_index < max_attempts:
                    await asyncio.sleep(self._retry_delay_seconds(attempt_index))
                    continue
                raise
            elapsed_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
            result_kind = "pass_after_retry" if attempt_index > 1 else "strict_pass_first_attempt"
            enriched_trace = {
                **_dict(trace),
                "provider_profile_id": self.profile["provider_profile_id"],
                "provider_profile_model": self.profile["model"],
                "provider_profile_role": self.profile["provider_profile_role"],
                "transport_policy": self.profile["transport_policy"],
                "schema_name": self.profile["schema_name"],
                "schema_version": self.profile["schema_version"],
                "production_selected": False,
                "not_production_selection": True,
                "live_llm_invoked": self.live_invoked,
                "latency_ms": elapsed_ms,
                "timeout_budget_ms": self.provider_request_timeout_ms,
                "attempt_count": attempt_index,
                "retry_policy_applied": attempt_index > 1,
                "result_kind": result_kind,
                "retry_attempts": retry_attempts,
            }
            self.invocations.append(
                {
                    "stage": stage,
                    "provider_profile_id": self.profile["provider_profile_id"],
                    "provider_profile_model": self.profile["model"],
                    "provider_profile_role": self.profile["provider_profile_role"],
                    "transport_policy": self.profile["transport_policy"],
                    "schema_name": self.profile["schema_name"],
                    "schema_version": self.profile["schema_version"],
                    "live_llm_invoked": self.live_invoked,
                    "latency_ms": elapsed_ms,
                    "timeout_budget_ms": self.provider_request_timeout_ms,
                    "attempt_count": attempt_index,
                    "retry_policy_applied": attempt_index > 1,
                    "result_kind": result_kind,
                    "failure_family": None,
                    "provider_trace": enriched_trace,
                }
            )
            return payload, enriched_trace
        raise RuntimeError("provider retry loop exited without result")

    def _retry_delay_seconds(self, attempt_index: int) -> float:
        backoff = (self.provider_request_retry_backoff_ms / 1000) * attempt_index
        jitter = random.uniform(0, self.provider_request_retry_jitter_ms / 1000) if self.provider_request_retry_jitter_ms else 0.0
        return backoff + jitter


class ScriptedAccurateIntakeLiveProvider:
    """Deterministic fake provider; script state is injected by the case runner, not inferred from text."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self._current_step: dict[str, Any] = {}

    def begin_step(self, step_script: dict[str, Any]) -> None:
        self._current_step = dict(step_script)

    def readiness(self) -> dict[str, Any]:
        return {
            "provider": "scripted_accurate_intake_live_fixture",
            "configured": True,
            "live_llm_invoked": False,
            "runner_inferred_semantics": False,
        }

    async def complete_with_trace(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        user_payload = _dict(kwargs.get("user_payload"))
        available_tools = {str(item) for item in _list(user_payload.get("available_tools"))}
        round_index = int(user_payload.get("round_index") or 0)
        self.calls.append(
            {
                "available_tools": sorted(available_tools),
                "round_index": round_index,
                "script_step_kind": self._current_step.get("kind"),
            }
        )
        if {"read_body_plan", "read_day_budget"}.intersection(available_tools):
            return self._entry_decision(), self._trace("entry_decision")
        return self._execution_decision(
            available_tools=available_tools,
            round_index=round_index,
            user_payload=user_payload,
        ), self._trace("execution_decision")

    def _entry_decision(self) -> dict[str, Any]:
        entry_intent = str(self._current_step.get("entry_intent") or "log_meal")
        if entry_intent == "answer_remaining_budget":
            return self._final(
                intent_type="answer_remaining_budget",
                current_turn_intent="answer_remaining_budget",
                final_action="answer_only",
                workflow_effect="answer_only",
                mutation_intent_candidate="ledger_read",
                evidence_posture="read_only_state",
                estimation_posture="not_applicable",
            )
        if entry_intent == "onboarding_required":
            return self._final(
                intent_type="onboarding_required",
                current_turn_intent="answer_remaining_budget",
                final_action="onboarding_required",
                workflow_effect="answer_only",
                mutation_intent_candidate="no_mutation",
                evidence_posture="read_only_state",
                estimation_posture="not_applicable",
            )
        return self._final(
            intent_type="log_meal",
            current_turn_intent=str(self._current_step.get("semantic_intent") or "log_meal"),
            final_action="commit",
            workflow_effect="route_to_intake",
            mutation_intent_candidate="canonical_write",
            target_attachment={"mode": self._current_step.get("target_mode") or "new_meal"},
            evidence_posture="needs_tool_evidence",
            estimation_posture="estimable",
        )

    def _execution_decision(
        self,
        *,
        available_tools: set[str],
        round_index: int,
        user_payload: dict[str, Any],
    ) -> dict[str, Any]:
        final_action = str(self._current_step.get("final_action") or "commit")
        if final_action == "ask_followup":
            return self._final(
                intent_type="log_meal",
                current_turn_intent="log_meal",
                final_action="ask_followup",
                workflow_effect="ask_followup",
                mutation_intent_candidate="no_mutation",
                target_attachment={"mode": "draft_thread"},
                evidence_posture="composition_unknown",
                estimation_posture="composition_unknown_basket",
                followup_question=str(self._current_step.get("followup_question") or "請補充品項。"),
            )
        if (
            self._current_step.get("target_canonical_name")
            and round_index == 0
            and "resolve_correction_target" in available_tools
        ):
            return {
                "manager_action": "call_tools",
                "response_mode": "tool_call",
                "tool_calls": [
                    {
                        "name": "resolve_correction_target",
                        "arguments": self._target_proposal(user_payload=user_payload),
                    }
                ],
                "evidence_posture": "target_resolution_pending",
                "semantic_decision": {
                    "current_turn_intent": "correct_meal",
                    "final_action_candidate": final_action,
                    "estimation_posture": "target_resolution_pending",
                    "mutation_intent_candidate": "correction_write",
                },
            }
        if (
            self._current_step.get("target_canonical_name")
            and self._current_step.get("correction_operation") != "remove_item"
            and _has_tool_result(user_payload, "resolve_correction_target")
            and not _has_tool_result(user_payload, "estimate_nutrition")
            and "estimate_nutrition" in available_tools
        ):
            return {
                "manager_action": "call_tools",
                "response_mode": "tool_call",
                "tool_calls": [{"name": "estimate_nutrition"}],
                "evidence_posture": "evidence_pending",
                "semantic_decision": {
                    "current_turn_intent": "correct_meal",
                    "final_action_candidate": final_action,
                    "estimation_posture": "pending_tool_call",
                    "mutation_intent_candidate": "correction_write",
                },
            }
        if (
            self._current_step.get("correction_operation") == "remove_item"
            and not _has_tool_result(user_payload, "resolve_correction_target")
            and "estimate_nutrition" in available_tools
        ):
            return {
                "manager_action": "call_tools",
                "response_mode": "tool_call",
                "tool_calls": [{"name": "estimate_nutrition"}],
                "evidence_posture": "evidence_pending",
                "semantic_decision": {
                    "current_turn_intent": "correct_meal",
                    "final_action_candidate": final_action,
                    "estimation_posture": "pending_tool_call",
                    "mutation_intent_candidate": "correction_write",
                },
            }
        if round_index == 0 and "estimate_nutrition" in available_tools:
            calls = [{"name": "estimate_nutrition"}]
            if self._current_step.get("compare_budget") and "compare_against_budget" in available_tools:
                calls.append({"name": "compare_against_budget"})
            return {
                "manager_action": "call_tools",
                "response_mode": "tool_call",
                "tool_calls": calls,
                "evidence_posture": "evidence_pending",
                "semantic_decision": {
                    "current_turn_intent": str(self._current_step.get("semantic_intent") or "log_meal"),
                    "final_action_candidate": final_action,
                    "estimation_posture": "pending_tool_call",
                    "mutation_intent_candidate": str(self._current_step.get("mutation_intent") or "canonical_write"),
                },
            }
        return self._final(
            intent_type="log_meal",
            current_turn_intent=str(self._current_step.get("semantic_intent") or "log_meal"),
            final_action=final_action,
            workflow_effect=str(self._current_step.get("workflow_effect") or final_action),
            mutation_intent_candidate=str(self._current_step.get("mutation_intent") or "canonical_write"),
            target_attachment={"mode": self._current_step.get("target_mode") or "new_meal"},
            evidence_posture="tool_evidence_present",
            estimation_posture="estimable",
            followup_question=str(self._current_step.get("followup_question") or ""),
        )

    def _target_proposal(self, *, user_payload: dict[str, Any]) -> dict[str, Any]:
        target_name = str(self._current_step.get("target_canonical_name") or "").strip()
        proposal: dict[str, Any] = {}
        if target_name:
            proposal["canonical_name"] = target_name
        target_reference = (
            _dict(_dict(_dict(user_payload.get("resolved_state")).get("injected_context")).get("TARGET_MEAL_REFERENCE"))
        )
        if target_reference.get("meal_thread_id") is not None:
            proposal["meal_thread_id"] = target_reference.get("meal_thread_id")
        for candidate in _list(target_reference.get("item_candidates")):
            item = _dict(candidate)
            if target_name and str(item.get("canonical_name") or "").casefold() != target_name.casefold():
                continue
            if item.get("meal_item_id") is not None:
                proposal["meal_item_id"] = item.get("meal_item_id")
            if item.get("canonical_name") is not None:
                proposal["canonical_name"] = item.get("canonical_name")
            break
        proposal["target_proposal_source"] = "manager_structured_tool_arguments"
        return proposal

    def _final(
        self,
        *,
        intent_type: str,
        current_turn_intent: str,
        final_action: str,
        workflow_effect: str,
        mutation_intent_candidate: str,
        target_attachment: dict[str, Any] | None = None,
        evidence_posture: str,
        estimation_posture: str,
        followup_question: str = "",
    ) -> dict[str, Any]:
        target = dict(target_attachment or {"mode": "none"})
        if self._current_step.get("correction_operation"):
            target["correction_operation"] = self._current_step.get("correction_operation")
        if self._current_step.get("target_canonical_name"):
            target["canonical_name"] = self._current_step.get("target_canonical_name")
        answer_contract = {"reply_text": workflow_effect}
        if self._current_step.get("correction_operation"):
            answer_contract["correction_operation"] = self._current_step.get("correction_operation")
        if followup_question:
            answer_contract["followup_question"] = followup_question
        return {
            "manager_action": "final",
            "intent": intent_type,
            "intent_type": intent_type,
            "tool_calls": [],
            "final_action": final_action,
            "workflow_effect": workflow_effect,
            "target_attachment": target,
            "exactness": "diagnostic_fixture",
            "confidence": "medium",
            "evidence_posture": evidence_posture,
            "repair_ack": False,
            "answer_contract": answer_contract,
            "response_summary": workflow_effect,
            "uncertainty_posture": "bounded",
            "evidence_honesty_posture": evidence_posture,
            "semantic_decision": {
                "semantic_authority": "deterministic_fake_provider",
                "current_turn_intent": current_turn_intent,
                "target_attachment": target,
                "workflow_effect": workflow_effect,
                "final_action_candidate": final_action,
                "estimation_posture": estimation_posture,
                "followup_posture": "none",
                "followup_question": followup_question or None,
                "followup_targets": [],
                "mutation_intent_candidate": mutation_intent_candidate,
                "uncertainty_posture": "bounded",
                "source": "scripted_accurate_intake_live_fixture",
                "semantic_owner": "manager",
                "deterministic_role": "fixture_simulates_manager_output_only",
            },
        }

    def _trace(self, stage: str) -> dict[str, Any]:
        return {
            "source": "scripted_accurate_intake_live_fixture",
            "stage": stage,
            "live_llm_invoked": False,
            "runner_inferred_semantics": False,
        }


def provider_profile(provider_profile_id: str) -> dict[str, Any]:
    if provider_profile_id not in _PROVIDER_PROFILES:
        supported = ", ".join(sorted(_PROVIDER_PROFILES))
        raise ValueError(
            f"Unsupported Accurate Intake live diagnostic provider profile: {provider_profile_id}. "
            f"Supported: {supported}"
        )
    return dict(_PROVIDER_PROFILES[provider_profile_id])


def build_missing_provider_report(*, profile: dict[str, Any]) -> dict[str, Any]:
    return _report_shell(
        profile=profile,
        provider_mode="not_invoked",
        live_invoked=False,
        provider_readiness={
            "provider": profile["provider"],
            "configured": False,
            "provider_profile_id": profile["provider_profile_id"],
            "provider_profile_model": profile["model"],
        },
        provider_invocations=[],
        stages=[
            _stage_result(
                profile=profile,
                stage_id=STAGE_PROVIDER_HEALTH_SMOKE,
                status="fail",
                timeout_budget_ms=0,
                failure_layer="provider_runtime_error",
                failure_family="environment_or_provider_blocker",
            )
        ],
        cases=[],
        failure_layer="provider_runtime_error",
        failure_family="environment_or_provider_blocker",
    )


def run_diagnostic(
    *,
    output_path: Path = ARTIFACT_PATH,
    db_path: Path = DEFAULT_DB_PATH,
    local_date: str = DEFAULT_LOCAL_DATE,
    provider_profile_id: str = DEFAULT_ACCURATE_INTAKE_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID,
    provider_timeout_ms: int = 180000,
    case_timeout_ms: int | None = None,
    provider_request_retry_count: int = 1,
    provider_request_retry_backoff_ms: int = 250,
    provider_request_retry_jitter_ms: int = 100,
    provider_override: Any | None = None,
    provider_mode: str = "live",
    live_invoked: bool = True,
    stage: str = STAGE_ALL,
    case_id: str | None = None,
    max_turn: int | None = None,
    offline_replay_artifact_path: Path | None = DEFAULT_OFFLINE_REPLAY_ARTIFACT,
) -> dict[str, Any]:
    profile = provider_profile(provider_profile_id)
    if provider_override is None:
        provider_override = _build_builderspace_provider(
            profile=profile,
            provider_timeout_ms=provider_timeout_ms,
            transport_retry_count=0,
            transport_retry_backoff_seconds=0.0,
        )
    provider = AccurateIntakeLiveDiagnosticProvider(
        provider_override,
        profile=profile,
        live_invoked=live_invoked,
        provider_request_timeout_ms=provider_timeout_ms,
        provider_request_retry_count=provider_request_retry_count,
        provider_request_retry_backoff_ms=provider_request_retry_backoff_ms,
        provider_request_retry_jitter_ms=provider_request_retry_jitter_ms,
    )
    readiness = provider.readiness()
    if provider_mode == "live" and not readiness.get("configured"):
        report = build_missing_provider_report(profile=profile)
        _write_report(output_path, report)
        return report

    selected_stage_ids = _stage_ids_for(stage)
    single_selected_stage = len(selected_stage_ids) == 1
    stages: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []
    retry_budget_ms = provider_timeout_ms * (provider_request_retry_count + 1) + (
        provider_request_retry_backoff_ms * provider_request_retry_count
    )
    effective_case_timeout_ms = int(case_timeout_ms if case_timeout_ms is not None else retry_budget_ms + 15000)
    for stage_id in selected_stage_ids:
        if stage_id == STAGE_PROVIDER_HEALTH_SMOKE:
            stages.append(
                _run_probe_stage(
                    provider=provider,
                    profile=profile,
                    stage_id=stage_id,
                    timeout_budget_ms=provider_timeout_ms,
                    require_contract_schema=False,
                )
            )
            if stages[-1]["status"] != "pass":
                break
        elif stage_id == STAGE_SCHEMA_CONTRACT_PROBE:
            if not single_selected_stage and not _stage_passed(stages, STAGE_PROVIDER_HEALTH_SMOKE):
                stages.append(
                    _stage_blocked(
                        profile=profile,
                        stage_id=stage_id,
                        timeout_budget_ms=provider_timeout_ms,
                        failure_layer="provider_runtime_error",
                        failure_family="provider_health_blocked",
                    )
                )
                break
            stages.append(
                _run_probe_stage(
                    provider=provider,
                    profile=profile,
                    stage_id=stage_id,
                    timeout_budget_ms=provider_timeout_ms,
                    require_contract_schema=True,
                )
            )
            if stages[-1]["status"] != "pass":
                break
        elif stage_id == STAGE_FAKE_PROVIDER_ACTIVE_RUNTIME_GATE:
            if not single_selected_stage and not _stage_passed(stages, STAGE_SCHEMA_CONTRACT_PROBE):
                stages.append(
                    _stage_blocked(
                        profile=profile,
                        stage_id=stage_id,
                        timeout_budget_ms=effective_case_timeout_ms,
                        failure_layer="provider_contract_non_adherence",
                        failure_family="schema_contract_blocked",
                    )
                )
                break
            fake_cases = _run_case_batch(
                db_path=_stage_db_path(db_path, stage_id),
                cases=_case_inventory(),
                provider=AccurateIntakeLiveDiagnosticProvider(
                    ScriptedAccurateIntakeLiveProvider(),
                    profile=profile,
                    live_invoked=False,
                    provider_request_timeout_ms=provider_timeout_ms,
                    provider_request_retry_count=0,
                    provider_request_retry_backoff_ms=0,
                    provider_request_retry_jitter_ms=0,
                ),
                profile=profile,
                local_date=local_date,
                case_timeout_ms=effective_case_timeout_ms,
                stage_id=stage_id,
            )
            stages.append(
                _runtime_gate_stage_result(
                    profile=profile,
                    stage_id=stage_id,
                    stage_cases=fake_cases,
                    timeout_budget_ms=effective_case_timeout_ms,
                )
            )
            if stages[-1]["status"] != "pass":
                break
        elif stage_id == STAGE_SINGLE_CASE_LIVE_PROBE:
            if not single_selected_stage and not _stage_passed(stages, STAGE_FAKE_PROVIDER_ACTIVE_RUNTIME_GATE):
                stages.append(
                    _stage_blocked(
                        profile=profile,
                        stage_id=stage_id,
                        timeout_budget_ms=effective_case_timeout_ms,
                        failure_layer="runtime",
                        failure_family="fake_provider_active_runtime_gate_blocked",
                    )
                )
                break
            single_cases = _run_case_batch(
                db_path=_stage_db_path(db_path, stage_id),
                cases=_single_case_probe_inventory(case_id=case_id, max_turn=max_turn),
                provider=provider,
                profile=profile,
                local_date=local_date,
                case_timeout_ms=effective_case_timeout_ms,
                stage_id=stage_id,
            )
            stages.append(
                _runtime_gate_stage_result(
                    profile=profile,
                    stage_id=stage_id,
                    stage_cases=single_cases,
                    timeout_budget_ms=effective_case_timeout_ms,
                )
            )
            if stage == STAGE_SINGLE_CASE_LIVE_PROBE:
                cases = single_cases
            if stages[-1]["status"] != "pass":
                break
        elif stage_id == STAGE_FULL_SUITE_LIVE_DIAGNOSTIC:
            offline_replay_gate = _full_suite_offline_replay_gate(offline_replay_artifact_path)
            if not offline_replay_gate.get("allowed"):
                stages.append(
                    _stage_blocked(
                        profile=profile,
                        stage_id=stage_id,
                        timeout_budget_ms=provider_timeout_ms,
                        failure_layer="diagnostic_ordering",
                        failure_family=str(offline_replay_gate.get("failure_family") or "offline_replay_required"),
                        summary={"offline_replay_gate": offline_replay_gate},
                    )
                )
                break
            if not _stage_passed(stages, STAGE_SINGLE_CASE_LIVE_PROBE) and stage != STAGE_FULL_SUITE_LIVE_DIAGNOSTIC:
                stages.append(
                    _stage_blocked(
                        profile=profile,
                        stage_id=stage_id,
                        timeout_budget_ms=provider_timeout_ms,
                        failure_layer="diagnostic_ordering",
                        failure_family="single_case_probe_required",
                    )
                )
                break
            cases = _run_case_batch(
                db_path=db_path,
                cases=_case_inventory(),
                provider=provider,
                profile=profile,
                local_date=local_date,
                case_timeout_ms=effective_case_timeout_ms,
                stage_id=stage_id,
            )
            stages.append(
                _runtime_gate_stage_result(
                    profile=profile,
                    stage_id=stage_id,
                    stage_cases=cases,
                    timeout_budget_ms=effective_case_timeout_ms,
                    extra_summary={"offline_replay_gate": offline_replay_gate},
                )
            )
    report = _report_shell(
        profile=profile,
        provider_mode=provider_mode,
        live_invoked=live_invoked,
        provider_readiness=readiness,
        provider_invocations=provider.invocations,
        stages=stages,
        cases=cases,
        failure_layer=_root_stage_failure(stages)[0],
        failure_family=_root_stage_failure(stages)[1],
    )
    _write_report(output_path, report)
    return report


def _stage_ids_for(stage: str) -> list[str]:
    if stage == STAGE_ALL:
        return list(ORDERED_STAGE_IDS)
    if stage not in ORDERED_STAGE_IDS:
        supported = ", ".join((STAGE_ALL, *ORDERED_STAGE_IDS))
        raise ValueError(f"Unsupported Accurate Intake live diagnostic stage: {stage}. Supported: {supported}")
    return [stage]


def _stage_db_path(db_path: Path, stage_id: str) -> Path:
    return db_path.with_name(f"{db_path.stem}.{stage_id}{db_path.suffix}")


def _stage_result(
    *,
    profile: dict[str, Any],
    stage_id: str,
    status: str,
    timeout_budget_ms: int,
    attempt_count: int = 0,
    latency_ms: int = 0,
    failure_layer: str | None = None,
    failure_family: str | None = None,
    retry_policy_applied: bool = False,
    result_kind: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    resolved_result_kind = result_kind or _stage_result_kind(status=status, retry_policy_applied=retry_policy_applied)
    result = {
        "stage_id": stage_id,
        "status": status,
        "provider_profile_id": profile["provider_profile_id"],
        "model": profile["model"],
        "transport_mode": profile["transport_policy"]["primary"],
        "attempt_count": int(attempt_count),
        "latency_ms": int(latency_ms),
        "timeout_budget_ms": int(timeout_budget_ms),
        "failure_layer": failure_layer,
        "failure_family": failure_family,
        "retry_policy_applied": bool(retry_policy_applied),
        "result_kind": resolved_result_kind,
    }
    result.update(extra)
    return _json_safe(result)


def _stage_blocked(
    *,
    profile: dict[str, Any],
    stage_id: str,
    timeout_budget_ms: int,
    failure_layer: str,
    failure_family: str,
    **extra: Any,
) -> dict[str, Any]:
    return _stage_result(
        profile=profile,
        stage_id=stage_id,
        status="blocked",
        timeout_budget_ms=timeout_budget_ms,
        failure_layer=failure_layer,
        failure_family=failure_family,
        **extra,
    )


def _stage_passed(stages: list[dict[str, Any]], stage_id: str) -> bool:
    return any(stage.get("stage_id") == stage_id and stage.get("status") == "pass" for stage in stages)


def _root_stage_failure(stages: list[dict[str, Any]]) -> tuple[str | None, str | None]:
    for stage in stages:
        if stage.get("status") != "pass":
            return _optional_string(stage.get("failure_layer")), _optional_string(stage.get("failure_family"))
    return None, None


def _stage_result_kind(*, status: str, retry_policy_applied: bool) -> str:
    if status == "pass":
        return "pass_after_retry" if retry_policy_applied else "strict_pass_first_attempt"
    if status == "timeout":
        return "timeout_after_retry" if retry_policy_applied else "timeout_first_attempt"
    return status


def _provider_attempt_count_from_trace(trace: dict[str, Any]) -> int:
    if int(trace.get("attempt_count") or 0) > 0:
        return int(trace.get("attempt_count") or 0)
    transport_attempts = _list(trace.get("transport_attempts"))
    if transport_attempts:
        return len(transport_attempts)
    return 1


def _provider_trace_retry_applied(trace: dict[str, Any]) -> bool:
    if trace.get("retry_policy_applied") is True:
        return True
    transport_attempts = _list(trace.get("transport_attempts"))
    return len(transport_attempts) > 1


def _latest_provider_invocation(
    *,
    provider: AccurateIntakeLiveDiagnosticProvider,
    stage_id: str,
) -> dict[str, Any]:
    for invocation in reversed(provider.invocations):
        if str(invocation.get("stage") or "") in {stage_id, MANAGER_LOOP_STAGE}:
            return _dict(invocation)
    return {}


def _run_probe_stage(
    *,
    provider: AccurateIntakeLiveDiagnosticProvider,
    profile: dict[str, Any],
    stage_id: str,
    timeout_budget_ms: int,
    require_contract_schema: bool,
) -> dict[str, Any]:
    started = datetime.now(UTC)
    try:
        payload, trace = asyncio.run(_provider_probe(provider=provider, stage_id=stage_id))
        if require_contract_schema:
            _validate_probe_payload_shape(payload)
    except Exception as exc:
        latency_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
        failure_layer = _failure_layer_for_exception(exc)
        failure_family = _failure_family_for_exception(exc)
        latest_invocation = _latest_provider_invocation(provider=provider, stage_id=stage_id)
        attempt_count = int(latest_invocation.get("attempt_count") or 1)
        retry_policy_applied = bool(latest_invocation.get("retry_policy_applied"))
        result_kind = str(
            latest_invocation.get("result_kind")
            or _stage_result_kind(
                status="timeout" if failure_family == "environment_or_provider_blocker" else "fail",
                retry_policy_applied=retry_policy_applied,
            )
        )
        if require_contract_schema and failure_family != "environment_or_provider_blocker":
            failure_layer = "provider_contract_non_adherence"
            failure_family = "schema_contract_blocked"
        return _stage_result(
            profile=profile,
            stage_id=stage_id,
            status="timeout" if failure_family == "environment_or_provider_blocker" else "fail",
            timeout_budget_ms=timeout_budget_ms,
            attempt_count=attempt_count,
            latency_ms=latency_ms,
            failure_layer=failure_layer,
            failure_family=failure_family,
            retry_policy_applied=retry_policy_applied,
            result_kind=result_kind,
            runtime_error={"type": type(exc).__name__, "message": str(exc)},
            retry_attempts=list(latest_invocation.get("retry_attempts") or []),
        )
    latency_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
    retry_policy_applied = _provider_trace_retry_applied(trace)
    return _stage_result(
        profile=profile,
        stage_id=stage_id,
        status="pass",
        timeout_budget_ms=timeout_budget_ms,
        attempt_count=_provider_attempt_count_from_trace(trace),
        latency_ms=latency_ms,
        retry_policy_applied=retry_policy_applied,
        result_kind=str(trace.get("result_kind") or _stage_result_kind(status="pass", retry_policy_applied=retry_policy_applied)),
        provider_trace=_dict(trace),
    )


async def _provider_probe(
    *,
    provider: AccurateIntakeLiveDiagnosticProvider,
    stage_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    provider.begin_step({"entry_intent": "answer_remaining_budget", "kind": stage_id})
    if stage_id == STAGE_PROVIDER_HEALTH_SMOKE:
        return await provider.complete_with_trace(
            system_prompt=(
                "You are running a provider health smoke test. Return a small JSON object only: "
                "{\"ok\": true, \"stage\": \"provider_health_smoke\"}."
            ),
            user_payload={
                "diagnostic_stage_id": stage_id,
                "raw_user_input": "provider health smoke",
                "constraints": {
                    "diagnostic_stage_id": stage_id,
                    "diagnostic_no_product_loop": True,
                    "manager_contract_not_required": True,
                },
            },
            stage=STAGE_PROVIDER_HEALTH_SMOKE,
            max_tokens=80,
        )
    return await provider.complete_with_trace(
        system_prompt=(
            "You are running an Accurate Intake manager schema contract probe. Return a manager structured "
            "decision with intent_type='answer_remaining_budget', intent='answer_remaining_budget', "
            "workflow_effect='answer_only', final_action='answer_only', and "
            "semantic_decision.current_turn_intent='answer_remaining_budget'. Include tool_calls=[] because "
            "manager_action is final. Do not mutate state."
        ),
        user_payload={
            "round_index": 0,
            "diagnostic_stage_id": stage_id,
            "raw_user_input": "How many calories did I consume today?",
            "available_tools": ["read_body_plan", "read_day_budget"],
            "tool_results": [],
            "constraints": {
                "diagnostic_stage_id": stage_id,
                "diagnostic_no_product_loop": True,
                "diagnostic_expected_manager_decision": {
                    "intent": "answer_remaining_budget",
                    "intent_type": "answer_remaining_budget",
                    "workflow_effect": "answer_only",
                    "final_action": "answer_only",
                    "semantic_decision.current_turn_intent": "answer_remaining_budget",
                },
            },
        },
        stage=MANAGER_LOOP_STAGE,
        max_tokens=800,
    )


def _validate_probe_payload_shape(payload: dict[str, Any]) -> None:
    missing = [field for field in FOUNDER_LIVE_MANAGER_REQUIRED_FIELDS if field not in payload]
    if missing:
        raise RuntimeError(f"schema contract probe missing required fields: {missing}")
    if not isinstance(payload.get("semantic_decision"), dict):
        raise RuntimeError("schema contract probe requires semantic_decision object")
    if not isinstance(payload.get("answer_contract"), dict):
        raise RuntimeError("schema contract probe requires answer_contract object")


def _run_case_batch(
    *,
    db_path: Path,
    cases: list[LiveCase],
    provider: AccurateIntakeLiveDiagnosticProvider,
    profile: dict[str, Any],
    local_date: str,
    case_timeout_ms: int,
    stage_id: str,
) -> list[dict[str, Any]]:
    if db_path.exists():
        db_path.unlink()
    SessionLocal = _session_factory(db_path)
    results: list[dict[str, Any]] = []
    try:
        for case in cases:
            started = datetime.now(UTC)
            invocation_start_index = len(provider.invocations)
            try:
                case_result = asyncio.run(
                    asyncio.wait_for(
                        _run_case(SessionLocal, case=case, provider=provider, local_date=local_date),
                        timeout=max(0.001, case_timeout_ms / 1000),
                    )
                )
            except Exception as exc:
                case_result = _case_error(
                    case,
                    exc,
                    provider_invocations=provider.invocations[invocation_start_index:],
                )
            case_result["latency_ms"] = int((datetime.now(UTC) - started).total_seconds() * 1000)
            case_result["stage_id"] = stage_id
            results.append(_decorate_case(case_result, profile=profile))
    finally:
        _dispose_session_factory(SessionLocal)
    return results


def _dispose_session_factory(SessionLocal: sessionmaker[Session]) -> None:
    bind = getattr(SessionLocal, "kw", {}).get("bind")
    if bind is not None and hasattr(bind, "dispose"):
        bind.dispose()


def _runtime_gate_stage_result(
    *,
    profile: dict[str, Any],
    stage_id: str,
    stage_cases: list[dict[str, Any]],
    timeout_budget_ms: int,
    extra_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary = _summary(stage_cases)
    if extra_summary:
        summary = {**summary, **extra_summary}
    failure_layer = None
    failure_family = None
    status = "pass"
    if summary["timeout_count"] > 0:
        status = "timeout"
        failure_layer = "provider_runtime_error"
        failure_family = "environment_or_provider_blocker"
    elif summary["contract_fail_count"] > 0:
        status = "fail"
        failure_layer = (summary.get("failure_layers") or ["runtime"])[0]
        failure_family = (summary.get("failure_families") or ["runtime_failure"])[0]
    retry_policy_applied = any(case.get("retry_policy_applied") is True for case in stage_cases)
    return _stage_result(
        profile=profile,
        stage_id=stage_id,
        status=status,
        timeout_budget_ms=timeout_budget_ms,
        attempt_count=sum(int(case.get("provider_request_attempt_count") or 1) for case in stage_cases),
        latency_ms=sum(int(case.get("latency_ms") or 0) for case in stage_cases),
        failure_layer=failure_layer,
        failure_family=failure_family,
        retry_policy_applied=retry_policy_applied,
        result_kind=_stage_result_kind(status=status, retry_policy_applied=retry_policy_applied),
        case_ids=[str(case.get("case_id") or "") for case in stage_cases],
        summary=summary,
    )


def _full_suite_offline_replay_gate(offline_replay_artifact_path: Path | None) -> dict[str, Any]:
    if offline_replay_artifact_path is None:
        return {"allowed": False, "failure_family": "offline_replay_required", "source_path": None}
    path = Path(offline_replay_artifact_path)
    if not path.exists():
        return {"allowed": False, "failure_family": "offline_replay_required", "source_path": str(path)}
    try:
        artifact = _dict(json.loads(path.read_text(encoding="utf-8")))
    except Exception:
        return {"allowed": False, "failure_family": "offline_replay_integrity_blocked", "source_path": str(path)}
    summary = _dict(artifact.get("summary"))
    integrity = _dict(artifact.get("input_integrity"))
    if artifact.get("artifact_type") != "accurate_intake_mvp_offline_shadow_replay":
        return {"allowed": False, "failure_family": "offline_replay_integrity_blocked", "source_path": str(path)}
    if integrity.get("passed") is not True:
        return {"allowed": False, "failure_family": "offline_replay_integrity_blocked", "source_path": str(path)}
    if summary.get("strict_replay_ready") is not True:
        return {"allowed": False, "failure_family": "offline_replay_not_strict", "source_path": str(path)}
    if int(summary.get("pass_after_retry_count") or 0) > 0 or int(summary.get("timeout_count") or 0) > 0:
        return {"allowed": False, "failure_family": "offline_replay_retry_or_timeout", "source_path": str(path)}
    if int(summary.get("failed_stage_count") or 0) > 0:
        return {"allowed": False, "failure_family": "offline_replay_has_failed_stage", "source_path": str(path)}
    return {
        "allowed": True,
        "failure_family": None,
        "source_path": str(path),
        "sample_run_count": int(summary.get("sample_run_count") or 0),
        "model_diversity_status": _optional_string(summary.get("model_diversity_status")),
    }


async def _run_case(
    SessionLocal: sessionmaker[Session],
    *,
    case: LiveCase,
    provider: AccurateIntakeLiveDiagnosticProvider,
    local_date: str,
) -> dict[str, Any]:
    with SessionLocal() as db:
        if case.body_plan_seeded:
            _seed_body_plan(db, user_external_id=case.user_external_id, local_date=local_date)
        seeded_state = _seed_case_state(db, case=case, local_date=local_date)
        turns: list[dict[str, Any]] = []
        for step in case.steps:
            provider.begin_step({**dict(step.script), "kind": step.kind})
            result = await _active_entrypoint()(
                db,
                user_external_id=case.user_external_id,
                raw_user_input=step.text,
                onboarding_payload=None,
                local_date=local_date,
                allow_search=False,
                provider=provider,
                search_port=None,
                extract_port=None,
            )
            turns.append(_turn_summary(step, result))
        debug_surface = build_accurate_intake_debug_payload(
            db,
            user_external_id=case.user_external_id,
            local_date=local_date,
        )
    verdict, blockers, failure_layer = _validate_case(case=case, turns=turns, debug_surface=debug_surface)
    case_result = {
        "case_id": case.case_id,
        "description": case.description,
        "verdict": verdict,
        "blockers": blockers,
        "failure_layer": failure_layer,
        "runner_inferred_semantics": False,
        "raw_text_routing_used": False,
        "turns": turns,
        "debug_surface": debug_surface,
        "seeded_state": seeded_state,
        "state_delta": _case_state_delta(turns=turns, debug_surface=debug_surface),
    }
    turn_limit = _turn_limit_payload(case, turns)
    if turn_limit is not None:
        case_result["turn_limit"] = turn_limit
    return case_result


def _case_inventory() -> list[LiveCase]:
    return [
        LiveCase(
            case_id="chinese_chicken_rice_correction_removal_debug",
            description="Chinese primary path: log meal, correct item, explicit item removal, then debug read.",
            user_external_id="live-diag-chicken-rice",
            body_plan_seeded=True,
            steps=(
                LiveStep(
                    1,
                    "new_meal",
                    "雞肉飯和湯",
                    {"entry_intent": "log_meal", "semantic_intent": "log_meal", "final_action": "commit"},
                ),
                LiveStep(
                    2,
                    "explicit_item_correction",
                    "雞肉飯少一點",
                    {
                        "entry_intent": "log_meal",
                        "semantic_intent": "correct_meal",
                        "final_action": "correction_applied",
                        "workflow_effect": "correction",
                        "mutation_intent": "correction_write",
                        "target_mode": "target_committed_thread",
                        "target_canonical_name": "\u96de\u8089\u98ef",
                    },
                ),
                LiveStep(
                    3,
                    "explicit_item_removal",
                    "把湯拿掉",
                    {
                        "entry_intent": "log_meal",
                        "semantic_intent": "correct_meal",
                        "final_action": "correction_applied",
                        "workflow_effect": "correction",
                        "mutation_intent": "correction_write",
                        "target_mode": "target_committed_thread",
                        "correction_operation": "remove_item",
                        "target_canonical_name": "\u6e6f",
                    },
                ),
                LiveStep(
                    4,
                    "debug_read",
                    "看現在的本地紀錄",
                    {"entry_intent": "answer_remaining_budget"},
                ),
            ),
        ),
        LiveCase(
            case_id="bubble_milk_tea_refinement",
            description="Bubble milk tea first estimate then size/sugar refinement.",
            user_external_id="live-diag-bubble-tea",
            body_plan_seeded=True,
            steps=(
                LiveStep(
                    1,
                    "new_meal",
                    "珍珠奶茶",
                    {"entry_intent": "log_meal", "semantic_intent": "log_meal", "final_action": "commit"},
                ),
                LiveStep(
                    2,
                    "followup_refinement",
                    "半糖大杯",
                    {
                        "entry_intent": "log_meal",
                        "semantic_intent": "log_meal",
                        "final_action": "commit",
                        "target_mode": "target_committed_thread",
                    },
                ),
            ),
        ),
        LiveCase(
            case_id="luwei_bare_to_listed_basket",
            description="Bare luwei drafts/asks first, listed basket can estimate later.",
            user_external_id="live-diag-luwei",
            body_plan_seeded=True,
            steps=(
                LiveStep(
                    1,
                    "bare_basket",
                    "滷味",
                    {
                        "entry_intent": "log_meal",
                        "semantic_intent": "log_meal",
                        "final_action": "ask_followup",
                        "followup_question": "請列出滷味品項。",
                    },
                ),
                LiveStep(
                    2,
                    "listed_basket",
                    "有豆干、海帶、貢丸",
                    {"entry_intent": "log_meal", "semantic_intent": "log_meal", "final_action": "commit"},
                ),
            ),
        ),
        LiveCase(
            case_id="today_consumed_query_only",
            description="Today consumed query reads state and must not mutate.",
            user_external_id="live-diag-query-only",
            body_plan_seeded=True,
            steps=(
                LiveStep(
                    1,
                    "budget_query",
                    "今天吃了多少？",
                    {"entry_intent": "answer_remaining_budget"},
                ),
            ),
        ),
        LiveCase(
            case_id="no_plan_consumed_without_budget_target",
            description="No-plan query can discuss consumed state but must not invent remaining or target.",
            user_external_id="live-diag-no-plan",
            body_plan_seeded=False,
            steps=(
                LiveStep(
                    1,
                    "no_plan_budget_query",
                    "今天吃了多少？我還能吃多少？",
                    {"entry_intent": "onboarding_required"},
                ),
            ),
        ),
    ]


def _seeded_explicit_removal_case() -> LiveCase:
    return LiveCase(
        case_id="explicit_item_removal_seeded",
        description="Seeded single-turn explicit item removal: canonical two-item meal exists before live turn.",
        user_external_id="live-diag-explicit-removal-seeded",
        body_plan_seeded=True,
        seed_kind="canonical_two_item_meal",
        steps=(
            LiveStep(
                1,
                "explicit_item_removal",
                "\u628a\u6e6f\u62ff\u6389",
                {
                    "entry_intent": "log_meal",
                    "semantic_intent": "correct_meal",
                    "final_action": "correction_applied",
                    "workflow_effect": "correction",
                    "mutation_intent": "correction_write",
                    "target_mode": "target_committed_thread",
                    "correction_operation": "remove_item",
                    "target_canonical_name": "soup",
                },
            ),
        ),
    )


def _limit_case_turns(case: LiveCase, *, max_turn: int | None) -> LiveCase:
    if max_turn is None:
        return case
    if max_turn <= 0:
        raise ValueError("--max-turn must be a positive integer")
    limited_steps = tuple(step for step in case.steps if step.turn <= max_turn)
    if not limited_steps:
        raise ValueError(f"max_turn={max_turn} excludes every turn for case_id={case.case_id!r}")
    return replace(
        case,
        steps=limited_steps,
        turn_limit_max_turn=max_turn,
        original_turn_count=len(case.steps),
    )


def _single_case_probe_inventory(*, case_id: str | None = None, max_turn: int | None = None) -> list[LiveCase]:
    cases = [_seeded_explicit_removal_case(), *_case_inventory()]
    selected = str(case_id or "explicit_item_removal_seeded")
    for case in cases:
        if case.case_id == selected:
            return [_limit_case_turns(case, max_turn=max_turn)]
    supported = ", ".join(case.case_id for case in cases)
    raise ValueError(f"Unsupported Accurate Intake live diagnostic case_id: {selected}. Supported: {supported}")


def _validate_case(
    *,
    case: LiveCase,
    turns: list[dict[str, Any]],
    debug_surface: dict[str, Any],
) -> tuple[str, list[str], str | None]:
    blockers: list[str] = []
    for turn in turns:
        if _dict(turn.get("runtime_error")):
            blockers.append("runtime_error")
    turn_by_number = {int(turn.get("turn") or 0): _dict(turn) for turn in turns}
    for step in case.steps:
        expected_final_action = str(step.script.get("final_action") or "")
        if expected_final_action not in {"commit", "correction_applied"}:
            continue
        turn = turn_by_number.get(step.turn)
        if not turn:
            continue
        state_delta = _dict(turn.get("state_delta"))
        if state_delta.get("canonical_commit") is not True:
            blockers.append(f"turn_{step.turn}_expected_canonical_mutation_missing")
        if expected_final_action == "correction_applied" and state_delta.get("new_meal_version_created") is not True:
            blockers.append(f"turn_{step.turn}_expected_new_version_missing")
    if case.case_id == "today_consumed_query_only":
        if _dict(turns[0].get("state_delta")).get("canonical_commit"):
            blockers.append("query_only_mutated_state")
    if case.case_id == "no_plan_consumed_without_budget_target":
        remaining = _dict(turns[0].get("remaining_budget"))
        if remaining.get("daily_target_kcal") is not None or remaining.get("remaining_kcal") is not None:
            blockers.append("no_plan_claimed_remaining_or_target")
    same_truth = _dict(_dict(_dict(debug_surface).get("model")).get("same_truth"))
    if same_truth and same_truth.get("status") != "pass":
        blockers.append("same_truth_failed")
    failure_layer = "runtime" if blockers else None
    return ("fail" if blockers else "pass"), blockers, failure_layer


def _turn_summary(step: LiveStep, result: dict[str, Any]) -> dict[str, Any]:
    execution = _dict(result.get("intake_execution_manager"))
    final = _dict(execution.get("final"))
    return {
        "turn": step.turn,
        "kind": step.kind,
        "text": step.text,
        "request_id": result.get("request_id"),
        "manager_intent": _dict(result.get("manager_decision")).get("intent_type"),
        "manager_final_action": final.get("final_action") or _dict(result.get("manager_decision")).get("final_action"),
        "workflow_effect": final.get("workflow_effect") or _dict(result.get("manager_decision")).get("workflow_effect"),
        "state_delta": _json_safe(_dict(result.get("state_delta"))),
        "remaining_budget": _json_safe(_dict(result.get("remaining_budget"))),
        "manager_rounds": _json_safe(_list(execution.get("manager_rounds"))),
        "hard_fail_conditions": list(result.get("hard_fail_conditions") or []),
        "runtime_error": None,
    }


def _turn_limit_payload(case: LiveCase, turns: list[dict[str, Any]]) -> dict[str, Any] | None:
    if case.turn_limit_max_turn is None:
        return None
    completed_turns = [int(turn.get("turn") or 0) for turn in turns]
    return {
        "max_turn": case.turn_limit_max_turn,
        "original_turn_count": int(case.original_turn_count or len(case.steps)),
        "executed_turn_count": len(turns),
        "completed_turns": completed_turns,
        "last_completed_turn": max(completed_turns) if completed_turns else None,
        "is_turn_limited": True,
    }


def _case_error(
    case: LiveCase,
    exc: Exception,
    *,
    provider_invocations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    invocations = [_dict(item) for item in (provider_invocations or [])]
    retry_policy_applied = any(item.get("retry_policy_applied") is True for item in invocations)
    attempt_count = sum(max(1, int(item.get("attempt_count") or 1)) for item in invocations) or 1
    return {
        "case_id": case.case_id,
        "description": case.description,
        "verdict": "fail",
        "blockers": ["runtime_error"],
        "failure_layer": _failure_layer_for_exception(exc),
        "failure_family": _failure_family_for_exception(exc),
        "runner_inferred_semantics": False,
        "raw_text_routing_used": False,
        "turns": [],
        "debug_surface": {},
        "state_delta": {},
        "provider_invocations": invocations,
        "provider_request_attempt_count": attempt_count,
        "retry_policy_applied": retry_policy_applied,
        "result_kind": "timeout_after_retry" if retry_policy_applied else "timeout_first_attempt",
        "runtime_error": {"type": type(exc).__name__, "message": str(exc)},
    }


def _decorate_case(case: dict[str, Any], *, profile: dict[str, Any]) -> dict[str, Any]:
    decorated = dict(case)
    result_kind = _case_result_kind(decorated)
    contract_status = _case_contract_status(decorated, result_kind=result_kind)
    failure_layer, failure_family = _classify_failure(decorated)
    decorated["provider_profile_id"] = profile["provider_profile_id"]
    decorated["provider_profile_model"] = profile["model"]
    decorated["provider_profile_role"] = profile["provider_profile_role"]
    decorated["transport_mode"] = profile["transport_policy"]["primary"]
    decorated["transport_policy"] = profile["transport_policy"]
    decorated["schema_name"] = profile["schema_name"]
    decorated["schema_version"] = profile["schema_version"]
    decorated["case_contract_status"] = contract_status
    decorated["result_kind"] = result_kind
    decorated["provider_request_attempt_count"] = _case_provider_attempt_count(decorated)
    decorated["retry_policy_applied"] = _case_retry_policy_applied(decorated)
    repair_diagnostics = _case_repair_diagnostics(decorated)
    if repair_diagnostics:
        decorated["repair_diagnostics"] = repair_diagnostics
        first_repair = repair_diagnostics[0]
        decorated.setdefault("repair_failure_family", first_repair.get("repair_failure_family"))
        decorated.setdefault("failed_invariant", first_repair.get("failed_invariant"))
    decorated["private_self_use_unlock_allowed"] = False
    decorated["readiness_claimed"] = False
    decorated["production_selected"] = False
    decorated["runner_inferred_semantics"] = False
    decorated["raw_text_routing_used"] = False
    if failure_layer is not None:
        decorated["failure_layer"] = failure_layer
    if failure_family is not None:
        decorated["failure_family"] = failure_family
    return decorated


def _case_contract_status(case: dict[str, Any], *, result_kind: str | None = None) -> str:
    if _case_has_provider_timeout(case):
        return "timeout"
    if _dict(case.get("runtime_error")):
        return "fail"
    for trace in _case_manager_traces(case):
        if trace.get("repair_attempted") is True or str(trace.get("repair_result") or "") == "passed_after_repair":
            return "repaired_pass"
    if result_kind == "pass_after_retry":
        return "retried_pass"
    return "strict_pass" if case.get("verdict") == "pass" else "fail"


def _case_result_kind(case: dict[str, Any]) -> str:
    if str(case.get("result_kind") or ""):
        return str(case.get("result_kind"))
    if _case_has_provider_timeout(case):
        return "timeout_after_retry" if _case_retry_policy_applied(case) else "timeout_first_attempt"
    if case.get("verdict") != "pass":
        return "fail"
    if _case_retry_policy_applied(case):
        return "pass_after_retry"
    return "strict_pass_first_attempt"


def _case_retry_policy_applied(case: dict[str, Any]) -> bool:
    if case.get("retry_policy_applied") is True:
        return True
    for item in _list(case.get("provider_invocations")):
        if _dict(item).get("retry_policy_applied") is True:
            return True
    return any(_provider_trace_retry_applied(trace) for trace in _case_manager_traces(case))


def _case_provider_attempt_count(case: dict[str, Any]) -> int:
    if int(case.get("provider_request_attempt_count") or 0) > 0:
        return int(case.get("provider_request_attempt_count") or 0)
    attempts = 0
    for item in _list(case.get("provider_invocations")):
        attempts += max(1, int(_dict(item).get("attempt_count") or 1))
    for trace in _case_manager_traces(case):
        attempts += _provider_attempt_count_from_trace(trace)
    return attempts or 1


def _case_manager_traces(case: dict[str, Any]) -> list[dict[str, Any]]:
    traces: list[dict[str, Any]] = []
    for turn in _list(case.get("turns")):
        turn_dict = _dict(turn)
        for round_item in _list(turn_dict.get("manager_rounds")):
            if isinstance(round_item, dict):
                traces.append(_dict(round_item.get("trace")))
    return traces


def _case_repair_diagnostics(case: dict[str, Any]) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    for turn in _list(case.get("turns")):
        turn_dict = _dict(turn)
        for round_item in _list(turn_dict.get("manager_rounds")):
            trace = _dict(_dict(round_item).get("trace"))
            if trace.get("repair_attempted") is not True and trace.get("repair_result") != "passed_after_repair":
                continue
            repair_family, failed_invariant = _repair_failure_from_trace(trace)
            diagnostics.append(
                {
                    "turn": int(turn_dict.get("turn") or 0),
                    "repair_result": _optional_string(trace.get("repair_result")),
                    "repair_attempt_count": int(trace.get("repair_attempt_count") or 0),
                    "repair_failure_family": repair_family,
                    "failed_invariant": failed_invariant,
                }
            )
    return diagnostics


def _repair_failure_from_trace(trace: dict[str, Any]) -> tuple[str | None, str | None]:
    for parse_attempt in _list(trace.get("parse_attempts")):
        attempt = _dict(parse_attempt)
        family = _optional_string(attempt.get("failure_family"))
        invariant = _failed_invariant_for_repair_attempt(attempt)
        if family or invariant:
            return family, invariant
    family = _optional_string(trace.get("request_failure_family"))
    return family, _failed_invariant_for_repair_attempt(trace)


def _failed_invariant_for_repair_attempt(payload: dict[str, Any]) -> str | None:
    message = " ".join(
        str(payload.get(key) or "")
        for key in ("error", "message", "request_failure_family", "failure_family")
    ).lower()
    if "non-empty tool_calls" in message and "manager_action='call_tools'" in message:
        return "call_tools_requires_tool_calls"
    if "remove_item" in message and "target evidence" in message:
        return "remove_item_requires_target_evidence"
    if "commit_without_evidence" in message:
        return "commit_requires_evidence"
    if "correction_without_target" in message:
        return "correction_requires_valid_target"
    if "mutation_without_final_mapping" in message:
        return "mutation_requires_final_mapping"
    return None


def _classify_failure(case: dict[str, Any]) -> tuple[str | None, str | None]:
    if case.get("verdict") == "pass" and not _case_has_provider_timeout(case):
        return case.get("failure_layer"), None
    if _case_has_provider_timeout(case):
        return "provider_runtime_error", "environment_or_provider_blocker"
    runtime_error = _dict(case.get("runtime_error"))
    if runtime_error:
        return _failure_layer_for_error_dict(runtime_error), _failure_family_for_error_dict(runtime_error)
    layer = case.get("failure_layer")
    if layer:
        return str(layer), str(case.get("failure_family") or layer)
    return None, None


def _summary(cases: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = [str(case.get("case_contract_status") or "fail") for case in cases]
    failure_layers = sorted(
        {
            str(case.get("failure_layer"))
            for case in cases
            if case.get("failure_layer") and case.get("verdict") != "pass"
        }
    )
    failure_families = sorted(
        {
            str(case.get("failure_family"))
            for case in cases
            if case.get("failure_family") and case.get("verdict") != "pass"
        }
    )
    return {
        "case_count": len(cases),
        "pass_count": sum(1 for case in cases if case.get("verdict") == "pass"),
        "fail_count": sum(1 for case in cases if case.get("verdict") == "fail"),
        "strict_pass_count": statuses.count("strict_pass"),
        "retried_pass_count": statuses.count("retried_pass"),
        "repaired_pass_count": statuses.count("repaired_pass"),
        "contract_fail_count": statuses.count("fail"),
        "timeout_count": statuses.count("timeout"),
        "provider_timeout_count": statuses.count("timeout"),
        "failure_layers": failure_layers,
        "failure_families": failure_families,
        "turn_limited_case_count": sum(1 for case in cases if _dict(case.get("turn_limit")).get("is_turn_limited") is True),
        "private_self_use_unlock_allowed": False,
    }


def _summary_with_stages(*, cases: list[dict[str, Any]], stages: list[dict[str, Any]]) -> dict[str, Any]:
    summary = dict(_summary(cases))
    stage_retried_pass_count = sum(1 for stage in stages if str(stage.get("result_kind") or "") == "pass_after_retry")
    stage_failure_layers = {
        str(stage.get("failure_layer"))
        for stage in stages
        if stage.get("failure_layer") and stage.get("status") != "pass"
    }
    stage_failure_families = {
        str(stage.get("failure_family"))
        for stage in stages
        if stage.get("failure_family") and stage.get("status") != "pass"
    }
    summary["failure_layers"] = sorted(set(summary["failure_layers"]) | stage_failure_layers)
    summary["failure_families"] = sorted(set(summary["failure_families"]) | stage_failure_families)
    summary["stage_count"] = len(stages)
    summary["stage_pass_count"] = sum(1 for stage in stages if stage.get("status") == "pass")
    summary["stage_timeout_count"] = sum(1 for stage in stages if stage.get("status") == "timeout")
    summary["stage_fail_count"] = sum(1 for stage in stages if stage.get("status") in {"fail", "blocked"})
    summary["stage_retried_pass_count"] = stage_retried_pass_count
    summary["retried_pass_count"] = int(summary.get("retried_pass_count") or 0) + stage_retried_pass_count
    provider_stage_timeout_count = sum(
        1 for stage in stages if stage.get("status") == "timeout" and not _list(stage.get("case_ids"))
    )
    summary["provider_timeout_count"] = int(summary.get("provider_timeout_count") or 0) + provider_stage_timeout_count
    summary["timeout_count"] = int(summary.get("timeout_count") or 0) + provider_stage_timeout_count
    return summary


def _report_shell(
    *,
    profile: dict[str, Any],
    provider_mode: str,
    live_invoked: bool,
    provider_readiness: dict[str, Any],
    provider_invocations: list[dict[str, Any]],
    stages: list[dict[str, Any]],
    cases: list[dict[str, Any]],
    failure_layer: str | None,
    failure_family: str | None,
) -> dict[str, Any]:
    return _json_safe(
        {
            "artifact_type": "accurate_intake_mvp_live_diagnostic",
            "artifact_schema_version": "1.0",
            "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "current_mainline": "Accurate Intake MVP live diagnostic re-entry",
            "claim_scope": "live_diagnostic",
            "provider_mode": provider_mode,
            "live_invoked": live_invoked,
            "live_llm_invoked": live_invoked,
            "provider_profile_id": profile["provider_profile_id"],
            "provider_profile_model": profile["model"],
            "provider_profile_role": profile["provider_profile_role"],
            "provider_readiness": provider_readiness,
            "provider_invocations": provider_invocations,
            "stages": stages,
            "transport_mode": profile["transport_policy"]["primary"],
            "transport_policy": profile["transport_policy"],
            "schema_name": profile["schema_name"],
            "schema_version": profile["schema_version"],
            "active_entrypoint": ACTIVE_ENTRYPOINT,
            "active_entrypoint_verified": _active_entrypoint_verified(),
            "runner_inferred_semantics": False,
            "raw_text_routing_used": False,
            "readiness_claimed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "production_selected": False,
            "not_production_selection": True,
            "mutation_rollout_approved": False,
            "live_provider_used_as_truth": False,
            "runtime_web_activation_approved": False,
            "runtime_web_activation_recommended": False,
            "tavily_or_web_activated": False,
            "web_tavily_invoked": False,
            "production_db_used": False,
            "user_facing_rollout": False,
            "allow_search": False,
            "failure_layer": failure_layer,
            "failure_family": failure_family,
            "readiness_claim": _readiness_claim(provider_mode=provider_mode, live_invoked=live_invoked),
            "cases": cases,
            "summary": _summary_with_stages(cases=cases, stages=stages),
        }
    )


def _readiness_claim(*, provider_mode: str, live_invoked: bool) -> dict[str, Any]:
    fake_contract_test = provider_mode != "live" or not live_invoked
    return build_readiness_claim(
        claim_scope="unit_contract" if fake_contract_test else "live_diagnostic",
        activation_stage="contract" if fake_contract_test else "live_diagnostic",
        semantic_authority_source="fake_manager_structured_output" if fake_contract_test else "live_manager_structured_output",
        producer_honesty={
            "runner_inferred_semantics": False,
            "fake_provider_simulated_manager": fake_contract_test,
            "final_mapping_fabricated": False,
            "mutation_fabricated": False,
        },
        evidence_lineage={
            "artifacts": [],
            "producers": ["scripts/run_accurate_intake_mvp_live_diagnostic.py"],
            "active_entrypoint": ACTIVE_ENTRYPOINT,
            "live_invoked": live_invoked,
            "legacy_oracle_used": False,
        },
        allowed_next_stage=None,
        forbidden_claims=_FORBIDDEN_CLAIMS,
        readiness_claimed=False,
    )


def _with_accurate_intake_live_contract_constraints(kwargs: dict[str, Any], *, profile: dict[str, Any]) -> dict[str, Any]:
    updated = dict(kwargs)
    user_payload = dict(_dict(updated.get("user_payload")))
    constraints = dict(_dict(user_payload.get("constraints")))
    constraints["accurate_intake_mvp_live_diagnostic"] = {
        "runner_inferred_semantics": False,
        "raw_text_routing_forbidden": True,
        "web_tavily_invoked": False,
        "live_provider_used_as_truth": False,
    }
    if str(updated.get("stage") or "") != MANAGER_LOOP_STAGE:
        user_payload["constraints"] = constraints
        user_payload.setdefault("accurate_intake_live_diagnostic_policy", constraints["accurate_intake_mvp_live_diagnostic"])
        updated["user_payload"] = user_payload
        return updated
    tool_results = [dict(item) for item in _list(user_payload.get("tool_results")) if isinstance(item, dict)]
    constraints.update(
        founder_live_manager_contract_constraints(
            str(profile["provider_profile_id"]),
            tool_results=tool_results,
        )
    )
    user_payload["constraints"] = constraints
    user_payload.setdefault("accurate_intake_live_diagnostic_policy", constraints["accurate_intake_mvp_live_diagnostic"])
    updated["user_payload"] = user_payload
    return updated


def _build_builderspace_provider(
    *,
    profile: dict[str, Any],
    provider_timeout_ms: int,
    transport_retry_count: int,
    transport_retry_backoff_seconds: float,
) -> Any:
    from app.providers.builderspace_adapter import BuilderSpaceAdapter

    timeout_seconds = max(1, int(provider_timeout_ms / 1000))
    previous_timeout = os.environ.get("AI_BUILDER_TIMEOUT_SECONDS")
    previous_retry_count = os.environ.get("AI_BUILDER_TRANSPORT_RETRY_COUNT")
    previous_retry_backoff = os.environ.get("AI_BUILDER_TRANSPORT_RETRY_BACKOFF_SECONDS")
    os.environ["AI_BUILDER_TIMEOUT_SECONDS"] = str(timeout_seconds)
    os.environ["AI_BUILDER_TRANSPORT_RETRY_COUNT"] = str(max(0, int(transport_retry_count)))
    os.environ["AI_BUILDER_TRANSPORT_RETRY_BACKOFF_SECONDS"] = str(max(0.0, float(transport_retry_backoff_seconds)))
    try:
        return BuilderSpaceAdapter(
            manager_model_override=str(profile["model"]),
            role_label="accurate_intake_mvp_live_diagnostic",
        )
    finally:
        if previous_timeout is None:
            os.environ.pop("AI_BUILDER_TIMEOUT_SECONDS", None)
        else:
            os.environ["AI_BUILDER_TIMEOUT_SECONDS"] = previous_timeout
        if previous_retry_count is None:
            os.environ.pop("AI_BUILDER_TRANSPORT_RETRY_COUNT", None)
        else:
            os.environ["AI_BUILDER_TRANSPORT_RETRY_COUNT"] = previous_retry_count
        if previous_retry_backoff is None:
            os.environ.pop("AI_BUILDER_TRANSPORT_RETRY_BACKOFF_SECONDS", None)
        else:
            os.environ["AI_BUILDER_TRANSPORT_RETRY_BACKOFF_SECONDS"] = previous_retry_backoff


def _session_factory(db_path: Path) -> sessionmaker[Session]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _active_entrypoint() -> Any:
    module = importlib.import_module("app.composition.intake_turn_orchestrator")
    return getattr(module, "execute_intake_turn")


def _active_entrypoint_verified() -> bool:
    entrypoint = _active_entrypoint()
    return f"{entrypoint.__module__}.{entrypoint.__name__}" == ACTIVE_ENTRYPOINT


def _seed_body_plan(db: Session, *, user_external_id: str, local_date: str) -> None:
    user = get_or_create_user(db, user_external_id)
    bootstrap_body_plan_for_date(
        db,
        user=user,
        inputs=OnboardingBootstrapInput(
            sex="female",
            age_years=34,
            height_cm=170,
            current_weight_kg=70,
            goal_type="lose_weight",
            weekly_target_rate_kg=0.5,
            timezone="Asia/Taipei",
            daily_lifestyle="sedentary_with_some_walking",
            weekly_exercise_days_band="1_2",
            local_date=local_date,
        ),
    )


def _seed_case_state(db: Session, *, case: LiveCase, local_date: str) -> dict[str, Any]:
    if case.seed_kind != "canonical_two_item_meal":
        return {}
    user = get_or_create_user(db, case.user_external_id)
    result = commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=CommitRequestCandidate(
            request_id=f"{case.case_id}-seed",
            manager_intent="food_estimation",
            version_reason="new_intake",
            meal_title="chicken rice and soup",
            raw_input="seeded canonical diagnostic state",
            estimated_kcal=650,
            protein_g=35,
            carb_g=70,
            fat_g=18,
            resolution_status="completed_meal",
            local_date=local_date,
            items=[
                MealItemPayload(name="chicken rice", estimated_kcal=500, protein_g=32, carb_g=65, fat_g=15),
                MealItemPayload(name="soup", estimated_kcal=150, protein_g=3, carb_g=5, fat_g=3),
            ],
        ),
        budget_kcal=1800,
    )
    if result is None:
        raise RuntimeError("seeded_explicit_removal_initial_commit_failed")
    items = (
        db.execute(
            select(MealItemRecord)
            .where(MealItemRecord.meal_version_id == result.meal_version_id)
            .order_by(MealItemRecord.item_index.asc())
        )
        .scalars()
        .all()
    )
    return {
        "seed_kind": case.seed_kind,
        "meal_thread_id": result.meal_thread_id,
        "meal_version_id": result.meal_version_id,
        "active_item_count": len(items),
        "active_items": [
            {
                "meal_item_id": item.id,
                "canonical_name": item.name,
                "estimated_kcal": int(item.estimated_kcal or 0),
            }
            for item in items
        ],
        "runner_inferred_semantics": False,
        "raw_text_routing_used": False,
    }


def _case_state_delta(*, turns: list[dict[str, Any]], debug_surface: dict[str, Any]) -> dict[str, Any]:
    return {
        "turn_state_deltas": [_dict(turn.get("state_delta")) for turn in turns],
        "same_truth": _dict(_dict(_dict(debug_surface).get("model")).get("same_truth")),
    }


def _case_has_provider_timeout(case: dict[str, Any]) -> bool:
    runtime_error = _dict(case.get("runtime_error"))
    error_type = str(runtime_error.get("type") or "")
    message = str(runtime_error.get("message") or "")
    if error_type in {"ReadTimeout", "TimeoutException", "TimeoutError", "ConnectTimeout", "WriteTimeout", "PoolTimeout"}:
        return True
    if str(case.get("case_contract_status") or "") == "timeout":
        return True
    return "timeout" in error_type.lower() or "timeout" in message.lower()


def _failure_layer_for_exception(exc: Exception) -> str:
    return _failure_layer_for_error_dict({"type": type(exc).__name__, "message": str(exc)})


def _failure_family_for_exception(exc: Exception) -> str:
    return _failure_family_for_error_dict({"type": type(exc).__name__, "message": str(exc)})


def _is_retryable_provider_exception(exc: Exception) -> bool:
    error_type = type(exc).__name__.lower()
    message = str(exc).lower()
    retryable_markers = (
        "timeout",
        "timed out",
        "rate limit",
        "ratelimit",
        "429",
        "too many requests",
        "temporarily unavailable",
        "connection",
        "connecterror",
        "readtimeout",
        "writetimeout",
        "pooltimeout",
        "503",
        "500",
    )
    return any(marker in error_type or marker in message for marker in retryable_markers)


def _failure_layer_for_error_dict(runtime_error: dict[str, Any]) -> str:
    error_type = str(runtime_error.get("type") or "")
    message = str(runtime_error.get("message") or "")
    if "timeout" in error_type.lower() or "timeout" in message.lower():
        return "provider_runtime_error"
    if "missing required fields" in message or "validate_manager_payload" in message or "BuilderSpace" in message:
        return "provider_contract_non_adherence"
    return "runtime"


def _failure_family_for_error_dict(runtime_error: dict[str, Any]) -> str:
    error_type = str(runtime_error.get("type") or "")
    message = str(runtime_error.get("message") or "")
    if "timeout" in error_type.lower() or "timeout" in message.lower():
        return "environment_or_provider_blocker"
    if "BuilderSpace is not configured" in message:
        return "environment_or_provider_blocker"
    if "did not return the synthetic decision tool call" in message:
        return "synthetic_decision_tool_call_missing"
    if "missing required fields" in message or "validate_manager_payload" in message:
        return "schema_payload_invalid"
    if "BuilderSpace" in message:
        return "semantic_contract_violation"
    return "runtime_failure"


def _provider_error_trace(exc: Exception, *, stage: str, profile: dict[str, Any]) -> dict[str, Any]:
    trace = _dict(getattr(exc, "trace", {}))
    return {
        "stage": stage,
        "provider_profile_id": profile["provider_profile_id"],
        "provider_profile_model": profile["model"],
        "provider_profile_role": profile["provider_profile_role"],
        "live_llm_invoked": True,
        "failure_family": _failure_family_for_exception(exc),
        "error_type": type(exc).__name__,
        "error_message": str(exc),
        "provider_trace": trace,
    }


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _has_tool_result(user_payload: dict[str, Any], tool_name: str) -> bool:
    for item in _list(user_payload.get("tool_results")):
        result = _dict(item)
        if str(result.get("tool_name") or result.get("name") or "") == tool_name:
            return True
    return False


def _optional_string(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_local_env(path: Path) -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(path, override=False, encoding="utf-8-sig")
        return
    except ModuleNotFoundError:
        pass
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def main() -> int:
    _load_local_env(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Run Accurate Intake MVP live diagnostic re-entry.")
    parser.add_argument("--output", default=str(ARTIFACT_PATH))
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--local-date", default=DEFAULT_LOCAL_DATE)
    parser.add_argument("--provider-profile-id", default=DEFAULT_ACCURATE_INTAKE_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID)
    parser.add_argument("--provider-timeout-ms", type=int, default=180000)
    parser.add_argument("--case-timeout-ms", type=int, default=None)
    parser.add_argument("--provider-request-retry-count", type=int, default=1)
    parser.add_argument("--provider-request-retry-backoff-ms", type=int, default=250)
    parser.add_argument("--provider-request-retry-jitter-ms", type=int, default=100)
    parser.add_argument("--stage", choices=(STAGE_ALL, *ORDERED_STAGE_IDS), default=STAGE_ALL)
    parser.add_argument("--case-id", default=None)
    parser.add_argument("--max-turn", type=int, default=None)
    parser.add_argument("--offline-replay-artifact", default=str(DEFAULT_OFFLINE_REPLAY_ARTIFACT))
    args = parser.parse_args()

    report = run_diagnostic(
        output_path=Path(args.output),
        db_path=Path(args.db_path),
        local_date=str(args.local_date),
        provider_profile_id=str(args.provider_profile_id),
        provider_timeout_ms=int(args.provider_timeout_ms),
        case_timeout_ms=args.case_timeout_ms,
        provider_request_retry_count=int(args.provider_request_retry_count),
        provider_request_retry_backoff_ms=int(args.provider_request_retry_backoff_ms),
        provider_request_retry_jitter_ms=int(args.provider_request_retry_jitter_ms),
        stage=str(args.stage),
        case_id=str(args.case_id) if args.case_id else None,
        max_turn=args.max_turn,
        offline_replay_artifact_path=Path(args.offline_replay_artifact) if args.offline_replay_artifact else None,
    )
    print(
        json.dumps(
            {
                "artifact": str(Path(args.output)),
                "provider_mode": report.get("provider_mode"),
                "live_invoked": report.get("live_invoked"),
                "provider_profile_model": report.get("provider_profile_model"),
                "summary": report.get("summary"),
                "readiness_claimed": report.get("readiness_claimed"),
                "failure_layer": report.get("failure_layer"),
                "failure_family": report.get("failure_family"),
            },
            ensure_ascii=False,
        )
    )
    return 0


__all__ = [
    "DEFAULT_ACCURATE_INTAKE_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID",
    "ScriptedAccurateIntakeLiveProvider",
    "AccurateIntakeLiveDiagnosticProvider",
    "build_missing_provider_report",
    "provider_profile",
    "run_diagnostic",
]


if __name__ == "__main__":
    raise SystemExit(main())
