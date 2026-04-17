from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_io_guard import enforce_file_backed_audit_input, load_json_audit_fixture


PACK_PATH = ROOT / "docs" / "quality" / "benchmarks" / "intake" / "intake_executable_action_pack_v1.json"
SOURCE_PACK_PATH = ROOT / "docs" / "quality" / "benchmarks" / "intake" / "intake_official_canonical_pack_v1.json"
LOG_ROOT = ROOT / ".logs" / "intake_executable_pack"


@dataclass
class RuntimeModules:
    SessionLocal: Any
    init_db: Any
    engine: Any
    EstimateRequest: Any
    run_text_meal_canary: Any
    get_or_create_user: Any
    save_meal_log: Any
    persist_text_meal_result: Any
    EstimatePayload: Any
    ComponentEstimate: Any
    MealLog: Any


@dataclass
class RuntimeCase:
    executable_case_id: str
    source_official_case_id: str
    suite_id: str
    derivation_status: str
    execution_mode: str
    source_utterance: str
    source_state_pack_summary: dict[str, Any]
    state_seed: dict[str, Any]
    expected_runtime_outcome: dict[str, Any]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run intake executable action pack cases in isolated mode.")
    parser.add_argument("--case-id", default=None, help="Optional executable_case_id filter.")
    parser.add_argument("--output-dir", default=str(LOG_ROOT), help="Directory for JSON report artifacts.")
    return parser


def _load_json_fixture(*, path: Path, audit_name: str) -> dict[str, Any]:
    payload = load_json_audit_fixture(path=path, audit_name=audit_name)
    if not isinstance(payload, dict):
        raise SystemExit(f"invalid fixture object: {path}")
    return payload


