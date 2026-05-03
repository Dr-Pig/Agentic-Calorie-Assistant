from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_debug_routes import build_accurate_intake_debug_payload
from app.composition.canonical_body_support import ensure_body_plan_skeleton, recompute_day_budget_ledger
from app.composition.canonical_persistence import commit_meal_payload_to_canonical
from app.composition.current_budget_answer import build_remaining_budget_answer_contract
from app.budget.infrastructure.models import LedgerEntryRecord
from app.database import get_or_create_user
from app.intake.infrastructure.models import MealItemRecord
from app.models import Base
from app.schemas import CommitRequestCandidate, MealItemPayload
from app.shared.infra.models import User

DEFAULT_ARTIFACT_PATH = ROOT / "artifacts" / "accurate_intake_mvp_self_use_smoke.json"
DEFAULT_DB_PATH = ROOT / "artifacts" / "accurate_intake_mvp_self_use_smoke.sqlite3"
DEFAULT_SCENARIO_WALL_ARTIFACT_PATH = ROOT / "artifacts" / "accurate_intake_mvp_self_use_scenario_wall.json"
DEFAULT_REOPEN_CONTINUITY_ARTIFACT_PATH = ROOT / "artifacts" / "accurate_intake_mvp_reopen_continuity.json"
DEFAULT_ONE_DAY_SCENARIO_WALL_ARTIFACT_PATH = ROOT / "artifacts" / "accurate_intake_one_day_self_use_wall.json"

_NOT_CLAIMING = [
    "product_ready",
    "rollout_ready",
    "live_llm_ready",
    "web_ready",
    "production_db_ready",
]


def _session_factory(db_path: Path) -> sessionmaker[Session]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _initial_candidate(*, local_date: str) -> CommitRequestCandidate:
    return CommitRequestCandidate(
        request_id="self-use-smoke-initial",
        manager_intent="food_estimation",
        version_reason="new_intake",
        meal_title="chicken rice and soup",
        raw_input="chicken rice and soup",
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
    )


def _correction_candidate(*, local_date: str, meal_thread_id: int, meal_item_id: int) -> CommitRequestCandidate:
    return CommitRequestCandidate(
        request_id="self-use-smoke-correction",
        manager_intent="food_estimation",
        meal_thread_id=meal_thread_id,
        version_reason="correction",
        meal_title="chicken rice and soup",
        raw_input="the chicken rice was smaller",
        estimated_kcal=470,
        protein_g=30,
        carb_g=55,
        fat_g=12,
        resolution_status="completed_meal",
        local_date=local_date,
        items=[MealItemPayload(name="chicken rice", estimated_kcal=320, protein_g=27, carb_g=50, fat_g=9)],
        trace_ref={
            "correction_target_ref": {
                "meal_thread_id": meal_thread_id,
                "meal_item_id": meal_item_id,
                "canonical_name": "chicken rice",
            }
        },
    )


def _removal_candidate(*, local_date: str, meal_thread_id: int, meal_item_id: int) -> CommitRequestCandidate:
    return CommitRequestCandidate(
        request_id="self-use-smoke-removal",
        manager_intent="food_estimation",
        meal_thread_id=meal_thread_id,
        version_reason="correction",
        meal_title="chicken rice and soup",
        raw_input="remove the chicken rice",
        estimated_kcal=150,
        protein_g=3,
        carb_g=5,
        fat_g=3,
        resolution_status="completed_meal",
        local_date=local_date,
        items=[],
        trace_ref={
            "correction_operation": "remove_item",
            "correction_target_ref": {
                "meal_thread_id": meal_thread_id,
                "meal_item_id": meal_item_id,
                "canonical_name": "chicken rice",
            },
        },
    )


def _candidate(
    *,
    request_id: str,
    meal_title: str,
    raw_input: str,
    estimated_kcal: int,
    local_date: str,
    items: list[MealItemPayload],
    meal_thread_id: int | None = None,
    version_reason: str = "new_intake",
    trace_ref: dict[str, Any] | None = None,
) -> CommitRequestCandidate:
    return CommitRequestCandidate(
        request_id=request_id,
        manager_intent="food_estimation",
        meal_thread_id=meal_thread_id,
        version_reason=version_reason,  # type: ignore[arg-type]
        meal_title=meal_title,
        raw_input=raw_input,
        estimated_kcal=estimated_kcal,
        protein_g=sum(int(item.protein_g or 0) for item in items),
        carb_g=sum(int(item.carb_g or 0) for item in items),
        fat_g=sum(int(item.fat_g or 0) for item in items),
        resolution_status="completed_meal",
        local_date=local_date,
        items=list(items),
        trace_ref=dict(trace_ref or {}),
    )


def _meal_item(
    name: str,
    kcal: int,
    *,
    protein_g: int = 0,
    carb_g: int = 0,
    fat_g: int = 0,
    quantity_hint: str | None = None,
) -> MealItemPayload:
    return MealItemPayload(
        name=name,
        quantity_hint=quantity_hint,
        source="lookup",
        evidence_role="ingredient_anchor",
        estimate_basis="anchored",
        confidence_tier="medium",
        estimated_kcal=kcal,
        protein_g=protein_g,
        carb_g=carb_g,
        fat_g=fat_g,
        evidence_ids=[f"local_seed:{name}"],
    )


def _manager_fixture(
    *,
    intent_type: str,
    workflow_effect: str,
    final_action: str,
    target_attachment: dict[str, Any] | None = None,
    follow_up_posture: str | None = None,
) -> dict[str, Any]:
    payload = {
        "source": "deterministic_manager_structured_fixture",
        "intent_type": intent_type,
        "workflow_effect": workflow_effect,
        "final_action": final_action,
        "semantic_decision": {"current_turn_intent": intent_type},
        "target_attachment": dict(target_attachment or {"attachment_kind": "none"}),
    }
    if follow_up_posture:
        payload["follow_up_posture"] = follow_up_posture
    return payload


def _seed_local_active_budget_fixture(
    db: Session,
    *,
    user: User,
    local_date: str,
    budget_kcal: int,
) -> None:
    ensure_body_plan_skeleton(
        db,
        user=user,
        estimated_tdee=budget_kcal,
        daily_budget_kcal=budget_kcal,
        safety_floor_kcal=1500,
    )
    recompute_day_budget_ledger(db, user_id=user.id, local_date=local_date, budget_kcal=budget_kcal)


def _runtime_validation(*, deterministic_role: str = "validate_reject_or_compute_state_truth") -> dict[str, Any]:
    return {
        "deterministic_role": deterministic_role,
        "accepted_authorities": [
            "manager_structured_decision",
            "canonical_state",
            "accepted_evidence_packet",
        ],
        "forbidden_authorities": [
            "raw_text_keyword_route",
            "food_seed_disposition",
            "runner_fabricated_semantics",
        ],
    }


def _turn(
    *,
    turn: int,
    raw_user_input: str,
    manager_decision: dict[str, Any],
    commit_result: dict[str, Any],
    runtime_validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "turn": turn,
        "raw_user_input": raw_user_input,
        "runner_inferred_semantics": False,
        "manager_decision": manager_decision,
        "runtime_validation": runtime_validation or _runtime_validation(),
        "commit_result": commit_result,
    }


