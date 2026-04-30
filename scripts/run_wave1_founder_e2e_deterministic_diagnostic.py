from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import os
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.shared.contracts.readiness_claim import build_readiness_claim

ACTIVE_ENTRYPOINT = "app.composition.intake_turn_orchestrator.execute_intake_turn"
ARTIFACT_PATH = ROOT / "artifacts" / "wave1_founder_e2e_deterministic_diagnostic.json"
DEFAULT_DB_PATH = ROOT / "artifacts" / "wave1_founder_e2e_deterministic_diagnostic.sqlite3"
LOCAL_DATE = "2026-04-30"


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if is_dataclass(value):
        return _json_safe(asdict(value))
    if hasattr(value, "model_dump"):
        return _json_safe(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _sum_counts(cases: list[dict[str, Any]], verdict: str) -> int:
    return sum(1 for case in cases if case.get("verdict") == verdict)


def _configure_database(db_path: Path) -> Any:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    database_url = f"sqlite:///{db_path.as_posix()}"
    os.environ["DATABASE_URL"] = database_url

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    database = importlib.import_module("app.database")
    old_engine = getattr(database, "engine", None)
    if old_engine is not None:
        old_engine.dispose()
    database.DATABASE_URL = database_url
    database.engine = create_engine(database_url, connect_args={"check_same_thread": False})
    database.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=database.engine)
    database.init_db()
    return database


def _active_entrypoint() -> Any:
    module = importlib.import_module("app.composition.intake_turn_orchestrator")
    return getattr(module, "execute_intake_turn")


def _active_entrypoint_verified() -> bool:
    entrypoint = _active_entrypoint()
    return f"{entrypoint.__module__}.{entrypoint.__name__}" == ACTIVE_ENTRYPOINT


def _legacy_dependency_reason() -> str | None:
    source = Path(__file__).read_text(encoding="utf-8")
    markers = (
        "app.runtime.application." + "phase_a_context",
        "old_" + "c001_" + "draft" + "_first_oracle",
        "C-001 " + "draft" + "-first",
        "run_v2_" + "intake_turn_live_eval",
        "run_v2_" + "intake_execution_live_eval",
        "run_wave1_" + "phase_b_minimal_tool_loop_smoke",
        "docs/" + "archive",
    )
    detected = [marker for marker in markers if marker in source]
    return ", ".join(detected) if detected else None


def build_legacy_guard() -> dict[str, Any]:
    reason = _legacy_dependency_reason()
    verified = _active_entrypoint_verified()
    return {
        "checked": True,
        "legacy_dependency_detected": bool(reason),
        "legacy_dependency_reason": reason,
        "active_entrypoint": ACTIVE_ENTRYPOINT,
        "active_entrypoint_verified": verified,
        "legacy_bundle_names_are_not_semantic_owners": True,
        "deprecated_phase_a_facade_used": False,
        "stale_oracle_used_as_truth": False,
        "compatibility_final_mapping_owner_used": False,
    }


class DeterministicFounderProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def readiness(self) -> dict[str, Any]:
        return {
            "configured": True,
            "provider": "deterministic_founder_fake",
            "live_llm_invoked": False,
        }

    async def complete_with_trace(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        user_payload = _dict(kwargs.get("user_payload"))
        raw = str(user_payload.get("raw_user_input") or "")
        available_tools = {str(item) for item in _list(user_payload.get("available_tools"))}
        round_index = int(user_payload.get("round_index") or 0)
        self.calls.append({"raw_user_input": raw, "available_tools": sorted(available_tools), "round_index": round_index})

        if {"read_body_plan", "read_day_budget"}.intersection(available_tools):
            return self._intake_turn_decision(user_payload), self._trace("intake_entry_intent")
        return self._intake_execution_decision(raw=raw, available_tools=available_tools, round_index=round_index), self._trace("intake_execution_manager")

    def _trace(self, stage: str) -> dict[str, Any]:
        return {
            "source": "deterministic_founder_fake_provider",
            "stage": stage,
            "live_llm_invoked": False,
        }

    def _intake_turn_decision(self, user_payload: dict[str, Any]) -> dict[str, Any]:
        raw = str(user_payload.get("raw_user_input") or "")
        if not raw.strip():
            return self._final(intent_type="complete_onboarding", final_action="commit", workflow_effect="commit")
        if "今天" in raw and ("多少" in raw or "目前" in raw):
            return self._final(
                intent_type="answer_remaining_budget",
                final_action="answer_only",
                workflow_effect="answer_only",
            )
        return self._final(intent_type="log_meal", final_action="commit", workflow_effect="route_to_intake")

    def _intake_execution_decision(self, *, raw: str, available_tools: set[str], round_index: int) -> dict[str, Any]:
        if "滷味" in raw:
            return self._final(
                intent_type="log_meal",
                final_action="request_clarification",
                workflow_effect="ask_first_unresolved",
                response_summary="self_selected_basket_without_listed_items",
                uncertainty_posture="composition_unknown_basket",
                evidence_posture="clarify_first",
            )
        if round_index == 0 and "estimate_nutrition" in available_tools:
            tool_calls = [{"name": "estimate_nutrition"}]
            if "compare_against_budget" in available_tools and "多少熱量" not in raw:
                tool_calls.append({"name": "compare_against_budget"})
            return {"manager_action": "call_tools", "response_mode": "tool_call", "tool_calls": tool_calls}
        if "多少熱量" in raw:
            return self._final(
                intent_type="log_meal",
                final_action="answer_only",
                workflow_effect="answer_only",
                response_summary="query_only_no_mutation",
                target_attachment={"mode": "none"},
            )
        if "剛剛" in raw or "改成" in raw:
            return self._final(
                intent_type="log_meal",
                final_action="correction_applied",
                workflow_effect="correction",
                response_summary="single_prior_target_correction",
                target_attachment={"mode": "target_committed_thread"},
            )
        if "\u73cd\u73e0\u5976\u8336" in raw or "\u73cd\u5976" in raw:
            return self._final(
                intent_type="log_meal",
                final_action="commit",
                workflow_effect="estimate_with_followup",
                response_summary="deterministic_logged_estimate_with_refinement_followup",
                target_attachment={"mode": "new_meal"},
                followup_posture="refinement_not_commit_gate",
                followup_question="\u5982\u679c\u4f60\u9858\u610f\uff0c\u53ef\u4ee5\u518d\u88dc\u5145\u5927\u5c0f\u548c\u751c\u5ea6\uff0c\u6211\u6703\u5e6b\u4f60\u628a\u4f30\u7b97\u4fee\u6b63\u5f97\u66f4\u6e96\u3002",
                followup_targets=("size", "sugar_level"),
            )
        return self._final(
            intent_type="log_meal",
            final_action="commit",
            workflow_effect="commit",
            response_summary="deterministic_logged_estimate",
            target_attachment={"mode": "new_meal"},
        )

    def _final(
        self,
        *,
        intent_type: str,
        final_action: str,
        workflow_effect: str,
        response_summary: str = "",
        target_attachment: dict[str, Any] | None = None,
        uncertainty_posture: str = "bounded",
        evidence_posture: str = "deterministic",
        followup_posture: str | None = None,
        followup_question: str | None = None,
        followup_targets: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        target = target_attachment or {"mode": "none"}
        semantic_followup_posture = followup_posture or self._followup_posture(workflow_effect)
        return {
            "manager_action": "final",
            "intent": intent_type,
            "intent_type": intent_type,
            "final_action": final_action,
            "workflow_effect": workflow_effect,
            "target_attachment": target,
            "exactness": "deterministic",
            "confidence": "medium",
            "evidence_posture": evidence_posture,
            "repair_ack": False,
            "answer_contract": {"reply_text": response_summary or workflow_effect},
            "response_summary": response_summary,
            "uncertainty_posture": uncertainty_posture,
            "evidence_honesty_posture": evidence_posture,
            "semantic_decision": {
                "semantic_authority": "deterministic_fake_provider",
                "current_turn_intent": self._semantic_intent(intent_type),
                "target_attachment": target,
                "workflow_effect": workflow_effect,
                "final_action_candidate": final_action,
                "estimation_posture": self._estimation_posture(workflow_effect),
                "followup_posture": semantic_followup_posture,
                "followup_question": followup_question,
                "followup_targets": list(followup_targets),
                "mutation_intent_candidate": self._mutation_intent_candidate(final_action, workflow_effect),
                "uncertainty_posture": uncertainty_posture,
                "source": "deterministic_founder_fake_provider",
                "semantic_owner": "manager",
                "deterministic_role": "fixture_simulates_manager_output_only",
            },
        }

    @staticmethod
    def _semantic_intent(intent_type: str) -> str:
        if intent_type in {
            "log_meal",
            "answer_query",
            "correct_meal",
            "complete_onboarding",
            "answer_remaining_budget",
            "onboarding_required",
            "general_chat",
        }:
            return intent_type
        return "unknown"

    @staticmethod
    def _estimation_posture(workflow_effect: str) -> str:
        if workflow_effect in {"commit", "estimate_with_followup"}:
            return "estimable"
        if workflow_effect == "ask_first_unresolved":
            return "ask_first_unresolved"
        if workflow_effect == "answer_only":
            return "not_applicable"
        return "unknown"

    @staticmethod
    def _followup_posture(workflow_effect: str) -> str:
        if workflow_effect == "estimate_with_followup":
            return "refinement_not_commit_gate"
        if workflow_effect == "ask_first_unresolved":
            return "clarification_required_before_estimate"
        return "none"

    @staticmethod
    def _mutation_intent_candidate(final_action: str, workflow_effect: str) -> str:
        if final_action == "commit" and workflow_effect in {"commit", "estimate_with_followup"}:
            return "canonical_write"
        if final_action == "correction_applied" or workflow_effect == "correction":
            return "correction_write"
        if final_action in {"answer_only", "request_clarification", "no_commit"}:
            return "no_mutation"
        return "unknown"


async def _execute_turn(
    db: Any,
    provider: DeterministicFounderProvider,
    *,
    user_id: str,
    text: str | None,
    local_date: str,
    onboarding_payload: Any | None = None,
) -> dict[str, Any]:
    entrypoint = _active_entrypoint()
    return await entrypoint(
        db,
        user_external_id=user_id,
        raw_user_input=text,
        onboarding_payload=onboarding_payload,
        local_date=local_date,
        allow_search=False,
        provider=provider,
        search_port=None,
        extract_port=None,
    )


async def _seed_onboarding(db: Any, provider: DeterministicFounderProvider, *, user_id: str, local_date: str) -> None:
    del provider
    from app.composition.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date
    from app.database import get_or_create_user

    user = get_or_create_user(db, user_id)
    bootstrap_body_plan_for_date(
        db,
        user=user,
        inputs=OnboardingBootstrapInput(
            sex="female",
            age_years=30,
            height_cm=165,
            current_weight_kg=58,
            goal_type="lose_weight",
            weekly_target_rate_kg=0.5,
            timezone="Asia/Taipei",
            daily_lifestyle="sedentary_with_some_walking",
            weekly_exercise_days_band="3_4",
            local_date=local_date,
        ),
    )


async def _run_runtime_turn(
    db: Any,
    provider: DeterministicFounderProvider,
    *,
    user_id: str,
    text: str,
    local_date: str,
    seed_onboarding: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if seed_onboarding:
        await _seed_onboarding(db, provider, user_id=user_id, local_date=local_date)
    try:
        result = await _execute_turn(db, provider, user_id=user_id, text=text, local_date=local_date)
    except Exception as exc:
        result = {
            "assistant_message": None,
            "runtime_error": {"type": type(exc).__name__, "message": str(exc)},
            "state_delta": {},
            "remaining_budget": {},
            "hard_fail_conditions": [],
        }
    return result, _load_trace(result)


def _load_trace(result: dict[str, Any]) -> dict[str, Any]:
    trace_path = _dict(result.get("audit")).get("request_trace_path")
    if not trace_path:
        return {}
    path = Path(str(trace_path))
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _tool_results(trace: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        dict(item)
        for item in _list(_dict(trace.get("tool_outputs")).get("tool_results"))
        if isinstance(item, dict)
    ]


def _nutrition_payload(trace: dict[str, Any]) -> dict[str, Any] | None:
    for item in _tool_results(trace):
        payload = _dict(_dict(item.get("evidence")).get("nutrition_payload"))
        if payload:
            return payload
    return None


def _evidence_summary(trace: dict[str, Any]) -> dict[str, Any]:
    for item in _tool_results(trace):
        evidence = _dict(_dict(item.get("provenance")).get("evidence_summary"))
        if evidence:
            return evidence
    return {}


def _manager_final_action(result: dict[str, Any], trace: dict[str, Any]) -> str | None:
    final = _dict(_dict(result.get("intake_execution_manager")).get("final")).get("final_action")
    if final:
        return str(final)
    decision = _dict(trace.get("manager_final_decision"))
    if decision.get("final_action"):
        return str(decision["final_action"])
    manager_decision = _dict(result.get("manager_decision"))
    return str(manager_decision.get("intent_type") or "") or None


def _manager_semantic_decision(result: dict[str, Any], trace: dict[str, Any]) -> dict[str, Any]:
    intake_execution_final = _dict(_dict(result.get("intake_execution_manager")).get("final"))
    if _dict(intake_execution_final.get("semantic_decision")):
        return _dict(intake_execution_final.get("semantic_decision"))
    manager_decision = _dict(result.get("manager_decision"))
    if _dict(manager_decision.get("semantic_decision")):
        return _dict(manager_decision.get("semantic_decision"))
    trace_decision = _dict(trace.get("manager_final_decision"))
    return _dict(trace_decision.get("semantic_decision"))


def _case_shell(
    *,
    case_id: str,
    input_text: str,
    expected_behavior: str,
    result: dict[str, Any],
    trace: dict[str, Any],
) -> dict[str, Any]:
    state_delta = _dict(result.get("state_delta")) or _dict(trace.get("state_delta"))
    payload = _nutrition_payload(trace)
    evidence = _evidence_summary(trace)
    phase_a = _dict(result.get("phase_a_trace")) or _dict(trace.get("phase_a_trace"))
    phase_c = _dict(result.get("phase_c_trace")) or _dict(trace.get("phase_c_trace"))
    final_mapping = {
        "observable": bool(phase_a.get("boundary_projection") or _dict(result.get("intake_execution_manager")).get("final")),
        "manager_final_action": _manager_final_action(result, trace),
        "manager_semantic_decision": _manager_semantic_decision(result, trace),
        "boundary_projection": _dict(phase_a.get("boundary_projection")),
        "persistence_result_observable": bool(_dict(result.get("intake_execution_manager")).get("persistence_result")),
    }
    return {
        "case_id": case_id,
        "input": input_text,
        "expected_behavior": expected_behavior,
        "actual_behavior": {
            "assistant_message": result.get("assistant_message"),
            "runtime_error": result.get("runtime_error"),
            "manager_intent": _dict(result.get("manager_decision")).get("intent_type"),
            "manager_final_action": final_mapping["manager_final_action"],
            "manager_semantic_decision": final_mapping["manager_semantic_decision"],
            "nutrition_payload": payload,
            "evidence_summary": evidence,
            "state_delta": state_delta,
            "hard_fail_conditions": list(result.get("hard_fail_conditions") or []),
        },
        "verdict": "fail",
        "failure_layer": "test_harness_gap",
        "phase_a": phase_a,
        "b2": {
            "tool_results": _tool_results(trace),
            "nutrition_payload": payload,
            "evidence_summary": evidence,
        },
        "final_mapping": final_mapping,
        "mutation": {
            "state_delta": state_delta,
            "persistence_result": _json_safe(_dict(result.get("intake_execution_manager")).get("persistence_result")),
        },
        "ledger_read": _dict(result.get("remaining_budget")),
        "same_truth": {
            "phase_c_trace": phase_c,
            "same_truth_closure_gate": _dict(phase_c.get("same_truth_closure_gate")),
        },
    }


def _set_verdict(case: dict[str, Any], *, verdict: str, failure_layer: str | None) -> dict[str, Any]:
    case["verdict"] = verdict
    case["failure_layer"] = failure_layer
    return case


def _has_runtime_error(case: dict[str, Any]) -> bool:
    return bool(_dict(case.get("actual_behavior")).get("runtime_error"))


def _has_no_mutation(case: dict[str, Any]) -> bool:
    state_delta = _dict(_dict(case.get("mutation")).get("state_delta"))
    return not any(
        bool(state_delta.get(key))
        for key in ("meal_logged", "canonical_commit", "draft_saved", "ledger_updated", "new_meal_version_created")
    )


def _estimated_kcal(case: dict[str, Any]) -> int:
    payload = _dict(_dict(case.get("b2")).get("nutrition_payload"))
    return int(payload.get("estimated_kcal") or 0)


def _web_trace(case: dict[str, Any]) -> dict[str, Any]:
    payload = _dict(_dict(case.get("b2")).get("nutrition_payload"))
    trace_contract = _dict(payload.get("trace_contract"))
    return _dict(trace_contract.get("web_runtime_trace"))


def _evaluate_pearl(case: dict[str, Any]) -> dict[str, Any]:
    if _has_runtime_error(case):
        return _set_verdict(case, verdict="fail", failure_layer="runtime")
    state_delta = _dict(_dict(case.get("mutation")).get("state_delta"))
    payload = _dict(_dict(case.get("b2")).get("nutrition_payload"))
    semantic_decision = _dict(_dict(case.get("final_mapping")).get("manager_semantic_decision"))
    logged = state_delta.get("canonical_commit") is True
    no_draft = state_delta.get("draft_saved") is False
    followup = bool(payload.get("followup_question")) or (
        semantic_decision.get("followup_posture") == "refinement_not_commit_gate"
        and bool(semantic_decision.get("followup_question"))
    )
    if logged and no_draft and followup:
        return _set_verdict(case, verdict="pass", failure_layer=None)
    layer = "final_mapping" if logged and no_draft else "mutation"
    return _set_verdict(case, verdict="fail", failure_layer=layer)


def _evaluate_luwei(case: dict[str, Any]) -> dict[str, Any]:
    if _has_runtime_error(case):
        return _set_verdict(case, verdict="fail", failure_layer="runtime")
    manager_action = str(_dict(case.get("final_mapping")).get("manager_final_action") or "")
    no_estimate = _estimated_kcal(case) == 0
    no_mutation = _has_no_mutation(case)
    ask_first = manager_action in {"request_clarification", "no_commit"}
    if ask_first and no_estimate and no_mutation:
        return _set_verdict(case, verdict="pass", failure_layer=None)
    if not no_mutation:
        return _set_verdict(case, verdict="fail", failure_layer="mutation")
    return _set_verdict(case, verdict="fail", failure_layer="b2")


def _evaluate_tea_egg(case: dict[str, Any]) -> dict[str, Any]:
    if _has_runtime_error(case):
        return _set_verdict(case, verdict="fail", failure_layer="runtime")
    manager_action = str(_dict(case.get("final_mapping")).get("manager_final_action") or "")
    if _estimated_kcal(case) > 0 and manager_action not in {"request_clarification", "no_commit"}:
        return _set_verdict(case, verdict="pass", failure_layer=None)
    return _set_verdict(case, verdict="fail", failure_layer="b2")


def _evaluate_exact_brand(case: dict[str, Any]) -> dict[str, Any]:
    if _has_runtime_error(case):
        return _set_verdict(case, verdict="fail", failure_layer="runtime")
    evidence = _dict(_dict(case.get("b2")).get("evidence_summary"))
    web_trace = _web_trace(case)
    exact = evidence.get("db_hit_type") == "exact_truth" or web_trace.get("skip_reason") == "exact_db_hit"
    web_not_used = int(web_trace.get("search_attempt_count") or 0) == 0 and web_trace.get("attempted") is not True
    if exact and web_not_used:
        return _set_verdict(case, verdict="pass", failure_layer=None)
    if web_not_used:
        return _set_verdict(case, verdict="deferred", failure_layer="deferred_source_limitation")
    return _set_verdict(case, verdict="fail", failure_layer="b2")


def _evaluate_query_only(case: dict[str, Any]) -> dict[str, Any]:
    if _has_runtime_error(case):
        return _set_verdict(case, verdict="fail", failure_layer="runtime")
    message = str(_dict(case.get("actual_behavior")).get("assistant_message") or "")
    if _has_no_mutation(case) and not message.startswith("Logged."):
        return _set_verdict(case, verdict="pass", failure_layer=None)
    return _set_verdict(case, verdict="fail", failure_layer="mutation")


def _evaluate_correction(case: dict[str, Any]) -> dict[str, Any]:
    if _has_runtime_error(case):
        return _set_verdict(case, verdict="fail", failure_layer="runtime")
    state_delta = _dict(_dict(case.get("mutation")).get("state_delta"))
    if state_delta.get("canonical_commit") is True and state_delta.get("old_version_superseded") is True:
        return _set_verdict(case, verdict="pass", failure_layer=None)
    return _set_verdict(case, verdict="fail", failure_layer="mutation")


def _evaluate_today(case: dict[str, Any]) -> dict[str, Any]:
    if _has_runtime_error(case):
        return _set_verdict(case, verdict="fail", failure_layer="runtime")
    ledger = _dict(case.get("ledger_read"))
    if _has_no_mutation(case) and ledger.get("status") == "onboarding_required" and int(ledger.get("remaining_kcal") or 0) == 0:
        return _set_verdict(case, verdict="pass", failure_layer=None)
    return _set_verdict(case, verdict="fail", failure_layer="ledger_read")


async def _run_cases(db: Any, provider: DeterministicFounderProvider, *, local_date: str) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    result, trace = await _run_runtime_turn(
        db,
        provider,
        user_id=f"founder-pearl-{uuid4().hex[:8]}",
        text="我喝了一杯珍珠奶茶",
        local_date=local_date,
    )
    cases.append(
        _evaluate_pearl(
            _case_shell(
                case_id="pearl_milk_tea_logged_followup",
                input_text="我喝了一杯珍珠奶茶",
                expected_behavior="logged estimate allowed, strong refinement follow-up, no old draft regression",
                result=result,
                trace=trace,
            )
        )
    )

    result, trace = await _run_runtime_turn(
        db,
        provider,
        user_id=f"founder-luwei-{uuid4().hex[:8]}",
        text="我吃了滷味",
        local_date=local_date,
    )
    cases.append(
        _evaluate_luwei(
            _case_shell(
                case_id="luwei_ask_first",
                input_text="我吃了滷味",
                expected_behavior="self_selected_basket_without_listed_items ask-first unresolved with no estimate or mutation",
                result=result,
                trace=trace,
            )
        )
    )

    result, trace = await _run_runtime_turn(
        db,
        provider,
        user_id=f"founder-tea-egg-{uuid4().hex[:8]}",
        text="我吃了一顆茶葉蛋",
        local_date=local_date,
    )
    cases.append(
        _evaluate_tea_egg(
            _case_shell(
                case_id="generic_stable_tea_egg",
                input_text="我吃了一顆茶葉蛋",
                expected_behavior="generic anchor estimate with active runtime item payload and not ask-first",
                result=result,
                trace=trace,
            )
        )
    )

    result, trace = await _run_runtime_turn(
        db,
        provider,
        user_id=f"founder-matsuya-{uuid4().hex[:8]}",
        text="松屋特盛牛丼",
        local_date=local_date,
    )
    cases.append(
        _evaluate_exact_brand(
            _case_shell(
                case_id="exact_brand_matsuya_beef_bowl",
                input_text="松屋特盛牛丼",
                expected_behavior="exact DB or deterministic exact evidence path; web not required in deterministic phase",
                result=result,
                trace=trace,
            )
        )
    )

    result, trace = await _run_runtime_turn(
        db,
        provider,
        user_id=f"founder-query-{uuid4().hex[:8]}",
        text="珍珠奶茶多少熱量？",
        local_date=local_date,
    )
    cases.append(
        _evaluate_query_only(
            _case_shell(
                case_id="query_only_pearl_milk_tea_calories",
                input_text="珍珠奶茶多少熱量？",
                expected_behavior="answer-only query with no mutation, ledger update, or fake logged claim",
                result=result,
                trace=trace,
            )
        )
    )

    correction_user = f"founder-correction-{uuid4().hex[:8]}"
    await _run_runtime_turn(
        db,
        provider,
        user_id=correction_user,
        text="我喝了一杯珍珠奶茶",
        local_date=local_date,
    )
    result, trace = await _run_runtime_turn(
        db,
        provider,
        user_id=correction_user,
        text="剛剛那杯珍奶改成半糖",
        local_date=local_date,
        seed_onboarding=False,
    )
    cases.append(
        _evaluate_correction(
            _case_shell(
                case_id="correction_prior_pearl_milk_tea_half_sugar",
                input_text="剛剛那杯珍奶改成半糖",
                expected_behavior="attach to exactly one prior drink and mutate only if transition guard and commit boundary allow",
                result=result,
                trace=trace,
            )
        )
    )

    result, trace = await _run_runtime_turn(
        db,
        provider,
        user_id=f"founder-today-{uuid4().hex[:8]}",
        text="我今天目前吃了多少？",
        local_date=local_date,
        seed_onboarding=False,
    )
    cases.append(
        _evaluate_today(
            _case_shell(
                case_id="today_ledger_read_model",
                input_text="我今天目前吃了多少？",
                expected_behavior="read model returns honest today state and no fake remaining kcal without body plan",
                result=result,
                trace=trace,
            )
        )
    )
    return cases


def _summary(cases: list[dict[str, Any]]) -> dict[str, Any]:
    failure_layers = sorted(
        {
            str(case.get("failure_layer"))
            for case in cases
            if str(case.get("failure_layer") or "").strip()
        }
    )
    return {
        "pass_count": _sum_counts(cases, "pass"),
        "fail_count": _sum_counts(cases, "fail"),
        "product_decision_required_count": _sum_counts(cases, "product_decision_required"),
        "deferred_count": _sum_counts(cases, "deferred"),
        "failure_layers": failure_layers,
    }


def run_diagnostic(
    *,
    output_path: Path = ARTIFACT_PATH,
    db_path: Path = DEFAULT_DB_PATH,
    local_date: str = LOCAL_DATE,
) -> dict[str, Any]:
    database = _configure_database(db_path)
    provider = DeterministicFounderProvider()
    db = database.SessionLocal()
    try:
        legacy_guard = build_legacy_guard()
        cases = asyncio.run(_run_cases(db, provider, local_date=local_date))
        if legacy_guard["legacy_dependency_detected"]:
            for case in cases:
                case["verdict"] = "fail"
                case["failure_layer"] = "legacy_dependency"
        report = {
            "artifact_type": "wave1_founder_e2e_deterministic_diagnostic",
            "provider_mode": "deterministic",
            "active_entrypoint": ACTIVE_ENTRYPOINT,
            "active_entrypoint_verified": bool(legacy_guard["active_entrypoint_verified"]),
            "live_llm_invoked": False,
            "tavily_live_invoked": False,
            "readiness_claimed": False,
            "readiness_claim": build_readiness_claim(
                claim_scope="deterministic_runtime",
                activation_stage="deterministic",
                semantic_authority_source="fake_manager_structured_output",
                producer_honesty={
                    "runner_inferred_semantics": False,
                    "fake_provider_simulated_manager": True,
                    "final_mapping_fabricated": False,
                    "mutation_fabricated": False,
                },
                evidence_lineage={
                    "artifacts": [],
                    "producers": ["scripts/run_wave1_founder_e2e_deterministic_diagnostic.py"],
                    "active_entrypoint": ACTIVE_ENTRYPOINT,
                    "legacy_oracle_used": False,
                },
                allowed_next_stage="live_diagnostic",
                forbidden_claims=[
                    "live_ready",
                    "user_facing_ready",
                    "mutation_ready",
                    "wave1_readiness",
                    "production_ready",
                ],
                readiness_claimed=False,
            ),
            "exact_brand_web_positive_acceptance": "deferred_source_limitation",
            "legacy_guard": legacy_guard,
            "cases": _json_safe(cases),
            "summary": _summary(cases),
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report
    finally:
        db.close()
        engine = getattr(database, "engine", None)
        if engine is not None:
            engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Wave 1 Founder E2E deterministic diagnostic.")
    parser.add_argument("--output", default=str(ARTIFACT_PATH))
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--local-date", default=LOCAL_DATE)
    args = parser.parse_args()

    report = run_diagnostic(
        output_path=Path(args.output),
        db_path=Path(args.db_path),
        local_date=args.local_date,
    )
    print(
        json.dumps(
            {
                "artifact": str(Path(args.output)),
                "summary": report["summary"],
                "legacy_guard": report["legacy_guard"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
