from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.composition import intake_routes
from app.composition.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date
from app.database import get_db, get_or_create_user
from app.models import Base
from app.routes import router
from scripts.run_accurate_intake_mvp_manager_style_smoke import DeterministicSelfUseManagerProvider

DEFAULT_DB_PATH = ROOT / ".pytest_tmp_local" / "accurate_intake_local_web_shell_bridge.sqlite3"
DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_local_web_shell_bridge.json"
NOT_CLAIMING = [
    "product_ready",
    "rollout_ready",
    "live_llm_ready",
    "web_ready",
    "production_db_ready",
]


def _session_factory(db_path: Path) -> tuple[Any, sessionmaker[Session]]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return engine, sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _seed_body_plan(db: Session, *, user_external_id: str, local_date: str) -> None:
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


def _build_test_client(db: Session, provider: DeterministicSelfUseManagerProvider) -> TestClient:
    previous_manager_provider = intake_routes.manager_provider
    previous_search_provider = intake_routes.search_provider
    previous_extract_provider = intake_routes.extract_provider
    try:
        intake_routes.manager_provider = provider
        intake_routes.search_provider = None
        intake_routes.extract_provider = None

        app = FastAPI()
        app.include_router(router)
        app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

        def override_get_db():
            yield db

        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)
        client._accurate_intake_restore_runtime = (  # type: ignore[attr-defined]
            previous_manager_provider,
            previous_search_provider,
            previous_extract_provider,
        )
        return client
    except Exception:
        intake_routes.manager_provider = previous_manager_provider
        intake_routes.search_provider = previous_search_provider
        intake_routes.extract_provider = previous_extract_provider
        raise


def _close_test_client(client: TestClient) -> None:
    previous = getattr(client, "_accurate_intake_restore_runtime", None)
    client.close()
    if previous is not None:
        intake_routes.manager_provider, intake_routes.search_provider, intake_routes.extract_provider = previous


def _json(response: Any) -> dict[str, Any]:
    return response.json() if response.content else {}


def _status(response: Any) -> dict[str, Any]:
    return {
        "status_code": response.status_code,
        "ok": bool(response.status_code < 400),
    }


def _validate(report: dict[str, Any]) -> tuple[str, list[str]]:
    blockers: list[str] = []
    if not report["static_shell"]["ok"]:
        blockers.append("static_shell_not_served")
    if report["static_shell"].get("contains_shell_id") is not True:
        blockers.append("static_shell_missing_boundary_markers")
    if report["backend_local_date_source"] != "today_current_budget":
        blockers.append("backend_local_date_not_read_model_owned")
    if report["manual_target"]["ok"] is not True:
        blockers.append("manual_target_endpoint_failed")
    if report["estimate"]["ok"] is not True:
        blockers.append("estimate_endpoint_failed")
    if report["debug"]["ok"] is not True:
        blockers.append("debug_endpoint_failed")
    if report["today_after_estimate"].get("consumed_kcal", 0) <= 0:
        blockers.append("today_budget_not_updated_after_estimate")
    if report["debug"].get("same_truth_status") != "pass":
        blockers.append("debug_same_truth_failed")
    if report["chat_history"].get("ok") is not True:
        blockers.append("chat_history_endpoint_failed")
    if report["chat_history"].get("source") != "sqlite_message_buffer":
        blockers.append("chat_history_not_sqlite_backed")
    if report["chat_history"].get("frontend_semantic_owner") is not False:
        blockers.append("chat_history_frontend_semantic_owner")
    if report["chat_history"].get("runtime_turn_trace_present") is not True:
        blockers.append("chat_history_missing_runtime_turn_trace")
    if report["chat_history"].get("context_snapshot_present") is not True:
        blockers.append("chat_history_missing_context_snapshot")
    if report["chat_history"].get("trace_chain_complete") is not True:
        blockers.append("chat_history_trace_chain_incomplete")
    if report["provider"]["live_llm_invoked"] is not False:
        blockers.append("live_llm_invoked")
    if report["frontend_semantic_owner"] is not False:
        blockers.append("frontend_claimed_semantic_ownership")
    return ("pass" if not blockers else "fail"), blockers