def _commit_result_payload(result: Any | None, *, mutation_applied: bool) -> dict[str, Any]:
    if result is None:
        return {"mutation_applied": False}
    return {
        "mutation_applied": mutation_applied,
        "meal_thread_id": result.meal_thread_id,
        "meal_version_id": result.meal_version_id,
        "active_version_id": result.active_version_id,
        "consumed_kcal": result.consumed_kcal,
        "ledger_entry_id": result.ledger_entry_id,
    }


def _ledger_event_count(db: Session, *, user_id: int, local_date: str) -> int:
    return len(
        db.execute(
            select(LedgerEntryRecord).where(
                LedgerEntryRecord.user_id == user_id,
                LedgerEntryRecord.local_date == local_date,
            )
        ).scalars().all()
    )


def _lookup_user(db: Session, user_external_id: str) -> User | None:
    return db.query(User).filter(User.user_id == user_external_id).first()


def _first_item_id(db: Session, *, meal_version_id: int, name: str | None = None) -> int:
    query = select(MealItemRecord).where(MealItemRecord.meal_version_id == meal_version_id)
    if name is not None:
        query = query.where(MealItemRecord.name == name)
    item = db.execute(query.order_by(MealItemRecord.item_index.asc(), MealItemRecord.id.asc())).scalars().first()
    if item is None:
        raise RuntimeError("self_use_scenario_target_item_missing")
    return int(item.id)


def _debug(db: Session, *, user_external_id: str, local_date: str) -> dict[str, Any]:
    return build_accurate_intake_debug_payload(db, user_external_id=user_external_id, local_date=local_date)


def _state_summary(debug_payload: dict[str, Any]) -> dict[str, Any]:
    model = dict(debug_payload.get("model") or {})
    same_truth = dict(model.get("same_truth") or {})
    return {
        "today_summary": dict(model.get("today_summary") or {}),
        "meal_thread_count": len(list(model.get("meal_threads") or [])),
        "pending_draft_count": len(list(model.get("pending_drafts") or [])),
        "same_truth_status": same_truth.get("status"),
    }


def _operator_turn_summary(turn: dict[str, Any]) -> dict[str, Any]:
    manager_decision = dict(turn.get("manager_decision") or {})
    runtime_validation = dict(turn.get("runtime_validation") or {})
    commit_result = dict(turn.get("commit_result") or {})
    summary = {
        "turn": turn.get("turn"),
        "raw_user_input": turn.get("raw_user_input"),
        "manager_intent": manager_decision.get("intent_type"),
        "workflow_effect": manager_decision.get("workflow_effect"),
        "final_action": manager_decision.get("final_action"),
        "target_attachment": dict(manager_decision.get("target_attachment") or {}),
        "deterministic_role": runtime_validation.get("deterministic_role"),
        "runner_inferred_semantics": turn.get("runner_inferred_semantics"),
        "mutation_applied": bool(commit_result.get("mutation_applied")),
    }
    if "consumed_kcal" in commit_result:
        summary["consumed_kcal"] = commit_result["consumed_kcal"]
    if "no_mutation_reason" in commit_result:
        summary["no_mutation_reason"] = commit_result["no_mutation_reason"]
    return summary


def _operator_scenario_summary(scenario: dict[str, Any]) -> dict[str, Any]:
    state_after = dict(scenario.get("state_after") or {})
    summary = {
        "scenario_id": scenario.get("scenario_id"),
        "status": scenario.get("status"),
        "turn_count": len(list(scenario.get("turns") or [])),
        "same_truth_status": state_after.get("same_truth_status"),
        "state_before": dict(scenario.get("state_before") or {}),
        "state_after": state_after,
        "turns": [_operator_turn_summary(dict(turn)) for turn in list(scenario.get("turns") or [])],
    }
    if "answer_contract" in scenario:
        summary["answer_contract"] = dict(scenario.get("answer_contract") or {})
    return summary


def _operator_transcript(scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "view_id": "accurate_intake_mvp_operator_transcript_v1",
        "read_only": True,
        "truth_source": "scenario_wall_v2_existing_evidence",
        "runner_inferred_semantics": False,
        "scenario_count": len(scenarios),
        "not_claiming": list(_NOT_CLAIMING),
        "canonical_truth_surfaces": [
            "scenario.state_before",
            "scenario.state_after",
            "scenario.final_debug_surface.model.today_summary",
            "scenario.final_debug_surface.model.same_truth",
        ],
        "scenario_summaries": [_operator_scenario_summary(scenario) for scenario in scenarios],
    }


_REOPEN_EXPECTATIONS: list[dict[str, Any]] = [
    {
        "scenario_id": "chinese_chicken_rice_correction_removal_debug",
        "user_external_id": "self-use-v2-chicken",
        "consumed_kcal": 320,
        "remaining_kcal": 1480,
        "ledger_event_count": 3,
        "active_item_names": ["雞肉飯"],
        "removed_item_names": ["湯"],
    },
    {
        "scenario_id": "bubble_milk_tea_refinement",
        "user_external_id": "self-use-v2-bubble-tea",
        "consumed_kcal": 520,
        "remaining_kcal": 1280,
        "ledger_event_count": 2,
        "active_item_names": ["珍珠奶茶"],
        "removed_item_names": [],
    },
    {
        "scenario_id": "luwei_draft_to_listed_basket",
        "user_external_id": "self-use-v2-luwei",
        "consumed_kcal": 420,
        "remaining_kcal": 1380,
        "ledger_event_count": 1,
        "active_item_names": ["豆干", "海帶", "貢丸"],
        "removed_item_names": [],
    },
    {
        "scenario_id": "query_only_today_consumed",
        "user_external_id": "self-use-v2-query",
        "consumed_kcal": 500,
        "remaining_kcal": 1300,
        "ledger_event_count": 1,
        "active_item_names": ["雞腿便當"],
        "removed_item_names": [],
    },
    {
        "scenario_id": "no_plan_consumed_without_target_or_remaining",
        "user_external_id": "self-use-v2-no-plan",
        "consumed_kcal": 420,
        "remaining_kcal": None,
        "ledger_event_count": 1,
        "active_item_names": ["三明治"],
        "removed_item_names": [],
        "today_status": "onboarding_required",
    },
]


def _active_item_names(debug_payload: dict[str, Any]) -> list[str]:
    model = dict(debug_payload.get("model") or {})
    meal_threads = list(model.get("meal_threads") or [])
    if not meal_threads:
        return []
    active_version = dict(dict(meal_threads[0]).get("active_version") or {})
    return [str(item.get("name")) for item in list(active_version.get("items") or [])]


def _removed_item_names(debug_payload: dict[str, Any]) -> list[str]:
    model = dict(debug_payload.get("model") or {})
    correction_history = list(model.get("correction_history") or [])
    if not correction_history:
        return []
    return list(dict(correction_history[-1]).get("removed_item_names") or [])


