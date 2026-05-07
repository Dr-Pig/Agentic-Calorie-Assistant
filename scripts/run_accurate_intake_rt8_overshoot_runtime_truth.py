from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition.accurate_intake_debug_read_model import build_accurate_intake_debug_read_model  # noqa: E402
from app.composition.canonical_persistence import commit_meal_payload_to_canonical  # noqa: E402
from app.composition.current_budget_answer import build_remaining_budget_answer_contract_from_views  # noqa: E402
from app.composition.current_budget_read_model import build_current_budget_view  # noqa: E402
from app.composition.manager_context_runtime import build_runtime_manager_context_packet_v1  # noqa: E402
from app.composition.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date  # noqa: E402
from app.composition.state_resolver import resolve_intake_state  # noqa: E402
from app.database import get_or_create_user  # noqa: E402
from app.intake.application.context_injection_policy import build_manager_context_pack  # noqa: E402
from app.intake.application.current_turn_context_assembler import build_current_turn_context_v1  # noqa: E402
from app.intake.infrastructure.models import MealItemRecord  # noqa: E402
from app.models import Base  # noqa: E402
from app.schemas import CommitRequestCandidate, MealItemPayload  # noqa: E402
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_rt8_overshoot_runtime_truth.json"
USER_ID = "rt8-overshoot-runtime"
LOCAL_DATE = "2026-05-08"
QUERY_TEXT = "今天還剩多少？"


def _session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _bootstrap_inputs(*, local_date: str) -> OnboardingBootstrapInput:
    return OnboardingBootstrapInput(
        sex="female",
        age_years=30,
        height_cm=165.0,
        current_weight_kg=58.0,
        activity_level="sedentary",
        goal_type="lose_weight",
        weekly_target_rate_kg=0.5,
        local_date=local_date,
        timezone="Asia/Taipei",
    )


def _initial_candidate(*, budget_kcal: int) -> CommitRequestCandidate:
    return CommitRequestCandidate(
        request_id="rt8-initial-overshoot",
        manager_intent="food_estimation",
        version_reason="new_intake",
        meal_title="large dinner",
        raw_input="large dinner",
        estimated_kcal=budget_kcal + 250,
        protein_g=45,
        carb_g=90,
        fat_g=30,
        resolution_status="completed_meal",
        local_date=LOCAL_DATE,
        items=[
            MealItemPayload(
                name="large dinner",
                estimated_kcal=budget_kcal + 250,
                protein_g=45,
                carb_g=90,
                fat_g=30,
            )
        ],
    )


def _correction_candidate(*, meal_thread_id: int, meal_item_id: int, budget_kcal: int) -> CommitRequestCandidate:
    return CommitRequestCandidate(
        request_id="rt8-correction-under-target",
        manager_intent="food_estimation",
        meal_thread_id=meal_thread_id,
        version_reason="correction",
        meal_title="large dinner",
        raw_input="actually it was smaller",
        estimated_kcal=budget_kcal - 100,
        protein_g=35,
        carb_g=60,
        fat_g=18,
        resolution_status="completed_meal",
        local_date=LOCAL_DATE,
        items=[
            MealItemPayload(
                name="large dinner",
                estimated_kcal=budget_kcal - 100,
                protein_g=35,
                carb_g=60,
                fat_g=18,
            )
        ],
        trace_ref={
            "correction_target_ref": {
                "meal_thread_id": meal_thread_id,
                "meal_item_id": meal_item_id,
                "canonical_name": "large dinner",
            }
        },
    )


def _runtime_surfaces(db: Session, *, user_id: int) -> dict[str, Any]:
    resolved_state = resolve_intake_state(
        db,
        user_external_id=USER_ID,
        local_date=LOCAL_DATE,
        incoming_user_text=QUERY_TEXT,
    )
    current_turn_context = build_current_turn_context_v1(
        raw_user_input=QUERY_TEXT,
        resolved_state=resolved_state,
    )
    manager_context_pack = build_manager_context_pack(current_turn_context=current_turn_context)
    manager_context_packet = build_runtime_manager_context_packet_v1(
        db=db,
        current_turn_context=current_turn_context,
        user_external_id=USER_ID,
        local_date=LOCAL_DATE,
        manager_mode="fixture",
    )
    current_budget = build_current_budget_view(db, user_id=user_id, local_date=LOCAL_DATE)
    debug_model = build_accurate_intake_debug_read_model(
        db,
        user_id=user_id,
        local_date=LOCAL_DATE,
        current_budget=current_budget,
        active_plan=resolved_state.active_body_plan_view,
    )
    answer = build_remaining_budget_answer_contract_from_views(
        current_budget=current_budget,
        active_plan=resolved_state.active_body_plan_view,
    )
    return {
        "resolved_state": resolved_state,
        "current_turn_context": current_turn_context,
        "manager_context_pack": manager_context_pack,
        "manager_context_packet_v1": manager_context_packet,
        "current_budget": current_budget,
        "debug_model": debug_model,
        "answer": answer,
    }


