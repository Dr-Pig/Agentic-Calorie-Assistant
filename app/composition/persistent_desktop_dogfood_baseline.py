from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.composition import accurate_intake_debug_routes, intake_routes, local_data_hygiene_routes
from app.composition.local_dogfood_data_hygiene import classify_local_dogfood_db
from app.composition.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date
from app.database import get_or_create_user
from app.runtime.interface.local_debug_auth import LOCAL_DEBUG_API_TOKEN_ENV
from scripts.run_accurate_intake_desktop_dogfood_launcher import (
    DEFAULT_DB_PATH,
    build_app_for_desktop_dogfood,
    close_desktop_dogfood_app,
)
from scripts.run_accurate_intake_mvp_manager_style_smoke import DeterministicSelfUseManagerProvider

ROOT = Path(__file__).resolve().parents[2]
NOT_CLAIMING = ["product_ready", "private_self_use_approved", "fooddb_expansion_ready", "live_llm_ready"]

def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)

def _base_report(*, db_path: Path, local_date: str, user_external_id: str) -> dict[str, Any]:
    return {
        "artifact_type": "accurate_intake_persistent_desktop_dogfood_baseline",
        "artifact_schema_version": "1.0",
        "claim_scope": "local_desktop_dogfood_operational_baseline",
        "status": "not_run",
        "blockers": [],
        "db_path": _repo_relative(db_path),
        "local_date": local_date,
        "user_external_id": user_external_id,
        "persistent_local_sqlite": True,
        "manager_mode": "deterministic_fixture",
        "runtime_truth_changed": False,
        "mutation_legality_changed": False,
        "fooddb_truth_updated": False,
        "frontend_semantic_owner": False,
        "live_llm_invoked": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "not_claiming": list(NOT_CLAIMING),
    }

@contextmanager
def _dogfood_route_context(
    *, feedback_dir: Path, backup_dir: Path, export_dir: Path, review_queue_artifact_path: Path, local_debug_token: str
) -> Iterator[None]:
    previous = {
        "manager": intake_routes.manager_provider,
        "search": intake_routes.search_provider,
        "extract": intake_routes.extract_provider,
        "token": os.environ.get(LOCAL_DEBUG_API_TOKEN_ENV),
        "feedback": accurate_intake_debug_routes.DOGFOOD_FEEDBACK_DIR,
        "review": accurate_intake_debug_routes.DOGFOOD_REVIEW_QUEUE_ARTIFACT_PATH,
        "data_feedback": local_data_hygiene_routes.DOGFOOD_FEEDBACK_DIR,
        "data_review": local_data_hygiene_routes.DOGFOOD_REVIEW_QUEUE_ARTIFACT_PATH,
        "backup": local_data_hygiene_routes.DOGFOOD_BACKUP_DIR,
        "export": local_data_hygiene_routes.DOGFOOD_EXPORT_DIR,
    }
    intake_routes.manager_provider = DeterministicSelfUseManagerProvider()
    intake_routes.search_provider = None
    intake_routes.extract_provider = None
    os.environ[LOCAL_DEBUG_API_TOKEN_ENV] = local_debug_token
    accurate_intake_debug_routes.DOGFOOD_FEEDBACK_DIR = feedback_dir
    accurate_intake_debug_routes.DOGFOOD_REVIEW_QUEUE_ARTIFACT_PATH = review_queue_artifact_path
    local_data_hygiene_routes.DOGFOOD_FEEDBACK_DIR = feedback_dir
    local_data_hygiene_routes.DOGFOOD_REVIEW_QUEUE_ARTIFACT_PATH = review_queue_artifact_path
    local_data_hygiene_routes.DOGFOOD_BACKUP_DIR = backup_dir
    local_data_hygiene_routes.DOGFOOD_EXPORT_DIR = export_dir
    try:
        yield
    finally:
        intake_routes.manager_provider = previous["manager"]
        intake_routes.search_provider = previous["search"]
        intake_routes.extract_provider = previous["extract"]
        os.environ.pop(LOCAL_DEBUG_API_TOKEN_ENV, None)
        if previous["token"] is not None:
            os.environ[LOCAL_DEBUG_API_TOKEN_ENV] = str(previous["token"])
        accurate_intake_debug_routes.DOGFOOD_FEEDBACK_DIR = previous["feedback"]
        accurate_intake_debug_routes.DOGFOOD_REVIEW_QUEUE_ARTIFACT_PATH = previous["review"]
        local_data_hygiene_routes.DOGFOOD_FEEDBACK_DIR = previous["data_feedback"]
        local_data_hygiene_routes.DOGFOOD_REVIEW_QUEUE_ARTIFACT_PATH = previous["data_review"]
        local_data_hygiene_routes.DOGFOOD_BACKUP_DIR = previous["backup"]
        local_data_hygiene_routes.DOGFOOD_EXPORT_DIR = previous["export"]

def _seed_body_plan(app: Any, *, user_external_id: str, local_date: str) -> None:
    db: Session = sessionmaker(bind=app.state.accurate_intake_desktop_engine)()
    try:
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
    finally:
        db.close()

def _session_client(app: Any, *, token: str) -> TestClient:
    client = TestClient(app)
    client.post("/accurate-intake/local-debug-session", json={"token": token}).raise_for_status()
    return client

