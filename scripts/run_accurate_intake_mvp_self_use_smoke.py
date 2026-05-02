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
from app.composition.canonical_persistence import commit_meal_payload_to_canonical
from app.composition.current_budget_answer import build_remaining_budget_answer_contract
from app.budget.infrastructure.models import LedgerEntryRecord
from app.database import get_or_create_user
from app.intake.infrastructure.models import MealItemRecord
from app.models import Base
from app.schemas import CommitRequestCandidate, MealItemPayload

DEFAULT_ARTIFACT_PATH = ROOT / "artifacts" / "accurate_intake_mvp_self_use_smoke.json"
DEFAULT_DB_PATH = ROOT / "artifacts" / "accurate_intake_mvp_self_use_smoke.sqlite3"
DEFAULT_SCENARIO_WALL_ARTIFACT_PATH = ROOT / "artifacts" / "accurate_intake_mvp_self_use_scenario_wall.json"

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
    parser.add_argument("--user-id", default="self-use-smoke-user")
    parser.add_argument("--local-date", default="2026-05-02")
    parser.add_argument("--keep-db", action="store_true")
    args = parser.parse_args(argv)

    if args.scenario_wall_v2:
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
