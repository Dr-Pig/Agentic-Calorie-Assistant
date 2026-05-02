from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import sys
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_debug_routes import build_accurate_intake_debug_payload
from app.composition.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date
from app.database import get_or_create_user
from app.models import Base
from app.runtime.agent.founder_live_manager_contract import (
    FOUNDER_LIVE_MANAGER_SCHEMA_NAME,
    FOUNDER_LIVE_MANAGER_SCHEMA_VERSION,
    FOUNDER_LIVE_MANAGER_TRANSPORT_POLICY,
    founder_live_manager_contract_constraints,
)
from app.shared.contracts.readiness_claim import build_readiness_claim


ARTIFACT_PATH = ROOT / "artifacts" / "accurate_intake_mvp_live_diagnostic.json"
DEFAULT_DB_PATH = ROOT / "artifacts" / "accurate_intake_mvp_live_diagnostic.sqlite3"
DEFAULT_LOCAL_DATE = "2026-05-02"
DEFAULT_ACCURATE_INTAKE_LIVE_DIAGNOSTIC_PROVIDER_PROFILE_ID = (
    "builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic"
)
ACTIVE_ENTRYPOINT = "app.composition.intake_turn_orchestrator.execute_intake_turn"

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


class AccurateIntakeLiveDiagnosticProvider:
    """Adds diagnostic profile metadata and shared manager contract constraints."""

    def __init__(self, provider: Any, *, profile: dict[str, Any], live_invoked: bool) -> None:
        self._provider = provider
        self.profile = dict(profile)
        self.live_invoked = live_invoked
        self.invocations: list[dict[str, Any]] = []

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
        started = datetime.now(UTC)
        kwargs = _with_accurate_intake_live_contract_constraints(kwargs, profile=self.profile)
        try:
            payload, trace = await self._provider.complete_with_trace(**kwargs)
        except Exception as exc:
            error_trace = _provider_error_trace(exc, stage=stage, profile=self.profile)
            self.invocations.append(error_trace)
            raise
        elapsed_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
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
                "failure_family": None,
                "provider_trace": enriched_trace,
            }
        )
        return payload, enriched_trace


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
        return self._execution_decision(available_tools=available_tools, round_index=round_index), self._trace(
            "execution_decision"
        )

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

    def _execution_decision(self, *, available_tools: set[str], round_index: int) -> dict[str, Any]:
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
        answer_contract = {"reply_text": workflow_effect}
        if followup_question:
            answer_contract["followup_question"] = followup_question
        return {
            "manager_action": "final",
            "intent": intent_type,
            "intent_type": intent_type,
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
                "semantic_authority": "scripted_fake_provider",
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
    provider_override: Any | None = None,
    provider_mode: str = "live",
    live_invoked: bool = True,
) -> dict[str, Any]:
    profile = provider_profile(provider_profile_id)
    if provider_override is None:
        provider_override = _build_builderspace_provider(profile=profile, provider_timeout_ms=provider_timeout_ms)
    provider = AccurateIntakeLiveDiagnosticProvider(provider_override, profile=profile, live_invoked=live_invoked)
    readiness = provider.readiness()
    if provider_mode == "live" and not readiness.get("configured"):
        report = build_missing_provider_report(profile=profile)
        _write_report(output_path, report)
        return report

    if db_path.exists():
        db_path.unlink()
    SessionLocal = _session_factory(db_path)
    cases: list[dict[str, Any]] = []
    effective_case_timeout_ms = int(case_timeout_ms if case_timeout_ms is not None else provider_timeout_ms + 15000)
    for case in _case_inventory():
        try:
            cases.append(
                asyncio.run(
                    asyncio.wait_for(
                        _run_case(SessionLocal, case=case, provider=provider, local_date=local_date),
                        timeout=max(0.001, effective_case_timeout_ms / 1000),
                    )
                )
            )
        except Exception as exc:
            cases.append(_case_error(case, exc))
    cases = [_decorate_case(case, profile=profile) for case in cases]
    report = _report_shell(
        profile=profile,
        provider_mode=provider_mode,
        live_invoked=live_invoked,
        provider_readiness=readiness,
        provider_invocations=provider.invocations,
        cases=cases,
        failure_layer=None,
        failure_family=None,
    )
    _write_report(output_path, report)
    return report


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
    return {
        "case_id": case.case_id,
        "description": case.description,
        "verdict": verdict,
        "blockers": blockers,
        "failure_layer": failure_layer,
        "runner_inferred_semantics": False,
        "raw_text_routing_used": False,
        "turns": turns,
        "debug_surface": debug_surface,
        "state_delta": _case_state_delta(turns=turns, debug_surface=debug_surface),
    }


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


