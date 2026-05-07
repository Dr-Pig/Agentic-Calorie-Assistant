from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.accurate_intake_body_observation_manager_fixture import BodyObservationManagerFixtureProvider  # noqa: E402
from app.body.application import build_active_body_plan_view  # noqa: E402
from app.body.application.body_observation_service import get_latest_weight_observation  # noqa: E402
from app.budget.infrastructure.models import DayBudgetLedgerRecord  # noqa: E402
from app.composition import intake_routes  # noqa: E402
from app.composition.body_observation_manager_turn import execute_body_observation_manager_turn  # noqa: E402
from app.composition.canonical_persistence import commit_meal_payload_to_canonical  # noqa: E402
from app.composition.current_budget_answer import build_remaining_budget_answer_contract  # noqa: E402
from app.composition.manager_context_runtime import build_runtime_manager_context_packet_v1  # noqa: E402
from app.composition.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date  # noqa: E402
from app.composition.state_resolver import resolve_intake_state  # noqa: E402
from app.composition.weight_routes import WeightObservationRequest, post_weight_observation  # noqa: E402
from app.database import get_or_create_user  # noqa: E402
from app.intake.application.current_turn_context_assembler import build_current_turn_context_v1  # noqa: E402
from app.models import Base  # noqa: E402
from app.schemas import CommitRequestCandidate, EstimateRequest  # noqa: E402
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_rt6_bootstrap_no_plan_body_closure.json"


def _session() -> Session:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
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


def _candidate() -> CommitRequestCandidate:
    return CommitRequestCandidate(
        request_id="rt6-no-plan-meal",
        manager_intent="food_estimation",
        version_reason="new_intake",
        meal_title="no plan sandwich",
        raw_input="no plan sandwich",
        estimated_kcal=420,
        protein_g=18,
        carb_g=32,
        fat_g=14,
        resolution_status="completed_meal",
        local_date="2026-05-02",
    )


def _ledger_snapshot(db: Session, *, user_id: int) -> list[tuple[str, int, int, int, int]]:
    ledgers = db.execute(
        select(DayBudgetLedgerRecord)
        .where(DayBudgetLedgerRecord.user_id == user_id)
        .order_by(DayBudgetLedgerRecord.local_date.asc(), DayBudgetLedgerRecord.id.asc())
    ).scalars()
    return [
        (ledger.local_date, ledger.budget_kcal, ledger.consumed_kcal, ledger.adjustment_kcal, ledger.remaining_kcal)
        for ledger in ledgers
    ]


def _bootstrap_ready_case() -> dict[str, Any]:
    db = _session()
    try:
        user = get_or_create_user(db, "rt6-bootstrap-ready")
        result = bootstrap_body_plan_for_date(db, user=user, inputs=_bootstrap_inputs(local_date="2026-05-07"))
        answer = build_remaining_budget_answer_contract(db, user_id=user.id, local_date="2026-05-07")
        blockers = []
        if result.active_body_plan_view.body_plan_id is None:
            blockers.append("body_plan_missing_after_bootstrap")
        if answer.status != "ready":
            blockers.append("remaining_budget_not_ready_after_bootstrap")
        if answer.daily_target_kcal != result.target_result.recommended_target_kcal:
            blockers.append("bootstrap_budget_target_mismatch")
        return {"case_id": "bootstrap_ready", "status": "pass" if not blockers else "fail", "blockers": blockers, "daily_target_kcal": answer.daily_target_kcal}
    finally:
        db.close()


