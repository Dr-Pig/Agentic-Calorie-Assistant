from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.application.canonical_commit_bridge import (
    apply_proposal_acceptance_skeleton,
    apply_rescue_overlay_skeleton,
    build_commit_request_candidate,
    commit_request_candidate_to_canonical,
    record_body_observation_skeleton,
    resolve_commit_candidate_target,
)
from app.infrastructure.canonical_persistence import (
    ensure_proactive_trigger_skeleton,
    load_active_meal_version,
    recompute_day_budget_ledger,
)
from app.infrastructure.meal_log_persistence import persist_text_meal_result
from app.infrastructure.schema_reset_export import export_schema_reset_snapshot
from app.application.text_meal_commit_service import persist_text_meal_payload
from app.application.stage_trace_runtime import append_stage_runtime_event
from app.models import (
    Base,
    BodyObservationRecord,
    BodyPlanRecord,
    DayBudgetLedgerRecord,
    LedgerEntryRecord,
    MealLog,
    MealThreadRecord,
    MealVersionRecord,
    ProposalContainerRecord,
    ProactiveTriggerRecord,
    User,
)
from app.observability.stage_trace_store import read_stage_trace_events
from app.schemas import ComponentEstimate, EstimatePayload


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return TestingSession()


def _user(db: Session) -> User:
    user = User(user_id="test-user")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _payload(*, request_id: str, title: str, kcal: int, protein: int = 10) -> EstimatePayload:
    return EstimatePayload(
        request_id=request_id,
        meal_title=title,
        estimated_kcal=kcal,
        protein_g=protein,
        carb_g=20,
        fat_g=5,
        route_target="best_effort_answer",
        action_taken="direct_answer",
        reply_text=f"{title} ok",
        quality_signals={"estimate_mode": "exact_item"},
        trace_contract={"local_date": "2026-04-11"},
        boundary_trace={},
        component_estimates=[
            ComponentEstimate(
                name=title,
                quantity_hint="1 serving",
                estimated_kcal=kcal,
                protein_g=protein,
                carb_g=20,
                fat_g=5,
            )
        ],
    )


def test_persist_text_meal_result_writes_canonical_thread_version_and_ledger() -> None:
    db = _session()
    user = _user(db)

    result = persist_text_meal_result(
        db,
        user=user,
        latest_log=None,
        planner_intent="food_estimation",
        payload=_payload(request_id="req-1", title="chicken bowl", kcal=520),
        raw_input="chicken bowl",
        request_id="req-1",
    )

    canonical_commit = result["canonical_commit"]
    assert canonical_commit is not None
    thread = db.get(MealThreadRecord, canonical_commit["meal_thread_id"])
    assert thread is not None
    assert thread.active_version_id == canonical_commit["meal_version_id"]

    version = db.get(MealVersionRecord, canonical_commit["meal_version_id"])
    assert version is not None
    assert version.total_kcal == 520
    assert version.local_date == "2026-04-11"

    ledger = db.execute(
        select(DayBudgetLedgerRecord).where(
            DayBudgetLedgerRecord.user_id == user.id,
            DayBudgetLedgerRecord.local_date == "2026-04-11",
        )
    ).scalar_one()
    assert ledger.consumed_kcal == 520