def _reopen_continuity_scenario(db: Session, *, expectation: dict[str, Any], local_date: str) -> dict[str, Any]:
    user_external_id = str(expectation["user_external_id"])
    user = _lookup_user(db, user_external_id)
    debug_surface = _debug(db, user_external_id=user_external_id, local_date=local_date)
    state_after = _state_summary(debug_surface)
    today = dict(state_after.get("today_summary") or {})
    active_item_names = _active_item_names(debug_surface)
    removed_item_names = _removed_item_names(debug_surface)
    ledger_count = _ledger_event_count(db, user_id=user.id, local_date=local_date) if user is not None else 0
    blockers: list[str] = []
    if user is None:
        blockers.append("missing_reopened_user")
    if today.get("consumed_kcal") != expectation.get("consumed_kcal"):
        blockers.append("consumed_kcal_reopen_mismatch")
    if today.get("remaining_kcal") != expectation.get("remaining_kcal"):
        blockers.append("remaining_kcal_reopen_mismatch")
    if expectation.get("today_status") and today.get("status") != expectation.get("today_status"):
        blockers.append("today_status_reopen_mismatch")
    if ledger_count != expectation.get("ledger_event_count"):
        blockers.append("ledger_event_count_reopen_mismatch")
    if active_item_names != expectation.get("active_item_names"):
        blockers.append("active_item_names_reopen_mismatch")
    if removed_item_names != expectation.get("removed_item_names"):
        blockers.append("removed_item_names_reopen_mismatch")
    if state_after.get("same_truth_status") != "pass":
        blockers.append("same_truth_reopen_failed")
    return {
        "scenario_id": expectation["scenario_id"],
        "user_external_id": user_external_id,
        "status": "pass" if not blockers else "fail",
        "blockers": blockers,
        "read_only": True,
        "mutation_applied": False,
        "state_after_reopen": state_after,
        "ledger_event_count_after_reopen": ledger_count,
        "active_item_names_after_reopen": active_item_names,
        "removed_item_names_after_reopen": removed_item_names,
        "debug_surface": debug_surface,
    }


def build_self_use_reopen_continuity_report(
    *,
    db_path: Path,
    local_date: str = "2026-05-02",
) -> dict[str, Any]:
    SessionLocal = _session_factory(db_path)
    with SessionLocal() as db:
        scenarios = [
            _reopen_continuity_scenario(db, expectation=expectation, local_date=local_date)
            for expectation in _REOPEN_EXPECTATIONS
        ]
    blockers = [
        f"{scenario['scenario_id']}:{blocker}"
        for scenario in scenarios
        for blocker in list(scenario.get("blockers") or [])
    ]
    ledger_event_count_total = sum(int(scenario.get("ledger_event_count_after_reopen") or 0) for scenario in scenarios)
    return {
        "artifact_schema_version": "1.0",
        "continuity_id": "accurate_intake_mvp_reopen_continuity_v1",
        "claim_scope": "local_deterministic_mvp_gate",
        "status": "pass" if not blockers else "fail",
        "blockers": blockers,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "not_claiming": list(_NOT_CLAIMING),
        "read_only": True,
        "mutation_applied": False,
        "product_readiness_claimed": False,
        "live_llm_invoked": False,
        "web_tavily_invoked": False,
        "production_db_used": False,
        "user_facing_rollout": False,
        "db_mode": "reopen_existing_local_sqlite",
        "local_date": local_date,
        "summary": {
            "scenario_count": len(scenarios),
            "pass_count": sum(1 for scenario in scenarios if scenario.get("status") == "pass"),
            "fail_count": sum(1 for scenario in scenarios if scenario.get("status") != "pass"),
            "ledger_event_count_total": ledger_event_count_total,
        },
        "scenarios": scenarios,
    }


def _scenario_chicken_correction_removal(db: Session, *, local_date: str) -> dict[str, Any]:
    user_external_id = "self-use-v2-chicken"
    user = get_or_create_user(db, user_external_id)
    state_before = _state_summary(_debug(db, user_external_id=user_external_id, local_date=local_date))
    initial = commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=_candidate(
            request_id="self-use-v2-chicken-initial",
            meal_title="雞肉飯和湯",
            raw_input="我吃了雞肉飯和湯",
            estimated_kcal=650,
            local_date=local_date,
            items=[
                _meal_item("雞肉飯", 500, protein_g=32, carb_g=65, fat_g=15),
                _meal_item("湯", 150, protein_g=3, carb_g=5, fat_g=3),
            ],
        ),
        budget_kcal=1800,
    )
    if initial is None:
        raise RuntimeError("self_use_v2_chicken_initial_failed")
    chicken_item_id = _first_item_id(db, meal_version_id=initial.meal_version_id, name="雞肉飯")
    correction = commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=_candidate(
            request_id="self-use-v2-chicken-correction",
            meal_thread_id=initial.meal_thread_id,
            version_reason="correction",
            meal_title="雞肉飯和湯",
            raw_input="雞肉飯少一點",
            estimated_kcal=470,
            local_date=local_date,
            items=[_meal_item("雞肉飯", 320, protein_g=27, carb_g=50, fat_g=9)],
            trace_ref={
                "correction_target_ref": {
                    "meal_thread_id": initial.meal_thread_id,
                    "meal_item_id": chicken_item_id,
                    "canonical_name": "雞肉飯",
                }
            },
        ),
        budget_kcal=1800,
    )
    if correction is None:
        raise RuntimeError("self_use_v2_chicken_correction_failed")
    soup_item_id = _first_item_id(db, meal_version_id=correction.meal_version_id, name="湯")
    removal = commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=_candidate(
            request_id="self-use-v2-chicken-removal",
            meal_thread_id=initial.meal_thread_id,
            version_reason="correction",
            meal_title="雞肉飯和湯",
            raw_input="把湯拿掉",
            estimated_kcal=320,
            local_date=local_date,
            items=[],
            trace_ref={
                "correction_operation": "remove_item",
                "correction_target_ref": {
                    "meal_thread_id": initial.meal_thread_id,
                    "meal_item_id": soup_item_id,
                    "canonical_name": "湯",
                },
            },
        ),
        budget_kcal=1800,
    )
    if removal is None:
        raise RuntimeError("self_use_v2_chicken_removal_failed")
    final_debug_surface = _debug(db, user_external_id=user_external_id, local_date=local_date)
    return {
        "scenario_id": "chinese_chicken_rice_correction_removal_debug",
        "status": "pass",
        "turns": [
            _turn(
                turn=1,
                raw_user_input="我吃了雞肉飯和湯",
                manager_decision=_manager_fixture(
                    intent_type="log_meal",
                    workflow_effect="new_meal_commit",
                    final_action="commit_logged_estimate",
                ),
                commit_result=_commit_result_payload(initial, mutation_applied=True),
            ),
            _turn(
                turn=2,
                raw_user_input="雞肉飯少一點",
                manager_decision=_manager_fixture(
                    intent_type="correct_meal",
                    workflow_effect="correction_replace_item",
                    final_action="commit_correction",
                    target_attachment={"attachment_kind": "explicit_item_target", "canonical_name": "雞肉飯"},
                ),
                commit_result=_commit_result_payload(correction, mutation_applied=True),
            ),
            _turn(
                turn=3,
                raw_user_input="把湯拿掉",
                manager_decision=_manager_fixture(
                    intent_type="correct_meal",
                    workflow_effect="correction_remove_item",
                    final_action="commit_correction",
                    target_attachment={"attachment_kind": "explicit_item_target", "canonical_name": "湯"},
                ),
                commit_result=_commit_result_payload(removal, mutation_applied=True),
            ),
            _turn(
                turn=4,
                raw_user_input="看目前狀態",
                manager_decision=_manager_fixture(
                    intent_type="debug_read",
                    workflow_effect="read_only_debug",
                    final_action="no_mutation",
                ),
                runtime_validation=_runtime_validation(deterministic_role="read_canonical_state_only"),
                commit_result={"mutation_applied": False},
            ),
        ],
        "state_delta": {"mutation_applied": True},
        "state_before": state_before,
        "state_after": _state_summary(final_debug_surface),
        "final_debug_surface": final_debug_surface,
    }


