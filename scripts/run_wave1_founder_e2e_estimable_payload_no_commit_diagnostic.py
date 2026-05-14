from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BASE_RUNNER = importlib.import_module("scripts.run_wave1_founder_e2e_deterministic_diagnostic")

ARTIFACT_PATH = ROOT / "artifacts" / "wave1_founder_e2e_estimable_payload_no_commit_diagnostic.json"
SOURCE_ARTIFACT_PATH = ROOT / "artifacts" / "wave1_founder_e2e_deterministic_diagnostic.json"
SOURCE_DB_PATH = ROOT / "artifacts" / "wave1_founder_e2e_estimable_payload_no_commit_source.sqlite3"
DETAIL_DB_PATH = ROOT / "artifacts" / "wave1_founder_e2e_estimable_payload_no_commit_detail.sqlite3"
LOCAL_DATE = "2026-04-30"

PRIMARY_INPUT = "\u6211\u559d\u4e86\u4e00\u676f\u73cd\u73e0\u5976\u8336"
TEA_EGG_INPUT = "\u6211\u5403\u4e86\u4e00\u9846\u8336\u8449\u86cb"
CORRECTION_INPUT = "\u525b\u525b\u90a3\u676f\u73cd\u5976\u6539\u6210\u534a\u7cd6"

ROOT_CAUSE_ENUM = (
    "phase_a_attachment_signal_gap",
    "transition_guard_blocked",
    "legacy_followup_blocks_commit",
    "route_target_clarify_blocks_commit",
    "action_taken_uncertainty_blocks_commit",
    "fake_provider_final_action_gap",
    "nutrition_final_mapping_denies_write",
    "commit_boundary_blocked",
    "payload_missing_required_commit_fields",
    "persistence_gap",
    "resolved_manager_semantic_contract",
    "diagnostic_harness_gap",
    "unknown",
)

LEGACY_SCAN_MARKERS = (
    "followup_question",
    "follow_up_needed",
    'route_target == "clarify_user_private"',
    'payload_route_target == "clarify_user_private"',
    'action_taken == "answer_with_uncertainty"',
    "estimate_with_followup",
)

LEGACY_SCAN_PATHS = (
    "app/intake",
    "app/nutrition",
    "app/runtime",
)


def _json_safe(value: Any) -> Any:
    return BASE_RUNNER._json_safe(value)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _first_payload(case: dict[str, Any]) -> dict[str, Any]:
    return _dict(_dict(case.get("b2")).get("nutrition_payload"))


def _contains_mojibake_or_private_use(text: str | None) -> bool:
    value = str(text or "")
    if not value:
        return False
    if "\ufffd" in value:
        return True
    if any(0xE000 <= ord(char) <= 0xF8FF for char in value):
        return True
    return value.count("?") >= 2 and any(ord(char) > 127 for char in value)


def _manager_round_items(trace: dict[str, Any]) -> list[dict[str, Any]]:
    wrapped_rounds = _list(trace.get("manager_rounds"))
    if wrapped_rounds:
        if any(_dict(item).get("decision") for item in wrapped_rounds if isinstance(item, dict)):
            return [dict(item) for item in wrapped_rounds if isinstance(item, dict)]
        decision = _dict(wrapped_rounds[0].get("decision") if isinstance(wrapped_rounds[0], dict) else {})
        nested = _list(decision.get("manager_rounds"))
        if nested:
            return [dict(item) for item in nested if isinstance(item, dict)]
    final_decision = _dict(trace.get("manager_final_decision"))
    nested = _list(final_decision.get("manager_rounds"))
    return [dict(item) for item in nested if isinstance(item, dict)]


def _manager_round_summary(trace: dict[str, Any]) -> dict[str, Any]:
    rounds = _manager_round_items(trace)
    final_decision = _dict(trace.get("manager_final_decision"))
    pre_guard_final_actions: list[str] = []
    normalized_rounds: list[dict[str, Any]] = []
    last_final_action: str | None = None
    for item in rounds:
        decision = _dict(item.get("decision"))
        final_action = decision.get("final_action")
        if decision.get("manager_action") == "final" and final_action:
            pre_guard_final_actions.append(str(final_action))
            last_final_action = str(final_action)
        normalized_rounds.append(
            {
                "round_index": item.get("round_index"),
                "manager_action": decision.get("manager_action"),
                "final_action": final_action,
                "tool_calls": decision.get("tool_calls") or [],
                "guard_feedback_present": bool(_dict(item.get("phase_a_input")).get("guard_feedback")),
            }
        )
    return {
        "rounds": normalized_rounds,
        "pre_guard_intended_final_actions": pre_guard_final_actions,
        "post_guard_final_action": final_decision.get("final_action") or last_final_action,
        "request_failure_family": final_decision.get("request_failure_family"),
        "guard_outcome": _dict(final_decision.get("guard_outcome")),
        "repair_round_used": bool(final_decision.get("repair_round_used")),
    }


