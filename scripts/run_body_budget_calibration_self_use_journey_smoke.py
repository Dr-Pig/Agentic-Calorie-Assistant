from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.body.infrastructure.models import BodyObservationRecord, BodyPlanRecord, BodyProfileRecord  # noqa: E402
from app.budget.infrastructure.models import DayBudgetLedgerRecord, LedgerEntryRecord  # noqa: E402
from app.composition import intake_routes as intake_routes_module  # noqa: E402
from app.database import get_db, get_or_create_user  # noqa: E402
from app.intake.infrastructure.models import MealThreadRecord, MealVersionRecord  # noqa: E402
from app.models import Base  # noqa: E402
from app.routes import router  # noqa: E402
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402
from app.shared.infra.models import ProposalContainerRecord  # noqa: E402


DEFAULT_DB_PATH = ROOT / "artifacts" / "body_budget_calibration_self_use_journey_smoke.sqlite3"
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "body_budget_calibration_self_use_journey_smoke.json"
DEFAULT_USER_ID = "body-budget-calibration-self-use-journey"
DEFAULT_LOCAL_DATE = "2026-05-14"
WINDOW_START = datetime(2026, 5, 1)


def _session(db_path: Path, *, reset_db: bool) -> Session:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if reset_db and db_path.exists():
        db_path.unlink()
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _install_local_noop_estimate_fallback() -> Callable[[], None]:
    original_parse_weight_or_budget_intent = intake_routes_module.parse_weight_or_budget_intent
    original_execute_intake_turn = intake_routes_module.execute_intake_turn

    async def local_noop_parse_weight_or_budget_intent(_llm: Any, _text: str) -> dict[str, Any]:
        return {"weight_kg": None, "delta_kcal": None}

    async def local_noop_execute_intake_turn(*_args: Any, **kwargs: Any) -> dict[str, Any]:
        return {
            "request_id": kwargs.get("request_id") or "calibration-smoke-raw-text-noop",
            "assistant_message": "No calibration state change from raw text.",
            "manager_decision": {
                "intent_type": "intake",
                "workflow_effect": "raw_text_route_fallback_without_calibration_state_mutation",
            },
            "state_after": kwargs.get("state_before"),
        }

    intake_routes_module.parse_weight_or_budget_intent = local_noop_parse_weight_or_budget_intent
    intake_routes_module.execute_intake_turn = local_noop_execute_intake_turn

    def restore() -> None:
        intake_routes_module.parse_weight_or_budget_intent = original_parse_weight_or_budget_intent
        intake_routes_module.execute_intake_turn = original_execute_intake_turn

    return restore


def _client(db: Session) -> TestClient:
    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def _date_for_offset(offset: int) -> str:
    return (WINDOW_START + timedelta(days=offset)).date().isoformat()


def _seed_meal(db: Session, *, user_id: int, local_date: str, kcal: int) -> None:
    occurred_at = datetime.fromisoformat(local_date).replace(hour=12)
    thread = MealThreadRecord(
        user_id=user_id,
        title=f"calibration smoke meal {local_date}",
        thread_kind="text_intake",
        created_at=occurred_at,
        updated_at=occurred_at,
    )
    db.add(thread)
    db.flush()
    version = MealVersionRecord(
        meal_thread_id=thread.id,
        version_status="active",
        version_reason="new_intake",
        meal_title=f"calibration smoke meal {local_date}",
        raw_input="calibration smoke meal",
        resolution_status="completed_meal",
        total_kcal=kcal,
        protein_g=25,
        carb_g=120,
        fat_g=35,
        occurred_at=occurred_at,
        local_date=local_date,
        created_at=occurred_at.replace(hour=13),
    )
    db.add(version)
    db.flush()
    thread.active_version_id = version.id


def _seed_weight(db: Session, *, user_id: int, local_date: str, value: float) -> None:
    observed_at = datetime.fromisoformat(local_date).replace(hour=7)
    db.add(
        BodyObservationRecord(
            user_id=user_id,
            observation_type="weight",
            value=value,
            unit="kg",
            observed_at=observed_at,
            local_date=local_date,
            source="manual",
            metadata_json={},
            created_at=observed_at.replace(minute=5),
        )
    )