def _source_case_map(source_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    source_cases = source_payload.get("cases")
    if not isinstance(source_cases, list):
        raise SystemExit("source official pack missing cases list")
    mapping: dict[str, dict[str, Any]] = {}
    for case in source_cases:
        if isinstance(case, dict) and isinstance(case.get("case_id"), str):
            mapping[str(case["case_id"])] = dict(case)
    return mapping


def _selected_runtime_cases(*, case_id: str | None) -> list[RuntimeCase]:
    pack_payload = _load_json_fixture(path=PACK_PATH, audit_name="intake_executable_pack")
    source_payload = _load_json_fixture(path=SOURCE_PACK_PATH, audit_name="intake_executable_pack_source")
    source_cases = _source_case_map(source_payload)
    selected: list[RuntimeCase] = []
    for raw_case in pack_payload.get("cases", []):
        if not isinstance(raw_case, dict):
            continue
        executable_case_id = str(raw_case.get("executable_case_id") or "")
        if not executable_case_id:
            continue
        if case_id is not None and executable_case_id != case_id:
            continue
        if raw_case.get("derivation_status") != "contract_ready":
            continue
        source_case_id = str(raw_case.get("source_official_case_id") or "")
        source_case = source_cases.get(source_case_id)
        if source_case is None:
            raise SystemExit(f"missing source official case for {executable_case_id}: {source_case_id}")
        source_utterance = source_case.get("utterance")
        if not isinstance(source_utterance, str) or not source_utterance.strip():
            raise SystemExit(f"source official case missing utterance: {source_case_id}")
        selected.append(
            RuntimeCase(
                executable_case_id=executable_case_id,
                source_official_case_id=source_case_id,
                suite_id=str(raw_case.get("suite_id") or ""),
                derivation_status=str(raw_case.get("derivation_status") or ""),
                execution_mode=str(raw_case.get("execution_mode") or ""),
                source_utterance=source_utterance,
                source_state_pack_summary=dict(source_case.get("state_pack_summary") or {}),
                state_seed=dict(raw_case.get("state_seed") or {}),
                expected_runtime_outcome=dict(raw_case.get("expected_runtime_outcome") or {}),
            )
        )
    if case_id is not None and not selected:
        raise SystemExit(f"unknown executable_case_id: {case_id}")
    return selected


def _set_isolated_runtime_env(runtime_root: Path) -> None:
    os.environ["RUNTIME_ROOT"] = str(runtime_root)
    os.environ["SESSION_RECORD_ROOT"] = str(runtime_root / "session_records")
    os.environ["DATABASE_URL"] = f"sqlite:///{(runtime_root / 'db' / 'canary_persistence.db').as_posix()}"


def _load_runtime_modules(*, runtime_root: Path) -> RuntimeModules:
    _set_isolated_runtime_env(runtime_root)
    app_database = importlib.import_module("app.database")
    schemas = importlib.import_module("app.schemas")
    text_meal = importlib.import_module("app.usecases.text_meal")
    meal_persistence = importlib.import_module("app.infrastructure.meal_log_persistence")
    models = importlib.import_module("app.models")
    return RuntimeModules(
        SessionLocal=app_database.SessionLocal,
        init_db=app_database.init_db,
        engine=app_database.engine,
        EstimateRequest=schemas.EstimateRequest,
        run_text_meal_canary=text_meal.run_text_meal_canary,
        get_or_create_user=app_database.get_or_create_user,
        save_meal_log=app_database.save_meal_log,
        persist_text_meal_result=meal_persistence.persist_text_meal_result,
        EstimatePayload=schemas.EstimatePayload,
        ComponentEstimate=schemas.ComponentEstimate,
        MealLog=models.MealLog,
    )


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_slug(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return cleaned.strip("_") or "case"


def _pending_followup_question(case: RuntimeCase) -> str:
    active_thread = dict(case.source_state_pack_summary.get("active_meal_thread") or {})
    explicit = str(active_thread.get("pending_followup_question") or "").strip()
    if explicit:
        return explicit
    lane = str(active_thread.get("followup_lane_family") or case.state_seed.get("seed_payload", {}).get("followup_lane_family") or "")
    if lane == "ask_followup_only":
        return "請補充剛剛那餐還吃了什麼？"
    return "請補充份量或更多細節。"


def _seed_completed_meal(
    modules: RuntimeModules,
    *,
    db: Any,
    user: Any,
    request_id: str,
) -> dict[str, Any]:
    payload = modules.EstimatePayload(
        request_id=request_id,
        meal_title="seeded committed intake meal",
        estimated_kcal=480,
        protein_g=20,
        carb_g=52,
        fat_g=14,
        route_target="best_effort_answer",
        action_taken="direct_answer",
        reply_text="seeded committed intake meal ok",
        quality_signals={"estimate_mode": "component_estimate"},
        trace_contract={"local_date": "2026-04-18"},
        boundary_trace={},
        component_estimates=[
            modules.ComponentEstimate(
                name="seeded committed intake meal",
                quantity_hint="1 serving",
                estimated_kcal=480,
                protein_g=20,
                carb_g=52,
                fat_g=14,
            )
        ],
    )
    return dict(
        modules.persist_text_meal_result(
            db,
            user=user,
            latest_log=None,
            planner_intent="food_estimation",
            payload=payload,
            raw_input="seeded committed intake meal",
            request_id=request_id,
        )
    )


def _seed_runtime_state(modules: RuntimeModules, *, db: Any, case: RuntimeCase, user_id: str) -> dict[str, Any]:
    user = modules.get_or_create_user(db, user_id)
    seed_kind = str(case.state_seed.get("seed_kind") or "")
    seed_payload = dict(case.state_seed.get("seed_payload") or {})
    if seed_kind == "empty_intake_state":
        return {
            "seed_kind": seed_kind,
            "user_id": user_id,
            "active_log_id": None,
            "canonical_meal_thread_id": None,
        }
    if seed_kind == "active_followup_meal_thread":
        if seed_payload.get("seed_canonical_lineage") is True:
            seeded = _seed_completed_meal(
                modules,
                db=db,
                user=user,
                request_id=f"{_safe_slug(case.executable_case_id)}-seed",
            )
            log = db.get(modules.MealLog, seeded.get("persisted_log_id"))
            if log is None:
                raise SystemExit(f"failed to load seeded log for {case.executable_case_id}")
            log.status = "draft_unresolved"
            log.pending_question = _pending_followup_question(case)
            db.add(log)
            db.commit()
            db.refresh(log)
            canonical_commit = dict(seeded.get("canonical_commit") or {})
        else:
            log = modules.save_meal_log(
                db,
                user,
                meal_title="seeded active intake meal",
                raw_input="seeded active intake meal",
                kcal=320,
                protein_g=12,
                carb_g=28,
                fat_g=11,
                components=[{"name": "seeded active intake meal", "portion_hint": "1 serving"}],
                debug_steps=[],
                status="draft_unresolved",
                pending_question=_pending_followup_question(case),
            )
            canonical_commit = {}
        return {
            "seed_kind": seed_kind,
            "user_id": user_id,
            "active_log_id": log.id,
            "canonical_meal_thread_id": canonical_commit.get("meal_thread_id") or seed_payload.get("meal_thread_id"),
            "canonical_meal_version_id": canonical_commit.get("meal_version_id"),
            "canonical_commit": canonical_commit or None,
            "seed_followup_lane_family": seed_payload.get("followup_lane_family"),
            "seed_pending_question": log.pending_question,
        }
    if seed_kind == "committed_meal_thread":
        seeded = _seed_completed_meal(
            modules,
            db=db,
            user=user,
            request_id=f"{_safe_slug(case.executable_case_id)}-seed",
        )
        canonical_commit = dict(seeded.get("canonical_commit") or {})
        return {
            "seed_kind": seed_kind,
            "user_id": user_id,
            "active_log_id": seeded.get("persisted_log_id"),
            "canonical_meal_thread_id": canonical_commit.get("meal_thread_id"),
            "canonical_meal_version_id": canonical_commit.get("meal_version_id"),
            "canonical_commit": canonical_commit,
        }
    raise SystemExit(f"unsupported seed_kind: {seed_kind}")


def _planner_result_for_case(case: RuntimeCase, *, seeded_state: dict[str, Any], user_payload: dict[str, Any]) -> dict[str, Any]:
    effect = str(case.expected_runtime_outcome.get("expected_workflow_effect") or "")
    if effect == "continue_followup_lane":
        return {
            "intent": "clarification",
            "scope": "meal_specific",
            "meal_link_action": "attach_to_existing_meal",
            "target_meal_id": seeded_state.get("active_log_id"),
            "link_confidence": "high",
            "boundary_reason": "same_meal_followup",
            "clarification_blocking": False,
            "normalized_user_input": user_payload["current_user_input"],
        }
    if effect == "correct_existing_meal_thread":
        return {
            "intent": "modification",
            "scope": "meal_specific",
            "meal_link_action": "attach_to_existing_meal",
            "target_meal_id": seeded_state.get("active_log_id"),
            "link_confidence": "high",
            "boundary_reason": "same_meal_followup",
            "clarification_blocking": False,
            "normalized_user_input": user_payload["current_user_input"],
        }
    return {
        "intent": "food_estimation",
        "scope": "meal_specific",
        "meal_link_action": "create_new_meal",
        "target_meal_id": None,
        "link_confidence": "high",
        "boundary_reason": "new_meal_switch" if effect == "open_new_workflow" else "new_meal",
        "clarification_blocking": False,
        "normalized_user_input": user_payload["current_user_input"],
    }


def _nutrition_payload_for_case(case: RuntimeCase) -> dict[str, Any]:
    case_title = case.executable_case_id.replace("_", " ")
    return {
        "action_taken": "direct_answer",
        "resolution_mode": "component_estimate",
        "resolution_basis": "component_model",
        "confidence": "high",
        "exactness": "best_effort",
        "estimate_mode": "llm_only",
        "response_mode_hint": "rough_estimate_ok",
        "tool_request": "none",
        "tool_request_reason": "",
        "state_transition_hint": "completed_meal",
        "food_origin": "generic_common",
        "food_class": "simple_meal",
        "needs_external_data": False,
        "private_info_risk": "low",
        "title": case_title,
        "components": [case_title],
        "protein_g": 18,
        "carb_g": 42,
        "fat_g": 14,
        "kcal_low": 360,
        "kcal_high": 420,
        "kcal_most_likely": 390,
        "uncertainty_factors": [],
        "follow_up_needed": False,
        "follow_up_question": "",
        "follow_up_reasoning": "",
        "followup_questions": [],
        "top_uncertainty_drivers": [],
        "external_data_query": "",
        "unresolved_info": [],
        "answer_payload": {},
    }


class ContractPlannerProvider:
    def __init__(self, *, case: RuntimeCase, seeded_state: dict[str, Any]) -> None:
        self.case = case
        self.seeded_state = seeded_state

    async def complete_with_trace(self, *, system_prompt: str, user_payload: dict[str, Any], stage: str, max_tokens: int | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
        if stage != "task_meal_link_pass":
            raise AssertionError(f"unexpected planner stage: {stage}")
        payload = _planner_result_for_case(self.case, seeded_state=self.seeded_state, user_payload=user_payload)
        return payload, {"stage": stage, "provider": "contract_planner_provider", "parsed_object": payload}


class ContractPrimaryProvider:
    def __init__(self, *, case: RuntimeCase) -> None:
        self.case = case

    async def complete_with_trace(self, *, system_prompt: str, user_payload: dict[str, Any], stage: str, max_tokens: int | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
        effect = str(self.case.expected_runtime_outcome.get("expected_workflow_effect") or "")
        if stage == "decision_pass":
            if effect == "create_thread_and_request_clarify":
                payload = {
                    "next_action": "run_clarify",
                    "tool_plan": "none",
                    "decision_confidence": "high",
                    "clarify_priority": "portion_or_detail",
                    "unresolved_info": ["portion_or_detail"],
                    "response_mode_hint": "clarify_first",
                    "clarify_is_blocking": True,
                    "can_proceed_without_clarify": True,
                }
            else:
                payload = {
                    "next_action": "run_nutrition_resolution",
                    "tool_plan": "none",
                    "decision_confidence": "high",
                    "clarify_priority": None,
                    "unresolved_info": [],
                    "response_mode_hint": "rough_estimate_ok",
                    "clarify_is_blocking": False,
                    "can_proceed_without_clarify": True,
                }
            return payload, {"stage": stage, "provider": "contract_primary_provider", "parsed_object": payload}
        if stage in {"nutrition_resolution_pass_initial", "nutrition_resolution_pass_repair"}:
            if effect == "create_thread_and_request_clarify":
                raise AssertionError("clarify case should not enter nutrition_resolution stages")
            payload = _nutrition_payload_for_case(self.case)
            return payload, {"stage": stage, "provider": "contract_primary_provider", "parsed_object": payload}
        if stage == "final_response_pass":
            if effect == "create_thread_and_request_clarify":
                payload = {
                    "reply_text": "請補充份量或更多細節。",
                    "ui_hints": {},
                }
            else:
                payload = {
                    "reply_text": f"{self.case.executable_case_id} runtime execution ok",
                    "ui_hints": {},
                }
            return payload, {"stage": stage, "provider": "contract_primary_provider", "parsed_object": payload}
        raise AssertionError(f"unexpected primary stage: {stage}")


def _case_checks(case: RuntimeCase, *, seeded_state: dict[str, Any], payload: Any) -> dict[str, Any]:
    persistence = dict(payload.trace_contract.get("persistence_decision") or {})
    boundary = dict(payload.boundary_trace or {})
    canonical_commit = dict(persistence.get("canonical_commit") or {})
    effect = str(case.expected_runtime_outcome.get("expected_workflow_effect") or "")
    checks: dict[str, bool] = {
        "expected_workflow_family_is_intake": case.expected_runtime_outcome.get("expected_target_workflow_family") == "intake",
        "execution_mode_is_text_turn": case.execution_mode == "text_turn",
    }

    if effect == "create_new_meal_thread":
        checks.update(
            {
                "boundary_started_new_meal": boundary.get("meal_boundary") == "start_new_meal",
                "persisted_completed_meal": persistence.get("status") == "completed_meal",
                "created_new_canonical_thread": canonical_commit.get("created_new_thread") is True,
            }
        )
    elif effect == "create_thread_and_request_clarify":
        checks.update(
            {
                "boundary_started_new_meal": boundary.get("meal_boundary") == "start_new_meal",
                "persisted_draft_unresolved": persistence.get("status") == "draft_unresolved",
                "route_target_is_clarify": payload.route_target == "clarify_user_private",
                "canonical_commit_absent": persistence.get("canonical_commit") is None,
            }
        )
    elif effect == "continue_followup_lane":
        checks.update(
            {
                "boundary_continued_active_meal": boundary.get("meal_boundary") == "continue_active_meal",
                "active_meal_context_allowed": boundary.get("active_meal_context_allowed") is True,
                "persisted_completed_meal": persistence.get("status") == "completed_meal",
                "reused_existing_canonical_thread": canonical_commit.get("created_new_thread") is False,
                "attached_to_seeded_parent_log": persistence.get("parent_log_id") == seeded_state.get("active_log_id"),
            }
        )
    elif effect == "correct_existing_meal_thread":
        correction_resolution = dict(payload.trace_contract.get("correction_target_resolution") or {})
        checks.update(
            {
                "boundary_continued_active_meal": boundary.get("meal_boundary") == "continue_active_meal",
                "persisted_completed_meal": persistence.get("status") == "completed_meal",
                "reused_existing_canonical_thread": canonical_commit.get("created_new_thread") is False,
                "attached_to_seeded_parent_log": persistence.get("parent_log_id") == seeded_state.get("active_log_id"),
                "resolved_prior_version_for_correction": bool(correction_resolution.get("parent_version_id") or correction_resolution.get("superseded_version_id")),
            }
        )
    elif effect == "open_new_workflow":
        checks.update(
            {
                "boundary_started_new_meal": boundary.get("meal_boundary") == "start_new_meal",
                "persisted_completed_meal": persistence.get("status") == "completed_meal",
                "created_new_canonical_thread": canonical_commit.get("created_new_thread") is True,
                "seed_had_active_followup_context": seeded_state.get("active_log_id") is not None,
            }
        )
    else:
        raise SystemExit(f"unsupported expected_workflow_effect: {effect}")

    checks["passed"] = all(bool(value) for key, value in checks.items() if key != "passed")
    return checks


def _case_result(case: RuntimeCase, *, seeded_state: dict[str, Any], payload: Any, user_id: str, request_id: str) -> dict[str, Any]:
    persistence = dict(payload.trace_contract.get("persistence_decision") or {})
    checks = _case_checks(case, seeded_state=seeded_state, payload=payload)
    return {
        "executable_case_id": case.executable_case_id,
        "source_official_case_id": case.source_official_case_id,
        "suite_id": case.suite_id,
        "derivation_status": case.derivation_status,
        "execution_mode": case.execution_mode,
        "user_id": user_id,
        "request_id": request_id,
        "input": {
            "source_utterance": case.source_utterance,
            "source_state_pack_summary": case.source_state_pack_summary,
            "state_seed": case.state_seed,
            "seed_runtime_state": seeded_state,
        },
        "expected_runtime_outcome": case.expected_runtime_outcome,
        "runtime_observation": {
            "route_target": payload.route_target,
            "action_taken": payload.action_taken,
            "follow_up_needed": payload.follow_up_needed,
            "reply_text": payload.reply_text,
            "boundary_trace": payload.boundary_trace,
            "persistence_decision": persistence,
            "correction_target_resolution": payload.trace_contract.get("correction_target_resolution"),
        },
        "checks": checks,
    }


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


async def _run_case(modules: RuntimeModules, *, db: Any, case: RuntimeCase, user_id: str) -> dict[str, Any]:
    seeded_state = _seed_runtime_state(modules, db=db, case=case, user_id=user_id)
    planner_provider = ContractPlannerProvider(case=case, seeded_state=seeded_state)
    primary_provider = ContractPrimaryProvider(case=case)
    request_id = f"{_safe_slug(case.executable_case_id)}-{_now_tag()}"
    payload = await modules.run_text_meal_canary(
        modules.EstimateRequest(text=case.source_utterance, allow_search=False, user_id=user_id),
        provider=primary_provider,
        planner_provider=planner_provider,
        primary_provider=primary_provider,
        request_id=request_id,
        search_adapter=None,
        db=db,
    )
    return _case_result(case, seeded_state=seeded_state, payload=payload, user_id=user_id, request_id=request_id)


async def _run_all_cases(modules: RuntimeModules, *, cases: list[RuntimeCase]) -> dict[str, Any]:
    modules.init_db()
    results: list[dict[str, Any]] = []
    for index, case in enumerate(cases, start=1):
        user_id = f"intake-executable-{_safe_slug(case.executable_case_id)}-{index}"
        db = modules.SessionLocal()
        try:
            results.append(await _run_case(modules, db=db, case=case, user_id=user_id))
        finally:
            db.close()
    passed_cases = sum(1 for item in results if item["checks"]["passed"])
    by_effect: dict[str, dict[str, int]] = {}
    for item in results:
        effect = str(item["expected_runtime_outcome"]["expected_workflow_effect"])
        bucket = by_effect.setdefault(effect, {"total": 0, "passed": 0, "failed": 0})
        bucket["total"] += 1
        if item["checks"]["passed"]:
            bucket["passed"] += 1
        else:
            bucket["failed"] += 1
    return {
        "run_id": f"intake_executable_pack_{_now_tag()}",
        "pack_id": "intake_executable_action_pack_v1",
        "pack_mode": "executable_action",
        "authority_level": "derived_from_official_canonical",
        "recorded_at_utc": _iso_now(),
        "isolated_mode": True,
        "summary": {
            "total_cases": len(results),
            "passed_cases": passed_cases,
            "failed_cases": len(results) - passed_cases,
            "by_expected_workflow_effect": by_effect,
        },
        "cases": results,
    }


def run_pack(*, case_id: str | None = None, output_dir: Path, runtime_root: Path) -> tuple[Path, Path, dict[str, Any]]:
    cases = _selected_runtime_cases(case_id=case_id)
    modules = _load_runtime_modules(runtime_root=runtime_root)
    try:
        report = asyncio.run(_run_all_cases(modules, cases=cases))
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = output_dir / f"{report['run_id']}.json"
        summary_path = output_dir / f"{report['run_id']}_summary.json"
        _save_json(report_path, report)
        _save_json(summary_path, report["summary"])
        return report_path, summary_path, report
    finally:
        modules.engine.dispose()


def main() -> int:
    enforce_file_backed_audit_input(audit_name="intake_executable_pack")
    args = _parser().parse_args()
    output_dir = Path(args.output_dir).resolve()
    with TemporaryDirectory(prefix="intake-executable-pack-") as temp_dir:
        runtime_root = Path(temp_dir)
        report_path, summary_path, report = run_pack(
            case_id=args.case_id,
            output_dir=output_dir,
            runtime_root=runtime_root,
        )
    print(report_path)
    print(summary_path)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0 if report["summary"]["failed_cases"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
