from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.current_budget_answer import build_remaining_budget_answer_contract
from app.application.general_chat_pass import build_general_chat_response_pass
from app.database import get_or_create_user
from app.models import Base, BodyPlanRecord, DayBudgetLedgerRecord, MealThreadRecord, MealVersionRecord
from scripts.audit_io_guard import enforce_file_backed_audit_input, load_json_audit_fixture


PACK_PATH = (
    ROOT
    / "docs"
    / "quality"
    / "benchmarks"
    / "general_chat"
    / "general_chat_official_canonical_pack_v1.json"
)
LOG_ROOT = ROOT / ".logs" / "general_chat_official_pack"


@dataclass(frozen=True)
class RuntimeCase:
    case_id: str
    suite_id: str
    utterance: str
    state_pack_summary: dict[str, Any]
    expected_target_workflow_family: str
    expected_disposition: str
    expected_workflow_effect: str
    expected_required_read_surfaces: list[str]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run general_chat official canonical pack cases.")
    parser.add_argument("--case-id", default=None, help="Optional case_id filter.")
    parser.add_argument("--output-dir", default=str(LOG_ROOT), help="Directory for JSON report artifacts.")
    return parser


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _safe_slug(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip())
    return cleaned.strip("_") or "case"


def _load_runtime_cases(*, case_id: str | None) -> list[RuntimeCase]:
    payload = load_json_audit_fixture(path=PACK_PATH, audit_name="general_chat_official_pack")
    if not isinstance(payload, dict):
        raise SystemExit(f"invalid fixture object: {PACK_PATH}")
    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, list):
        raise SystemExit("general_chat official pack missing cases list")

    selected: list[RuntimeCase] = []
    for raw_case in raw_cases:
        if not isinstance(raw_case, dict):
            continue
        current_case_id = str(raw_case.get("case_id") or "")
        if not current_case_id:
            continue
        if case_id is not None and current_case_id != case_id:
            continue
        selected.append(
            RuntimeCase(
                case_id=current_case_id,
                suite_id=str(raw_case.get("suite_id") or ""),
                utterance=str(raw_case.get("utterance") or ""),
                state_pack_summary=dict(raw_case.get("state_pack_summary") or {}),
                expected_target_workflow_family=str(raw_case.get("expected_target_workflow_family") or ""),
                expected_disposition=str(raw_case.get("expected_disposition") or ""),
                expected_workflow_effect=str(raw_case.get("expected_workflow_effect") or ""),
                expected_required_read_surfaces=[
                    str(item)
                    for item in list(raw_case.get("expected_required_read_surfaces") or [])
                    if isinstance(item, str)
                ],
            )
        )
    if case_id is not None and not selected:
        raise SystemExit(f"unknown case_id: {case_id}")
    return selected


def _session_factory() -> sessionmaker[Session]:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _seed_active_body_plan(db: Session, *, user_id: int, summary: dict[str, Any]) -> BodyPlanRecord | None:
    plan_summary = dict(summary.get("active_body_plan_view") or {})
    daily_budget_kcal = int(plan_summary.get("daily_budget_kcal") or 0)
    if daily_budget_kcal <= 0:
        return None
    goal_type = str(plan_summary.get("goal_type") or "").strip() or None
    plan_source = str(plan_summary.get("plan_source") or "").strip() or "official_pack_seed"
    record = BodyPlanRecord(
        user_id=user_id,
        plan_status="active",
        plan_label="general_chat_seed_plan",
        estimated_tdee=daily_budget_kcal,
        daily_budget_kcal=daily_budget_kcal,
        safety_floor_kcal=0,
        metadata_json={
            "goal_type": goal_type,
            "plan_source": plan_source,
            "recommended_target_kcal": daily_budget_kcal,
        },
    )
    db.add(record)
    db.flush()
    return record