def _case_error(case: LiveCase, exc: Exception) -> dict[str, Any]:
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
        "runtime_error": {"type": type(exc).__name__, "message": str(exc)},
    }


def _decorate_case(case: dict[str, Any], *, profile: dict[str, Any]) -> dict[str, Any]:
    decorated = dict(case)
    contract_status = _case_contract_status(decorated)
    failure_layer, failure_family = _classify_failure(decorated)
    decorated["provider_profile_id"] = profile["provider_profile_id"]
    decorated["provider_profile_model"] = profile["model"]
    decorated["provider_profile_role"] = profile["provider_profile_role"]
    decorated["transport_mode"] = profile["transport_policy"]["primary"]
    decorated["transport_policy"] = profile["transport_policy"]
    decorated["schema_name"] = profile["schema_name"]
    decorated["schema_version"] = profile["schema_version"]
    decorated["case_contract_status"] = contract_status
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


def _case_contract_status(case: dict[str, Any]) -> str:
    if _case_has_provider_timeout(case):
        return "timeout"
    if _dict(case.get("runtime_error")):
        return "fail"
    for trace in _case_manager_traces(case):
        if trace.get("repair_attempted") is True or str(trace.get("repair_result") or "") == "passed_after_repair":
            return "repaired_pass"
    return "strict_pass" if case.get("verdict") == "pass" else "fail"


def _case_manager_traces(case: dict[str, Any]) -> list[dict[str, Any]]:
    traces: list[dict[str, Any]] = []
    for turn in _list(case.get("turns")):
        turn_dict = _dict(turn)
        for round_item in _list(turn_dict.get("manager_rounds")):
            if isinstance(round_item, dict):
                traces.append(_dict(round_item.get("trace")))
    return traces


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
        "repaired_pass_count": statuses.count("repaired_pass"),
        "contract_fail_count": statuses.count("fail"),
        "timeout_count": statuses.count("timeout"),
        "provider_timeout_count": statuses.count("timeout"),
        "failure_layers": failure_layers,
        "failure_families": failure_families,
        "private_self_use_unlock_allowed": False,
    }


def _report_shell(
    *,
    profile: dict[str, Any],
    provider_mode: str,
    live_invoked: bool,
    provider_readiness: dict[str, Any],
    provider_invocations: list[dict[str, Any]],
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
            "summary": _summary(cases),
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
    tool_results = [dict(item) for item in _list(user_payload.get("tool_results")) if isinstance(item, dict)]
    constraints.update(
        founder_live_manager_contract_constraints(
            str(profile["provider_profile_id"]),
            tool_results=tool_results,
        )
    )
    constraints["accurate_intake_mvp_live_diagnostic"] = {
        "runner_inferred_semantics": False,
        "raw_text_routing_forbidden": True,
        "web_tavily_invoked": False,
        "live_provider_used_as_truth": False,
    }
    user_payload["constraints"] = constraints
    user_payload.setdefault("accurate_intake_live_diagnostic_policy", constraints["accurate_intake_mvp_live_diagnostic"])
    updated["user_payload"] = user_payload
    return updated


def _build_builderspace_provider(*, profile: dict[str, Any], provider_timeout_ms: int) -> Any:
    from app.providers.builderspace_adapter import BuilderSpaceAdapter

    timeout_seconds = max(1, int(provider_timeout_ms / 1000))
    previous_timeout = os.environ.get("AI_BUILDER_TIMEOUT_SECONDS")
    os.environ["AI_BUILDER_TIMEOUT_SECONDS"] = str(timeout_seconds)
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
    if "missing required fields" in message or "validate_manager_payload" in message or "BuilderSpace" in message:
        return "provider_contract_non_adherence"
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
    args = parser.parse_args()

    report = run_diagnostic(
        output_path=Path(args.output),
        db_path=Path(args.db_path),
        local_date=str(args.local_date),
        provider_profile_id=str(args.provider_profile_id),
        provider_timeout_ms=int(args.provider_timeout_ms),
        case_timeout_ms=args.case_timeout_ms,
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
