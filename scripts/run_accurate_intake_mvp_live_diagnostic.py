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

from app.composition.accurate_intake_debug_routes import build_accurate_intake_debug_payload  # noqa: E402
from app.composition.accurate_intake_live_trace_expectations import grade_live_trace_expectations  # noqa: E402
from app.composition.canonical_persistence import commit_meal_payload_to_canonical  # noqa: E402
from app.composition.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date  # noqa: E402
from app.database import get_or_create_user  # noqa: E402
from app.intake.infrastructure.models import MealItemRecord  # noqa: E402
from app.models import Base  # noqa: E402
from app.runtime.agent.founder_live_manager_contract import (  # noqa: E402
    FOUNDER_LIVE_MANAGER_INTENT_TYPE_BY_SEMANTIC_INTENT,
    FOUNDER_LIVE_MANAGER_SCHEMA_NAME,
    FOUNDER_LIVE_MANAGER_SCHEMA_VERSION,
    FOUNDER_LIVE_MANAGER_REQUIRED_FIELDS,
    FOUNDER_LIVE_MANAGER_TRANSPORT_POLICY,
    founder_live_manager_contract_constraints,
)
from app.runtime.contracts.trace import MANAGER_LOOP_STAGE  # noqa: E402
from app.shared.contracts.readiness_claim import build_readiness_claim  # noqa: E402
from app.shared.contracts.intake_payloads import CommitRequestCandidate, MealItemPayload  # noqa: E402


ARTIFACT_PATH = ROOT / "artifacts" / "accurate_intake_mvp_live_diagnostic.json"
DEFAULT_DB_PATH = ROOT / "artifacts" / "accurate_intake_mvp_live_diagnostic.sqlite3"
DEFAULT_OFFLINE_REPLAY_ARTIFACT = ROOT / "artifacts" / "accurate_intake_mvp_offline_shadow_replay.json"
DEFAULT_LOCAL_DATE = "2026-05-02"
DEFAULT_ACCURATE_INTAKE_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID = (
    "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic"
)
ACTIVE_ENTRYPOINT = "app.composition.intake_turn_orchestrator.execute_intake_turn"
PUBLIC_ENTRY_READ_TOOLS = {"body.get_active_plan", "budget.get_today_summary"}
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
DEFAULT_PROVIDER_REQUEST_TIMEOUT_MS = 180_000
DEFAULT_CASE_TIMEOUT_GRACE_MS = 15_000
DEFAULT_PROVIDER_REQUEST_RETRY_COUNT = 0
INITIAL_MANIFEST_SINGLE_TURN_CASES = {
    "MVP-LIVE-001": "no_plan_consumed_without_budget_target",
    "MVP-LIVE-005": "generic_common_food_range",
}

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
    manifest_case_id: str | None = None
    case_family: str | None = None
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
        provider_request_timeout_ms: int = DEFAULT_PROVIDER_REQUEST_TIMEOUT_MS,
        provider_request_retry_count: int = 0,
        provider_request_retry_backoff_ms: int = 0,
        provider_request_retry_jitter_ms: int = 0,
    ) -> None:
        self._provider = provider
        self.profile = dict(profile)
        self.live_invoked = live_invoked
        self.invocations: list[dict[str, Any]] = []
        self._current_step: dict[str, Any] = {}
        self.provider_request_timeout_ms = max(1, int(provider_request_timeout_ms))
        self.provider_request_retry_count = max(0, int(provider_request_retry_count))
        self.provider_request_retry_backoff_ms = max(0, int(provider_request_retry_backoff_ms))
        self.provider_request_retry_jitter_ms = max(0, int(provider_request_retry_jitter_ms))

    def begin_step(self, step_script: dict[str, Any]) -> None:
        self._current_step = dict(step_script)
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
        span_context = self._provider_span_context(stage=stage, kwargs=kwargs)
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
                        **span_context,
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
                error_trace.update(_transport_attempt_summary(error_trace))
                retry_attempts.append(error_trace)
                self.invocations.append(error_trace)
                if retryable and attempt_index < max_attempts:
                    await asyncio.sleep(self._retry_delay_seconds(attempt_index))
                    continue
                raise
            elapsed_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
            result_kind = "pass_after_retry" if attempt_index > 1 else "strict_pass_first_attempt"
            transport_summary = _transport_attempt_summary(_dict(trace))
            provider_wrapper_overhead_ms = _provider_wrapper_overhead_ms(elapsed_ms, transport_summary)
            enriched_trace = {
                **_dict(trace),
                **transport_summary,
                "provider_wrapper_overhead_ms": provider_wrapper_overhead_ms,
                **span_context,
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
                    **span_context,
                    "provider_trace_stage": _optional_string(_dict(trace).get("stage")),
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
                    "provider_wrapper_overhead_ms": provider_wrapper_overhead_ms,
                    **transport_summary,
                    "provider_trace": enriched_trace,
                }
            )
            return payload, enriched_trace
        raise RuntimeError("provider retry loop exited without result")

    def _provider_span_context(self, *, stage: str, kwargs: dict[str, Any]) -> dict[str, Any]:
        user_payload = _dict(kwargs.get("user_payload"))
        step = self._current_step
        context: dict[str, Any] = {
            "span_kind": "provider_request",
            "diagnostic_stage_id": _optional_string(
                step.get("diagnostic_stage_id") or user_payload.get("diagnostic_stage_id")
            ),
            "diagnostic_case_id": _optional_string(step.get("case_id")),
            "diagnostic_manifest_case_id": _optional_string(step.get("manifest_case_id")),
            "diagnostic_case_family": _optional_string(step.get("case_family")),
            "diagnostic_turn": _optional_int(step.get("turn")),
            "diagnostic_turn_kind": _optional_string(step.get("turn_kind") or step.get("kind")),
            "manager_round_index": _optional_int(user_payload.get("round_index")),
            "manager_loop_scope": _optional_string(user_payload.get("manager_loop_scope")),
        }
        return {key: value for key, value in context.items() if value is not None}

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
        if PUBLIC_ENTRY_READ_TOOLS.intersection(available_tools):
            return self._entry_decision(user_payload=user_payload), self._trace("entry_decision")
        return self._execution_decision(
            available_tools=available_tools,
            round_index=round_index,
            user_payload=user_payload,
        ), self._trace("execution_decision")

    def _entry_decision(self, *, user_payload: dict[str, Any] | None = None) -> dict[str, Any]:
        user_payload = _dict(user_payload)
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
        if entry_intent == "answer_query":
            answer_basis = _active_meal_answer_basis_from_context_packet(user_payload)
            return self._final(
                intent_type="answer_query",
                current_turn_intent="answer_query",
                final_action="answer_only",
                workflow_effect="answer_only",
                mutation_intent_candidate="no_mutation",
                evidence_posture="active_meal_basis_read_only",
                estimation_posture="not_applicable",
                answer_basis=answer_basis,
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
        current_turn_intent = str(self._current_step.get("semantic_intent") or "log_meal")
        payload = self._final(
            intent_type=_intent_type_for_semantic_intent(current_turn_intent),
            current_turn_intent=current_turn_intent,
            final_action="no_commit",
            workflow_effect="route_to_intake",
            mutation_intent_candidate="canonical_write",
            target_attachment={"mode": self._current_step.get("target_mode") or "new_meal"},
            evidence_posture="needs_tool_evidence",
            estimation_posture="estimable",
        )
        payload["semantic_decision"]["final_action_candidate"] = str(self._current_step.get("final_action") or "commit")
        payload["semantic_decision"]["mutation_intent_candidate"] = str(
            self._current_step.get("mutation_intent") or "canonical_write"
        )
        return payload

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
            semantic_extras = {
                key: self._current_step[key]
                for key in ("base_dish", "listed_items", "retrieval_goal")
                if key in self._current_step
            }
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
                    **semantic_extras,
                },
            }
        return self._final(
            intent_type=_intent_type_for_semantic_intent(str(self._current_step.get("semantic_intent") or "log_meal")),
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
        target_reference = _target_reference_from_manager_context_packet(user_payload)
        if not target_reference:
            target_reference = _target_reference_from_legacy_resolved_state(user_payload)
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
        answer_basis: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        target = dict(target_attachment or {"mode": "none"})
        if self._current_step.get("correction_operation"):
            target["correction_operation"] = self._current_step.get("correction_operation")
        if self._current_step.get("target_canonical_name"):
            target["canonical_name"] = self._current_step.get("target_canonical_name")
        answer_contract = {"reply_text": str(self._current_step.get("reply_text") or workflow_effect)}
        if self._current_step.get("correction_operation"):
            answer_contract["correction_operation"] = self._current_step.get("correction_operation")
        if followup_question:
            answer_contract["followup_question"] = followup_question
        if answer_basis:
            answer_contract["answer_basis"] = answer_basis
        semantic_extras = {
            key: self._current_step[key]
            for key in ("base_dish", "listed_items", "retrieval_goal")
            if key in self._current_step
        }
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
                **semantic_extras,
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
        timeout_policy=_timeout_policy(
            provider_timeout_ms=0,
            case_timeout_ms=0,
            effective_case_timeout_ms=0,
            provider_request_retry_count=0,
            provider_request_retry_backoff_ms=0,
            provider_request_retry_jitter_ms=0,
        ),
        failure_layer="provider_runtime_error",
        failure_family="environment_or_provider_blocker",
    )