def _seed_completed_meals(
    db: Session,
    *,
    user_id: int,
    local_date: str,
    consumed_kcal: int,
    meal_count: int,
) -> None:
    if meal_count <= 0:
        return
    base = consumed_kcal // meal_count
    remainder = consumed_kcal % meal_count
    start = datetime(2026, 4, 18, 8, 0, tzinfo=timezone.utc)
    for index in range(meal_count):
        meal_kcal = base + (1 if index < remainder else 0)
        thread = MealThreadRecord(
            user_id=user_id,
            title=f"seeded meal {index + 1}",
            thread_kind="text_intake",
        )
        db.add(thread)
        db.flush()
        version = MealVersionRecord(
            meal_thread_id=thread.id,
            version_status="active",
            version_reason="new_intake",
            meal_title=f"seeded meal {index + 1}",
            raw_input=f"seeded meal {index + 1}",
            planner_intent="food_estimation",
            resolution_status="completed_meal",
            total_kcal=meal_kcal,
            occurred_at=start + timedelta(hours=index * 4),
            local_date=local_date,
        )
        db.add(version)
        db.flush()
        thread.active_version_id = version.id
        db.add(thread)


def _seed_current_budget(db: Session, *, user_id: int, local_date: str, summary: dict[str, Any]) -> None:
    budget_summary = dict(summary.get("current_budget_view") or {})
    budget_kcal = int(budget_summary.get("budget_kcal") or 0)
    consumed_kcal = int(budget_summary.get("consumed_kcal") or 0)
    remaining_kcal = int(budget_summary.get("remaining_kcal") or max(0, budget_kcal - consumed_kcal))
    meal_count = int(budget_summary.get("active_meal_count") or 0)
    if budget_kcal <= 0 and consumed_kcal <= 0 and meal_count <= 0:
        return
    ledger = DayBudgetLedgerRecord(
        user_id=user_id,
        local_date=local_date,
        budget_kcal=budget_kcal,
        consumed_kcal=consumed_kcal,
        adjustment_kcal=0,
        remaining_kcal=remaining_kcal,
    )
    db.add(ledger)
    db.flush()
    _seed_completed_meals(
        db,
        user_id=user_id,
        local_date=local_date,
        consumed_kcal=consumed_kcal,
        meal_count=meal_count,
    )


def _seed_case_state(db: Session, *, case: RuntimeCase, user_external_id: str, local_date: str) -> int:
    user = get_or_create_user(db, user_external_id)
    _seed_active_body_plan(db, user_id=user.id, summary=case.state_pack_summary)
    _seed_current_budget(db, user_id=user.id, local_date=local_date, summary=case.state_pack_summary)
    db.commit()
    return int(user.id)