def _turn_summary(body: dict[str, Any]) -> dict[str, Any]:
    payload = dict(body.get("payload") or {})
    sidecar = dict(payload.get("sidecar") or {})
    trace = dict(dict(sidecar.get("macro") or {}).get("approved_fooddb_evidence_trace") or {})
    return {
        "request_id": body.get("request_id"),
        "canonical_commit": dict(payload.get("state_delta") or {}).get("canonical_commit") is True,
        "final_action": dict(dict(payload.get("intake_execution_manager") or {}).get("final") or {}).get("final_action"),
        "db_hit_type": dict(sidecar.get("evidence") or {}).get("db_hit_type"),
        "disambiguation_required": trace.get("disambiguation_required") is True,
        "macro_visibility_status": trace.get("macro_visibility_status"),
    }

def _snapshot(client: TestClient, *, user_external_id: str, local_date: str) -> dict[str, Any]:
    params = {"user_id": user_external_id, "local_date": local_date}
    today = client.get("/today/current-budget", params=params).json()
    chat = client.get("/accurate-intake/chat-history", params=params).json()
    debug = client.get("/accurate-intake/debug", params=params).json()
    complete = sum(1 for message in chat.get("messages", []) if message.get("trace_chain_complete") is True)
    return {
        "today": {
            "budget_kcal": today.get("budget_kcal"),
            "consumed_kcal": today.get("consumed_kcal"),
            "remaining_kcal": today.get("remaining_kcal"),
            "active_meal_count": today.get("active_meal_count"),
            "show_macro": today.get("show_macro"),
            "macro_guard_reason": today.get("macro_guard_reason"),
        },
        "chat_history": {"message_count": chat.get("message_count"), "complete_trace_message_count": complete},
        "debug": {"same_truth_status": dict(dict(debug.get("model") or {}).get("same_truth") or {}).get("status")},
    }

def _run_first_launch(db_path: Path, *, user_external_id: str, local_date: str, token: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    app = build_app_for_desktop_dogfood(db_path)
    try:
        _seed_body_plan(app, user_external_id=user_external_id, local_date=local_date)
        with _session_client(app, token=token) as client:
            base = {"allow_search": False, "user_id": user_external_id, "local_date": local_date}
            approved = client.post("/estimate", json={**base, "text": "茶葉蛋"})
            ambiguous = client.post("/estimate", json={**base, "text": "boba milk teaa"})
            approved.raise_for_status()
            ambiguous.raise_for_status()
            return _turn_summary(approved.json()), _turn_summary(ambiguous.json()), _snapshot(client, user_external_id=user_external_id, local_date=local_date)
    finally:
        close_desktop_dogfood_app(app)

def _run_second_launch(db_path: Path, *, user_external_id: str, local_date: str, token: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    app = build_app_for_desktop_dogfood(db_path)
    try:
        with _session_client(app, token=token) as client:
            feedback = client.post(
                "/accurate-intake/feedback",
                json={"category": "product_feedback", "feedback_text": "Persistent desktop baseline feedback.", "page": "desktop", "selected_date": local_date, "user_external_id": user_external_id, "trace_id": "persistent-baseline-trace", "severity": "low"},
            )
            review = client.get("/accurate-intake/review-queue")
            export = client.post("/accurate-intake/local-data-hygiene/export", json={"label": "persistent-baseline"})
            feedback.raise_for_status()
            review.raise_for_status()
            export.raise_for_status()
            return _snapshot(client, user_external_id=user_external_id, local_date=local_date), {"record_count": 1, "response": feedback.json()}, review.json(), export.json()
    finally:
        close_desktop_dogfood_app(app)

def build_persistent_desktop_dogfood_baseline_report(
    *,
    db_path: Path = DEFAULT_DB_PATH,
    local_date: str,
    user_external_id: str,
    local_debug_token: str,
    reset_db: bool = False,
    feedback_dir: Path = ROOT / "workspace_data" / "local_dogfood_feedback",
    backup_dir: Path = ROOT / "workspace_data" / "local_dogfood_backups",
    export_dir: Path = ROOT / "workspace_data" / "local_dogfood_exports",
    review_queue_artifact_path: Path = ROOT / "artifacts" / "accurate_intake_dogfood_review_queue.json",
) -> dict[str, Any]:
    report = _base_report(db_path=db_path, local_date=local_date, user_external_id=user_external_id)
    if reset_db and classify_local_dogfood_db(db_path)["backup_required_before_reset"] is True:
        return {**report, "status": "blocked", "blockers": ["backup_required_before_reset"]}
    if reset_db and db_path.exists():
        db_path.unlink()
    with _dogfood_route_context(feedback_dir=feedback_dir, backup_dir=backup_dir, export_dir=export_dir, review_queue_artifact_path=review_queue_artifact_path, local_debug_token=local_debug_token):
        approved, ambiguous, before = _run_first_launch(db_path, user_external_id=user_external_id, local_date=local_date, token=local_debug_token)
        after, feedback, review, export = _run_second_launch(db_path, user_external_id=user_external_id, local_date=local_date, token=local_debug_token)
    blockers = []
    if not approved["canonical_commit"]:
        blockers.append("approved_packet_not_committed")
    if ambiguous["canonical_commit"] or not ambiguous["disambiguation_required"]:
        blockers.append("ambiguous_packet_boundary_failed")
    if before["today"] != after["today"]:
        blockers.append("restart_today_truth_changed")
    if int(after["chat_history"]["complete_trace_message_count"] or 0) < 4:
        blockers.append("restart_trace_chain_incomplete")
    if export.get("sidecar_evidence_included") is not True:
        blockers.append("export_sidecars_missing")
    return {**report, "status": "pass" if not blockers else "fail", "blockers": blockers, "approved_packet_turn": approved, "ambiguous_packet_turn": ambiguous, "before_restart": before, "after_restart": after, "feedback": feedback, "review_queue": review, "export": export}