def _no_plan_honesty_case() -> dict[str, Any]:
    db = _session()
    try:
        user_external_id = "rt6-no-plan-honesty"
        user = get_or_create_user(db, user_external_id)
        commit_meal_payload_to_canonical(db, user=user, candidate=_candidate())
        previous_router = intake_routes.build_workflow_routing_decision
        intake_routes.build_workflow_routing_decision = lambda **_: SimpleNamespace(
            target_workflow_family="general_chat",
            disposition="answer_only",
            required_read_surfaces=["CurrentBudgetView", "ActiveBodyPlanView"],
            phase_a_trace={},
        )
        try:
            route_result = asyncio.run(
                intake_routes.estimate(
                    EstimateRequest(
                        text="how many calories can I still eat?",
                        user_id=user_external_id,
                        local_date="2026-05-02",
                        allow_search=False,
                    ),
                    SimpleNamespace(headers={}),
                    db=db,
                )
            )
        finally:
            intake_routes.build_workflow_routing_decision = previous_router
        answer = build_remaining_budget_answer_contract(db, user_id=user.id, local_date="2026-05-02")
        blockers = []
        if _ledger_snapshot(db, user_id=user.id):
            blockers.append("no_plan_created_day_budget_ledger_truth")
        if route_result.get("payload") is not None:
            blockers.append("no_plan_runtime_route_exposed_unexpected_payload")
        coach_message = str(route_result.get("coach_message") or "")
        if "420 kcal consumed today" not in coach_message:
            blockers.append("no_plan_runtime_route_honesty_mismatch")
        if "onboarding is required before I can answer remaining budget." not in coach_message:
            blockers.append("no_plan_runtime_route_missing_onboarding_boundary")
        if answer.status != "onboarding_required":
            blockers.append("no_plan_answer_not_onboarding_required")
        if answer.consumed_kcal != 420:
            blockers.append("no_plan_consumed_kcal_mismatch")
        if answer.daily_target_kcal is not None or answer.remaining_kcal is not None:
            blockers.append("no_plan_budget_honesty_failed")
        return {"case_id": "no_plan_honesty", "status": "pass" if not blockers else "fail", "blockers": blockers, "answer_status": answer.status}
    finally:
        db.close()


def _manager_body_observation_case() -> dict[str, Any]:
    db = _session()
    try:
        provider = BodyObservationManagerFixtureProvider()
        user_external_id = "rt6-manager-body-observation"
        user = get_or_create_user(db, user_external_id)
        bootstrap_body_plan_for_date(db, user=user, inputs=_bootstrap_inputs(local_date="2026-05-07"))
        before_plan = build_active_body_plan_view(db, user_id=user.id)
        before_ledgers = _ledger_snapshot(db, user_id=user.id)
        state_before = resolve_intake_state(db, user_external_id=user_external_id, local_date="2026-05-07", incoming_user_text="my weight is 70kg")
        turn_context = build_current_turn_context_v1(raw_user_input="my weight is 70kg", resolved_state=state_before)
        packet = build_runtime_manager_context_packet_v1(
            db=db,
            current_turn_context=turn_context,
            user_external_id=user_external_id,
            local_date="2026-05-07",
            session_id="rt6-body-observation-session",
        )
        result = asyncio.run(
            execute_body_observation_manager_turn(
                db,
                request_id="rt6-body-observation-turn",
                user_external_id=user_external_id,
                raw_user_input="my weight is 70kg",
                local_date="2026-05-07",
                allow_search=False,
                manager_provider=provider,
                state_before=state_before,
                current_turn_context=turn_context,
                manager_context_packet_v1=packet,
                phase_a_trace={},
            )
        )
        latest_weight = get_latest_weight_observation(db, user_id=user.id, local_date="2026-05-07")
        after_plan = build_active_body_plan_view(db, user_id=user.id)
        blockers = []
        first_call = provider.calls[0] if provider.calls else {}
        second_results = provider.calls[1]["tool_results"] if len(provider.calls) > 1 else []
        if first_call.get("available_tools") != ["body.record_observation"]:
            blockers.append("manager_body_observation_tool_inventory_mismatch")
        if not second_results or second_results[0].get("tool_name") != "body.record_observation":
            blockers.append("manager_body_observation_tool_result_missing")
        if second_results and second_results[0].get("provenance", {}).get("canonical_tool_name") != "body.record_observation":
            blockers.append("manager_body_observation_provenance_mismatch")
        if result["state_delta"].get("body_observation_recorded") is not True:
            blockers.append("manager_body_observation_not_recorded")
        if result["state_delta"].get("ledger_updated") is not False:
            blockers.append("manager_body_observation_ledger_mutated")
        if latest_weight is None or latest_weight.value != 70.0 or latest_weight.unit != "kg":
            blockers.append("manager_body_observation_latest_weight_mismatch")
        if after_plan.body_plan_id != before_plan.body_plan_id or after_plan.daily_budget_kcal != before_plan.daily_budget_kcal:
            blockers.append("manager_body_observation_changed_plan_budget")
        if _ledger_snapshot(db, user_id=user.id) != before_ledgers:
            blockers.append("manager_body_observation_changed_ledger_snapshot")
        return {"case_id": "manager_body_observation_write", "status": "pass" if not blockers else "fail", "blockers": blockers, "latest_weight_value": None if latest_weight is None else latest_weight.value}
    finally:
        db.close()