def _persistence_result(result: dict[str, Any]) -> Any:
    return _dict(_dict(result.get("intake_execution_manager")).get("persistence_result"))


def _classify_root_cause(
    *,
    case: dict[str, Any],
    trace: dict[str, Any],
    manager_rounds: dict[str, Any],
) -> tuple[str, list[str]]:
    phase_a = _dict(case.get("phase_a"))
    attachment = _dict(phase_a.get("attachment_decision"))
    transition = _dict(phase_a.get("transition_guard_result"))
    payload = _first_payload(case)
    boundary_projection = _dict(_dict(case.get("final_mapping")).get("boundary_projection"))
    commit_decision = _dict(boundary_projection.get("commit_boundary_decision"))
    preflight = _dict(phase_a.get("phase_a_commit_boundary_preflight"))
    state_delta = _dict(_dict(case.get("mutation")).get("state_delta"))
    contributing: list[str] = []

    pre_guard_commit_attempted = "commit" in {
        str(item) for item in _list(manager_rounds.get("pre_guard_intended_final_actions"))
    }
    if (
        pre_guard_commit_attempted
        and transition.get("verdict") in {"answer_only", "clarify_required", "block"}
        and preflight.get("blocked") is True
    ):
        contributing.append("transition_guard_blocked")

    if payload and state_delta.get("canonical_commit") is True:
        return "resolved_manager_semantic_contract", contributing

    if (
        attachment.get("disposition") == "answer_only"
        and attachment.get("reason") == "no_attachment_signal"
        and transition.get("verdict") == "answer_only"
        and transition.get("reason") == "no_state_mutation_allowed"
    ):
        return "phase_a_attachment_signal_gap", contributing

    if transition.get("verdict") in {"answer_only", "clarify_required", "block"}:
        return "transition_guard_blocked", contributing

    if commit_decision.get("intent") == "draft" and commit_decision.get("canonical_write_allowed") is False:
        if payload.get("route_target") == "clarify_user_private":
            return "route_target_clarify_blocks_commit", contributing
        if payload.get("followup_question") or payload.get("follow_up_needed"):
            return "legacy_followup_blocks_commit", contributing
        return "nutrition_final_mapping_denies_write", contributing

    if preflight.get("blocked") is True:
        return "commit_boundary_blocked", contributing

    if payload and int(payload.get("estimated_kcal") or 0) > 0 and manager_rounds.get("post_guard_final_action") == "no_commit":
        return "fake_provider_final_action_gap", contributing

    if payload and not state_delta.get("canonical_commit"):
        return "persistence_gap", contributing

    if not payload:
        return "payload_missing_required_commit_fields", contributing

    return "unknown", contributing


def _scan_legacy_drift() -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    for root in LEGACY_SCAN_PATHS:
        base = ROOT / root
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            for line_number, line in enumerate(lines, start=1):
                for marker in LEGACY_SCAN_MARKERS:
                    if marker in line:
                        matches.append(
                            {
                                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                                "line": line_number,
                                "marker": marker,
                                "snippet": line.strip()[:240],
                            }
                        )
    return {
        "checked": True,
        "matches_are_supporting_evidence_only": True,
        "must_not_override_active_trace_precedence": True,
        "match_count": len(matches),
        "matches": matches[:80],
    }


async def _run_detail_turn(
    db: Any,
    provider: Any,
    *,
    user_id: str,
    text: str,
    local_date: str,
    case_id: str,
    expected_behavior: str,
    seed_onboarding: bool = True,
) -> dict[str, Any]:
    result, trace = await BASE_RUNNER._run_runtime_turn(
        db,
        provider,
        user_id=user_id,
        text=text,
        local_date=local_date,
        seed_onboarding=seed_onboarding,
    )
    case = BASE_RUNNER._case_shell(
        case_id=case_id,
        input_text=text,
        expected_behavior=expected_behavior,
        result=result,
        trace=trace,
    )
    return {"case": case, "result": result, "trace": trace}