def test_modification_supersedes_active_version_in_canonical_thread() -> None:
    db = _session()
    user = _user(db)

    first = persist_text_meal_result(
        db,
        user=user,
        latest_log=None,
        planner_intent="food_estimation",
        payload=_payload(request_id="req-1", title="beef bowl", kcal=600),
        raw_input="beef bowl",
        request_id="req-1",
    )
    first_log_id = first["persisted_log_id"]
    latest_log = db.get(MealLog, first_log_id)

    second = persist_text_meal_result(
        db,
        user=user,
        latest_log=latest_log,
        planner_intent="modification",
        payload=_payload(request_id="req-2", title="beef bowl no sauce", kcal=480),
        raw_input="beef bowl no sauce",
        request_id="req-2",
    )

    canonical_commit = second["canonical_commit"]
    assert canonical_commit is not None
    active_version = load_active_meal_version(db, canonical_commit["meal_thread_id"])
    assert active_version is not None
    assert active_version.id == canonical_commit["meal_version_id"]
    assert canonical_commit["superseded_version_id"] is not None

    old_version = db.get(MealVersionRecord, canonical_commit["superseded_version_id"])
    assert old_version is not None
    assert old_version.version_status == "superseded"

    ledger = db.execute(
        select(DayBudgetLedgerRecord).where(
            DayBudgetLedgerRecord.user_id == user.id,
            DayBudgetLedgerRecord.local_date == "2026-04-11",
        )
    ).scalar_one()
    assert ledger.consumed_kcal == 480


def test_explicit_parent_version_candidate_controls_historical_correction_target() -> None:
    db = _session()
    user = _user(db)

    first = persist_text_meal_result(
        db,
        user=user,
        latest_log=None,
        planner_intent="food_estimation",
        payload=_payload(request_id="req-a", title="rice bowl", kcal=700),
        raw_input="rice bowl",
        request_id="req-a",
    )
    original_thread_id = first["canonical_commit"]["meal_thread_id"]
    original_version_id = first["canonical_commit"]["meal_version_id"]

    second = persist_text_meal_result(
        db,
        user=user,
        latest_log=None,
        planner_intent="food_estimation",
        payload=_payload(request_id="req-b", title="salad bowl", kcal=300),
        raw_input="salad bowl",
        request_id="req-b",
    )
    assert second["canonical_commit"]["meal_thread_id"] != original_thread_id

    from app.application.canonical_commit_bridge import build_commit_request_candidate, commit_request_candidate_to_canonical

    correction_payload = _payload(request_id="req-c", title="rice bowl corrected", kcal=640)
    candidate = build_commit_request_candidate(
        payload=correction_payload,
        raw_input="rice bowl corrected",
        planner_intent="correction",
        request_id="req-c",
        meal_thread_id=original_thread_id,
        parent_version_id=original_version_id,
    )

    commit = commit_request_candidate_to_canonical(
        db,
        user=user,
        candidate=candidate,
    )

    assert commit is not None
    assert commit.meal_thread_id == original_thread_id
    assert commit.superseded_version_id == original_version_id

    active_version = load_active_meal_version(db, original_thread_id)
    assert active_version is not None
    assert active_version.total_kcal == 640

    ledger = db.execute(
        select(DayBudgetLedgerRecord).where(
            DayBudgetLedgerRecord.user_id == user.id,
            DayBudgetLedgerRecord.local_date == "2026-04-11",
        )
    ).scalar_one()
    assert ledger.consumed_kcal == 940


def test_historical_correction_target_resolution_prefers_active_supersession_target() -> None:
    db = _session()
    user = _user(db)

    first = persist_text_meal_result(
        db,
        user=user,
        latest_log=None,
        planner_intent="food_estimation",
        payload=_payload(request_id="req-hist-1", title="salmon bowl", kcal=540),
        raw_input="salmon bowl",
        request_id="req-hist-1",
    )
    first_thread_id = first["canonical_commit"]["meal_thread_id"]
    first_version_id = first["canonical_commit"]["meal_version_id"]
    first_log = db.get(MealLog, first["persisted_log_id"])
    assert first_log is not None

    second = persist_text_meal_result(
        db,
        user=user,
        latest_log=first_log,
        planner_intent="modification",
        payload=_payload(request_id="req-hist-2", title="salmon bowl extra rice", kcal=620),
        raw_input="salmon bowl extra rice",
        request_id="req-hist-2",
    )
    second_version_id = second["canonical_commit"]["meal_version_id"]
    assert second["canonical_commit"]["superseded_version_id"] == first_version_id

    correction_payload = _payload(request_id="req-hist-3", title="salmon bowl corrected", kcal=560)
    candidate = build_commit_request_candidate(
        payload=correction_payload,
        raw_input="salmon bowl corrected",
        planner_intent="correction",
        request_id="req-hist-3",
        meal_thread_id=first_thread_id,
        parent_version_id=first_version_id,
        version_reason="historical_correction",
    )

    resolved_target = resolve_commit_candidate_target(db, candidate=candidate)
    assert resolved_target.meal_thread_id == first_thread_id
    assert resolved_target.parent_version_id == first_version_id
    assert resolved_target.correction_target_version_id == first_version_id
    assert resolved_target.superseded_version_id == second_version_id
    assert resolved_target.version_reason == "historical_correction"