def _weight_route_case() -> dict[str, Any]:
    db = _session()
    try:
        user = get_or_create_user(db, "rt6-weight-route")
        bootstrap_body_plan_for_date(db, user=user, inputs=_bootstrap_inputs(local_date="2026-05-07"))
        before_plan = build_active_body_plan_view(db, user_id=user.id)
        before_ledgers = _ledger_snapshot(db, user_id=user.id)
        response = asyncio.run(post_weight_observation(WeightObservationRequest(user_id="rt6-weight-route", weight_kg=69.5, local_date="2026-05-08"), db=db))
        latest_weight = get_latest_weight_observation(db, user_id=user.id, local_date="2026-05-08")
        after_plan = build_active_body_plan_view(db, user_id=user.id)
        blockers = []
        if response.get("status") != "ok":
            blockers.append("weight_route_failed")
        if response.get("recomputed_target_kcal") is not None:
            blockers.append("weight_route_recomputed_target")
        if latest_weight is None or latest_weight.value != 69.5 or latest_weight.unit != "kg":
            blockers.append("weight_route_latest_weight_mismatch")
        if after_plan.body_plan_id != before_plan.body_plan_id or after_plan.daily_budget_kcal != before_plan.daily_budget_kcal:
            blockers.append("weight_route_changed_plan_budget")
        if after_plan.current_weight_kg != before_plan.current_weight_kg:
            blockers.append("weight_route_changed_plan_current_weight")
        if _ledger_snapshot(db, user_id=user.id) != before_ledgers:
            blockers.append("weight_route_changed_ledger_snapshot")
        return {
            "case_id": "weight_route_write",
            "status": "pass" if not blockers else "fail",
            "blockers": blockers,
            "latest_weight_value": None if latest_weight is None else latest_weight.value,
            "response_local_date": response.get("local_date"),
        }
    finally:
        db.close()


def build_rt6_bootstrap_no_plan_body_closure_artifact(
    *,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    cases = [_bootstrap_ready_case(), _no_plan_honesty_case(), _manager_body_observation_case(), _weight_route_case()]
    blockers = [f"{case['case_id']}.{blocker}" for case in cases for blocker in case["blockers"]]
    resolved_output = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH
    return json.loads(
        json.dumps(
            {
                "artifact_schema_version": "1.0",
                "artifact_name": resolved_output.name,
                "artifact_path": str(resolved_output),
                "schema_version": "1.0",
                "fixture_or_real": "fixture",
                "producer_track": "CurrentShell/ManagerRuntime",
                "intended_consumers": ["CurrentShell/AppShell", "CurrentShell/SharedCurrentShell", "human_review"],
                "ready_for_other_tracks": True,
                "non_claims": {
                    "product_readiness_claimed": False,
                    "private_self_use_approved": False,
                    "real_fooddb_pass_claimed": False,
                },
                "gate_id": "accurate_intake_rt6_bootstrap_no_plan_body_closure",
                "claim_scope": "manager_runtime_rt6_bootstrap_no_plan_body_closure",
                "status": "pass" if not blockers else "fail",
                "generated_at_utc": datetime.now(UTC).isoformat(),
                "target_manager_runtime_gate": "rt6_bootstrap_no_plan_body_closure",
                "supports_journeys": ["A", "G", "H", "J"],
                "runtime_backed": True,
                "live_llm_invoked": False,
                "fooddb_used": False,
                "web_tavily_used": False,
                "runtime_truth_changed": False,
                "mutation_changed": False,
                "manager_context_packet_schema_changed": False,
                "product_readiness_claimed": False,
                "private_self_use_approved": False,
                "summary": {"case_count": len(cases), "passed_case_count": sum(1 for case in cases if case["status"] == "pass")},
                "cases": cases,
                "blockers": blockers,
            },
            ensure_ascii=False,
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the RT6 bootstrap/no-plan/body closure gate without live providers.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args(argv)
    artifact = build_rt6_bootstrap_no_plan_body_closure_artifact(output_path=args.output)
    output_path = Path(args.output)
    write_json_artifact(output_path, artifact)
    print(json.dumps({"artifact": str(output_path), "status": artifact["status"], "passed_case_count": artifact["summary"]["passed_case_count"], "case_count": artifact["summary"]["case_count"]}, ensure_ascii=False))
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