def _build_case_result(*, db: Session, case: RuntimeCase, user_external_id: str, local_date: str) -> dict[str, Any]:
    before_counts = {
        "body_plans": db.query(BodyPlanRecord).count(),
        "ledgers": db.query(DayBudgetLedgerRecord).count(),
        "meal_threads": db.query(MealThreadRecord).count(),
    }
    result = build_general_chat_response_pass(
        db,
        user_external_id=user_external_id,
        raw_user_input=case.utterance,
        local_date=local_date,
    )
    after_counts = {
        "body_plans": db.query(BodyPlanRecord).count(),
        "ledgers": db.query(DayBudgetLedgerRecord).count(),
        "meal_threads": db.query(MealThreadRecord).count(),
    }
    user = get_or_create_user(db, user_external_id)
    budget_answer = build_remaining_budget_answer_contract(db, user_id=user.id, local_date=local_date)
    checks = {
        "workflow_family_matches": result.target_workflow_family == case.expected_target_workflow_family,
        "disposition_matches": result.disposition == case.expected_disposition,
        "workflow_effect_matches": result.workflow_effect == case.expected_workflow_effect,
        "required_read_surfaces_match": result.required_read_surfaces == case.expected_required_read_surfaces,
        "state_counts_unchanged": before_counts == after_counts,
    }
    if case.suite_id == "general_chat_budget_query_golden_v1":
        checks["budget_answer_is_ready"] = budget_answer.status == "ready"
        checks["budget_numbers_reflected_in_reply"] = all(
            str(value) in result.reply_text
            for value in (
                budget_answer.daily_target_kcal,
                budget_answer.consumed_kcal,
                budget_answer.remaining_kcal,
            )
        )
    elif case.suite_id == "general_chat_goal_query_golden_v1":
        goal_type = str(case.state_pack_summary.get("active_body_plan_view", {}).get("goal_type") or "")
        checks["goal_type_reflected_in_reply"] = bool(goal_type) and goal_type in result.reply_text
    elif case.suite_id == "general_chat_open_workflow_boundary_golden_v1":
        checks["read_surfaces_empty"] = result.required_read_surfaces == []
    checks["passed"] = all(bool(value) for key, value in checks.items() if key != "passed")
    return {
        "case_id": case.case_id,
        "suite_id": case.suite_id,
        "utterance": case.utterance,
        "expected": {
            "target_workflow_family": case.expected_target_workflow_family,
            "disposition": case.expected_disposition,
            "workflow_effect": case.expected_workflow_effect,
            "required_read_surfaces": case.expected_required_read_surfaces,
        },
        "runtime_observation": {
            "target_workflow_family": result.target_workflow_family,
            "disposition": result.disposition,
            "workflow_effect": result.workflow_effect,
            "required_read_surfaces": result.required_read_surfaces,
            "reply_text": result.reply_text,
            "ui_hints": result.ui_hints,
            "remaining_budget_contract": {
                "status": budget_answer.status,
                "daily_target_kcal": budget_answer.daily_target_kcal,
                "consumed_kcal": budget_answer.consumed_kcal,
                "remaining_kcal": budget_answer.remaining_kcal,
                "meal_count": budget_answer.meal_count,
            },
        },
        "checks": checks,
    }


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def run_pack(*, case_id: str | None = None, output_dir: Path) -> tuple[Path, Path, dict[str, Any]]:
    cases = _load_runtime_cases(case_id=case_id)
    session_local = _session_factory()
    results: list[dict[str, Any]] = []
    local_date = "2026-04-18"
    for index, case in enumerate(cases, start=1):
        user_external_id = f"general-chat-official-{_safe_slug(case.case_id)}-{index}"
        db = session_local()
        try:
            _seed_case_state(db, case=case, user_external_id=user_external_id, local_date=local_date)
            results.append(
                _build_case_result(
                    db=db,
                    case=case,
                    user_external_id=user_external_id,
                    local_date=local_date,
                )
            )
        finally:
            db.close()
    passed_cases = sum(1 for item in results if item["checks"]["passed"])
    report = {
        "run_id": f"general_chat_official_pack_{_now_tag()}",
        "pack_id": "general_chat_official_canonical_pack_v1",
        "pack_mode": "official_canonical",
        "authority_level": "canonical",
        "recorded_at_utc": _iso_now(),
        "summary": {
            "total_cases": len(results),
            "passed_cases": passed_cases,
            "failed_cases": len(results) - passed_cases,
        },
        "cases": results,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"{report['run_id']}.json"
    summary_path = output_dir / f"{report['run_id']}_summary.json"
    _save_json(report_path, report)
    _save_json(summary_path, report["summary"])
    return report_path, summary_path, report


def main() -> int:
    enforce_file_backed_audit_input(audit_name="general_chat_official_pack")
    args = _parser().parse_args()
    output_dir = Path(args.output_dir).resolve()
    with TemporaryDirectory(prefix="general-chat-official-pack-"):
        report_path, summary_path, report = run_pack(case_id=args.case_id, output_dir=output_dir)
    print(report_path)
    print(summary_path)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0 if report["summary"]["failed_cases"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