def test_historical_correction_supersedes_current_active_version() -> None:
    db = _session()
    user = _user(db)

    first = persist_text_meal_result(
        db,
        user=user,
        latest_log=None,
        planner_intent="food_estimation",
        payload=_payload(request_id="req-corr-1", title="noodle soup", kcal=430),
        raw_input="noodle soup",
        request_id="req-corr-1",
    )
    first_thread_id = first["canonical_commit"]["meal_thread_id"]
    first_version_id = first["canonical_commit"]["meal_version_id"]
    first_log = db.get(MealLog, first["persisted_log_id"])
    assert first_log is not None

    second = persist_text_meal_result(
        db,
        user=user,
        latest_log=first_log,
        planner_intent="modification",
        payload=_payload(request_id="req-corr-2", title="noodle soup larger", kcal=510),
        raw_input="noodle soup larger",
        request_id="req-corr-2",
    )
    second_version_id = second["canonical_commit"]["meal_version_id"]

    correction_payload = _payload(request_id="req-corr-3", title="noodle soup corrected", kcal=470)
    candidate = build_commit_request_candidate(
        payload=correction_payload,
        raw_input="noodle soup corrected",
        planner_intent="correction",
        request_id="req-corr-3",
        meal_thread_id=first_thread_id,
        parent_version_id=first_version_id,
        version_reason="historical_correction",
    )

    commit = commit_request_candidate_to_canonical(
        db,
        user=user,
        candidate=candidate,
    )

    assert commit is not None
    assert commit.meal_thread_id == first_thread_id
    assert commit.superseded_version_id == second_version_id

    first_version = db.get(MealVersionRecord, first_version_id)
    second_version = db.get(MealVersionRecord, second_version_id)
    new_version = db.get(MealVersionRecord, commit.meal_version_id)
    assert first_version is not None and first_version.version_status == "superseded"
    assert second_version is not None and second_version.version_status == "superseded"
    assert new_version is not None and new_version.version_reason == "historical_correction"
    assert new_version.parent_version_id == first_version_id


def test_ledger_recompute_and_rescue_overlay_skeleton() -> None:
    db = _session()
    user = _user(db)

    entry = apply_rescue_overlay_skeleton(
        db,
        user=user,
        local_date="2026-04-11",
        delta_kcal=-120,
        budget_kcal=1800,
    )
    ledger = recompute_day_budget_ledger(db, user_id=user.id, local_date="2026-04-11", budget_kcal=1800)

    assert isinstance(entry, LedgerEntryRecord)
    assert ledger.adjustment_kcal == -120
    assert ledger.remaining_kcal == 1920