def run_diagnostic(
    *,
    output_path: Path = ARTIFACT_PATH,
    db_path: Path = DEFAULT_DB_PATH,
    local_date: str = DEFAULT_LOCAL_DATE,
    provider_profile_id: str = DEFAULT_ACCURATE_INTAKE_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID,
    provider_timeout_ms: int = DEFAULT_PROVIDER_REQUEST_TIMEOUT_MS,
    case_timeout_ms: int | None = None,
    provider_request_retry_count: int = DEFAULT_PROVIDER_REQUEST_RETRY_COUNT,
    provider_request_retry_backoff_ms: int = 250,
    provider_request_retry_jitter_ms: int = 100,
    provider_override: Any | None = None,
    provider_mode: str = "live",
    live_invoked: bool = True,
    stage: str = STAGE_ALL,
    case_id: str | None = None,
    manifest_case_id: str | None = None,
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
    effective_case_timeout_ms = int(case_timeout_ms if case_timeout_ms is not None else retry_budget_ms + DEFAULT_CASE_TIMEOUT_GRACE_MS)
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
                cases=_single_case_probe_inventory(
                    case_id=case_id,
                    manifest_case_id=manifest_case_id,
                    max_turn=max_turn,
                ),
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
        timeout_policy=_timeout_policy(
            provider_timeout_ms=provider_timeout_ms,
            case_timeout_ms=case_timeout_ms,
            effective_case_timeout_ms=effective_case_timeout_ms,
            provider_request_retry_count=provider_request_retry_count,
            provider_request_retry_backoff_ms=provider_request_retry_backoff_ms,
            provider_request_retry_jitter_ms=provider_request_retry_jitter_ms,
        ),
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
            "available_tools": sorted(PUBLIC_ENTRY_READ_TOOLS),
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
                        _run_case(
                            SessionLocal,
                            case=case,
                            provider=provider,
                            local_date=local_date,
                            stage_id=stage_id,
                        ),
                        timeout=max(0.001, case_timeout_ms / 1000),
                    )
                )
            except Exception as exc:
                case_result = _case_error(
                    case,
                    exc,
                    provider_invocations=provider.invocations[invocation_start_index:],
                )
            case_invocations = _json_safe(provider.invocations[invocation_start_index:])
            case_latency_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
            case_provider_latency_ms = sum(int(item.get("latency_ms") or 0) for item in case_invocations)
            case_result.setdefault("provider_invocations", case_invocations)
            case_result["provider_invocation_count"] = len(case_invocations)
            case_result["provider_invocation_latency_ms"] = case_provider_latency_ms
            case_result["latency_ms"] = case_latency_ms
            case_result["non_provider_latency_ms"] = max(0, case_latency_ms - case_provider_latency_ms)
            case_result["latency_attribution"] = {
                "case_total_ms": case_latency_ms,
                "provider_invocation_ms": case_provider_latency_ms,
                "non_provider_runtime_ms": max(0, case_latency_ms - case_provider_latency_ms),
            }
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
        manifest_case_ids=[str(case.get("manifest_case_id") or "") for case in stage_cases if case.get("manifest_case_id")],
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
        return {"allowed": False, "failure_family": "offline_replay_not_clean_strict", "source_path": str(path)}
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
    stage_id: str,
) -> dict[str, Any]:
    with SessionLocal() as db:
        if case.body_plan_seeded:
            _seed_body_plan(db, user_external_id=case.user_external_id, local_date=local_date)
        seeded_state = _seed_case_state(db, case=case, local_date=local_date)
        turns: list[dict[str, Any]] = []
        for step in case.steps:
            provider.begin_step(
                {
                    **dict(step.script),
                    "diagnostic_stage_id": stage_id,
                    "case_id": case.case_id,
                    "manifest_case_id": case.manifest_case_id,
                    "case_family": case.case_family,
                    "turn": step.turn,
                    "turn_kind": step.kind,
                    "kind": step.kind,
                }
            )
            turn_invocation_start_index = len(provider.invocations)
            turn_started = datetime.now(UTC)
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
            turn_latency_ms = int((datetime.now(UTC) - turn_started).total_seconds() * 1000)
            turns.append(
                _turn_summary(
                    step,
                    result,
                    latency_ms=turn_latency_ms,
                    provider_invocations=provider.invocations[turn_invocation_start_index:],
                )
            )
        debug_surface = build_accurate_intake_debug_payload(
            db,
            user_external_id=case.user_external_id,
            local_date=local_date,
        )
    verdict, blockers, failure_layer = _validate_case(case=case, turns=turns, debug_surface=debug_surface)
    case_result = {
        "case_id": case.case_id,
        "manifest_case_id": case.manifest_case_id,
        "case_family": case.case_family,
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
                    {
                        "entry_intent": "log_meal",
                        "semantic_intent": "log_meal",
                        "final_action": "commit",
                        "listed_items": ["雞肉飯", "湯"],
                        "retrieval_goal": "listed_item_lookup",
                    },
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
                        "listed_items": ["雞肉飯少一點"],
                        "retrieval_goal": "listed_item_lookup",
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
                    {
                        "entry_intent": "log_meal",
                        "semantic_intent": "log_meal",
                        "final_action": "commit",
                        "listed_items": ["珍珠奶茶"],
                        "retrieval_goal": "listed_item_lookup",
                    },
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
                        "listed_items": ["半糖大杯珍珠奶茶"],
                        "retrieval_goal": "listed_item_lookup",
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
                    {
                        "entry_intent": "log_meal",
                        "semantic_intent": "log_meal",
                        "final_action": "commit",
                        "listed_items": ["豆干", "海帶", "貢丸"],
                        "retrieval_goal": "listed_item_lookup",
                    },
                ),
            ),
        ),
        LiveCase(
            case_id="teppan_breakfast_explain_refine_dogfood",
            description="Dogfood breakfast combo: unanchored combo asks first, listed components commit, then basis question stays read-only.",
            user_external_id="live-diag-teppan-breakfast",
            body_plan_seeded=True,
            steps=(
                LiveStep(
                    1,
                    "patterned_combo_without_anchor",
                    "\u6211\u65e9\u9910\u5403\u65e9\u9910\u5e97\u9435\u677f\u9eb5\u5957\u9910",
                    {
                        "entry_intent": "log_meal",
                        "semantic_intent": "log_meal",
                        "final_action": "ask_followup",
                        "followup_question": "\u9019\u500b\u9435\u677f\u9eb5\u5957\u9910\u6709\u54ea\u4e9b\u5167\u5bb9\uff1f\u4f8b\u5982\u86cb\u3001\u8c6c\u6392\u6216\u98f2\u6599\u3002",
                        "reply_text": "\u9019\u500b\u5957\u9910\u6211\u9084\u4e0d\u78ba\u5b9a\u7d44\u6210\uff0c\u5148\u4e0d\u5e6b\u4f60\u8a18\u5165\u3002\u53ef\u4ee5\u544a\u8a34\u6211\u6709\u9435\u677f\u9eb5\u4ee5\u5916\u7684\u5167\u5bb9\u55ce\uff1f",
                    },
                ),
                LiveStep(
                    2,
                    "component_followup",
                    "\u6709\u9435\u677f\u9eb5\u3001\u8c6c\u8089\u7247\u3001\u8377\u5305\u86cb\uff0c\u9084\u6709\u4e00\u676f\u7d05\u8336",
                    {
                        "entry_intent": "log_meal",
                        "semantic_intent": "log_meal",
                        "final_action": "commit",
                        "target_mode": "target_pending_followup",
                        "base_dish": "\u65e9\u9910\u5e97\u9435\u677f\u9eb5\u5957\u9910",
                        "listed_items": [
                            "\u9435\u677f\u9eb5",
                            "\u65e9\u9910\u5e97\u8c6c\u8089\u7247",
                            "\u8377\u5305\u86cb",
                            "\u7d05\u8336",
                        ],
                        "retrieval_goal": "listed_item_lookup",
                    },
                ),
                LiveStep(
                    3,
                    "estimate_basis_question",
                    "\u4f60\u662f\u600e\u9ebc\u4f30\u7684\uff1f\u4f60\u662f\u4e0d\u662f\u8a8d\u70ba\u6709\u4ec0\u9ebc\u7d44\u6210\uff1f",
                    {
                        "entry_intent": "answer_query",
                        "reply_text": "\u6211\u662f\u6839\u64da\u4f60\u88dc\u5145\u7684\u9435\u677f\u9eb5\u3001\u8c6c\u8089\u7247\u3001\u8377\u5305\u86cb\u548c\u7d05\u8336\u4f86\u4f30\uff0c\u6c92\u6709\u518d\u984d\u5916\u5047\u8a2d\u5176\u4ed6\u914d\u6599\u3002",
                    },
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
            manifest_case_id="MVP-LIVE-001",
            case_family="no_plan_degraded",
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


def _exact_item_official_label_case() -> LiveCase:
    return LiveCase(
        case_id="exact_item_official_label",
        description="Exact-item single-turn commit uses official-card posture without followup drift.",
        user_external_id="live-diag-exact-item",
        body_plan_seeded=True,
        steps=(
            LiveStep(
                1,
                "exact_item_commit",
                "\u6211\u559d\u4e86\u661f\u5df4\u514b\u51b0\u90a3\u5802\u5927\u676f",
                {
                    "entry_intent": "log_meal",
                    "semantic_intent": "log_meal",
                    "final_action": "commit",
                },
            ),
        ),
    )


def _generic_common_food_range_case() -> LiveCase:
    return LiveCase(
        case_id="generic_common_food_range",
        description="Generic common-food single-turn commit preserves range posture without fake exactness.",
        user_external_id="live-diag-generic-range",
        body_plan_seeded=True,
        manifest_case_id="MVP-LIVE-005",
        case_family="generic_food_range",
        steps=(
            LiveStep(
                1,
                "generic_common_food_commit",
                "\u6211\u5403\u4e86\u4e00\u7897\u725b\u8089\u9eb5",
                {
                    "entry_intent": "log_meal",
                    "semantic_intent": "log_meal",
                    "final_action": "commit",
                    "base_dish": "\u725b\u8089\u9eb5",
                    "retrieval_goal": "generic_anchor_lookup",
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


def _single_case_probe_inventory(
    *,
    case_id: str | None = None,
    manifest_case_id: str | None = None,
    max_turn: int | None = None,
) -> list[LiveCase]:
    if case_id and manifest_case_id:
        raise ValueError("Use either case_id or manifest_case_id for a single-case live diagnostic, not both.")
    cases = [
        _seeded_explicit_removal_case(),
        _exact_item_official_label_case(),
        _generic_common_food_range_case(),
        *_case_inventory(),
    ]
    selected = (
        _runtime_case_id_for_manifest_case_id(manifest_case_id)
        if manifest_case_id
        else str(case_id or "explicit_item_removal_seeded")
    )
    for case in cases:
        if case.case_id == selected:
            return [_limit_case_turns(case, max_turn=max_turn)]
    supported = ", ".join(case.case_id for case in cases)
    raise ValueError(f"Unsupported Accurate Intake live diagnostic case_id: {selected}. Supported: {supported}")


def _runtime_case_id_for_manifest_case_id(manifest_case_id: str | None) -> str:
    selected = str(manifest_case_id or "").strip()
    if not selected:
        return "explicit_item_removal_seeded"
    runtime_case_id = INITIAL_MANIFEST_SINGLE_TURN_CASES.get(selected)
    if runtime_case_id:
        return runtime_case_id
    supported = ", ".join(sorted(INITIAL_MANIFEST_SINGLE_TURN_CASES))
    raise ValueError(
        f"Unsupported Accurate Intake live diagnostic manifest_case_id: {selected}. "
        f"Initial single-turn manifest support: {supported}"
    )


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


def _turn_summary(
    step: LiveStep,
    result: dict[str, Any],
    *,
    latency_ms: int,
    provider_invocations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    execution = _dict(result.get("intake_execution_manager"))
    final = _dict(execution.get("final"))
    manager_decision = _dict(result.get("manager_decision"))
    manager_rounds = _json_safe(_list(execution.get("manager_rounds")))
    invocation_summary = _provider_invocation_summary(provider_invocations or [])
    provider_latency_ms = int(invocation_summary.get("provider_invocation_latency_ms") or 0)
    non_provider_latency_ms = max(0, int(latency_ms) - provider_latency_ms)
    runtime_stage_timings = _json_safe(_list(_dict(result.get("latency_tracking")).get("stage_timings")))
    return {
        "turn": step.turn,
        "kind": step.kind,
        "text": step.text,
        "request_id": result.get("request_id"),
        "latency_ms": int(latency_ms),
        "non_provider_latency_ms": non_provider_latency_ms,
        "latency_attribution": {
            "turn_total_ms": int(latency_ms),
            "provider_invocation_ms": provider_latency_ms,
            "non_provider_runtime_ms": non_provider_latency_ms,
        },
        "coach_message": result.get("coach_message") or result.get("assistant_message"),
        "show_macro": result.get("show_macro"),
        "macro_guard_reason": result.get("macro_guard_reason"),
        "manager_intent": manager_decision.get("intent_type"),
        "manager_final_action": final.get("final_action") or manager_decision.get("final_action"),
        "workflow_effect": final.get("workflow_effect") or manager_decision.get("workflow_effect"),
        "answer_basis": _turn_answer_basis(manager_decision),
        "estimation_summary": _turn_estimation_summary(manager_rounds),
        "state_delta": _json_safe(_dict(result.get("state_delta"))),
        "remaining_budget": _json_safe(_dict(result.get("remaining_budget"))),
        "manager_rounds": manager_rounds,
        "prompt_footprint_summary": _prompt_footprint_summary_from_rounds(manager_rounds),
        "provider_invocation_summary": invocation_summary,
        "runtime_stage_timings": runtime_stage_timings,
        "runtime_stage_timing_summary": _runtime_stage_timing_summary(runtime_stage_timings),
        "hard_fail_conditions": list(result.get("hard_fail_conditions") or []),
        "runtime_error": None,
    }


def _turn_answer_basis(manager_decision: dict[str, Any]) -> dict[str, Any]:
    answer_contract = _dict(manager_decision.get("answer_contract"))
    basis = _dict(answer_contract.get("answer_basis"))
    if basis:
        return _json_safe(basis)
    basis_text = str(answer_contract.get("answer_basis") or "").strip()
    references_active_meal = answer_contract.get("references_active_meal") is True or _basis_text_references_active_meal(
        basis_text
    )
    if basis_text and references_active_meal:
        normalized = {
            "references_active_meal": True,
            "assumption_or_composition_explained": True,
            "basis_text": basis_text,
        }
        active_basis = _active_meal_basis_from_manager_decision_trace(manager_decision)
        for key in ("meal_thread_id", "meal_version_id"):
            if active_basis.get(key) is not None:
                normalized[key] = active_basis[key]
        return _json_safe(normalized)
    return {}


def _basis_text_references_active_meal(basis_text: str) -> bool:
    normalized = " ".join(str(basis_text or "").lower().split())
    return "active_meal_estimate_basis" in normalized or "references_active_meal: true" in normalized


def _active_meal_basis_from_manager_decision_trace(manager_decision: dict[str, Any]) -> dict[str, Any]:
    trace = _dict(manager_decision.get("trace"))
    for round_item in _list(trace.get("manager_rounds")):
        phase_a_input = _dict(_dict(round_item).get("phase_a_input"))
        packet = _dict(phase_a_input.get("manager_context_packet_v1"))
        active_day_state = _dict(packet.get("active_day_state"))
        active_basis = _dict(active_day_state.get("active_meal_estimate_basis"))
        if active_basis:
            return active_basis
    return {}


def _turn_estimation_summary(manager_rounds: list[dict[str, Any]]) -> dict[str, Any]:
    component_names: list[str] = []
    estimated_kcal_values: list[int] = []
    for round_item in _list(manager_rounds):
        round_dict = _dict(round_item)
        decision = _dict(round_dict.get("decision"))
        semantic_decision = _dict(decision.get("semantic_decision"))
        for item in _list(semantic_decision.get("listed_items")):
            name = str(item or "").strip()
            if name:
                component_names.append(name)
        for tool_result in _list(round_dict.get("tool_results")):
            nutrition_payload = _dict(_dict(tool_result).get("evidence")).get("nutrition_payload")
            nutrition_payload = _dict(nutrition_payload)
            if nutrition_payload.get("estimated_kcal") is not None:
                estimated_kcal_values.append(int(nutrition_payload.get("estimated_kcal") or 0))
            trace_contract = _dict(nutrition_payload.get("trace_contract"))
            for item in _list(trace_contract.get("components")):
                name = str(item or "").strip()
                if name:
                    component_names.append(name)
            for item in _list(trace_contract.get("component_breakdown")):
                name = str(_dict(item).get("name") or _dict(item).get("canonical_name") or "").strip()
                if name:
                    component_names.append(name)
    deduped = list(dict.fromkeys(component_names))
    return {
        "component_names": deduped,
        "estimated_kcal_values": estimated_kcal_values,
        "used_default_fallback_400_macro": bool(not deduped and 400 in estimated_kcal_values),
    }


def _runtime_stage_timing_summary(stage_timings: list[dict[str, Any]]) -> dict[str, Any]:
    durations = [int(_dict(item).get("duration_ms") or 0) for item in stage_timings]
    slowest = max(stage_timings, key=lambda item: int(_dict(item).get("duration_ms") or 0), default={})
    return {
        "recorded_stage_count": len(stage_timings),
        "recorded_stage_total_ms": sum(durations),
        "slowest_stage_name": str(_dict(slowest).get("stage") or "none"),
        "slowest_stage_ms": int(_dict(slowest).get("duration_ms") or 0),
    }


def _provider_invocation_summary(invocations: list[dict[str, Any]]) -> dict[str, Any]:
    usage_records = [_dict(_dict(invocation).get("provider_trace")).get("usage") for invocation in invocations]
    usage_dicts = [_dict(usage) for usage in usage_records]
    cache_reporting_call_count = sum(1 for usage in usage_dicts if _cached_tokens_from_usage(usage) is not None)
    cache_hit_call_count = sum(1 for usage in usage_dicts if int(_cached_tokens_from_usage(usage) or 0) > 0)
    cached_tokens_known = len(usage_dicts) == cache_reporting_call_count
    transport_summaries = [
        _transport_attempt_summary(_dict(_dict(invocation).get("provider_trace"))) for invocation in invocations
    ]
    prompt_cache = _provider_prompt_cache_summary(invocations)
    return {
        "provider_invocation_count": len(invocations),
        "provider_invocation_latency_ms": sum(int(_dict(item).get("latency_ms") or 0) for item in invocations),
        "prompt_tokens": sum(_usage_prompt_tokens(usage) for usage in usage_dicts),
        "completion_tokens": sum(_usage_completion_tokens(usage) for usage in usage_dicts),
        "cached_tokens": sum(_cached_tokens_from_usage(usage) or 0 for usage in usage_dicts),
        "cache_reporting_call_count": cache_reporting_call_count,
        "cache_hit_call_count": cache_hit_call_count,
        "cached_tokens_known": cached_tokens_known,
        "cached_tokens_unknown": len(usage_dicts) > cache_reporting_call_count,
        "cache_miss_claim_allowed": bool(usage_dicts) and cached_tokens_known and cache_hit_call_count == 0,
        "provider_wrapper_overhead_ms": sum(
            int(item.get("provider_wrapper_overhead_ms") or 0) for item in invocations
        ),
        "transport_attempt_count": sum(int(item.get("transport_attempt_count") or 0) for item in transport_summaries),
        "transport_attempt_latency_ms": sum(
            int(item.get("transport_attempt_latency_ms") or 0) for item in transport_summaries
        ),
        "slowest_transport_attempt_ms": max(
            (int(item.get("slowest_transport_attempt_ms") or 0) for item in transport_summaries),
            default=0,
        ),
        "prompt_cache": prompt_cache,
    }


def _provider_prompt_cache_summary(invocations: list[dict[str, Any]]) -> dict[str, Any]:
    cache_requests = [
        _dict(_dict(_dict(invocation).get("provider_trace")).get("prompt_cache_request"))
        for invocation in invocations
    ]
    identity_requests = [item for item in cache_requests if item.get("identity_version")]
    stable_hashes = {
        str(item.get("stable_prefix_sha256"))
        for item in identity_requests
        if item.get("stable_prefix_sha256")
    }
    dynamic_hashes = {
        str(item.get("dynamic_suffix_sha256"))
        for item in identity_requests
        if item.get("dynamic_suffix_sha256")
    }
    return {
        "provider_usage_is_cache_truth": True,
        "identity_count": len(identity_requests),
        "missing_identity_count": max(0, len(invocations) - len(identity_requests)),
        "prompt_cache_key_count": sum(
            1 for item in identity_requests if item.get("provider_request_includes_prompt_cache_key") is True
        ),
        "stable_prefix_unique_count": len(stable_hashes),
        "dynamic_suffix_unique_count": len(dynamic_hashes),
        "repeated_stable_prefix_observed": len(stable_hashes) == 1 and len(identity_requests) > 1,
        "request_payload_utf8_bytes": sum(int(item.get("request_payload_utf8_bytes") or 0) for item in identity_requests),
        "stable_prefix_utf8_bytes": sum(int(item.get("stable_prefix_utf8_bytes") or 0) for item in identity_requests),
        "dynamic_suffix_utf8_bytes": sum(int(item.get("dynamic_suffix_utf8_bytes") or 0) for item in identity_requests),
    }


def _prompt_footprint_summary_from_rounds(manager_rounds: list[dict[str, Any]]) -> dict[str, Any]:
    footprints: list[dict[str, Any]] = []
    for round_item in _list(manager_rounds):
        prompt_layer = _dict(_dict(round_item).get("prompt_layer_contract"))
        footprint = _dict(prompt_layer.get("prompt_footprint"))
        if footprint:
            footprints.append(footprint)
    return _combine_prompt_footprint_summaries(
        _prompt_footprint_summary_from_footprint(footprint) for footprint in footprints
    )


def _prompt_footprint_summary_from_turns(turns: list[dict[str, Any]]) -> dict[str, Any]:
    return _combine_prompt_footprint_summaries(
        _dict(_dict(turn).get("prompt_footprint_summary")) for turn in _list(turns)
    )


def _prompt_footprint_summary_from_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    return _combine_prompt_footprint_summaries(
        _dict(_dict(case).get("prompt_footprint_summary")) for case in _list(cases)
    )


def _prompt_footprint_summary_from_footprint(footprint: dict[str, Any]) -> dict[str, Any]:
    section_totals: dict[str, int] = {}
    key_totals: dict[str, int] = {}
    for section in _list(footprint.get("dynamic_sections")):
        section_id = _optional_string(_dict(section).get("section_id"))
        if not section_id:
            continue
        section_totals[section_id] = section_totals.get(section_id, 0) + int(
            _dict(section).get("utf8_bytes") or 0
        )
        for key_footprint in _list(_dict(section).get("key_footprints")):
            key = _optional_string(_dict(key_footprint).get("key"))
            if not key:
                continue
            key_totals[key] = key_totals.get(key, 0) + int(
                _dict(key_footprint).get("utf8_bytes") or 0
            )
    return {
        "measurement": "json_utf8_bytes_trace_only",
        "provider_usage_is_token_truth": bool(footprint.get("provider_usage_is_token_truth") is True),
        "manager_round_count": 1,
        "system_prompt_utf8_bytes_sent": int(footprint.get("system_prompt_utf8_bytes") or 0),
        "dynamic_payload_utf8_bytes_sent": int(footprint.get("dynamic_payload_total_utf8_bytes") or 0),
        "max_dynamic_payload_utf8_bytes": int(footprint.get("dynamic_payload_total_utf8_bytes") or 0),
        "largest_dynamic_section_id": _largest_section_id(section_totals)
        or _optional_string(footprint.get("largest_dynamic_section_id")),
        "dynamic_section_utf8_bytes": dict(sorted(section_totals.items())),
        "largest_dynamic_key": _largest_key_payload(key_totals)
        or _dict(footprint.get("largest_dynamic_key"))
        or None,
        "dynamic_key_utf8_bytes": dict(sorted(key_totals.items())),
    }


def _combine_prompt_footprint_summaries(summaries: Any) -> dict[str, Any]:
    section_totals: dict[str, int] = {}
    key_totals: dict[str, int] = {}
    manager_round_count = 0
    system_prompt_bytes = 0
    dynamic_payload_bytes = 0
    max_dynamic_payload_bytes = 0
    provider_usage_is_token_truth = True
    for raw_summary in summaries:
        summary = _dict(raw_summary)
        if not summary:
            continue
        manager_round_count += int(summary.get("manager_round_count") or 0)
        system_prompt_bytes += int(summary.get("system_prompt_utf8_bytes_sent") or 0)
        dynamic_payload_bytes += int(summary.get("dynamic_payload_utf8_bytes_sent") or 0)
        max_dynamic_payload_bytes = max(
            max_dynamic_payload_bytes,
            int(summary.get("max_dynamic_payload_utf8_bytes") or 0),
        )
        if summary.get("provider_usage_is_token_truth") is False:
            provider_usage_is_token_truth = False
        for section_id, value in _dict(summary.get("dynamic_section_utf8_bytes")).items():
            section_totals[str(section_id)] = section_totals.get(str(section_id), 0) + int(value or 0)
        for key, value in _dict(summary.get("dynamic_key_utf8_bytes")).items():
            key_totals[str(key)] = key_totals.get(str(key), 0) + int(value or 0)
    return {
        "measurement": "json_utf8_bytes_trace_only",
        "provider_usage_is_token_truth": provider_usage_is_token_truth,
        "manager_round_count": manager_round_count,
        "system_prompt_utf8_bytes_sent": system_prompt_bytes,
        "dynamic_payload_utf8_bytes_sent": dynamic_payload_bytes,
        "max_dynamic_payload_utf8_bytes": max_dynamic_payload_bytes,
        "largest_dynamic_section_id": _largest_section_id(section_totals),
        "dynamic_section_utf8_bytes": dict(sorted(section_totals.items())),
        "largest_dynamic_key": _largest_key_payload(key_totals),
        "dynamic_key_utf8_bytes": dict(sorted(key_totals.items())),
    }


def _largest_section_id(section_totals: dict[str, int]) -> str | None:
    if not section_totals:
        return None
    return max(section_totals.items(), key=lambda item: item[1])[0]


def _largest_key_payload(key_totals: dict[str, int]) -> dict[str, Any] | None:
    if not key_totals:
        return None
    key, utf8_bytes = max(key_totals.items(), key=lambda item: item[1])
    return {"key": key, "utf8_bytes": utf8_bytes}


def _transport_attempt_summary(trace: dict[str, Any]) -> dict[str, Any]:
    attempts = [_dict(item) for item in _list(trace.get("transport_attempts"))]
    durations = [int(attempt.get("duration_ms") or 0) for attempt in attempts]
    return {
        "transport_attempt_count": len(attempts),
        "transport_attempt_latency_ms": sum(durations),
        "slowest_transport_attempt_ms": max(durations, default=0),
    }


def _provider_wrapper_overhead_ms(latency_ms: int, transport_summary: dict[str, Any]) -> int:
    if int(transport_summary.get("transport_attempt_count") or 0) <= 0:
        return 0
    return max(0, int(latency_ms) - int(transport_summary.get("transport_attempt_latency_ms") or 0))


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
        "manifest_case_id": case.manifest_case_id,
        "case_family": case.case_family,
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
    trace_expectation_grade = grade_live_trace_expectations(decorated)
    if trace_expectation_grade.get("required_status") == "fail":
        decorated["verdict"] = "fail"
        decorated["blockers"] = [*_list(decorated.get("blockers")), "trace_expectation_required_failed"]
        decorated["failure_layer"] = "trace_expectation"
        decorated["failure_family"] = "golden_trace_required_mismatch"
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
    decorated["trace_expectation_grade"] = trace_expectation_grade
    decorated["runner_inferred_semantics"] = False
    decorated["raw_text_routing_used"] = False
    decorated["prompt_footprint_summary"] = _prompt_footprint_summary_from_turns(_list(decorated.get("turns")))
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
        "prompt_footprint_summary": _prompt_footprint_summary_from_cases(cases),
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
    timeout_policy: dict[str, Any],
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
            "timeout_policy": timeout_policy,
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


def _timeout_policy(
    *,
    provider_timeout_ms: int,
    case_timeout_ms: int | None,
    effective_case_timeout_ms: int,
    provider_request_retry_count: int,
    provider_request_retry_backoff_ms: int,
    provider_request_retry_jitter_ms: int,
) -> dict[str, Any]:
    return {
        "provider_request_timeout_ms": int(provider_timeout_ms),
        "case_timeout_ms": int(effective_case_timeout_ms),
        "case_timeout_override_supplied": case_timeout_ms is not None,
        "case_timeout_grace_ms": None if case_timeout_ms is not None else DEFAULT_CASE_TIMEOUT_GRACE_MS,
        "provider_request_retry_count": int(provider_request_retry_count),
        "provider_request_retry_backoff_ms": int(provider_request_retry_backoff_ms),
        "provider_request_retry_jitter_ms": int(provider_request_retry_jitter_ms),
        "strict_pass_requires_first_attempt": True,
        "timeout_values_are_failure_boundaries_not_product_latency_targets": True,
    }


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


def _target_reference_from_manager_context_packet(user_payload: dict[str, Any]) -> dict[str, Any]:
    packet = _dict(user_payload.get("manager_context_packet_v1"))
    target_candidates = _list(_dict(packet.get("target_candidates")).get("for_correction_or_removal"))
    if not target_candidates:
        target_candidates = _list(_dict(user_payload.get("phase_a_current_turn_context")).get("recent_item_targets"))
    item_candidates = [_dict(candidate) for candidate in target_candidates if _dict(candidate)]
    if not item_candidates:
        return {}
    selected = item_candidates[0]
    return {
        "meal_thread_id": selected.get("meal_thread_id"),
        "meal_version_id": selected.get("meal_version_id"),
        "item_candidates": item_candidates,
    }


def _active_meal_answer_basis_from_context_packet(user_payload: dict[str, Any]) -> dict[str, Any]:
    packet = _dict(user_payload.get("manager_context_packet_v1"))
    active_meal = _dict(_dict(packet.get("active_day_state")).get("active_meal_estimate_basis"))
    if not active_meal:
        return {
            "references_active_meal": False,
            "assumption_or_composition_explained": False,
            "source": "manager_context_packet_v1",
        }
    return {
        "meal_thread_id": active_meal.get("meal_thread_id"),
        "meal_version_id": active_meal.get("meal_version_id"),
        "meal_title": active_meal.get("meal_title"),
        "total_kcal": active_meal.get("total_kcal"),
        "component_names": [
            str(_dict(item).get("canonical_name") or "").strip()
            for item in _list(active_meal.get("items"))
            if str(_dict(item).get("canonical_name") or "").strip()
        ],
        "references_active_meal": True,
        "assumption_or_composition_explained": True,
        "source": "manager_context_packet_v1.active_day_state.active_meal_estimate_basis",
    }


def _target_reference_from_legacy_resolved_state(user_payload: dict[str, Any]) -> dict[str, Any]:
    return _dict(_dict(_dict(user_payload.get("resolved_state")).get("injected_context")).get("TARGET_MEAL_REFERENCE"))


def _has_tool_result(user_payload: dict[str, Any], tool_name: str) -> bool:
    for item in _list(user_payload.get("tool_results")):
        result = _dict(item)
        if str(result.get("tool_name") or result.get("name") or "") == tool_name:
            return True
    return False


def _optional_string(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return int(stripped)
        except ValueError:
            return None
    return None


def _intent_type_for_semantic_intent(semantic_intent: str) -> str:
    return FOUNDER_LIVE_MANAGER_INTENT_TYPE_BY_SEMANTIC_INTENT.get(semantic_intent, "log_meal")


def _usage_prompt_tokens(usage: dict[str, Any]) -> int:
    if "prompt_tokens" in usage:
        return int(usage.get("prompt_tokens") or 0)
    cache_read_tokens = _optional_usage_int(usage, "cache_read_input_tokens")
    cache_creation_tokens = _optional_usage_int(usage, "cache_creation_input_tokens")
    if cache_read_tokens is not None or cache_creation_tokens is not None:
        return int(usage.get("input_tokens") or 0) + int(cache_read_tokens or 0) + int(cache_creation_tokens or 0)
    return int(usage.get("input_tokens") or 0)


def _usage_completion_tokens(usage: dict[str, Any]) -> int:
    return int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)


def _cached_tokens_from_usage(usage: dict[str, Any]) -> int | None:
    prompt_details = usage.get("prompt_tokens_details")
    if isinstance(prompt_details, dict) and "cached_tokens" in prompt_details:
        return int(prompt_details.get("cached_tokens") or 0)
    input_details = usage.get("input_tokens_details")
    if isinstance(input_details, dict) and "cached_tokens" in input_details:
        return int(input_details.get("cached_tokens") or 0)
    if "cached_tokens" in usage:
        return int(usage.get("cached_tokens") or 0)
    if "cache_read_input_tokens" in usage:
        return int(usage.get("cache_read_input_tokens") or 0)
    if "cache_creation_input_tokens" in usage:
        return 0
    return None


def _optional_usage_int(usage: dict[str, Any], key: str) -> int | None:
    if key in usage:
        return int(usage.get(key) or 0)
    return None


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
    parser.add_argument("--provider-timeout-ms", type=int, default=DEFAULT_PROVIDER_REQUEST_TIMEOUT_MS)
    parser.add_argument("--case-timeout-ms", type=int, default=None)
    parser.add_argument("--provider-request-retry-count", type=int, default=DEFAULT_PROVIDER_REQUEST_RETRY_COUNT)
    parser.add_argument("--provider-request-retry-backoff-ms", type=int, default=250)
    parser.add_argument("--provider-request-retry-jitter-ms", type=int, default=100)
    parser.add_argument("--stage", choices=(STAGE_ALL, *ORDERED_STAGE_IDS), default=STAGE_ALL)
    parser.add_argument(
        "--allow-live-all-diagnostic",
        action="store_true",
        help="Explicitly allow the live CLI to run every stage in one process. Prefer staged single-case artifacts.",
    )
    parser.add_argument("--case-id", default=None)
    parser.add_argument(
        "--manifest-case-id",
        default=None,
        help="Select an initial single-turn live probe by fixed 18-case manifest id.",
    )
    parser.add_argument("--max-turn", type=int, default=None)
    parser.add_argument("--offline-replay-artifact", default=str(DEFAULT_OFFLINE_REPLAY_ARTIFACT))
    args = parser.parse_args()

    if args.stage == STAGE_ALL and not args.allow_live_all_diagnostic:
        parser.error(
            "stage all is disabled for live CLI diagnostics; run staged commands one at a time "
            "or pass --allow-live-all-diagnostic for explicit debugging."
        )

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
        manifest_case_id=str(args.manifest_case_id) if args.manifest_case_id else None,
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
    "DEFAULT_PROVIDER_REQUEST_RETRY_COUNT",
    "DEFAULT_PROVIDER_REQUEST_TIMEOUT_MS",
    "ScriptedAccurateIntakeLiveProvider",
    "AccurateIntakeLiveDiagnosticProvider",
    "build_missing_provider_report",
    "provider_profile",
    "run_diagnostic",
]


if __name__ == "__main__":
    raise SystemExit(main())