def _seed_calibration_history(db: Session, *, user_external_id: str, local_date: str) -> int:
    existing_plan_id = db.execute(select(BodyPlanRecord.id).limit(1)).scalar_one_or_none()
    if existing_plan_id is not None:
        raise RuntimeError("body_budget_calibration_smoke_requires_empty_database_or_reset")

    user = get_or_create_user(db, user_external_id)
    db.add(
        BodyPlanRecord(
            user_id=user.id,
            plan_status="active",
            plan_label="calibration smoke baseline",
            estimated_tdee=2100,
            daily_budget_kcal=1800,
            safety_floor_kcal=1200,
            target_pace_kg_per_week=0.5,
            metadata_json={
                "recommended_target_kcal": 1800,
                "plan_source": "calibration_smoke_baseline",
                "goal_type": "lose_weight",
            },
            started_at=datetime(2026, 5, 1, 8, 0, 0),
            created_at=datetime(2026, 5, 1, 8, 0, 0),
        )
    )
    db.add(
        BodyProfileRecord(
            user_id=user.id,
            profile_status="active",
            sex="female",
            age_years=31,
            height_cm=165.0,
            current_weight_kg=70.0,
            activity_level="light",
            goal_type="lose_weight",
            timezone="Asia/Taipei",
            created_at=datetime(2026, 5, 1, 8, 0, 0),
            updated_at=datetime(2026, 5, 1, 8, 0, 0),
        )
    )
    for offset in range(14):
        _seed_meal(db, user_id=user.id, local_date=_date_for_offset(offset), kcal=1450)
    for sample_date, value in [
        ("2026-05-01", 70.0),
        ("2026-05-04", 70.0),
        ("2026-05-07", 69.95),
        ("2026-05-10", 69.95),
        ("2026-05-14", 69.9),
    ]:
        _seed_weight(db, user_id=user.id, local_date=sample_date, value=value)
    db.add(
        DayBudgetLedgerRecord(
            user_id=user.id,
            local_date=local_date,
            budget_kcal=1800,
            consumed_kcal=1450,
            adjustment_kcal=0,
            remaining_kcal=350,
        )
    )
    db.commit()
    return int(user.id)


def _get_json(client: TestClient, path: str, *, params: dict[str, Any]) -> dict[str, Any]:
    response = client.get(path, params=params)
    if response.status_code != 200:
        raise RuntimeError(f"{path} returned {response.status_code}: {response.text}")
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} did not return a JSON object")
    return payload