async def _run_detail_cases(db: Any, provider: Any, *, local_date: str) -> dict[str, dict[str, Any]]:
    details: dict[str, dict[str, Any]] = {}
    details["pearl_milk_tea_logged_followup"] = await _run_detail_turn(
        db,
        provider,
        user_id=f"no-commit-pearl-{uuid4().hex[:8]}",
        text=PRIMARY_INPUT,
        local_date=local_date,
        case_id="pearl_milk_tea_logged_followup",
        expected_behavior="logged estimate allowed, strong refinement follow-up, no old draft regression",
    )
    details["generic_stable_tea_egg"] = await _run_detail_turn(
        db,
        provider,
        user_id=f"no-commit-tea-egg-{uuid4().hex[:8]}",
        text=TEA_EGG_INPUT,
        local_date=local_date,
        case_id="generic_stable_tea_egg",
        expected_behavior="generic anchor estimate with active runtime item payload and not ask-first",
    )
    correction_user = f"no-commit-correction-{uuid4().hex[:8]}"
    seed_detail = await _run_detail_turn(
        db,
        provider,
        user_id=correction_user,
        text=PRIMARY_INPUT,
        local_date=local_date,
        case_id="correction_seed_pearl_milk_tea",
        expected_behavior="seed one prior committed drink before correction",
    )
    correction_detail = await _run_detail_turn(
        db,
        provider,
        user_id=correction_user,
        text=CORRECTION_INPUT,
        local_date=local_date,
        case_id="correction_prior_pearl_milk_tea_half_sugar",
        expected_behavior="attach to exactly one prior drink and mutate only if transition guard and commit boundary allow",
        seed_onboarding=False,
    )
    correction_detail["precondition"] = {
        "seed_canonical_commit": bool(
            _dict(_dict(seed_detail["case"].get("mutation")).get("state_delta")).get("canonical_commit")
        ),
        "seed_root_cause_hint": "upstream_no_commit" if not _dict(_dict(seed_detail["case"].get("mutation")).get("state_delta")).get("canonical_commit") else None,
    }
    details["correction_prior_pearl_milk_tea_half_sugar"] = correction_detail
    return details


def _build_case_diagnostic(detail: dict[str, Any], *, primary: bool) -> dict[str, Any]:
    case = _dict(detail.get("case"))
    trace = _dict(detail.get("trace"))
    result = _dict(detail.get("result"))
    phase_a = _dict(case.get("phase_a"))
    guard_preflight = _dict(
        _dict(_dict(_dict(result.get("intake_execution_manager")).get("react_trace")).get("guard_result")).get(
            "phase_a_transition_guard_preflight"
        )
    )
    transition_guard_result = _dict(phase_a.get("transition_guard_result"))
    if not transition_guard_result and guard_preflight:
        transition_guard_result = {
            "verdict": guard_preflight.get("transition_guard_verdict"),
            "reason": guard_preflight.get("transition_guard_reason"),
            "source": "intake_execution_manager.react_trace.guard_result",
        }
    commit_boundary_preflight = _dict(phase_a.get("phase_a_commit_boundary_preflight")) or guard_preflight
    attachment_decision = _dict(phase_a.get("attachment_decision")) or {
        "status": "not_emitted_by_current_runtime",
        "source": "manager_semantic_decision",
    }
    payload = _first_payload(case)
    trace_for_rounds = trace or {"manager_rounds": _list(_dict(case.get("actual_behavior")).get("manager_rounds"))}
    manager_rounds = _manager_round_summary(trace_for_rounds)
    root_cause, contributing = _classify_root_cause(case=case, trace=trace, manager_rounds=manager_rounds)
    if root_cause not in ROOT_CAUSE_ENUM:
        root_cause = "unknown"
    persistence = _persistence_result(result)
    state_delta = _dict(_dict(case.get("mutation")).get("state_delta"))
    followup_question = str(payload.get("followup_question") or "")
    diagnostic = {
        "case_id": case.get("case_id"),
        "input": case.get("input"),
        "expected_behavior": case.get("expected_behavior"),
        "nutrition_payload_present": bool(payload),
        "estimated_kcal": int(payload.get("estimated_kcal") or 0),
        "route_target": payload.get("route_target"),
        "action_taken": payload.get("action_taken"),
        "followup_question_present": bool(followup_question),
        "followup_question": followup_question,
        "output_text_encoding_issue_detected": _contains_mojibake_or_private_use(followup_question),
        "attachment_decision": attachment_decision,
        "transition_guard_result": transition_guard_result,
        "manager_rounds": manager_rounds,
        "commit_boundary_preflight": commit_boundary_preflight,
        "boundary_projection": _dict(_dict(case.get("final_mapping")).get("boundary_projection")),
        "persistence_attempted": bool(persistence),
        "persistence_result": _json_safe(persistence),
        "state_delta": state_delta,
        "root_cause": root_cause,
        "contributing_root_causes": contributing,
        "root_cause_source": "active_trace_precedence",
    }
    if not primary and detail.get("precondition"):
        diagnostic["precondition"] = _json_safe(detail["precondition"])
        if not detail["precondition"].get("seed_canonical_commit"):
            diagnostic["secondary_classification"] = "precondition_blocked"
    return diagnostic


