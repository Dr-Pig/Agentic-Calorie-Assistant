from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition import intake_routes  # noqa: E402
from app.composition.manager_context_runtime import build_runtime_manager_context_packet_v1  # noqa: E402
from app.composition.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date  # noqa: E402
from app.composition.state_resolver import resolve_intake_state  # noqa: E402
from app.database import get_db, get_or_create_user  # noqa: E402
from app.intake.application.current_turn_context_assembler import build_current_turn_context_v1  # noqa: E402
from app.models import Base  # noqa: E402
from app.routes import router  # noqa: E402
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_rt7b_blocking_clarify_pending_followup_boundary.json"
FOLLOWUP_QUESTION = "Which items and portions should I estimate?"
INITIAL_TEXT = "I ate luwei"
FOLLOWUP_TEXT = "Tofu skin and fish cake."


class AskFollowupManagerFixtureProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def readiness(self) -> dict[str, Any]:
        return {
            "configured": True,
            "provider": "rt7b_ask_followup_fixture",
            "live_llm_invoked": False,
        }

    async def complete_with_trace(
        self,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        user_payload = dict(kwargs.get("user_payload") or {})
        self.calls.append(
            {
                "available_tools": list(user_payload.get("available_tools") or []),
                "tool_results": list(user_payload.get("tool_results") or []),
                "round_index": user_payload.get("round_index"),
            }
        )
        return (
            {
                "manager_action": "final",
                "intent": "log_meal",
                "intent_type": "log_meal",
                "final_action": "ask_followup",
                "workflow_effect": "ask_followup",
                "target_attachment": {"mode": "new_meal"},
                "exactness": "unknown",
                "confidence": "medium",
                "evidence_posture": "composition_unknown",
                "repair_ack": False,
                "answer_contract": {
                    "reply_text": FOLLOWUP_QUESTION,
                    "followup_question": FOLLOWUP_QUESTION,
                },
                "response_summary": "ask_followup",
                "uncertainty_posture": "high",
                "evidence_honesty_posture": "insufficient_details",
                "semantic_decision": {
                    "semantic_authority": "deterministic_fake_provider",
                    "current_turn_intent": "log_meal",
                    "target_attachment": {"mode": "new_meal"},
                    "workflow_effect": "ask_followup",
                    "final_action_candidate": "ask_followup",
                    "estimation_posture": "insufficient_details",
                    "followup_posture": "ask_required",
                    "followup_question": FOLLOWUP_QUESTION,
                    "mutation_intent_candidate": "no_mutation",
                    "uncertainty_posture": "high",
                    "source": "rt7b_ask_followup_fixture",
                    "semantic_owner": "manager",
                    "deterministic_role": "fixture_simulates_manager_output_only",
                },
                "tool_calls": [],
            },
            {
                "source": "rt7b_ask_followup_fixture",
                "live_llm_invoked": False,
            },
        )


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


def _client(db: Session, provider: AskFollowupManagerFixtureProvider) -> TestClient:
    previous_manager_provider = intake_routes.manager_provider
    previous_search_provider = intake_routes.search_provider
    previous_extract_provider = intake_routes.extract_provider
    intake_routes.manager_provider = provider
    intake_routes.search_provider = None
    intake_routes.extract_provider = None

    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    def _restore() -> None:
        client.close()
        intake_routes.manager_provider = previous_manager_provider
        intake_routes.search_provider = previous_search_provider
        intake_routes.extract_provider = previous_extract_provider

    client._rt7b_restore = _restore  # type: ignore[attr-defined]
    return client


def _bootstrap_user(db: Session, *, user_external_id: str, local_date: str) -> None:
    user = get_or_create_user(db, user_external_id)
    bootstrap_body_plan_for_date(db, user=user, inputs=_bootstrap_inputs(local_date=local_date))


def _run_seeded_blocking_clarify_route(
    *,
    user_external_id: str,
    local_date: str,
) -> tuple[Session, TestClient, AskFollowupManagerFixtureProvider, dict[str, Any]]:
    db = _session()
    provider = AskFollowupManagerFixtureProvider()
    _bootstrap_user(db, user_external_id=user_external_id, local_date=local_date)
    client = _client(db, provider)
    response = client.post(
        "/estimate",
        json={
            "text": INITIAL_TEXT,
            "allow_search": False,
            "user_id": user_external_id,
            "local_date": local_date,
        },
    )
    return db, client, provider, {"status_code": response.status_code, "json": response.json()}


def _close_client(client: TestClient) -> None:
    restore = getattr(client, "_rt7b_restore", None)
    if callable(restore):
        restore()
    else:
        client.close()


def _blocking_clarify_route_no_commit_case() -> dict[str, Any]:
    db, client, provider, response = _run_seeded_blocking_clarify_route(
        user_external_id="rt7b-blocking-clarify",
        local_date="2026-05-07",
    )
    try:
        payload = response["json"]["payload"]
        blockers = []
        if response["status_code"] != 200:
            blockers.append("blocking_clarify_route_failed")
        if payload["manager_decision"]["intent_type"] != "log_meal":
            blockers.append("blocking_clarify_intent_type_mismatch")
        if payload["manager_decision"]["workflow_effect"] != "ask_followup":
            blockers.append("blocking_clarify_workflow_effect_mismatch")
        if payload["intake_execution_manager"]["final"]["final_action"] != "ask_followup":
            blockers.append("blocking_clarify_final_action_mismatch")
        entry_tools = set(provider.calls[0]["available_tools"])
        expected_read_tools = {"budget.get_today_summary", "budget.get_remaining_calories"}
        forbidden_entry_tools = {"estimate_nutrition", "compare_against_budget", "resolve_correction_target"}
        if not expected_read_tools.issubset(entry_tools):
            blockers.append("blocking_clarify_phase_a_read_tool_inventory_missing")
        if entry_tools.intersection(forbidden_entry_tools):
            blockers.append("blocking_clarify_phase_a_mutation_tool_leaked")
        if "estimate_nutrition" not in provider.calls[1]["available_tools"]:
            blockers.append("blocking_clarify_runtime_tool_inventory_missing_estimate")
        if provider.calls[1]["tool_results"]:
            blockers.append("blocking_clarify_executed_tools_before_followup")
        if payload["state_delta"]["canonical_commit"] is not False:
            blockers.append("blocking_clarify_canonical_commit_changed")
        if payload["state_delta"]["draft_saved"] is not True:
            blockers.append("blocking_clarify_draft_not_saved")
        if payload["state_delta"]["meal_logged"] is not False:
            blockers.append("blocking_clarify_meal_logged_truth_drift")
        if payload["state_delta"]["ledger_updated"] is not False:
            blockers.append("blocking_clarify_ledger_updated")
        mutation_outcome = payload["phase_c_trace"]["mutation_outcome"]
        if mutation_outcome["canonical_commit_status"] != "not_committed":
            blockers.append("blocking_clarify_mutation_outcome_commit_status")
        if mutation_outcome["draft_status"] != "saved":
            blockers.append("blocking_clarify_mutation_outcome_draft_status")
        return {
            "case_id": "blocking_clarify_route_no_commit",
            "status": "pass" if not blockers else "fail",
            "blockers": blockers,
        }
    finally:
        _close_client(client)
        db.close()


def _pending_followup_persisted_case() -> dict[str, Any]:
    db, client, _provider, response = _run_seeded_blocking_clarify_route(
        user_external_id="rt7b-pending-followup",
        local_date="2026-05-07",
    )
    try:
        payload = response["json"]["payload"]
        conversation_state = payload["state_after"]["conversation_state"]
        pending_followup_state = conversation_state["pending_followup_state"]
        session_summary = conversation_state["session_summary"]
        blockers = []
        if conversation_state["latest_log_status"] != "draft_unresolved":
            blockers.append("pending_followup_latest_log_status_mismatch")
        if conversation_state["pending_question"] != FOLLOWUP_QUESTION:
            blockers.append("pending_followup_question_not_persisted")
        if pending_followup_state["is_open"] is not True:
            blockers.append("pending_followup_state_not_open")
        if pending_followup_state["pending_question"] != FOLLOWUP_QUESTION:
            blockers.append("pending_followup_state_question_mismatch")
        if session_summary["pending_followup"]["is_open"] is not True:
            blockers.append("session_summary_pending_followup_missing")
        if session_summary["active_meal"]["status"] != "draft_unresolved":
            blockers.append("session_summary_active_meal_status_mismatch")
        return {
            "case_id": "pending_followup_persisted",
            "status": "pass" if not blockers else "fail",
            "blockers": blockers,
        }
    finally:
        _close_client(client)
        db.close()


def _next_turn_context_packet_case() -> dict[str, Any]:
    db, client, _provider, _response = _run_seeded_blocking_clarify_route(
        user_external_id="rt7b-next-turn-context",
        local_date="2026-05-07",
    )
    try:
        state = resolve_intake_state(
            db,
            user_external_id="rt7b-next-turn-context",
            local_date="2026-05-07",
            incoming_user_text=FOLLOWUP_TEXT,
        )
        current_turn_context = build_current_turn_context_v1(
            raw_user_input=FOLLOWUP_TEXT,
            resolved_state=state,
        )
        packet = build_runtime_manager_context_packet_v1(
            db=db,
            current_turn_context=current_turn_context,
            user_external_id="rt7b-next-turn-context",
            local_date="2026-05-07",
            session_id="rt7b-next-turn-context-session",
        )
        blockers = []
        if current_turn_context.pending_followup.get("is_open") is not True:
            blockers.append("next_turn_context_missing_pending_followup")
        if packet["context_loading_artifact"]["loaded_context_summary"]["pending_followup_present"] is not True:
            blockers.append("next_turn_packet_missing_pending_followup_summary")
        if packet["hard_pins"]["pending_followup"]["is_open"] is not True:
            blockers.append("next_turn_packet_missing_pending_followup_hard_pin")
        if packet["hard_pins"]["pending_draft"] is not None:
            blockers.append("next_turn_packet_unexpected_pending_draft_authority")
        if packet["target_candidates"]["for_correction_or_removal"]:
            blockers.append("next_turn_packet_guessed_correction_targets")
        if len(packet["recent_chat_window"]["messages"]) != 2:
            blockers.append("next_turn_packet_recent_chat_window_mismatch")
        return {
            "case_id": "next_turn_context_packet_pending_followup",
            "status": "pass" if not blockers else "fail",
            "blockers": blockers,
        }
    finally:
        _close_client(client)
        db.close()


def build_rt7b_blocking_clarify_pending_followup_boundary_artifact(
    *,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    cases = [
        _blocking_clarify_route_no_commit_case(),
        _pending_followup_persisted_case(),
        _next_turn_context_packet_case(),
    ]
    blockers = [f"{case['case_id']}.{blocker}" for case in cases for blocker in case["blockers"]]
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
                "gate_id": "accurate_intake_rt7b_blocking_clarify_pending_followup_boundary",
                "claim_scope": "manager_runtime_rt7b_blocking_clarify_pending_followup_boundary",
                "status": "pass" if not blockers else "fail",
                "generated_at_utc": datetime.now(UTC).isoformat(),
                "target_manager_runtime_gate": "rt7b_blocking_clarify_pending_followup_boundary",
                "supports_journeys": ["D"],
                "runtime_backed": True,
                "live_llm_invoked": False,
                "fooddb_used": False,
                "web_tavily_used": False,
                "runtime_truth_changed": False,
                "mutation_changed": False,
                "manager_context_packet_schema_changed": False,
                "summary": {
                    "case_count": len(cases),
                    "passed_case_count": sum(1 for case in cases if case["status"] == "pass"),
                },
                "cases": cases,
                "blockers": blockers,
            },
            ensure_ascii=False,
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run RT7b blocking clarify and pending followup boundary gate.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args(argv)
    artifact = build_rt7b_blocking_clarify_pending_followup_boundary_artifact(output_path=args.output)
    output_path = Path(args.output)
    write_json_artifact(output_path, artifact)
    print(
        json.dumps(
            {
                "artifact": str(output_path),
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