def _post_json(client: TestClient, path: str, *, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post(path, json=payload)
    if response.status_code != 200:
        raise RuntimeError(f"{path} returned {response.status_code}: {response.text}")
    response_payload = response.json()
    if not isinstance(response_payload, dict):
        raise RuntimeError(f"{path} did not return a JSON object")
    return response_payload


def _body_plan_counts(db: Session) -> dict[str, int]:
    plans = db.execute(select(BodyPlanRecord)).scalars().all()
    return {
        "total": len(plans),
        "active": sum(1 for plan in plans if plan.plan_status == "active"),
        "superseded": sum(1 for plan in plans if plan.plan_status == "superseded"),
    }


def _active_plan_snapshot(db: Session, *, user_id: int) -> dict[str, Any]:
    plan = db.execute(
        select(BodyPlanRecord)
        .where(BodyPlanRecord.user_id == user_id, BodyPlanRecord.plan_status == "active")
        .order_by(BodyPlanRecord.id.desc())
        .limit(1)
    ).scalar_one()
    return {
        "id": plan.id,
        "plan_status": plan.plan_status,
        "estimated_tdee": plan.estimated_tdee,
        "daily_budget_kcal": plan.daily_budget_kcal,
        "safety_floor_kcal": plan.safety_floor_kcal,
        "target_pace_kg_per_week": plan.target_pace_kg_per_week,
        "metadata_json": dict(plan.metadata_json or {}),
    }


def _ledger_snapshot(db: Session, *, user_id: int, local_date: str) -> dict[str, Any]:
    ledger = db.execute(
        select(DayBudgetLedgerRecord).where(
            DayBudgetLedgerRecord.user_id == user_id,
            DayBudgetLedgerRecord.local_date == local_date,
        )
    ).scalar_one()
    return {
        "id": ledger.id,
        "budget_kcal": ledger.budget_kcal,
        "consumed_kcal": ledger.consumed_kcal,
        "adjustment_kcal": ledger.adjustment_kcal,
        "remaining_kcal": ledger.remaining_kcal,
    }


def _ledger_entry_snapshot(db: Session, *, user_id: int) -> list[dict[str, Any]]:
    entries = (
        db.execute(
            select(LedgerEntryRecord)
            .where(LedgerEntryRecord.user_id == user_id)
            .order_by(LedgerEntryRecord.id.asc())
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": entry.id,
            "local_date": entry.local_date,
            "entry_type": entry.entry_type,
            "source_type": entry.source_type,
            "source_id": entry.source_id,
            "delta_kcal": entry.delta_kcal,
            "metadata_json": dict(entry.metadata_json or {}),
        }
        for entry in entries
    ]


def _proposal_status(db: Session, proposal_container_id: int) -> str:
    proposal = db.get(ProposalContainerRecord, proposal_container_id)
    if proposal is None:
        raise RuntimeError("calibration_self_use_journey_missing_proposal")
    return str(proposal.proposal_status)


def _history_projection_safe(history_payload: dict[str, Any]) -> bool:
    forbidden = {"metadata", "trace_envelope", "proposal_policy_packet", "options", "effect_payload"}
    proposals = history_payload.get("proposals")
    if not isinstance(proposals, list):
        return False
    return all(isinstance(item, dict) and forbidden.isdisjoint(item) for item in proposals)


def _weekly_current_day(weekly_progress: dict[str, Any], *, local_date: str) -> dict[str, Any]:
    days = weekly_progress.get("days")
    if not isinstance(days, list):
        raise RuntimeError("weekly_progress_days_missing")
    for day in days:
        if isinstance(day, dict) and day.get("local_date") == local_date:
            return day
    raise RuntimeError("weekly_progress_current_day_missing")


def _first_proposal(payload: dict[str, Any]) -> dict[str, Any]:
    proposals = payload.get("proposals")
    if not isinstance(proposals, list) or not proposals or not isinstance(proposals[0], dict):
        return {}
    return proposals[0]


def _add_invariant(blockers: list[str], condition: bool, message: str) -> None:
    if not condition:
        blockers.append(message)


def _evaluate_invariants(report: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    preview = report["proposal_preview"]
    raw_apply = report["raw_text_apply_attempt"]
    action = report["proposal_action"]
    sync = report["post_accept_read_model_sync"]
    inbox_before = report["proposal_inbox_before_accept"]
    inbox_after = report["proposal_inbox_after_accept"]
    history_before = report["proposal_history_before_accept"]
    history_after = report["proposal_history_after_accept"]
    history_before_item = _first_proposal(history_before)
    history_after_item = _first_proposal(history_after)

    _add_invariant(
        blockers,
        preview["workflow_effect"] == "preview_calibration_proposal_without_plan_mutation",
        "preview did not use calibration preview workflow",
    )
    _add_invariant(blockers, preview["proposal_actions_enabled"] is True, "preview did not surface proposal actions")
    _add_invariant(blockers, preview["plan_mutated"] is False, "preview mutated active BodyPlan")
    _add_invariant(blockers, preview["ledger_mutated"] is False, "preview mutated DayBudgetLedger")
    _add_invariant(blockers, preview["ledger_entry_mutated"] is False, "preview mutated LedgerEntry")
    _add_invariant(blockers, preview["plan_count_changed"] is False, "preview changed BodyPlan row count")
    _add_invariant(blockers, preview["ledger_count_changed"] is False, "preview changed DayBudgetLedger row count")
    _add_invariant(
        blockers,
        preview["ledger_entry_count_changed"] is False,
        "preview changed LedgerEntry row count",
    )

    _add_invariant(blockers, inbox_before.get("open_count") == 1, "open proposal inbox missing preview proposal")
    _add_invariant(blockers, history_before.get("history_count") == 1, "history missing open preview proposal")
    _add_invariant(blockers, history_before_item.get("proposal_status") == "open", "history did not show open proposal")
    _add_invariant(
        blockers,
        report["boundaries"]["history_projection_safe_before_accept"] is True,
        "history before accept leaked forbidden fields",
    )

    _add_invariant(
        blockers,
        raw_apply["workflow_effect"] == "raw_text_route_fallback_without_calibration_state_mutation",
        "raw apply text did not stay on route fallback without calibration state mutation",
    )
    _add_invariant(blockers, raw_apply["proposal_status_after_attempt"] == "open", "raw apply text changed proposal status")
    _add_invariant(blockers, raw_apply["proposal_count_changed"] is False, "raw apply text changed proposal count")
    _add_invariant(blockers, raw_apply["plan_mutated"] is False, "raw apply text mutated active BodyPlan")
    _add_invariant(blockers, raw_apply["ledger_mutated"] is False, "raw apply text mutated DayBudgetLedger")
    _add_invariant(
        blockers,
        raw_apply["raw_text_authorized_mutation"] is False,
        "raw text was marked as authorized mutation",
    )

    _add_invariant(
        blockers,
        action["workflow_effect"] == "apply_calibration_proposal_action_with_state_mutation",
        "explicit stored action did not use mutation workflow",
    )
    _add_invariant(blockers, action["proposal_status"] == "accepted", "explicit stored action did not accept proposal")
    _add_invariant(blockers, action["plan_mutated"] is True, "explicit stored action did not authorize plan mutation")
    _add_invariant(blockers, action["ledger_mutated"] is True, "explicit stored action did not authorize ledger refresh")
    _add_invariant(blockers, action["db_plan_mutated"] is True, "explicit stored action did not change active BodyPlan")
    _add_invariant(blockers, action["db_ledger_mutated"] is True, "explicit stored action did not change DayBudgetLedger")
    _add_invariant(blockers, action["db_proposal_status"] == "accepted", "proposal status was not persisted as accepted")
    _add_invariant(
        blockers,
        action["active_body_plan_daily_budget_kcal"] == preview["effect_payload_summary"]["new_daily_budget_kcal"],
        "active BodyPlan daily budget does not match proposal effect",
    )
    _add_invariant(
        blockers,
        action["active_body_plan_estimated_tdee"] == preview["effect_payload_summary"]["new_estimated_tdee_kcal"],
        "active BodyPlan TDEE does not match proposal effect",
    )
    _add_invariant(
        blockers,
        action["current_budget_kcal"] == preview["effect_payload_summary"]["new_daily_budget_kcal"],
        "current budget does not match proposal effect",
    )
    if preview["effect_payload_summary"]["calibration_adjustment_delta_kcal_present"]:
        _add_invariant(
            blockers,
            action["calibration_adjustment_entry_count"] == 1,
            "accepted proposal did not create calibration adjustment ledger entry",
        )
        _add_invariant(
            blockers,
            action["calibration_adjustment_delta_kcal"]
            == preview["effect_payload_summary"]["calibration_adjustment_delta_kcal"],
            "calibration adjustment ledger entry delta does not match proposal effect",
        )
    else:
        _add_invariant(
            blockers,
            action["calibration_adjustment_entry_count"] == 0,
            "accepted proposal created unexpected calibration adjustment ledger entry",
        )
    _add_invariant(blockers, inbox_after.get("open_count") == 0, "accepted proposal remained in open inbox")
    _add_invariant(blockers, history_after.get("history_count") == 1, "history after accept missing proposal")
    _add_invariant(
        blockers,
        history_after_item.get("proposal_status") == "accepted",
        "history after accept did not show accepted proposal",
    )
    _add_invariant(
        blockers,
        report["boundaries"]["history_projection_safe_after_accept"] is True,
        "history after accept leaked forbidden fields",
    )

    _add_invariant(
        blockers,
        sync["current_budget_kcal"] == sync["active_body_plan_daily_budget_kcal"],
        "current budget and active body plan daily budget diverged",
    )
    _add_invariant(
        blockers,
        sync["effective_budget_kcal"] == sync["current_budget_kcal"],
        "effective budget and current budget diverged",
    )
    _add_invariant(
        blockers,
        sync["current_budget_remaining_kcal"] == sync["effective_budget_remaining_kcal"],
        "current budget and effective budget remaining diverged",
    )
    _add_invariant(
        blockers,
        sync["weekly_progress_current_day_target_kcal"] == sync["current_budget_kcal"],
        "weekly progress current-day target diverged from current budget",
    )
    _add_invariant(
        blockers,
        sync["weekly_progress_current_day_consumed_kcal"] == sync["current_budget_consumed_kcal"],
        "weekly progress current-day consumed diverged from current budget",
    )
    _add_invariant(
        blockers,
        sync["weekly_progress_current_day_remaining_kcal"] == sync["current_budget_remaining_kcal"],
        "weekly progress current-day remaining diverged from current budget",
    )
    _add_invariant(blockers, report["live_tool_calling"] is False, "live tool calling was enabled")
    _add_invariant(
        blockers,
        report["automatic_calibration_enabled"] is False,
        "automatic calibration was enabled",
    )
    _add_invariant(blockers, report["rescue_enabled"] is False, "rescue was enabled")
    _add_invariant(blockers, report["recommendation_enabled"] is False, "recommendation was enabled")
    _add_invariant(blockers, report["proactive_enabled"] is False, "proactive was enabled")
    _add_invariant(
        blockers,
        report["product_readiness_claimed"] is False,
        "product readiness was claimed",
    )
    _add_invariant(
        blockers,
        report["private_self_use_approved"] is False,
        "private self-use approval was claimed",
    )
    return blockers


def build_body_budget_calibration_self_use_journey_report(
    *,
    db_path: Path = DEFAULT_DB_PATH,
    output_path: Path | None = None,
    user_external_id: str = DEFAULT_USER_ID,
    local_date: str = DEFAULT_LOCAL_DATE,
    reset_db: bool = True,
) -> dict[str, Any]:
    db = _session(db_path, reset_db=reset_db)
    engine = db.get_bind()
    restore_route_fallback = _install_local_noop_estimate_fallback()
    try:
        user_id = _seed_calibration_history(db, user_external_id=user_external_id, local_date=local_date)
        client = _client(db)
        before_preview_plan_counts = _body_plan_counts(db)
        before_preview_ledger_count = db.query(DayBudgetLedgerRecord).count()
        before_preview_ledger_entries = _ledger_entry_snapshot(db, user_id=user_id)
        before_preview_plan_snapshot = _active_plan_snapshot(db, user_id=user_id)
        before_preview_ledger_snapshot = _ledger_snapshot(db, user_id=user_id, local_date=local_date)

        preview_response = _post_json(
            client,
            "/estimate",
            payload={
                "text": "Should we adjust my calorie target from the last two weeks?",
                "allow_search": False,
                "user_id": user_external_id,
                "local_date": local_date,
                "calibration_preview_requested": True,
                "persist_calibration_proposal": True,
            },
        )
        preview_payload = dict(preview_response["payload"])
        preview_ui_hints = dict(preview_payload.get("ui_hints") or {})
        preview_artifact = preview_payload.get("proposal_artifact")
        if not isinstance(preview_artifact, dict):
            raise RuntimeError("calibration_self_use_journey_expected_persisted_proposal")
        after_preview_plan_counts = _body_plan_counts(db)
        after_preview_ledger_count = db.query(DayBudgetLedgerRecord).count()
        after_preview_ledger_entries = _ledger_entry_snapshot(db, user_id=user_id)
        after_preview_plan_snapshot = _active_plan_snapshot(db, user_id=user_id)
        after_preview_ledger_snapshot = _ledger_snapshot(db, user_id=user_id, local_date=local_date)
        proposal_container_id = int(preview_artifact["proposal_container_id"])
        proposal_record = db.get(ProposalContainerRecord, proposal_container_id)
        if proposal_record is None:
            raise RuntimeError("calibration_self_use_journey_missing_persisted_proposal")
        top_option = next(option for option in proposal_record.options if option.id == proposal_record.top_option_id)
        effect_payload = dict(top_option.effect_payload_json or {})

        inbox_before = _get_json(
            client,
            "/calibration/proposals/open",
            params={"user_id": user_external_id},
        )
        history_before = _get_json(
            client,
            "/calibration/proposals/history",
            params={"user_id": user_external_id},
        )
        before_raw_apply_plan_snapshot = _active_plan_snapshot(db, user_id=user_id)
        before_raw_apply_ledger_snapshot = _ledger_snapshot(db, user_id=user_id, local_date=local_date)
        before_raw_apply_proposal_count = db.query(ProposalContainerRecord).count()
        raw_apply_response = _post_json(
            client,
            "/estimate",
            payload={
                "text": "Apply that calibration proposal.",
                "allow_search": False,
                "user_id": user_external_id,
                "local_date": local_date,
                "persist_calibration_proposal": True,
            },
        )
        raw_apply_payload = dict(raw_apply_response["payload"])
        raw_apply_manager_decision = dict(raw_apply_payload.get("manager_decision") or {})
        after_raw_apply_plan_snapshot = _active_plan_snapshot(db, user_id=user_id)
        after_raw_apply_ledger_snapshot = _ledger_snapshot(db, user_id=user_id, local_date=local_date)
        after_raw_apply_proposal_status = _proposal_status(db, proposal_container_id)
        after_raw_apply_proposal_count = db.query(ProposalContainerRecord).count()
        before_action_plan_counts = _body_plan_counts(db)
        before_action_plan_snapshot = _active_plan_snapshot(db, user_id=user_id)
        before_action_ledger_snapshot = _ledger_snapshot(db, user_id=user_id, local_date=local_date)
        before_action_ledger_entries = _ledger_entry_snapshot(db, user_id=user_id)
        action_response = _post_json(
            client,
            "/estimate",
            payload={
                "text": "Apply that calibration proposal.",
                "allow_search": False,
                "user_id": user_external_id,
                "local_date": local_date,
                "calibration_proposal_container_id": proposal_container_id,
                "calibration_action": "accept_calibration_proposal",
            },
        )
        action_payload = dict(action_response["payload"])
        action_ui_hints = dict(action_payload.get("ui_hints") or {})
        after_action_plan_counts = _body_plan_counts(db)
        after_action_plan_snapshot = _active_plan_snapshot(db, user_id=user_id)
        after_action_ledger_snapshot = _ledger_snapshot(db, user_id=user_id, local_date=local_date)
        after_action_ledger_entries = _ledger_entry_snapshot(db, user_id=user_id)
        after_action_proposal_status = _proposal_status(db, proposal_container_id)
        inbox_after = _get_json(
            client,
            "/calibration/proposals/open",
            params={"user_id": user_external_id},
        )
        history_after = _get_json(
            client,
            "/calibration/proposals/history",
            params={"user_id": user_external_id},
        )
        current_budget = _get_json(
            client,
            "/today/current-budget",
            params={"user_id": user_external_id, "local_date": local_date},
        )
        active_body_plan = _get_json(
            client,
            "/body-plan/active",
            params={"user_id": user_external_id},
        )
        effective_budget = _get_json(
            client,
            "/today/effective-budget",
            params={"user_id": user_external_id, "local_date": local_date},
        )
        weekly_progress = _get_json(
            client,
            "/today/weekly-progress",
            params={"user_id": user_external_id, "local_date": local_date},
        )
        weekly_current_day = _weekly_current_day(weekly_progress, local_date=local_date)

        ledger_entries = (
            db.execute(select(LedgerEntryRecord).where(LedgerEntryRecord.user_id == user_id))
            .scalars()
            .all()
        )
        calibration_adjustment_entries = [
            entry for entry in ledger_entries if entry.entry_type == "calibration_adjustment"
        ]
        preview_input = dict(preview_payload.get("input_assembly") or {})
        preview_trace = dict(preview_input.get("trace") or {})
        action_result = dict(action_payload.get("calibration_action_result") or {})
        report: dict[str, Any] = {
            "artifact_type": "body_budget_calibration_self_use_journey_smoke",
            "claim_scope": "local_deterministic_body_budget_calibration_smoke",
            "status": "not_evaluated",
            "invariant_blockers": [],
            "user_external_id": user_external_id,
            "local_date": local_date,
            "runtime_truth_changed": "diagnostic_fixture_only",
            "fooddb_truth_changed": False,
            "live_tool_calling": False,
            "automatic_calibration_enabled": False,
            "rescue_enabled": False,
            "recommendation_enabled": False,
            "proactive_enabled": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "proposal_preview": {
                "entrypoint": "/estimate",
                "workflow_effect": preview_payload["manager_decision"]["workflow_effect"],
                "reply_text": preview_response["coach_message"],
                "proposal_surface": bool(preview_ui_hints.get("proposal_surface")),
                "proposal_actions_enabled": bool(preview_ui_hints.get("proposal_actions_enabled")),
                "proposal_container_id": proposal_container_id,
                "proposal_family": preview_ui_hints.get("proposal_family"),
                "calibration_preview_requested": True,
                "persist_calibration_proposal": True,
                "calibration_posture": (preview_payload.get("calibration_diagnostic") or {})
                .get("calibration_result", {})
                .get("calibration_posture"),
                "operating_expenditure_shift_kcal": preview_trace.get("operating_expenditure_shift_kcal"),
                "intake_coverage": preview_trace.get("intake_coverage"),
                "body_observation_count": preview_trace.get("body_observation_count"),
                "weight_delta_kg": preview_trace.get("weight_delta_kg"),
                "plan_mutated": after_preview_plan_snapshot != before_preview_plan_snapshot,
                "ledger_mutated": after_preview_ledger_snapshot != before_preview_ledger_snapshot,
                "ledger_entry_mutated": after_preview_ledger_entries != before_preview_ledger_entries,
                "plan_count_changed": after_preview_plan_counts["total"] != before_preview_plan_counts["total"],
                "ledger_count_changed": after_preview_ledger_count != before_preview_ledger_count,
                "ledger_entry_count_changed": len(after_preview_ledger_entries)
                != len(before_preview_ledger_entries),
                "effect_payload_summary": {
                    "new_daily_budget_kcal": effect_payload.get("new_daily_budget_kcal"),
                    "new_estimated_tdee_kcal": effect_payload.get("new_estimated_tdee_kcal"),
                    "delta_kcal": effect_payload.get("delta_kcal"),
                    "calibration_adjustment_delta_kcal": effect_payload.get("calibration_adjustment_delta_kcal"),
                    "calibration_adjustment_delta_kcal_present": "calibration_adjustment_delta_kcal"
                    in effect_payload,
                },
            },
            "proposal_inbox_before_accept": inbox_before,
            "proposal_history_before_accept": history_before,
            "raw_text_apply_attempt": {
                "entrypoint": "/estimate",
                "workflow_effect": raw_apply_manager_decision.get("workflow_effect"),
                "proposal_status_after_attempt": after_raw_apply_proposal_status,
                "proposal_count_changed": after_raw_apply_proposal_count != before_raw_apply_proposal_count,
                "plan_mutated": after_raw_apply_plan_snapshot != before_raw_apply_plan_snapshot,
                "ledger_mutated": after_raw_apply_ledger_snapshot != before_raw_apply_ledger_snapshot,
                "calibration_preview_requested_supplied": False,
                "persist_calibration_proposal_supplied": True,
                "proposal_container_id_supplied": False,
                "calibration_action_supplied": False,
                "raw_text_authorized_mutation": False,
            },
            "proposal_action": {
                "entrypoint": "/estimate",
                "workflow_effect": action_payload["manager_decision"]["workflow_effect"],
                "reply_text": action_response["coach_message"],
                "proposal_status": action_ui_hints.get("proposal_status"),
                "proposal_container_id": action_ui_hints.get("proposal_container_id"),
                "effective_from": action_ui_hints.get("effective_from"),
                "plan_mutated": bool(action_ui_hints.get("plan_mutation_authorized")),
                "ledger_mutated": bool(action_ui_hints.get("ledger_mutation_authorized")),
                "db_plan_mutated": after_action_plan_snapshot != before_action_plan_snapshot
                and after_action_plan_counts["total"] == before_action_plan_counts["total"] + 1
                and after_action_plan_counts["active"] == 1
                and after_action_plan_counts["superseded"] == before_action_plan_counts["superseded"] + 1,
                "db_ledger_mutated": after_action_ledger_snapshot != before_action_ledger_snapshot,
                "db_ledger_entry_count_changed": len(after_action_ledger_entries)
                != len(before_action_ledger_entries),
                "db_proposal_status": after_action_proposal_status,
                "active_body_plan_id": after_action_plan_snapshot["id"],
                "current_budget_kcal": (action_result.get("current_budget_view") or {}).get("budget_kcal"),
                "active_body_plan_daily_budget_kcal": (action_result.get("active_body_plan_view") or {}).get(
                    "daily_budget_kcal"
                ),
                "active_body_plan_estimated_tdee": (action_result.get("active_body_plan_view") or {}).get(
                    "estimated_tdee"
                ),
                "calibration_adjustment_entry_count": len(calibration_adjustment_entries),
                "calibration_adjustment_delta_kcal": (
                    calibration_adjustment_entries[0].delta_kcal if calibration_adjustment_entries else None
                ),
            },
            "proposal_inbox_after_accept": inbox_after,
            "proposal_history_after_accept": history_after,
            "post_accept_read_model_sync": {
                "body_plan_counts": after_action_plan_counts,
                "current_budget_kcal": current_budget["budget_kcal"],
                "current_budget_consumed_kcal": current_budget["consumed_kcal"],
                "current_budget_remaining_kcal": current_budget["remaining_kcal"],
                "active_body_plan_daily_budget_kcal": active_body_plan["daily_budget_kcal"],
                "active_body_plan_estimated_tdee": active_body_plan["estimated_tdee"],
                "effective_budget_kcal": effective_budget["runtime_effective_budget_kcal"],
                "effective_budget_remaining_kcal": effective_budget["remaining_kcal"],
                "effective_budget_adjustment_total_kcal": effective_budget["runtime_adjustment_total_kcal"],
                "weekly_progress_latest_weight_kg": weekly_progress["latest_weight_kg"],
                "weekly_progress_weight_observation_count": weekly_progress["weight_observation_count"],
                "weekly_progress_estimated_weekly_deficit_kcal": weekly_progress[
                    "estimated_weekly_deficit_kcal"
                ],
                "weekly_progress_current_day_target_kcal": weekly_current_day["active_daily_target_kcal"],
                "weekly_progress_current_day_consumed_kcal": weekly_current_day["consumed_kcal"],
                "weekly_progress_current_day_remaining_kcal": weekly_current_day["remaining_kcal"],
                "calibration_adjustment_entry_count": len(calibration_adjustment_entries),
            },
            "boundaries": {
                "preview_mutation_authority": "proposal_artifact_only",
                "accept_mutation_authority": "explicit_stored_calibration_proposal_action",
                "history_projection_safe_before_accept": _history_projection_safe(history_before),
                "history_projection_safe_after_accept": _history_projection_safe(history_after),
                "manager_context_packet_changed": False,
                "fooddb_changed": False,
                "live_provider_used": False,
            },
        }
        blockers = _evaluate_invariants(report)
        report["invariant_blockers"] = blockers
        report["status"] = "fail" if blockers else "pass"
        if output_path is not None:
            write_json_artifact(output_path, report)
        return report
    finally:
        restore_route_fallback()
        db.close()
        engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the BodyBudget calibration local self-use journey smoke.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--user-id", default=DEFAULT_USER_ID)
    parser.add_argument("--local-date", default=DEFAULT_LOCAL_DATE)
    parser.add_argument("--reset-db", dest="reset_db", action="store_true", default=True)
    parser.add_argument("--keep-db", dest="reset_db", action="store_false")
    args = parser.parse_args(argv)

    output = Path(args.output)
    report = build_body_budget_calibration_self_use_journey_report(
        db_path=Path(args.db_path),
        output_path=output,
        user_external_id=args.user_id,
        local_date=args.local_date,
        reset_db=bool(args.reset_db),
    )
    print(json.dumps({"artifact": str(output), "status": report["status"]}, ensure_ascii=False))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