def _scenario_bubble_refinement(db: Session, *, local_date: str) -> dict[str, Any]:
    user_external_id = "self-use-v2-bubble-tea"
    user = get_or_create_user(db, user_external_id)
    state_before = _state_summary(_debug(db, user_external_id=user_external_id, local_date=local_date))
    initial = commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=_candidate(
            request_id="self-use-v2-bubble-initial",
            meal_title="珍珠奶茶",
            raw_input="我喝了一杯珍珠奶茶",
            estimated_kcal=450,
            local_date=local_date,
            items=[_meal_item("珍珠奶茶", 450, carb_g=80, fat_g=12)],
        ),
        budget_kcal=1800,
    )
    if initial is None:
        raise RuntimeError("self_use_v2_bubble_initial_failed")
    target_item_id = _first_item_id(db, meal_version_id=initial.meal_version_id, name="珍珠奶茶")
    refinement = commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=_candidate(
            request_id="self-use-v2-bubble-refinement",
            meal_thread_id=initial.meal_thread_id,
            version_reason="correction",
            meal_title="珍珠奶茶",
            raw_input="半糖大杯",
            estimated_kcal=520,
            local_date=local_date,
            items=[_meal_item("珍珠奶茶", 520, carb_g=92, fat_g=14, quantity_hint="半糖大杯")],
            trace_ref={
                "correction_target_ref": {
                    "meal_thread_id": initial.meal_thread_id,
                    "meal_item_id": target_item_id,
                    "canonical_name": "珍珠奶茶",
                }
            },
        ),
        budget_kcal=1800,
    )
    if refinement is None:
        raise RuntimeError("self_use_v2_bubble_refinement_failed")
    final_debug_surface = _debug(db, user_external_id=user_external_id, local_date=local_date)
    return {
        "scenario_id": "bubble_milk_tea_refinement",
        "status": "pass",
        "turns": [
            _turn(
                turn=1,
                raw_user_input="我喝了一杯珍珠奶茶",
                manager_decision=_manager_fixture(
                    intent_type="log_meal",
                    workflow_effect="new_meal_commit",
                    final_action="commit_logged_estimate",
                    follow_up_posture="ask_size_sugar_after_logging",
                ),
                commit_result=_commit_result_payload(initial, mutation_applied=True),
            ),
            _turn(
                turn=2,
                raw_user_input="半糖大杯",
                manager_decision=_manager_fixture(
                    intent_type="refine_meal",
                    workflow_effect="same_item_refinement",
                    final_action="commit_correction",
                    target_attachment={"attachment_kind": "same_item_refinement", "canonical_name": "珍珠奶茶"},
                ),
                commit_result=_commit_result_payload(refinement, mutation_applied=True),
            ),
        ],
        "state_delta": {"mutation_applied": True},
        "state_before": state_before,
        "state_after": _state_summary(final_debug_surface),
        "final_debug_surface": final_debug_surface,
    }


def _scenario_luwei(db: Session, *, local_date: str) -> dict[str, Any]:
    user_external_id = "self-use-v2-luwei"
    user = get_or_create_user(db, user_external_id)
    state_before = _state_summary(_debug(db, user_external_id=user_external_id, local_date=local_date))
    listed = commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=_candidate(
            request_id="self-use-v2-luwei-listed",
            meal_title="滷味",
            raw_input="有豆干、海帶、貢丸",
            estimated_kcal=420,
            local_date=local_date,
            items=[
                _meal_item("豆干", 120, protein_g=10, carb_g=6, fat_g=6),
                _meal_item("海帶", 40, carb_g=8),
                _meal_item("貢丸", 260, protein_g=12, carb_g=14, fat_g=18),
            ],
        ),
        budget_kcal=1800,
    )
    if listed is None:
        raise RuntimeError("self_use_v2_luwei_listed_failed")
    final_debug_surface = _debug(db, user_external_id=user_external_id, local_date=local_date)
    return {
        "scenario_id": "luwei_draft_to_listed_basket",
        "status": "pass",
        "turns": [
            _turn(
                turn=1,
                raw_user_input="我吃了滷味",
                manager_decision=_manager_fixture(
                    intent_type="log_meal",
                    workflow_effect="draft_clarify_no_mutation",
                    final_action="ask_items",
                ),
                commit_result={"mutation_applied": False, "no_mutation_reason": "composition_unknown_basket"},
            ),
            _turn(
                turn=2,
                raw_user_input="有豆干、海帶、貢丸",
                manager_decision=_manager_fixture(
                    intent_type="complete_meal_details",
                    workflow_effect="listed_basket_commit",
                    final_action="commit_logged_estimate",
                    target_attachment={"attachment_kind": "draft_followup", "canonical_name": "滷味"},
                ),
                commit_result=_commit_result_payload(listed, mutation_applied=True),
            ),
        ],
        "state_delta": {"mutation_applied": True},
        "state_before": state_before,
        "state_after": _state_summary(final_debug_surface),
        "final_debug_surface": final_debug_surface,
    }


def _scenario_query_only(db: Session, *, local_date: str) -> dict[str, Any]:
    user_external_id = "self-use-v2-query"
    user = get_or_create_user(db, user_external_id)
    initial = commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=_candidate(
            request_id="self-use-v2-query-seed",
            meal_title="雞腿便當",
            raw_input="我吃了雞腿便當",
            estimated_kcal=500,
            local_date=local_date,
            items=[_meal_item("雞腿便當", 500, protein_g=35, carb_g=60, fat_g=18)],
        ),
        budget_kcal=1800,
    )
    if initial is None:
        raise RuntimeError("self_use_v2_query_seed_failed")
    before = _ledger_event_count(db, user_id=user.id, local_date=local_date)
    debug_surface = _debug(db, user_external_id=user_external_id, local_date=local_date)
    state_before = _state_summary(debug_surface)
    after = _ledger_event_count(db, user_id=user.id, local_date=local_date)
    return {
        "scenario_id": "query_only_today_consumed",
        "status": "pass",
        "turns": [
            _turn(
                turn=1,
                raw_user_input="今天吃了多少？",
                manager_decision=_manager_fixture(
                    intent_type="answer_consumed_today",
                    workflow_effect="read_only_query",
                    final_action="no_mutation",
                ),
                runtime_validation=_runtime_validation(deterministic_role="read_canonical_state_only"),
                commit_result={"mutation_applied": False},
            ),
        ],
        "state_delta": {
            "mutation_applied": False,
            "ledger_event_count_before": before,
            "ledger_event_count_after": after,
        },
        "state_before": state_before,
        "state_after": _state_summary(debug_surface),
        "final_debug_surface": debug_surface,
    }