def test_body_plan_proposal_observation_and_proactive_skeletons_are_writable() -> None:
    db = _session()
    user = _user(db)

    proposal = apply_proposal_acceptance_skeleton(
        db,
        user=user,
        proposal_type="budget_adjustment",
        option_type="budget_adjustment",
        option_label="Lower by 150 kcal",
        estimated_tdee=2200,
        daily_budget_kcal=1800,
        safety_floor_kcal=1500,
    )
    observation_id = record_body_observation_skeleton(
        db,
        user=user,
        value=72.4,
        unit="kg",
        observed_at=datetime(2026, 4, 11, 7, 30, 0),
        local_date="2026-04-11",
    )
    proactive = ensure_proactive_trigger_skeleton(db, user=user, trigger_type="calibration_check")

    assert proposal["proposal_container_id"] is not None
    assert db.get(ProposalContainerRecord, proposal["proposal_container_id"]) is not None
    body_plan = db.get(BodyPlanRecord, proposal["body_plan_id"])
    assert body_plan is not None
    assert body_plan.safety_floor_kcal == 1500
    assert db.get(BodyObservationRecord, observation_id) is not None
    assert isinstance(proactive, ProactiveTriggerRecord)


def test_body_plan_persists_safety_floor_kcal() -> None:
    db = _session()
    user = _user(db)

    proposal = apply_proposal_acceptance_skeleton(
        db,
        user=user,
        proposal_type="budget_adjustment",
        option_type="budget_adjustment",
        option_label="Lower by 150 kcal",
        estimated_tdee=2200,
        daily_budget_kcal=1800,
        safety_floor_kcal=1500,
    )

    body_plan = db.get(BodyPlanRecord, proposal["body_plan_id"])
    assert body_plan is not None
    assert body_plan.plan_status == "active"
    assert body_plan.safety_floor_kcal == 1500


def test_stage_trace_store_appends_and_reads_events() -> None:
    request_id = "stage-trace-test"
    class FakeProvider:
        role_label = "primary"

        def readiness(self) -> dict[str, str]:
            return {"provider": "builderspace", "role": "primary"}

    append_stage_runtime_event(
        request_id=request_id,
        stage="decision_pass",
        provider=FakeProvider(),
        merged_trace={"attempt_index": 1, "model": "grok-4-fast"},
    )
    events = read_stage_trace_events(request_id)
    assert events
    assert events[-1]["stage"] == "decision_pass"
    assert events[-1]["logical_model_role"] == "fast_router_model"


def test_export_schema_reset_snapshot_writes_schema_and_sample_rows(tmp_path: Path) -> None:
    db = _session()
    user = _user(db)
    persist_text_meal_result(
        db,
        user=user,
        latest_log=None,
        planner_intent="food_estimation",
        payload=_payload(request_id="req-export", title="salmon rice", kcal=640),
        raw_input="salmon rice",
        request_id="req-export",
    )

    export_dir = export_schema_reset_snapshot(db, output_root=tmp_path, label="phase1-test", sample_limit=10)

    assert (export_dir / "metadata.json").exists()
    assert (export_dir / "schema.json").exists()
    assert (export_dir / "sample_rows.json").exists()

    metadata = json.loads((export_dir / "metadata.json").read_text(encoding="utf-8"))
    samples = json.loads((export_dir / "sample_rows.json").read_text(encoding="utf-8"))
    assert "meal_logs" in metadata["legacy_tables"]
    assert "meal_threads" in metadata["canonical_tables"]
    assert samples["meal_logs"]
    assert samples["meal_threads"]


def test_persist_text_meal_payload_records_commit_request_candidate() -> None:
    db = _session()
    user = _user(db)
    payload = _payload(request_id="req-typed", title="tuna sandwich", kcal=410)

    result = persist_text_meal_payload(
        db=db,
        user=user,
        latest_log=None,
        planner_intent="food_estimation",
        payload=payload,
        raw_input="tuna sandwich",
        request_id="req-typed",
        incoming_user_message_id=None,
        conversation_state=type("State", (), {"boundary_clarification_open": False})(),
        planner_result=type("Planner", (), {"meal_boundary": "start_new_meal"})(),
    )

    assert result["canonical_commit"] is not None
    candidate = payload.trace_contract["commit_request_candidate"]
    assert candidate["commit_kind"] == "meal_commit"
    assert candidate["meal_title"] == "tuna sandwich"
    assert candidate["estimated_kcal"] == 410
