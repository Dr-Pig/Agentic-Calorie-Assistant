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
from app.composition.accurate_intake_debug_routes import build_accurate_intake_debug_payload  # noqa: E402
from app.composition.manager_context_runtime import build_runtime_manager_context_packet_v1  # noqa: E402
from app.composition.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date  # noqa: E402
from app.composition.state_resolver import resolve_intake_state  # noqa: E402
from app.database import get_db, get_or_create_user  # noqa: E402
from app.intake.application.current_turn_context_assembler import build_current_turn_context_v1  # noqa: E402
from app.models import Base  # noqa: E402
from app.routes import router  # noqa: E402
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_rt7d_optional_refinement_attach_boundary.json"
INITIAL_TEXT = "bubble milk tea"
REFINEMENT_TEXT = "that milk tea half sugar"
FOLLOWUP_QUESTION = "What size and sugar level was it?"


class OptionalRefinementAttachFixtureProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def readiness(self) -> dict[str, Any]:
        return {
            "configured": True,
            "provider": "rt7d_optional_refinement_fixture",
            "live_llm_invoked": False,
        }

    async def complete_with_trace(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        user_payload = dict(kwargs.get("user_payload") or {})
        tool_results = list(user_payload.get("tool_results") or [])
        self.calls.append(
            {
                "raw_user_input": user_payload.get("raw_user_input"),
                "available_tools": list(user_payload.get("available_tools") or []),
                "tool_results": tool_results,
                "round_index": user_payload.get("round_index"),
                "current_turn_context": user_payload.get("phase_a_current_turn_context"),
                "manager_context_pack": user_payload.get("phase_a_manager_context_pack"),
                "manager_context_packet_v1": user_payload.get("manager_context_packet_v1"),
            }
        )
        available_tools = {str(item) for item in user_payload.get("available_tools") or []}
        raw = str(user_payload.get("raw_user_input") or "").strip().lower()
        if {"budget.get_today_summary", "budget.get_remaining_calories"}.intersection(available_tools):
            return self._entry_decision(), self._trace("entry_decision")
        if not _has_tool_result(tool_results, "estimate_nutrition") and "estimate_nutrition" in available_tools:
            return self._tool_request(available_tools), self._trace("tool_request")
        if raw == REFINEMENT_TEXT:
            return self._refinement_final(), self._trace("refinement_final")
        return self._initial_commit_final(), self._trace("initial_commit_final")

    def _trace(self, stage: str) -> dict[str, Any]:
        return {
            "source": "rt7d_optional_refinement_fixture",
            "stage": stage,
            "live_llm_invoked": False,
        }

    def _entry_decision(self) -> dict[str, Any]:
        return {
            "manager_action": "final",
            "intent": "log_meal",
            "intent_type": "log_meal",
            "final_action": "no_commit",
            "workflow_effect": "route_to_intake",
            "target_attachment": {"mode": "new_meal"},
            "exactness": "unknown",
            "confidence": "medium",
            "evidence_posture": "needs_tool_evidence",
            "repair_ack": False,
            "answer_contract": {"reply_text": "route_to_intake"},
            "semantic_decision": {
                "semantic_authority": "deterministic_fake_provider",
                "current_turn_intent": "log_meal",
                "target_attachment": {"mode": "new_meal"},
                "workflow_effect": "route_to_intake",
                "final_action_candidate": "commit",
                "estimation_posture": "needs_tool_evidence",
                "followup_posture": "none",
                "followup_targets": [],
                "mutation_intent_candidate": "canonical_write",
                "uncertainty_posture": "bounded",
                "source": "rt7d_optional_refinement_fixture",
                "semantic_owner": "manager",
                "deterministic_role": "fixture_simulates_manager_output_only",
            },
        }

    def _tool_request(self, available_tools: set[str]) -> dict[str, Any]:
        tool_calls = [{"name": "estimate_nutrition"}]
        if "compare_against_budget" in available_tools:
            tool_calls.append({"name": "compare_against_budget"})
        return {
            "manager_action": "call_tools",
            "response_mode": "tool_call",
            "tool_calls": tool_calls,
        }

    def _initial_commit_final(self) -> dict[str, Any]:
        return {
            "manager_action": "final",
            "intent": "log_meal",
            "intent_type": "log_meal",
            "final_action": "commit",
            "workflow_effect": "estimate_with_followup",
            "target_attachment": {"mode": "new_meal"},
            "exactness": "generic_with_uncertainty",
            "confidence": "medium",
            "evidence_posture": "tool_evidence_present",
            "repair_ack": False,
            "answer_contract": {
                "reply_text": "Logged a milk tea estimate.",
                "followup_question": FOLLOWUP_QUESTION,
            },
            "semantic_decision": {
                "semantic_authority": "deterministic_fake_provider",
                "current_turn_intent": "log_meal",
                "target_attachment": {"mode": "new_meal"},
                "workflow_effect": "estimate_with_followup",
                "final_action_candidate": "commit",
                "estimation_posture": "estimable_with_optional_refinement",
                "followup_posture": "refinement_optional",
                "followup_question": FOLLOWUP_QUESTION,
                "followup_targets": [],
                "mutation_intent_candidate": "canonical_write",
                "uncertainty_posture": "bounded",
                "source": "rt7d_optional_refinement_fixture",
                "semantic_owner": "manager",
                "deterministic_role": "fixture_simulates_manager_output_only",
            },
        }

    def _refinement_final(self) -> dict[str, Any]:
        return {
            "manager_action": "final",
            "intent": "log_meal",
            "intent_type": "log_meal",
            "final_action": "correction_applied",
            "workflow_effect": "same_item_refinement",
            "target_attachment": {"mode": "target_committed_thread"},
            "exactness": "near_exact",
            "confidence": "high",
            "evidence_posture": "tool_evidence_present",
            "repair_ack": False,
            "answer_contract": {"reply_text": "Updated the milk tea estimate."},
            "semantic_decision": {
                "semantic_authority": "deterministic_fake_provider",
                "current_turn_intent": "correct_meal",
                "target_attachment": {"mode": "target_committed_thread"},
                "workflow_effect": "same_item_refinement",
                "final_action_candidate": "correction_applied",
                "estimation_posture": "refinement_attached_to_existing_item",
                "followup_posture": "none",
                "followup_targets": [],
                "mutation_intent_candidate": "correction_write",
                "uncertainty_posture": "bounded",
                "source": "rt7d_optional_refinement_fixture",
                "semantic_owner": "manager",
                "deterministic_role": "fixture_simulates_manager_output_only",
            },
        }


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


def _bootstrap_user(db: Session, *, user_external_id: str, local_date: str) -> None:
    user = get_or_create_user(db, user_external_id)
    bootstrap_body_plan_for_date(db, user=user, inputs=_bootstrap_inputs(local_date=local_date))


def _client(db: Session, provider: OptionalRefinementAttachFixtureProvider) -> TestClient:
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

    client._rt7d_restore = _restore  # type: ignore[attr-defined]
    return client


def _close_client(client: TestClient) -> None:
    restore = getattr(client, "_rt7d_restore", None)
    if callable(restore):
        restore()
    else:
        client.close()


def _has_tool_result(tool_results: list[Any], tool_name: str) -> bool:
    for result in tool_results:
        if not isinstance(result, dict):
            continue
        name = str(result.get("tool_name") or result.get("name") or "").strip()
        if name == tool_name and not result.get("failure_family"):
            return True
    return False


def _seed_and_first_commit() -> tuple[Session, TestClient, OptionalRefinementAttachFixtureProvider, dict[str, Any]]:
    db = _session()
    provider = OptionalRefinementAttachFixtureProvider()
    user_external_id = "rt7d-optional-refinement"
    local_date = "2026-05-07"
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


def _first_runtime_estimate_call(provider: OptionalRefinementAttachFixtureProvider) -> dict[str, Any] | None:
    return next(
        (
            call
            for call in provider.calls
            if str(call.get("raw_user_input") or "") == INITIAL_TEXT
            and "estimate_nutrition" in set(call.get("available_tools") or [])
        ),
        None,
    )


def _second_runtime_estimate_call(provider: OptionalRefinementAttachFixtureProvider) -> dict[str, Any] | None:
    return next(
        (
            call
            for call in provider.calls
            if str(call.get("raw_user_input") or "") == REFINEMENT_TEXT
            and "estimate_nutrition" in set(call.get("available_tools") or [])
        ),
        None,
    )


def _initial_commit_with_optional_followup_case() -> dict[str, Any]:
    db, client, provider, response = _seed_and_first_commit()
    try:
        payload = response["json"]["payload"]
        mutation_outcome = payload["phase_c_trace"]["mutation_outcome"]
        conversation_state = payload["state_after"]["conversation_state"]
        runtime_call = _first_runtime_estimate_call(provider)
        blockers: list[str] = []
        if response["status_code"] != 200:
            blockers.append("initial_route_failed")
        if payload["manager_decision"]["intent_type"] != "log_meal":
            blockers.append("initial_manager_intent_mismatch")
        if payload["intake_execution_manager"]["final"]["final_action"] != "commit":
            blockers.append("initial_final_action_not_commit")
        if payload["intake_execution_manager"]["final"]["workflow_effect"] != "estimate_with_followup":
            blockers.append("initial_workflow_effect_not_optional_refinement")
        if runtime_call is None:
            blockers.append("initial_runtime_estimate_call_missing")
        if payload["state_delta"]["canonical_commit"] is not True:
            blockers.append("initial_canonical_commit_missing")
        if payload["state_delta"]["meal_logged"] is not True:
            blockers.append("initial_meal_logged_missing")
        if payload["state_delta"]["draft_saved"] is not False:
            blockers.append("initial_draft_saved_truth_drift")
        if payload["state_delta"]["ledger_updated"] is not True:
            blockers.append("initial_ledger_update_missing")
        if mutation_outcome["canonical_commit_status"] != "committed":
            blockers.append("initial_mutation_outcome_not_committed")
        if conversation_state["pending_followup_state"]["is_open"] is not True:
            blockers.append("initial_pending_followup_not_open")
        if conversation_state["pending_followup_state"]["pending_question"] != FOLLOWUP_QUESTION:
            blockers.append("initial_pending_followup_question_mismatch")
        if conversation_state["latest_log_status"] != "completed_meal":
            blockers.append("initial_latest_log_status_mismatch")
        return {
            "case_id": "initial_commit_with_optional_followup",
            "status": "pass" if not blockers else "fail",
            "blockers": blockers,
            "committed_kcal": payload["state_after"]["current_budget_view"]["consumed_kcal"],
        }
    finally:
        _close_client(client)
        db.close()


def _next_turn_context_packet_case() -> dict[str, Any]:
    db, client, _provider, _response = _seed_and_first_commit()
    try:
        state = resolve_intake_state(
            db,
            user_external_id="rt7d-optional-refinement",
            local_date="2026-05-07",
            incoming_user_text=REFINEMENT_TEXT,
        )
        current_turn_context = build_current_turn_context_v1(
            raw_user_input=REFINEMENT_TEXT,
            resolved_state=state,
        )
        packet = build_runtime_manager_context_packet_v1(
            db=db,
            current_turn_context=current_turn_context,
            user_external_id="rt7d-optional-refinement",
            local_date="2026-05-07",
            session_id="rt7d-optional-refinement-session",
        )
        blockers: list[str] = []
        pending_followup = dict(current_turn_context.pending_followup or {})
        packet_pending_followup = dict((packet.get("hard_pins") or {}).get("pending_followup") or {})
        if pending_followup.get("is_open") is not True:
            blockers.append("next_turn_pending_followup_missing")
        if current_turn_context.open_workflow_type != "meal_followup":
            blockers.append("next_turn_open_workflow_type_mismatch")
        if current_turn_context.candidate_attachment_targets != [
            {
                "target_object_type": "meal_thread",
                "target_object_id": "1",
                "source": "pending_followup_state",
                "confidence": "high",
                "mutation_authority": False,
            }
        ]:
            blockers.append("next_turn_candidate_attachment_targets_mismatch")
        posture = current_turn_context.target_resolution_posture
        if posture.get("target_resolution_source") != "pending_followup_state":
            blockers.append("next_turn_target_resolution_source_mismatch")
        if posture.get("item_resolution_source") != "single_active_item":
            blockers.append("next_turn_item_resolution_source_mismatch")
        if packet_pending_followup.get("pending_question") != FOLLOWUP_QUESTION:
            blockers.append("next_turn_packet_pending_followup_missing")
        if packet["hard_pins"]["pending_draft"] is not None:
            blockers.append("next_turn_packet_unexpected_pending_draft")
        if packet["context_loading_artifact"]["loaded_context_summary"]["target_candidate_count"] != 1:
            blockers.append("next_turn_packet_target_candidate_count_mismatch")
        return {
            "case_id": "next_turn_context_packet_optional_refinement",
            "status": "pass" if not blockers else "fail",
            "blockers": blockers,
        }
    finally:
        _close_client(client)
        db.close()


def _optional_refinement_supersedes_same_thread_case() -> dict[str, Any]:
    db, client, provider, _response = _seed_and_first_commit()
    try:
        second_response = client.post(
            "/estimate",
            json={
                "text": REFINEMENT_TEXT,
                "allow_search": False,
                "user_id": "rt7d-optional-refinement",
                "local_date": "2026-05-07",
            },
        )
        payload = second_response.json()["payload"]
        mutation_outcome = payload["phase_c_trace"]["mutation_outcome"]
        debug_surface = build_accurate_intake_debug_payload(
            db,
            user_external_id="rt7d-optional-refinement",
            local_date="2026-05-07",
        )
        today_summary = debug_surface["model"]["today_summary"]
        same_truth = debug_surface["model"]["same_truth"]
        meal_threads = debug_surface["model"]["meal_threads"]
        runtime_call = _second_runtime_estimate_call(provider)
        blockers: list[str] = []
        if second_response.status_code != 200:
            blockers.append("refinement_route_failed")
        if payload["intake_execution_manager"]["final"]["final_action"] != "correction_applied":
            blockers.append("refinement_final_action_mismatch")
        if payload["intake_execution_manager"]["final"]["workflow_effect"] != "same_item_refinement":
            blockers.append("refinement_workflow_effect_mismatch")
        if payload["state_delta"]["canonical_commit"] is not True:
            blockers.append("refinement_canonical_commit_missing")
        if payload["state_delta"]["old_version_superseded"] is not True:
            blockers.append("refinement_old_version_not_superseded")
        if payload["state_delta"]["ledger_updated"] is not True:
            blockers.append("refinement_ledger_update_missing")
        if mutation_outcome["canonical_commit_status"] != "committed":
            blockers.append("refinement_mutation_outcome_not_committed")
        if mutation_outcome["meal_version_delta"] != "superseded_previous":
            blockers.append("refinement_meal_version_delta_mismatch")
        active_total_kcal = int(meal_threads[0]["active_version"]["total_kcal"] or 0) if len(meal_threads) == 1 else None
        if active_total_kcal is None or int(today_summary["consumed_kcal"] or 0) != active_total_kcal:
            blockers.append("refinement_today_summary_consumed_kcal_mismatch")
        if same_truth["status"] != "pass":
            blockers.append("refinement_same_truth_not_pass")
        if len(meal_threads) != 1:
            blockers.append("refinement_meal_thread_count_mismatch")
        elif "milk tea" not in str(meal_threads[0]["active_version"]["items"][0]["name"] or ""):
            blockers.append("refinement_active_item_name_mismatch")
        if runtime_call is None:
            blockers.append("refinement_runtime_estimate_call_missing")
        else:
            packet = dict(runtime_call.get("manager_context_packet_v1") or {})
            hard_pins = dict(packet.get("hard_pins") or {})
            active_day_state = dict(packet.get("active_day_state") or {})
            target_candidates = dict(packet.get("target_candidates") or {})
            pending_followup = dict(hard_pins.get("pending_followup") or {})
            active_meal_ref = dict(active_day_state.get("active_meal_thread_ref") or {})
            tool_results = [item for item in list(runtime_call.get("tool_results") or []) if isinstance(item, dict)]
            correction_sources = {
                str(dict(dict(item.get("provenance") or {}).get("correction_target") or {}).get("target_resolution_source") or "")
                for item in tool_results
            }
            if pending_followup.get("pending_question") != FOLLOWUP_QUESTION:
                blockers.append("refinement_runtime_missing_pending_followup")
            if str(active_meal_ref.get("meal_thread_id") or "") != "1":
                blockers.append("refinement_runtime_candidate_target_missing")
            if int(target_candidates.get("candidate_count") or 0) < 1:
                blockers.append("refinement_runtime_target_candidate_count_missing")
            if "pending_followup_state" not in correction_sources:
                blockers.append("refinement_runtime_target_resolution_posture_missing")
            if packet.get("hard_pins", {}).get("pending_draft") is not None:
                blockers.append("refinement_runtime_unexpected_pending_draft")
        return {
            "case_id": "optional_refinement_supersedes_same_thread",
            "status": "pass" if not blockers else "fail",
            "blockers": blockers,
            "refined_consumed_kcal": int(today_summary["consumed_kcal"] or 0),
            "same_truth_status": same_truth["status"],
        }
    finally:
        _close_client(client)
        db.close()


def build_rt7d_optional_refinement_attach_boundary_artifact(
    *,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    cases = [
        _initial_commit_with_optional_followup_case(),
        _next_turn_context_packet_case(),
        _optional_refinement_supersedes_same_thread_case(),
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
                "gate_id": "accurate_intake_rt7d_optional_refinement_attach_boundary",
                "claim_scope": "manager_runtime_rt7d_optional_refinement_attach_boundary",
                "status": "pass" if not blockers else "fail",
                "generated_at_utc": datetime.now(UTC).isoformat(),
                "target_manager_runtime_gate": "rt7d_optional_refinement_attach_boundary",
                "supports_journeys": ["C"],
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
    parser = argparse.ArgumentParser(description="Run RT7d optional refinement attach boundary gate.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args(argv)
    artifact = build_rt7d_optional_refinement_attach_boundary_artifact(output_path=args.output)
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