def _scenario_no_plan(db: Session, *, local_date: str) -> dict[str, Any]:
    user_external_id = "self-use-v2-no-plan"
    user = get_or_create_user(db, user_external_id)
    commit = commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=_candidate(
            request_id="self-use-v2-no-plan-meal",
            meal_title="三明治",
            raw_input="我吃了三明治",
            estimated_kcal=420,
            local_date=local_date,
            items=[_meal_item("三明治", 420, protein_g=18, carb_g=32, fat_g=14)],
        ),
    )
    if commit is None:
        raise RuntimeError("self_use_v2_no_plan_commit_failed")
    state_before = _state_summary(_debug(db, user_external_id=user_external_id, local_date=local_date))
    answer = build_remaining_budget_answer_contract(db, user_id=user.id, local_date=local_date)
    final_debug_surface = _debug(db, user_external_id=user_external_id, local_date=local_date)
    return {
        "scenario_id": "no_plan_consumed_without_target_or_remaining",
        "status": "pass",
        "turns": [
            _turn(
                turn=1,
                raw_user_input="今天吃了多少？我還能吃多少？",
                manager_decision=_manager_fixture(
                    intent_type="answer_consumed_today",
                    workflow_effect="read_only_no_plan_query",
                    final_action="no_mutation",
                ),
                runtime_validation=_runtime_validation(deterministic_role="read_canonical_state_only"),
                commit_result={"mutation_applied": False},
            ),
        ],
        "state_delta": {"mutation_applied": False},
        "answer_contract": {
            "status": answer.status,
            "consumed_kcal": answer.consumed_kcal,
            "daily_target_kcal": answer.daily_target_kcal,
            "remaining_kcal": answer.remaining_kcal,
        },
        "state_before": state_before,
        "state_after": _state_summary(final_debug_surface),
        "final_debug_surface": final_debug_surface,
    }


def build_self_use_scenario_wall_report(
    *,
    db_path: Path,
    local_date: str = "2026-05-02",
    reset_db: bool = True,
) -> dict[str, Any]:
    if reset_db and db_path.exists():
        db_path.unlink()
    SessionLocal = _session_factory(db_path)
    with SessionLocal() as db:
        scenarios = [
            _scenario_chicken_correction_removal(db, local_date=local_date),
            _scenario_bubble_refinement(db, local_date=local_date),
            _scenario_luwei(db, local_date=local_date),
            _scenario_query_only(db, local_date=local_date),
            _scenario_no_plan(db, local_date=local_date),
        ]
    blockers = [str(scenario["scenario_id"]) for scenario in scenarios if scenario.get("status") != "pass"]
    return {
        "artifact_schema_version": "1.0",
        "scenario_wall_id": "accurate_intake_mvp_self_use_scenario_wall_v2",
        "claim_scope": "local_deterministic_mvp_gate",
        "status": "pass" if not blockers else "fail",
        "blockers": blockers,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "not_claiming": list(_NOT_CLAIMING),
        "product_readiness_claimed": False,
        "live_llm_invoked": False,
        "web_tavily_invoked": False,
        "production_db_used": False,
        "user_facing_rollout": False,
        "local_date": local_date,
        "summary": {
            "scenario_count": len(scenarios),
            "pass_count": sum(1 for scenario in scenarios if scenario.get("status") == "pass"),
            "fail_count": sum(1 for scenario in scenarios if scenario.get("status") != "pass"),
            "runner_inferred_semantics": False,
        },
        "operator_transcript": _operator_transcript(scenarios),
        "scenarios": scenarios,
    }


def _packet(
    *,
    packet_status: str = "accepted",
    evidence_class: str = "local_deterministic_candidate_evidence",
    source: str = "deterministic_manager_fixture",
) -> dict[str, Any]:
    return {
        "packet_status": packet_status,
        "evidence_class": evidence_class,
        "source": source,
        "candidate_only": True,
        "runtime_truth_owner": False,
    }


def _final_mapping(
    *,
    final_action: str,
    workflow_effect: str,
    mutation_allowed: bool,
) -> dict[str, Any]:
    return {
        "owner": "b2_final_mapping",
        "final_action": final_action,
        "workflow_effect": workflow_effect,
        "mutation_allowed": mutation_allowed,
    }