def build_local_web_shell_bridge_report(
    *,
    db_path: Path = DEFAULT_DB_PATH,
    user_external_id: str = "local-web-shell-smoke-user",
    reset_db: bool = True,
) -> dict[str, Any]:
    if reset_db and db_path.exists():
        db_path.unlink()
    engine, SessionLocal = _session_factory(db_path)
    provider = DeterministicSelfUseManagerProvider()
    db = SessionLocal()
    client: TestClient | None = None
    try:
        client = _build_test_client(db, provider)
        initial_budget_response = client.get("/today/current-budget", params={"user_id": user_external_id})
        initial_budget = _json(initial_budget_response)
        backend_local_date = str(initial_budget.get("local_date") or "")
        if backend_local_date:
            _seed_body_plan(db, user_external_id=user_external_id, local_date=backend_local_date)

        static_response = client.get("/static/accurate-intake-local-shell.html")
        static_text = static_response.text
        budget_response = client.get("/today/current-budget", params={"user_id": user_external_id})
        budget = _json(budget_response)
        backend_local_date = str(budget.get("local_date") or backend_local_date)
        manual_target_response = client.post(
            "/body-plan/manual-daily-target",
            json={
                "user_id": user_external_id,
                "daily_target_kcal": 1600,
                "local_date": backend_local_date,
                "source": "user_ui",
            },
        )
        estimate_response = client.post(
            "/estimate",
            json={
                "text": "chicken sandwich",
                "user_id": user_external_id,
                "allow_search": False,
            },
            headers={"X-Canary-Page-Version": "accurate-intake-local-shell.v1"},
        )
        today_after_response = client.get("/today/current-budget", params={"user_id": user_external_id})
        debug_response = client.get(
            "/accurate-intake/debug",
            params={"user_id": user_external_id, "local_date": backend_local_date},
        )
        debug_payload = _json(debug_response)
        debug_model = dict(debug_payload.get("model") or {})
        same_truth = dict(debug_model.get("same_truth") or {})
        today_after = _json(today_after_response)
        chat_history_response = client.get(
            "/accurate-intake/chat-history",
            params={"user_id": user_external_id, "local_date": backend_local_date},
        )
        chat_history_payload = _json(chat_history_response)
        chat_history_messages = list(chat_history_payload.get("messages") or [])

        report: dict[str, Any] = {
            "artifact_schema_version": "1.0",
            "route_bridge_id": "accurate_intake_local_web_shell_route_bridge_v1",
            "claim_scope": "local_deterministic_web_shell_route_bridge_smoke",
            "evidence_scope": "server_route_compatibility_not_browser_execution",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "not_claiming": list(NOT_CLAIMING),
            "user_external_id": user_external_id,
            "db_path": str(db_path),
            "static_shell": {
                **_status(static_response),
                "path": "/static/accurate-intake-local-shell.html",
                "contains_shell_id": 'data-shell-id="accurate-intake-local-shell-v1"' in static_text,
                "contains_frontend_non_owner_marker": 'data-frontend-semantic-owner="false"' in static_text,
            },
            "backend_local_date": backend_local_date,
            "backend_local_date_source": "today_current_budget",
            "frontend_semantic_owner": False,
            "browser_executed": False,
            "browser_execution_required": False,
            "deferred_evidence": ["browser_executed_fetch_sequence"],
            "live_llm_invoked": False,
            "production_db_used": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "production_selected": False,
            "provider": provider.readiness(),
            "initial_budget": {
                **_status(budget_response),
                "local_date": budget.get("local_date"),
                "budget_kcal": budget.get("budget_kcal"),
                "consumed_kcal": budget.get("consumed_kcal"),
                "remaining_kcal": budget.get("remaining_kcal"),
            },
            "manual_target": {
                **_status(manual_target_response),
                "live_llm_invoked": _json(manual_target_response).get("live_llm_invoked"),
                "production_selected": _json(manual_target_response).get("production_selected"),
            },
            "estimate": {
                **_status(estimate_response),
                "request_id": _json(estimate_response).get("request_id"),
                "has_payload": bool(_json(estimate_response).get("payload")),
            },
            "today_after_estimate": {
                **_status(today_after_response),
                "local_date": today_after.get("local_date"),
                "budget_kcal": today_after.get("budget_kcal"),
                "consumed_kcal": today_after.get("consumed_kcal"),
                "remaining_kcal": today_after.get("remaining_kcal"),
            },
            "debug": {
                **_status(debug_response),
                "read_only": debug_payload.get("read_only"),
                "same_truth_status": same_truth.get("status"),
                "consumed_kcal": dict(debug_model.get("today_summary") or {}).get("consumed_kcal"),
            },
            "chat_history": {
                **_status(chat_history_response),
                "source": chat_history_payload.get("source"),
                "frontend_semantic_owner": chat_history_payload.get("frontend_semantic_owner"),
                "message_count": len(chat_history_messages),
                "runtime_turn_trace_present": any(
                    message.get("runtime_turn_trace_present") is True for message in chat_history_messages
                ),
                "context_snapshot_present": any(
                    message.get("context_snapshot_present") is True for message in chat_history_messages
                ),
                "trace_chain_complete": any(
                    message.get("trace_chain_complete") is True for message in chat_history_messages
                ),
                "long_term_memory_used": chat_history_payload.get("long_term_memory_used"),
                "proactive_or_rescue_used": chat_history_payload.get("proactive_or_rescue_used"),
            },
            "manager_provider_call_count": len(provider.calls),
        }
        status, blockers = _validate(report)
        report["status"] = status
        report["blockers"] = blockers
        return report
    finally:
        if client is not None:
            _close_test_client(client)
        db.close()
        engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Accurate Intake local web shell route-bridge smoke.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--user-id", default="local-web-shell-smoke-user")
    parser.add_argument("--keep-db", action="store_true")
    args = parser.parse_args(argv)

    report = build_local_web_shell_bridge_report(
        db_path=Path(args.db_path),
        user_external_id=args.user_id,
        reset_db=not args.keep_db,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