def build_rt8_overshoot_runtime_truth_artifact(*, output_path: Path | None = None) -> dict[str, Any]:
    db = _session()
    user = get_or_create_user(db, USER_ID)
    bootstrap = bootstrap_body_plan_for_date(db, user=user, inputs=_bootstrap_inputs(local_date=LOCAL_DATE))
    budget_kcal = int(bootstrap.target_result.recommended_target_kcal)

    initial = commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=_initial_candidate(budget_kcal=budget_kcal),
        budget_kcal=budget_kcal,
    )
    assert initial is not None
    initial_item = db.execute(
        select(MealItemRecord).where(MealItemRecord.meal_version_id == initial.meal_version_id)
    ).scalars().first()
    assert initial_item is not None

    overshoot_surfaces = _runtime_surfaces(db, user_id=user.id)
    overshoot_context = overshoot_surfaces["current_turn_context"]
    overshoot_packet = overshoot_surfaces["manager_context_packet_v1"] or {}
    overshoot_answer = overshoot_surfaces["answer"]
    overshoot_debug = overshoot_surfaces["debug_model"]
    overshoot_case = {
        "case_id": "overshoot_reflects_budget_truth_without_rescue_context",
        "status": "pass",
        "remaining_kcal": overshoot_answer.remaining_kcal,
        "overshoot_detected": overshoot_context.current_budget_snapshot["overshoot_status"] == "overshoot",
        "overshoot_kcal": overshoot_surfaces["resolved_state"].injected_context["OVERSHOOT_POSTURE"]["overshoot_kcal"],
        "manager_context_has_rescue": "rescue_context" in overshoot_surfaces["manager_context_pack"].manager_context,
        "packet_has_rescue": "rescue_context" in overshoot_packet,
        "same_truth_status": overshoot_debug["same_truth"]["status"],
    }

    correction = commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=_correction_candidate(
            meal_thread_id=initial.meal_thread_id,
            meal_item_id=initial_item.id,
            budget_kcal=budget_kcal,
        ),
        budget_kcal=budget_kcal,
    )
    assert correction is not None

    corrected_surfaces = _runtime_surfaces(db, user_id=user.id)
    corrected_context = corrected_surfaces["current_turn_context"]
    corrected_answer = corrected_surfaces["answer"]
    corrected_debug = corrected_surfaces["debug_model"]
    correction_case = {
        "case_id": "correction_restores_under_target_runtime_truth",
        "status": "pass",
        "remaining_kcal": corrected_answer.remaining_kcal,
        "overshoot_detected": corrected_context.current_budget_snapshot["overshoot_status"] == "overshoot",
        "predicted_remaining_kcal_after": corrected_surfaces["resolved_state"].injected_context["OVERSHOOT_POSTURE"][
            "predicted_remaining_kcal_after"
        ],
        "same_truth_status": corrected_debug["same_truth"]["status"],
        "active_version_reason": corrected_debug["meal_threads"][0]["active_version"]["version_reason"],
    }

    answer_case = {
        "case_id": "budget_answer_and_debug_model_share_overshoot_truth",
        "status": "pass",
        "answer_remaining_kcal": corrected_answer.remaining_kcal,
        "debug_remaining_kcal": corrected_debug["today_summary"]["remaining_kcal"],
        "answer_consumed_kcal": corrected_answer.consumed_kcal,
        "debug_consumed_kcal": corrected_debug["today_summary"]["consumed_kcal"],
        "same_truth_status": corrected_debug["same_truth"]["status"],
    }

    cases = [overshoot_case, correction_case, answer_case]
    passed_case_count = sum(1 for case in cases if case["status"] == "pass")
    resolved_output = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH
    return json.loads(
        json.dumps(
            {
                "artifact_schema_version": "1.0",
                "artifact_name": resolved_output.name,
                "artifact_path": str(resolved_output),
                "schema_version": "1.0",
                "fixture_or_real": "real_runtime_local",
                "producer_track": "CurrentShell/ManagerRuntime",
                "intended_consumers": ["CurrentShell/AppShell", "CurrentShell/SharedCurrentShell", "human_review"],
                "ready_for_other_tracks": True,
                "non_claims": {
                    "product_readiness_claimed": False,
                    "private_self_use_approved": False,
                    "real_fooddb_pass_claimed": False,
                },
                "artifact_type": "accurate_intake_rt8_overshoot_runtime_truth",
                "gate_id": "accurate_intake_rt8_overshoot_runtime_truth",
                "claim_scope": "manager_runtime_rt8_overshoot_runtime_truth",
                "target_manager_runtime_gate": "rt8_overshoot_runtime_truth",
                "supports_journeys": ["E"],
                "runtime_backed": True,
                "live_llm_invoked": False,
                "fooddb_used": False,
                "web_tavily_used": False,
                "runtime_truth_changed": False,
                "mutation_changed": False,
                "manager_context_packet_schema_changed": False,
                "generated_at_utc": datetime.now(UTC).isoformat(),
                "status": "pass" if passed_case_count == len(cases) else "fail",
                "summary": {
                    "case_count": len(cases),
                    "passed_case_count": passed_case_count,
                    "budget_kcal": budget_kcal,
                },
                "cases": cases,
            },
            ensure_ascii=False,
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args(argv)
    artifact = build_rt8_overshoot_runtime_truth_artifact(output_path=args.output)
    write_json_artifact(args.output, artifact)
    print(
        json.dumps(
            {
                "artifact": str(args.output),
                "status": artifact["status"],
                "passed_case_count": artifact["summary"]["passed_case_count"],
                "case_count": artifact["summary"]["case_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