def _one_day_turn(
    *,
    turn_id: str,
    turn: int,
    raw_user_input: str,
    manager_decision: dict[str, Any],
    commit_result: dict[str, Any],
    state_before: dict[str, Any],
    state_after: dict[str, Any],
    evidence_packet: dict[str, Any] | None = None,
    final_mapping: dict[str, Any] | None = None,
    target_evidence: dict[str, Any] | None = None,
    runtime_validation: dict[str, Any] | None = None,
    state_delta: dict[str, Any] | None = None,
    answer_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    workflow_effect = str(manager_decision.get("workflow_effect") or "")
    final_action = str(manager_decision.get("final_action") or "")
    payload = _turn(
        turn=turn,
        raw_user_input=raw_user_input,
        manager_decision=manager_decision,
        runtime_validation=runtime_validation,
        commit_result=commit_result,
    )
    payload.update(
        {
            "turn_id": turn_id,
            "state_before": state_before,
            "state_after": state_after,
            "evidence_packet": evidence_packet or _packet(packet_status="not_required"),
            "final_mapping": final_mapping
            or _final_mapping(
                final_action=final_action,
                workflow_effect=workflow_effect,
                mutation_allowed=bool(commit_result.get("mutation_applied")),
            ),
        }
    )
    if target_evidence is not None:
        payload["target_evidence"] = target_evidence
    if state_delta is not None:
        payload["state_delta"] = state_delta
    if answer_contract is not None:
        payload["answer_contract"] = answer_contract
    return payload


def build_one_day_self_use_scenario_wall_report(
    *,
    db_path: Path,
    user_external_id: str = "self-use-one-day-v1",
    local_date: str = "2026-05-03",
    reset_db: bool = True,
) -> dict[str, Any]:
    if reset_db and db_path.exists():
        db_path.unlink()
    SessionLocal = _session_factory(db_path)
    turns: list[dict[str, Any]] = []
    with SessionLocal() as db:
        user = get_or_create_user(db, user_external_id)
        _seed_local_active_budget_fixture(db, user=user, local_date=local_date, budget_kcal=1800)
        initial_debug = _debug(db, user_external_id=user_external_id, local_date=local_date)
        day_state_before = _state_summary(initial_debug)

        before = _state_summary(_debug(db, user_external_id=user_external_id, local_date=local_date))
        breakfast = commit_meal_payload_to_canonical(
            db,
            user=user,
            candidate=_candidate(
                request_id="one-day-breakfast",
                meal_title="茶葉蛋和拿鐵",
                raw_input="早餐吃茶葉蛋和拿鐵",
                estimated_kcal=270,
                local_date=local_date,
                items=[
                    _meal_item("茶葉蛋", 80, protein_g=7, fat_g=5),
                    _meal_item("拿鐵", 190, protein_g=9, carb_g=16, fat_g=9),
                ],
            ),
            budget_kcal=1800,
        )
        if breakfast is None:
            raise RuntimeError("one_day_breakfast_commit_failed")
        after = _state_summary(_debug(db, user_external_id=user_external_id, local_date=local_date))
        turns.append(
            _one_day_turn(
                turn_id="breakfast_tea_egg_latte",
                turn=1,
                raw_user_input="早餐吃茶葉蛋和拿鐵",
                manager_decision=_manager_fixture(
                    intent_type="log_meal",
                    workflow_effect="new_meal_commit",
                    final_action="commit_logged_estimate",
                    follow_up_posture="none",
                ),
                evidence_packet=_packet(),
                commit_result=_commit_result_payload(breakfast, mutation_applied=True),
                state_before=before,
                state_after=after,
            )
        )

        before = after
        lunch = commit_meal_payload_to_canonical(
            db,
            user=user,
            candidate=_candidate(
                request_id="one-day-lunch-bento",
                meal_title="雞腿便當",
                raw_input="午餐吃雞腿便當",
                estimated_kcal=850,
                local_date=local_date,
                items=[
                    _meal_item("雞腿", 420, protein_g=35, fat_g=24),
                    _meal_item("白飯", 280, carb_g=62),
                    _meal_item("配菜", 150, protein_g=4, carb_g=12, fat_g=8),
                ],
            ),
            budget_kcal=1800,
        )
        if lunch is None:
            raise RuntimeError("one_day_lunch_commit_failed")
        after = _state_summary(_debug(db, user_external_id=user_external_id, local_date=local_date))
        turns.append(
            _one_day_turn(
                turn_id="lunch_chicken_bento",
                turn=2,
                raw_user_input="午餐吃雞腿便當",
                manager_decision=_manager_fixture(
                    intent_type="log_meal",
                    workflow_effect="new_meal_commit",
                    final_action="commit_logged_estimate",
                    follow_up_posture="optional_portion_refinement",
                ),
                evidence_packet=_packet(),
                commit_result=_commit_result_payload(lunch, mutation_applied=True),
                state_before=before,
                state_after=after,
            )
        )

        rice_item_id = _first_item_id(db, meal_version_id=lunch.meal_version_id, name="白飯")
        before = after
        lunch_correction = commit_meal_payload_to_canonical(
            db,
            user=user,
            candidate=_candidate(
                request_id="one-day-lunch-rice-less",
                meal_thread_id=lunch.meal_thread_id,
                version_reason="correction",
                meal_title="雞腿便當",
                raw_input="飯少一點",
                estimated_kcal=720,
                local_date=local_date,
                items=[_meal_item("白飯", 150, carb_g=34, quantity_hint="少飯")],
                trace_ref={
                    "correction_target_ref": {
                        "meal_thread_id": lunch.meal_thread_id,
                        "meal_item_id": rice_item_id,
                        "canonical_name": "白飯",
                    }
                },
            ),
            budget_kcal=1800,
        )
        if lunch_correction is None:
            raise RuntimeError("one_day_lunch_correction_failed")
        after = _state_summary(_debug(db, user_external_id=user_external_id, local_date=local_date))
        turns.append(
            _one_day_turn(
                turn_id="lunch_rice_less_correction",
                turn=3,
                raw_user_input="飯少一點",
                manager_decision=_manager_fixture(
                    intent_type="correct_meal",
                    workflow_effect="correction_replace_item",
                    final_action="commit_correction",
                    target_attachment={"attachment_kind": "explicit_item_target", "canonical_name": "白飯"},
                ),
                evidence_packet=_packet(),
                commit_result=_commit_result_payload(lunch_correction, mutation_applied=True),
                state_before=before,
                state_after=after,
            )
        )

        before = after
        bubble = commit_meal_payload_to_canonical(
            db,
            user=user,
            candidate=_candidate(
                request_id="one-day-bubble-initial",
                meal_title="珍珠奶茶",
                raw_input="下午喝珍珠奶茶",
                estimated_kcal=450,
                local_date=local_date,
                items=[_meal_item("珍珠奶茶", 450, carb_g=80, fat_g=12)],
            ),
            budget_kcal=1800,
        )
        if bubble is None:
            raise RuntimeError("one_day_bubble_commit_failed")
        after = _state_summary(_debug(db, user_external_id=user_external_id, local_date=local_date))
        turns.append(
            _one_day_turn(
                turn_id="bubble_tea_first_value",
                turn=4,
                raw_user_input="下午喝珍珠奶茶",
                manager_decision=_manager_fixture(
                    intent_type="log_meal",
                    workflow_effect="new_meal_commit",
                    final_action="commit_logged_estimate",
                    follow_up_posture="ask_size_sugar_after_logging",
                ),
                evidence_packet=_packet(),
                commit_result=_commit_result_payload(bubble, mutation_applied=True),
                state_before=before,
                state_after=after,
            )
        )

        bubble_item_id = _first_item_id(db, meal_version_id=bubble.meal_version_id, name="珍珠奶茶")
        before = after
        bubble_refinement = commit_meal_payload_to_canonical(
            db,
            user=user,
            candidate=_candidate(
                request_id="one-day-bubble-refinement",
                meal_thread_id=bubble.meal_thread_id,
                version_reason="correction",
                meal_title="珍珠奶茶",
                raw_input="半糖大杯",
                estimated_kcal=520,
                local_date=local_date,
                items=[_meal_item("珍珠奶茶", 520, carb_g=92, fat_g=14, quantity_hint="半糖大杯")],
                trace_ref={
                    "correction_target_ref": {
                        "meal_thread_id": bubble.meal_thread_id,
                        "meal_item_id": bubble_item_id,
                        "canonical_name": "珍珠奶茶",
                    }
                },
            ),
            budget_kcal=1800,
        )
        if bubble_refinement is None:
            raise RuntimeError("one_day_bubble_refinement_failed")
        after = _state_summary(_debug(db, user_external_id=user_external_id, local_date=local_date))
        turns.append(
            _one_day_turn(
                turn_id="bubble_tea_half_sugar_large_refinement",
                turn=5,
                raw_user_input="半糖大杯",
                manager_decision=_manager_fixture(
                    intent_type="refine_meal",
                    workflow_effect="same_item_refinement",
                    final_action="commit_correction",
                    target_attachment={"attachment_kind": "same_item_refinement", "canonical_name": "珍珠奶茶"},
                ),
                evidence_packet=_packet(),
                commit_result=_commit_result_payload(bubble_refinement, mutation_applied=True),
                state_before=before,
                state_after=after,
            )
        )

        before = after
        turns.append(
            _one_day_turn(
                turn_id="dinner_luwei_bare_draft",
                turn=6,
                raw_user_input="晚餐吃滷味",
                manager_decision=_manager_fixture(
                    intent_type="log_meal",
                    workflow_effect="draft_clarify_no_mutation",
                    final_action="ask_items",
                ),
                evidence_packet=_packet(packet_status="not_required", evidence_class="composition_unknown_basket"),
                final_mapping=_final_mapping(
                    final_action="ask_items",
                    workflow_effect="draft_clarify_no_mutation",
                    mutation_allowed=False,
                ),
                commit_result={"mutation_applied": False, "no_mutation_reason": "composition_unknown_basket"},
                state_before=before,
                state_after=before,
            )
        )

        luwei = commit_meal_payload_to_canonical(
            db,
            user=user,
            candidate=_candidate(
                request_id="one-day-luwei-listed",
                meal_title="滷味",
                raw_input="有豆干、海帶、貢丸",
                estimated_kcal=420,
                local_date=local_date,
                items=[
                    _meal_item("豆干", 120, protein_g=10, carb_g=6, fat_g=6),
                    _meal_item("海帶", 40, carb_g=8),
                    _meal_item("貢丸", 260, protein_g=12, carb_g=14, fat_g=18),
                ],
            ),
            budget_kcal=1800,
        )
        if luwei is None:
            raise RuntimeError("one_day_luwei_commit_failed")
        after = _state_summary(_debug(db, user_external_id=user_external_id, local_date=local_date))
        turns.append(
            _one_day_turn(
                turn_id="dinner_luwei_listed_commit",
                turn=7,
                raw_user_input="有豆干、海帶、貢丸",
                manager_decision=_manager_fixture(
                    intent_type="complete_meal_details",
                    workflow_effect="listed_basket_commit",
                    final_action="commit_logged_estimate",
                    target_attachment={"attachment_kind": "draft_followup", "canonical_name": "滷味"},
                ),
                evidence_packet=_packet(),
                commit_result=_commit_result_payload(luwei, mutation_applied=True),
                state_before=before,
                state_after=after,
            )
        )

        gongwan_item_id = _first_item_id(db, meal_version_id=luwei.meal_version_id, name="貢丸")
        before = after
        removal = commit_meal_payload_to_canonical(
            db,
            user=user,
            candidate=_candidate(
                request_id="one-day-luwei-remove-gongwan",
                meal_thread_id=luwei.meal_thread_id,
                version_reason="correction",
                meal_title="滷味",
                raw_input="把貢丸拿掉",
                estimated_kcal=160,
                local_date=local_date,
                items=[],
                trace_ref={
                    "correction_operation": "remove_item",
                    "correction_target_ref": {
                        "meal_thread_id": luwei.meal_thread_id,
                        "meal_item_id": gongwan_item_id,
                        "canonical_name": "貢丸",
                    },
                },
            ),
            budget_kcal=1800,
        )
        if removal is None:
            raise RuntimeError("one_day_luwei_removal_failed")
        after = _state_summary(_debug(db, user_external_id=user_external_id, local_date=local_date))
        turns.append(
            _one_day_turn(
                turn_id="dinner_remove_gongwan",
                turn=8,
                raw_user_input="把貢丸拿掉",
                manager_decision=_manager_fixture(
                    intent_type="correct_meal",
                    workflow_effect="correction_remove_item",
                    final_action="commit_correction",
                    target_attachment={"attachment_kind": "explicit_item_target", "canonical_name": "貢丸"},
                ),
                evidence_packet=_packet(packet_status="not_required", evidence_class="target_evidence_only"),
                target_evidence={
                    "target_evidence_present": True,
                    "nutrition_evidence_present": False,
                    "canonical_name": "貢丸",
                },
                commit_result=_commit_result_payload(removal, mutation_applied=True),
                state_before=before,
                state_after=after,
            )
        )

        before = after
        before_ledger_count = _ledger_event_count(db, user_id=user.id, local_date=local_date)
        answer = build_remaining_budget_answer_contract(db, user_id=user.id, local_date=local_date)
        final_debug_surface = _debug(db, user_external_id=user_external_id, local_date=local_date)
        after_ledger_count = _ledger_event_count(db, user_id=user.id, local_date=local_date)
        after = _state_summary(final_debug_surface)
        turns.append(
            _one_day_turn(
                turn_id="today_consumed_remaining_query",
                turn=9,
                raw_user_input="今天吃了多少？還剩多少？",
                manager_decision=_manager_fixture(
                    intent_type="answer_remaining_budget",
                    workflow_effect="read_only_budget_query",
                    final_action="no_mutation",
                ),
                runtime_validation=_runtime_validation(deterministic_role="read_canonical_state_only"),
                commit_result={"mutation_applied": False},
                state_delta={
                    "mutation_applied": False,
                    "ledger_event_count_before": before_ledger_count,
                    "ledger_event_count_after": after_ledger_count,
                },
                answer_contract={
                    "status": answer.status,
                    "consumed_kcal": answer.consumed_kcal,
                    "daily_target_kcal": answer.daily_target_kcal,
                    "remaining_kcal": answer.remaining_kcal,
                },
                state_before=before,
                state_after=after,
            )
        )

    blockers: list[str] = []
    final_today = dict(after.get("today_summary") or {})
    if final_today.get("consumed_kcal") != 1670:
        blockers.append("final_consumed_kcal_mismatch")
    if final_today.get("remaining_kcal") != 130:
        blockers.append("final_remaining_kcal_mismatch")
    if dict(final_debug_surface.get("model") or {}).get("same_truth", {}).get("status") != "pass":
        blockers.append("same_truth_failed")
    mutation_turn_count = sum(1 for turn in turns if dict(turn.get("commit_result") or {}).get("mutation_applied"))
    return {
        "artifact_schema_version": "1.0",
        "scenario_wall_id": "accurate_intake_one_day_self_use_wall_v1",
        "claim_scope": "local_deterministic_mvp_gate",
        "status": "pass" if not blockers else "fail",
        "blockers": blockers,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "not_claiming": list(_NOT_CLAIMING),
        "product_readiness_claimed": False,
        "live_llm_invoked": False,
        "web_tavily_invoked": False,
        "production_db_used": False,
        "user_facing_rollout": False,
        "runner_inferred_semantics": False,
        "scenario_id": "one_day_v1",
        "user_external_id": user_external_id,
        "local_date": local_date,
        "state_before": day_state_before,
        "state_after": after,
        "final_debug_surface": final_debug_surface,
        "summary": {
            "turn_count": len(turns),
            "mutation_turn_count": mutation_turn_count,
            "no_mutation_turn_count": len(turns) - mutation_turn_count,
            "final_consumed_kcal": final_today.get("consumed_kcal"),
            "final_remaining_kcal": final_today.get("remaining_kcal"),
            "runner_inferred_semantics": False,
        },
        "turns": turns,
    }


def build_one_day_self_use_reopen_report(
    *,
    db_path: Path,
    user_external_id: str = "self-use-one-day-v1",
    local_date: str = "2026-05-03",
) -> dict[str, Any]:
    SessionLocal = _session_factory(db_path)
    with SessionLocal() as db:
        user = _lookup_user(db, user_external_id)
        debug_surface = _debug(db, user_external_id=user_external_id, local_date=local_date)
        state_after = _state_summary(debug_surface)
        today = dict(state_after.get("today_summary") or {})
        same_truth_status = state_after.get("same_truth_status")
        ledger_event_count = _ledger_event_count(db, user_id=user.id, local_date=local_date) if user is not None else 0
    blockers: list[str] = []
    if user is None:
        blockers.append("missing_reopened_user")
    if today.get("consumed_kcal") != 1670:
        blockers.append("final_consumed_kcal_reopen_mismatch")
    if today.get("remaining_kcal") != 130:
        blockers.append("final_remaining_kcal_reopen_mismatch")
    if today.get("active_meal_count") != 4:
        blockers.append("active_meal_count_reopen_mismatch")
    if ledger_event_count != 7:
        blockers.append("ledger_event_count_reopen_mismatch")
    if same_truth_status != "pass":
        blockers.append("same_truth_reopen_failed")
    return {
        "artifact_schema_version": "1.0",
        "continuity_id": "accurate_intake_one_day_reopen_continuity_v1",
        "claim_scope": "local_deterministic_mvp_gate",
        "status": "pass" if not blockers else "fail",
        "blockers": blockers,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "not_claiming": list(_NOT_CLAIMING),
        "read_only": True,
        "mutation_applied": False,
        "product_readiness_claimed": False,
        "live_llm_invoked": False,
        "web_tavily_invoked": False,
        "production_db_used": False,
        "user_facing_rollout": False,
        "db_mode": "reopen_existing_local_sqlite",
        "local_date": local_date,
        "debug_surface": debug_surface,
        "summary": {
            "final_consumed_kcal": today.get("consumed_kcal"),
            "final_remaining_kcal": today.get("remaining_kcal"),
            "active_meal_count": today.get("active_meal_count"),
            "ledger_event_count": ledger_event_count,
            "same_truth_status": same_truth_status,
        },
    }


def build_self_use_smoke_report(
    *,
    db_path: Path,
    user_external_id: str = "self-use-smoke-user",
    local_date: str = "2026-05-02",
    reset_db: bool = True,
) -> dict[str, Any]:
    if reset_db and db_path.exists():
        db_path.unlink()
    SessionLocal = _session_factory(db_path)
    with SessionLocal() as db:
        user = get_or_create_user(db, user_external_id)
        initial = commit_meal_payload_to_canonical(
            db,
            user=user,
            candidate=_initial_candidate(local_date=local_date),
            budget_kcal=1800,
        )
        if initial is None:
            raise RuntimeError("self_use_initial_commit_failed")
        target_item = db.execute(
            select(MealItemRecord).where(MealItemRecord.meal_version_id == initial.meal_version_id)
        ).scalars().first()
        if target_item is None:
            raise RuntimeError("self_use_target_item_missing")
        correction = commit_meal_payload_to_canonical(
            db,
            user=user,
            candidate=_correction_candidate(
                local_date=local_date,
                meal_thread_id=initial.meal_thread_id,
                meal_item_id=target_item.id,
            ),
            budget_kcal=1800,
        )
        if correction is None:
            raise RuntimeError("self_use_correction_commit_failed")
        corrected_target = db.execute(
            select(MealItemRecord)
            .where(MealItemRecord.meal_version_id == correction.meal_version_id, MealItemRecord.name == "chicken rice")
        ).scalars().first()
        if corrected_target is None:
            raise RuntimeError("self_use_corrected_target_item_missing")
        removal = commit_meal_payload_to_canonical(
            db,
            user=user,
            candidate=_removal_candidate(
                local_date=local_date,
                meal_thread_id=initial.meal_thread_id,
                meal_item_id=corrected_target.id,
            ),
            budget_kcal=1800,
        )
        if removal is None:
            raise RuntimeError("self_use_item_removal_commit_failed")

    with SessionLocal() as db:
        debug_payload = build_accurate_intake_debug_payload(
            db,
            user_external_id=user_external_id,
            local_date=local_date,
        )

    model = dict(debug_payload.get("model") or {})
    today = dict(model.get("today_summary") or {})
    same_truth = dict(model.get("same_truth") or {})
    correction_history = list(model.get("correction_history") or [])
    status = "pass"
    blockers: list[str] = []
    if today.get("consumed_kcal") != 150:
        status = "fail"
        blockers.append("consumed_kcal_not_from_removed_item_active_version")
    if today.get("remaining_kcal") != 1650:
        status = "fail"
        blockers.append("remaining_kcal_not_from_current_budget_truth")
    if same_truth.get("status") != "pass":
        status = "fail"
        blockers.append("debug_surface_same_truth_failed")
    if not correction_history or correction_history[-1].get("non_target_item_names_preserved") != ["soup"]:
        status = "fail"
        blockers.append("item_removal_non_target_item_not_preserved")
    if not correction_history or correction_history[-1].get("removed_item_names") != ["chicken rice"]:
        status = "fail"
        blockers.append("item_removal_target_not_removed")
    return {
        "artifact_schema_version": "1.0",
        "smoke_id": "accurate_intake_mvp_self_use_smoke_v1",
        "claim_scope": "local_deterministic_self_use_smoke",
        "status": status,
        "blockers": blockers,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "not_claiming": list(_NOT_CLAIMING),
        "live_llm_invoked": False,
        "web_tavily_invoked": False,
        "production_db_used": False,
        "user_facing_rollout": False,
        "local_date": local_date,
        "input_sequence": [
            {"turn": 1, "kind": "new_meal", "text": "chicken rice and soup"},
            {"turn": 2, "kind": "explicit_item_correction", "text": "the chicken rice was smaller"},
            {"turn": 3, "kind": "explicit_item_removal", "text": "remove the chicken rice"},
            {"turn": 4, "kind": "debug_read", "text": "show current local product-loop truth"},
        ],
        "debug_surface": debug_payload,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Accurate Intake MVP local self-use smoke.")
    parser.add_argument("--output", default=str(DEFAULT_ARTIFACT_PATH))
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--scenario-wall-v2", action="store_true")
    parser.add_argument("--reopen-continuity", action="store_true")
    parser.add_argument("--one-day-scenario-wall", action="store_true")
    parser.add_argument("--one-day-reopen-continuity", action="store_true")
    parser.add_argument("--user-id", default="self-use-smoke-user")
    parser.add_argument("--local-date", default="2026-05-02")
    parser.add_argument("--keep-db", action="store_true")
    args = parser.parse_args(argv)

    selected_modes = [
        args.scenario_wall_v2,
        args.reopen_continuity,
        args.one_day_scenario_wall,
        args.one_day_reopen_continuity,
    ]
    if sum(1 for selected in selected_modes if selected) > 1:
        raise SystemExit("self-use smoke modes cannot be combined")
    if args.one_day_scenario_wall:
        report = build_one_day_self_use_scenario_wall_report(
            db_path=Path(args.db_path),
            user_external_id=args.user_id if args.user_id != "self-use-smoke-user" else "self-use-one-day-v1",
            local_date=args.local_date if args.local_date != "2026-05-02" else "2026-05-03",
            reset_db=not args.keep_db,
        )
        output_path = Path(args.output)
    elif args.one_day_reopen_continuity:
        report = build_one_day_self_use_reopen_report(
            db_path=Path(args.db_path),
            user_external_id=args.user_id if args.user_id != "self-use-smoke-user" else "self-use-one-day-v1",
            local_date=args.local_date if args.local_date != "2026-05-02" else "2026-05-03",
        )
        output_path = Path(args.output)
    elif args.reopen_continuity:
        report = build_self_use_reopen_continuity_report(
            db_path=Path(args.db_path),
            local_date=args.local_date,
        )
        output_path = Path(args.output)
        if output_path == DEFAULT_ARTIFACT_PATH:
            output_path = DEFAULT_REOPEN_CONTINUITY_ARTIFACT_PATH
    elif args.scenario_wall_v2:
        report = build_self_use_scenario_wall_report(
            db_path=Path(args.db_path),
            local_date=args.local_date,
            reset_db=not args.keep_db,
        )
        output_path = Path(args.output)
        if output_path == DEFAULT_ARTIFACT_PATH:
            output_path = DEFAULT_SCENARIO_WALL_ARTIFACT_PATH
    else:
        report = build_self_use_smoke_report(
            db_path=Path(args.db_path),
            user_external_id=args.user_id,
            local_date=args.local_date,
            reset_db=not args.keep_db,
        )
        output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
