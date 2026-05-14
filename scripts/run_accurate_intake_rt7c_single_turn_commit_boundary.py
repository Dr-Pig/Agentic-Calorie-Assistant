from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
import sys
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition import intake_routes  # noqa: E402
from app.composition.accurate_intake_debug_routes import build_accurate_intake_debug_payload  # noqa: E402
from app.composition.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date  # noqa: E402
from app.database import get_db, get_or_create_user  # noqa: E402
from app.models import Base  # noqa: E402
from app.routes import router  # noqa: E402
from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402
from scripts.run_accurate_intake_mvp_manager_style_smoke import DeterministicSelfUseManagerProvider  # noqa: E402


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_rt7c_single_turn_commit_boundary.json"
DEFAULT_DB_PATH = ROOT / "artifacts" / "accurate_intake_rt7c_single_turn_commit_boundary.sqlite3"


def _session(db_path: Path) -> Session:
    if db_path.exists():
        db_path.unlink()
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _bootstrap_user(db: Session, *, user_external_id: str, local_date: str) -> None:
    user = get_or_create_user(db, user_external_id)
    bootstrap_body_plan_for_date(
        db,
        user=user,
        inputs=OnboardingBootstrapInput(
            sex="female",
            age_years=34,
            height_cm=170,
            current_weight_kg=70,
            goal_type="lose_weight",
            weekly_target_rate_kg=0.5,
            timezone="Asia/Taipei",
            daily_lifestyle="sedentary_with_some_walking",
            weekly_exercise_days_band="1_2",
            local_date=local_date,
        ),
    )


def _client(db: Session, provider: DeterministicSelfUseManagerProvider) -> TestClient:
    monkey_manager = intake_routes.manager_provider
    monkey_search = intake_routes.search_provider
    monkey_extract = intake_routes.extract_provider
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
        intake_routes.manager_provider = monkey_manager
        intake_routes.search_provider = monkey_search
        intake_routes.extract_provider = monkey_extract

    client._rt7c_restore = _restore  # type: ignore[attr-defined]
    return client


def _close_client(client: TestClient) -> None:
    restore = getattr(client, "_rt7c_restore", None)
    if callable(restore):
        restore()
    else:
        client.close()


def build_rt7c_single_turn_commit_boundary_artifact(
    *,
    output_path: str | Path | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    resolved_output = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH
    resolved_db = Path(db_path) if db_path is not None else DEFAULT_DB_PATH

    db = _session(resolved_db)
    provider = DeterministicSelfUseManagerProvider()
    client: TestClient | None = None
    try:
        user_external_id = "rt7c-single-turn-commit"
        local_date = "2026-05-02"
        _bootstrap_user(db, user_external_id=user_external_id, local_date=local_date)
        client = _client(db, provider)

        response = client.post(
            "/estimate",
            json={
                "text": "chicken sandwich",
                "allow_search": False,
                "user_id": user_external_id,
                "local_date": local_date,
            },
        )
        debug_surface = build_accurate_intake_debug_payload(
            db,
            user_external_id=user_external_id,
            local_date=local_date,
        )
        payload = response.json()["payload"]
        react_trace = payload["intake_execution_manager"]["react_trace"]
        guard = react_trace["guard_result"]["phase_a_transition_guard_preflight"]
        phase_c = payload["phase_c_trace"]
        today_summary = debug_surface["model"]["today_summary"]
        same_truth = debug_surface["model"]["same_truth"]

        blockers: list[str] = []
        if response.status_code != 200:
            blockers.append("route_response_failed")
        if payload["manager_decision"]["intent_type"] != "log_meal":
            blockers.append("intent_type_mismatch")
        if payload["intake_execution_manager"]["final"]["final_action"] != "commit":
            blockers.append("manager_final_action_not_commit")
        if react_trace["manager_pass_count"] != 2:
            blockers.append("manager_pass_count_not_two")
        requested_tools = set(react_trace["requested_tools"])
        executed_tools = set(react_trace["executed_tools"])
        allowed_runtime_tools = {"estimate_nutrition", "compare_against_budget"}
        if "estimate_nutrition" not in requested_tools:
            blockers.append("estimate_tool_not_requested")
        if "estimate_nutrition" not in executed_tools:
            blockers.append("estimate_tool_not_executed")
        if requested_tools - allowed_runtime_tools:
            blockers.append("unexpected_requested_tools")
        if executed_tools - allowed_runtime_tools:
            blockers.append("unexpected_executed_tools")
        if guard["blocked"] is not False:
            blockers.append("guard_blocked_commit")
        if guard["transition_guard_verdict"] != "pass":
            blockers.append("guard_verdict_not_pass")
        if guard["mutation_effect_class"] != "canonical_write":
            blockers.append("guard_mutation_effect_class_mismatch")
        if payload["state_delta"]["canonical_commit"] is not True:
            blockers.append("state_delta_canonical_commit_missing")
        if payload["state_delta"]["meal_logged"] is not True:
            blockers.append("state_delta_meal_logged_missing")
        if payload["state_delta"]["ledger_updated"] is not True:
            blockers.append("state_delta_ledger_updated_missing")
        if payload["state_delta"]["new_meal_version_created"] is not True:
            blockers.append("state_delta_new_meal_version_missing")
        if phase_c["mutation_outcome"]["canonical_commit_status"] != "committed":
            blockers.append("phase_c_commit_status_mismatch")
        if phase_c["mutation_outcome"]["ledger_mutation_status"] != "updated":
            blockers.append("phase_c_ledger_status_mismatch")
        if int(today_summary["consumed_kcal"] or 0) != 480:
            blockers.append("today_summary_consumed_kcal_mismatch")
        if same_truth["status"] != "pass":
            blockers.append("same_truth_not_pass")
        if provider.readiness()["live_llm_invoked"] is not False:
            blockers.append("live_llm_invoked_truth_drift")
        if len(provider.calls) < 2:
            blockers.append("provider_call_count_too_small")

        artifact = {
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
            "gate_id": "accurate_intake_rt7c_single_turn_commit_boundary",
            "claim_scope": "manager_runtime_rt7c_single_turn_commit_boundary",
            "status": "pass" if not blockers else "fail",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "target_manager_runtime_gate": "rt7c_single_turn_commit_boundary",
            "supports_journeys": ["B"],
            "runtime_backed": True,
            "live_llm_invoked": False,
            "fooddb_used": False,
            "web_tavily_used": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_schema_changed": False,
            "summary": {"case_count": 1, "passed_case_count": 1 if not blockers else 0},
            "case": {
                "case_id": "single_turn_commit_boundary",
                "status": "pass" if not blockers else "fail",
                "blockers": blockers,
                "manager_pass_count": react_trace["manager_pass_count"],
                "requested_tools": react_trace["requested_tools"],
                "executed_tools": react_trace["executed_tools"],
                "transition_guard_verdict": guard["transition_guard_verdict"],
                "canonical_commit_status": phase_c["mutation_outcome"]["canonical_commit_status"],
                "same_truth_status": same_truth["status"],
            },
            "blockers": blockers,
        }
        return json.loads(json.dumps(artifact, ensure_ascii=False))
    finally:
        if client is not None:
            _close_client(client)
        db.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run RT7c single-turn commit boundary gate.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    args = parser.parse_args(argv)
    artifact = build_rt7c_single_turn_commit_boundary_artifact(
        output_path=args.output,
        db_path=args.db_path,
    )
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