def _run_detail_runtime(*, detail_db_path: Path, local_date: str) -> dict[str, dict[str, Any]]:
    database = BASE_RUNNER._configure_database(detail_db_path)
    provider = BASE_RUNNER.DeterministicFounderProvider()
    db = database.SessionLocal()
    try:
        return asyncio.run(_run_detail_cases(db, provider, local_date=local_date))
    finally:
        db.close()
        engine = getattr(database, "engine", None)
        if engine is not None:
            engine.dispose()


def run_diagnostic(
    *,
    output_path: Path = ARTIFACT_PATH,
    source_output_path: Path = SOURCE_ARTIFACT_PATH,
    source_db_path: Path = SOURCE_DB_PATH,
    detail_db_path: Path = DETAIL_DB_PATH,
    local_date: str = LOCAL_DATE,
) -> dict[str, Any]:
    source_report = BASE_RUNNER.run_diagnostic(
        output_path=source_output_path,
        db_path=source_db_path,
        local_date=local_date,
    )
    details = _run_detail_runtime(detail_db_path=detail_db_path, local_date=local_date)
    primary = _build_case_diagnostic(details["pearl_milk_tea_logged_followup"], primary=True)
    secondary = [
        _build_case_diagnostic(details["generic_stable_tea_egg"], primary=False),
        _build_case_diagnostic(details["correction_prior_pearl_milk_tea_half_sugar"], primary=False),
    ]
    legacy_scan = _scan_legacy_drift()
    legacy_scan["active_trace_root_cause"] = primary["root_cause"]
    report = {
        "artifact_type": "wave1_founder_e2e_estimable_payload_no_commit_diagnostic",
        "provider_mode": "deterministic",
        "active_entrypoint": BASE_RUNNER.ACTIVE_ENTRYPOINT,
        "active_entrypoint_verified": bool(BASE_RUNNER._active_entrypoint_verified()),
        "live_llm_invoked": False,
        "tavily_live_invoked": False,
        "readiness_claimed": False,
        "source_artifact": str(source_output_path),
        "source_summary": _json_safe(_dict(source_report.get("summary"))),
        "root_cause_enum": list(ROOT_CAUSE_ENUM),
        "root_cause_precedence": [
            "active_trace_precedence",
            "legacy_scan_supporting_evidence_only",
        ],
        "primary_case": primary,
        "secondary_cases": secondary,
        "legacy_drift_scan": legacy_scan,
        "next_repair_guidance": {
            "repair_target": "semantic_owner_inversion",
            "deterministic_diagnostic_mode_is_not_semantic_ownership": True,
            "phase_a_should_consume_manager_structured_semantic_decision": True,
            "fake_provider_may_simulate_llm_manager_structured_outputs": True,
            "diagnostic_harness_must_not_infer_user_intent_by_keyword": True,
            "do_not_patch_cjk_keyword_intent_as_semantic_owner": True,
            "non_goal": "deterministic keyword or regex intent classification",
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(_json_safe(report), ensure_ascii=False, indent=2), encoding="utf-8")
    return _json_safe(report)


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose estimable Founder E2E payloads that end in no_commit.")
    parser.add_argument("--output", default=str(ARTIFACT_PATH))
    parser.add_argument("--source-output", default=str(SOURCE_ARTIFACT_PATH))
    parser.add_argument("--source-db-path", default=str(SOURCE_DB_PATH))
    parser.add_argument("--detail-db-path", default=str(DETAIL_DB_PATH))
    parser.add_argument("--local-date", default=LOCAL_DATE)
    args = parser.parse_args()

    report = run_diagnostic(
        output_path=Path(args.output),
        source_output_path=Path(args.source_output),
        source_db_path=Path(args.source_db_path),
        detail_db_path=Path(args.detail_db_path),
        local_date=args.local_date,
    )
    print(
        json.dumps(
            {
                "artifact": str(Path(args.output)),
                "source_artifact": report["source_artifact"],
                "primary_root_cause": report["primary_case"]["root_cause"],
                "contributing_root_causes": report["primary_case"]["contributing_root_causes"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
