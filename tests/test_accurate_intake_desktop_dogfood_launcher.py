from __future__ import annotations

import json
from pathlib import Path

from app.composition import accurate_intake_debug_routes, local_data_hygiene_routes
from app.database import append_message, get_or_create_user
from app.shared.infra.models import Base
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from scripts.run_accurate_intake_desktop_dogfood_launcher import (
    DESKTOP_PAGES,
    build_launch_descriptor,
    build_app_for_desktop_dogfood,
    close_desktop_dogfood_app,
    main,
)


def _seed_feedback_chat_trace(db_path: Path) -> None:
    engine = create_engine(
        f"sqlite:///{db_path.as_posix()}",
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    try:
        with SessionLocal() as db:
            user = get_or_create_user(db, "dogfood-user")
            trace = {
                "request_id": "trace-auto-ctx-001",
                "local_date": "2026-05-10",
                "assistant_response": {"structured_followup_question": None},
                "trace_chain": {
                    "manager_decision_present": True,
                    "evidence_packet_present": True,
                    "evidence_requirement_satisfied": True,
                    "final_mapping_present": True,
                    "state_before_present": True,
                    "state_after_present": True,
                },
            }
            append_message(
                db,
                user,
                "user",
                "早餐吃鐵板麵、荷包蛋、豬肉片",
                trace_id="trace-auto-ctx-001",
                trace_json={"runtime_turn_trace": trace},
            )
            append_message(
                db,
                user,
                "assistant",
                "已記錄這餐，並用鐵板麵、荷包蛋、豬肉片估算。",
                trace_id="trace-auto-ctx-001",
                trace_json={"runtime_turn_trace": trace},
            )
    finally:
        engine.dispose()


def test_desktop_dogfood_launch_descriptor_uses_persistent_local_sqlite_and_launchpad_url() -> None:
    descriptor = build_launch_descriptor(
        host="127.0.0.1",
        port=8765,
        user_id="dogfood-user",
        db_path=Path("workspace_data/local_dogfood/accurate_intake.sqlite3"),
        local_debug_token="test-token",
        provider_status={
            "provider": {"status": "configured", "configured": True},
            "manager_provider": {"status": "configured", "configured": True},
            "search": {"status": "not_configured", "configured": False},
            "extract": {"status": "not_configured", "configured": False},
        },
    )

    assert descriptor["artifact_type"] == "accurate_intake_desktop_dogfood_launcher_descriptor"
    assert descriptor["status"] == "launch_descriptor_ready"
    assert descriptor["entry_surface"] == "desktop_dogfood_hub"
    assert descriptor["host"] == "127.0.0.1"
    assert descriptor["port"] == 8765
    assert descriptor["db_path"] == "workspace_data/local_dogfood/accurate_intake.sqlite3"
    assert descriptor["persistent_local_sqlite"] is True
    assert descriptor["reset_db_default"] is False
    assert descriptor["launch_url"] == "http://127.0.0.1:8765/accurate-intake?user_id=dogfood-user"
    assert descriptor["entry_pages"] == [
        "desktop",
        "chat",
        "today",
        "body",
        "feedback",
        "review",
        "data",
    ]
    assert descriptor["entry_page_urls"] == {
        "desktop": "http://127.0.0.1:8765/accurate-intake/desktop?user_id=dogfood-user",
        "chat": "http://127.0.0.1:8765/accurate-intake/chat?user_id=dogfood-user",
        "today": "http://127.0.0.1:8765/accurate-intake/today?user_id=dogfood-user",
        "body": "http://127.0.0.1:8765/accurate-intake/body?user_id=dogfood-user",
        "feedback": "http://127.0.0.1:8765/accurate-intake/feedback?user_id=dogfood-user",
        "review": "http://127.0.0.1:8765/accurate-intake/review?user_id=dogfood-user",
        "data": "http://127.0.0.1:8765/accurate-intake/data?user_id=dogfood-user",
    }
    assert descriptor["local_debug_token"] == "test-token"
    assert descriptor["local_debug_header"] == "X-Local-Debug-Token"
    assert descriptor["local_debug_token_in_url"] is False
    assert descriptor["local_debug_session_auto_cookie"] is True
    assert descriptor["manual_local_debug_token_fallback"] is True
    assert descriptor["provider_status"]["manager_provider"] == {
        "status": "configured",
        "configured": True,
    }
    assert descriptor["provider_status"]["search"] == {
        "status": "not_configured",
        "configured": False,
    }


def test_desktop_dogfood_launch_descriptor_preserves_non_claims_and_boundaries() -> None:
    descriptor = build_launch_descriptor(
        host="127.0.0.1",
        port=8765,
        user_id="dogfood-user",
        db_path=Path("workspace_data/local_dogfood/accurate_intake.sqlite3"),
        local_debug_token="test-token",
    )

    assert descriptor["runtime_truth_changed"] is False
    assert descriptor["mutation_legality_changed"] is False
    assert descriptor["fooddb_truth_updated"] is False
    assert descriptor["frontend_semantic_owner"] is False
    assert descriptor["live_llm_invoked"] is False
    assert descriptor["production_db_used"] is False
    assert descriptor["product_readiness_claimed"] is False
    assert descriptor["private_self_use_approved"] is False
    assert descriptor["not_claiming"] == [
        "product_ready",
        "private_self_use_approved",
        "production_ready",
        "live_llm_ready",
        "fooddb_expansion_ready",
    ]
    assert "base_url" not in json.dumps(descriptor)
    assert "api_key" not in json.dumps(descriptor).lower()


def test_desktop_dogfood_launcher_cli_prints_descriptor_without_starting_server(
    tmp_path: Path,
    capsys,
) -> None:
    output_path = tmp_path / "launcher.json"
    db_path = tmp_path / "accurate_intake.sqlite3"

    exit_code = main(
        [
            "--describe-only",
            "--host",
            "127.0.0.1",
            "--port",
            "8765",
            "--user-id",
            "dogfood-user",
            "--db-path",
            str(db_path),
            "--local-debug-token",
            "test-token",
            "--output",
            str(output_path),
        ]
    )
    printed = json.loads(capsys.readouterr().out)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact == printed
    assert artifact["status"] == "launch_descriptor_ready"
    assert artifact["server_started"] is False
    assert artifact["browser_open_requested"] is False
    assert artifact["db_path"].endswith(
        "test_desktop_dogfood_launcher_0/accurate_intake.sqlite3"
    )


def test_desktop_dogfood_launcher_app_path_captures_feedback_into_review_queue(
    monkeypatch,
    tmp_path: Path,
) -> None:
    token = "launcher-token"
    db_path = tmp_path / "accurate_intake.sqlite3"
    feedback_dir = tmp_path / "feedback"
    review_path = tmp_path / "review" / "queue.json"
    data_dir = tmp_path / "data"
    monkeypatch.setenv("LOCAL_DEBUG_API_TOKEN", token)
    monkeypatch.setattr(accurate_intake_debug_routes, "DOGFOOD_FEEDBACK_DIR", feedback_dir, raising=False)
    monkeypatch.setattr(
        accurate_intake_debug_routes,
        "DOGFOOD_REVIEW_QUEUE_ARTIFACT_PATH",
        review_path,
        raising=False,
    )
    monkeypatch.setattr(local_data_hygiene_routes, "DOGFOOD_FEEDBACK_DIR", feedback_dir, raising=False)
    monkeypatch.setattr(local_data_hygiene_routes, "DOGFOOD_REVIEW_QUEUE_ARTIFACT_PATH", review_path, raising=False)
    monkeypatch.setattr(local_data_hygiene_routes, "DOGFOOD_BACKUP_DIR", data_dir / "backups", raising=False)
    monkeypatch.setattr(local_data_hygiene_routes, "DOGFOOD_EXPORT_DIR", data_dir / "exports", raising=False)

    app = build_app_for_desktop_dogfood(db_path)
    try:
        with TestClient(app) as client:
            entry = client.get("/static/accurate-intake-desktop.html?user_id=dogfood-user")
            assert entry.status_code == 200
            assert 'data-surface-role="desktop-dogfood-entry"' in entry.text

            establish = client.post("/accurate-intake/local-debug-session", json={"token": token})
            feedback = client.post(
                "/accurate-intake/feedback",
                json={
                    "category": "ui_ux",
                    "feedback_text": "Launcher path feedback.",
                    "page": "desktop",
                    "selected_date": "2026-05-10",
                    "user_external_id": "dogfood-user",
                    "trace_id": "trace-launcher-001",
                    "message_id": "assistant-launcher-001",
                    "severity": "medium",
                    "ui_event": {
                        "source_page": "desktop",
                        "route": "/static/accurate-intake-desktop.html",
                    },
                },
            )
            review = client.get("/accurate-intake/review-queue")
            data = client.get("/accurate-intake/local-data-hygiene")

        assert establish.status_code == 204
        assert "local_debug_session" in establish.headers["set-cookie"]
        assert feedback.status_code == 200
        assert review.status_code == 200
        assert data.status_code == 200
        feedback_payload = feedback.json()
        review_payload = review.json()
        assert feedback_payload["linked_context"]["trace_id"] == "trace-launcher-001"
        assert feedback_payload["review_status"] == "needs_review"
        assert feedback_payload["routing_target"] == "AppShell"
        assert feedback_payload["operation_context"]["submitted_endpoint"] == "/accurate-intake/feedback"
        assert feedback_payload["operation_context"]["http_status"] == 200
        assert isinstance(feedback_payload["operation_context"]["duration_ms"], int)
        assert feedback_payload["manager_context_injection_allowed"] is False
        assert feedback_payload["food_kb_truth_update_allowed"] is False
        assert feedback_payload["canonical_eval_promotion_allowed"] is False
        assert review_payload["feedback_triage_record_count"] == 1
        assert review_payload["desktop_feedback_records"][0]["feedback_id"] == feedback_payload["feedback_id"]
        assert review_payload["desktop_feedback_records"][0]["routing_target"] == "AppShell"
        assert review_payload["desktop_feedback_records"][0]["operation_context"][
            "submitted_endpoint"
        ] == "/accurate-intake/feedback"
        assert review_payload["manager_context_injection_allowed"] is False
        assert review_payload["food_kb_truth_update_allowed"] is False
        assert review_payload["canonical_eval_promotion_allowed"] is False
        assert data.json()["db_path"].endswith("accurate_intake.sqlite3")
        assert db_path.exists()
    finally:
        close_desktop_dogfood_app(app)


def test_desktop_feedback_auto_attaches_recent_trace_and_read_model_without_manual_ids(
    monkeypatch,
    tmp_path: Path,
) -> None:
    token = "launcher-token"
    db_path = tmp_path / "accurate_intake.sqlite3"
    feedback_dir = tmp_path / "feedback"
    review_path = tmp_path / "review" / "queue.json"
    monkeypatch.setenv("LOCAL_DEBUG_API_TOKEN", token)
    monkeypatch.setattr(accurate_intake_debug_routes, "DOGFOOD_FEEDBACK_DIR", feedback_dir, raising=False)
    monkeypatch.setattr(
        accurate_intake_debug_routes,
        "DOGFOOD_REVIEW_QUEUE_ARTIFACT_PATH",
        review_path,
        raising=False,
    )
    _seed_feedback_chat_trace(db_path)
    app = build_app_for_desktop_dogfood(db_path)
    try:
        with TestClient(app) as client:
            establish = client.post("/accurate-intake/local-debug-session", json={"token": token})
            feedback = client.post(
                "/accurate-intake/feedback",
                json={
                    "category": "manager_behavior",
                    "feedback_text": "它把詢問估算依據誤解成修改餐點。",
                    "page": "chat",
                    "selected_date": "2026-05-10",
                    "user_external_id": "dogfood-user",
                    "severity": "high",
                    "ui_event": {"source_page": "chat", "route": "/static/accurate-intake-chat.html"},
                },
            )
            review = client.get("/accurate-intake/review-queue")

        assert establish.status_code == 204
        assert feedback.status_code == 200
        assert review.status_code == 200
        feedback_payload = feedback.json()
        linked = feedback_payload["linked_context"]
        assert linked["context_status"] == "auto_attached"
        assert linked["auto_context_source"] == "chat_history_and_read_model"
        assert linked["trace_id"] == "trace-auto-ctx-001"
        assert linked["request_id"] == "trace-auto-ctx-001"
        assert str(linked["message_id"])
        assert linked["feedback_links_to_trace"] is True
        assert [message["role"] for message in linked["recent_messages"]] == ["user", "assistant"]
        assert "鐵板麵" in linked["recent_messages"][0]["content"]
        assert linked["read_model_snapshot"]["state_posture"] == "canonical_user_state"
        assert linked["read_model_snapshot"]["local_date"] == "2026-05-10"
        assert feedback_payload["operation_context"]["auto_context_status"] == "auto_attached"
        assert feedback_payload["manager_context_injection_allowed"] is False
        assert feedback_payload["canonical_eval_promotion_allowed"] is False
        review_payload = review.json()
        review_record = review_payload["desktop_feedback_records"][0]
        assert review_record["linked_context"]["trace_id"] == "trace-auto-ctx-001"
        assert review_record["linked_context"]["read_model_snapshot"]["local_date"] == "2026-05-10"
    finally:
        close_desktop_dogfood_app(app)


def test_desktop_dogfood_app_redirects_friendly_page_routes(tmp_path: Path) -> None:
    app = build_app_for_desktop_dogfood(tmp_path / "accurate_intake.sqlite3")
    try:
        with TestClient(app) as client:
            home = client.get(
                "/accurate-intake/desktop?user_id=dogfood-user&local_date=2026-05-11",
                follow_redirects=False,
            )
            root_alias = client.get(
                "/accurate-intake-desktop.html?user_id=dogfood-user",
                follow_redirects=False,
            )
            chat = client.get(
                "/accurate-intake/chat?user_id=dogfood-user",
                follow_redirects=False,
            )

        assert home.status_code == 307
        assert home.headers["location"] == (
            "/static/accurate-intake-desktop.html?user_id=dogfood-user&local_date=2026-05-11"
        )
        assert root_alias.status_code == 307
        assert root_alias.headers["location"] == "/static/accurate-intake-desktop.html?user_id=dogfood-user"
        assert chat.status_code == 307
        assert chat.headers["location"] == "/static/accurate-intake-chat.html?user_id=dogfood-user"
    finally:
        close_desktop_dogfood_app(app)


def test_desktop_dogfood_friendly_routes_auto_establish_cookie_without_url_token(
    monkeypatch,
    tmp_path: Path,
) -> None:
    token = "launcher-token"
    monkeypatch.setenv("LOCAL_DEBUG_API_TOKEN", token)
    app = build_app_for_desktop_dogfood(tmp_path / "accurate_intake.sqlite3")
    try:
        with TestClient(app) as client:
            home = client.get(
                "/accurate-intake?user_id=dogfood-user&local_date=2026-05-11",
                follow_redirects=False,
            )
            protected = client.get("/accurate-intake/local-debug-session")

        assert home.status_code == 307
        assert home.headers["location"] == (
            "/static/accurate-intake-desktop.html?user_id=dogfood-user&local_date=2026-05-11"
        )
        assert "local_debug_token=" not in home.headers["location"]
        set_cookie = home.headers["set-cookie"]
        assert "local_debug_session=" in set_cookie
        assert "HttpOnly" in set_cookie
        assert "samesite=strict" in set_cookie.lower()
        assert "Path=/" in set_cookie
        assert "Domain=" not in set_cookie
        assert protected.status_code == 200
        assert protected.json() == {"status": "connected", "local_only": True}
    finally:
        close_desktop_dogfood_app(app)


def test_all_desktop_shortcut_routes_establish_session_for_protected_dogfood_apis(
    monkeypatch,
    tmp_path: Path,
) -> None:
    token = "launcher-token"
    feedback_dir = tmp_path / "feedback"
    review_path = tmp_path / "review" / "queue.json"
    data_dir = tmp_path / "data"
    monkeypatch.setenv("LOCAL_DEBUG_API_TOKEN", token)
    monkeypatch.setattr(accurate_intake_debug_routes, "DOGFOOD_FEEDBACK_DIR", feedback_dir, raising=False)
    monkeypatch.setattr(
        accurate_intake_debug_routes,
        "DOGFOOD_REVIEW_QUEUE_ARTIFACT_PATH",
        review_path,
        raising=False,
    )
    monkeypatch.setattr(local_data_hygiene_routes, "DOGFOOD_FEEDBACK_DIR", feedback_dir, raising=False)
    monkeypatch.setattr(local_data_hygiene_routes, "DOGFOOD_REVIEW_QUEUE_ARTIFACT_PATH", review_path, raising=False)
    monkeypatch.setattr(local_data_hygiene_routes, "DOGFOOD_BACKUP_DIR", data_dir / "backups", raising=False)
    monkeypatch.setattr(local_data_hygiene_routes, "DOGFOOD_EXPORT_DIR", data_dir / "exports", raising=False)
    app = build_app_for_desktop_dogfood(tmp_path / "accurate_intake.sqlite3")
    try:
        for page in DESKTOP_PAGES:
            with TestClient(app) as client:
                route = "/accurate-intake" if page == "desktop" else f"/accurate-intake/{page}"
                entry = client.get(
                    f"{route}?user_id=dogfood-user&local_date=2026-05-11",
                    follow_redirects=False,
                )
                probe = client.get("/accurate-intake/local-debug-session")

                assert entry.status_code == 307
                assert entry.headers["location"] == (
                    f"/static/accurate-intake-{page}.html"
                    "?user_id=dogfood-user&local_date=2026-05-11"
                )
                assert "local_debug_token=" not in entry.headers["location"]
                assert "local_debug_session=" in entry.headers["set-cookie"]
                assert probe.status_code == 200

                if page == "feedback":
                    feedback = client.post(
                        "/accurate-intake/feedback",
                        json={
                            "category": "bug",
                            "feedback_text": "Shortcut route feedback smoke.",
                            "page": "feedback",
                            "selected_date": "2026-05-11",
                            "user_external_id": "dogfood-user",
                        },
                    )
                    assert feedback.status_code == 200
                if page == "review":
                    assert client.get("/accurate-intake/review-queue").status_code == 200
                if page == "data":
                    assert client.get("/accurate-intake/local-data-hygiene").status_code == 200
    finally:
        close_desktop_dogfood_app(app)


def test_tracked_desktop_shortcut_script_uses_friendly_routes_and_stale_server_recovery() -> None:
    script = Path("scripts/open_accurate_intake_desktop_page.ps1").read_text(encoding="utf-8")

    assert '[ValidateSet("desktop", "chat", "today", "body", "feedback", "review", "data")]' in script
    assert "Test-AcaAutoSession" in script
    assert "Stop-AcaServerIfOwned" in script
    assert "run_accurate_intake_desktop_dogfood_launcher.py" in script
    assert "/accurate-intake/local-debug-session" in script
    assert 'if ($Page -eq "desktop") { "accurate-intake" } else { "accurate-intake/$Page" }' in script
    assert "local_debug_token=" not in script
    assert "-WindowStyle Hidden" in script


def test_desktop_shortcut_folder_generator_creates_stable_aca_entrypoints_without_token_leak() -> None:
    script = Path("scripts/create_accurate_intake_desktop_shortcuts.ps1").read_text(encoding="utf-8")

    expected_shortcuts = {
        "ACA 0 Local Token.lnk": "notepad.exe",
        "ACA 1 Start Home.lnk": '-Page "desktop"',
        "ACA 2 Chat.lnk": '-Page "chat"',
        "ACA 3 Today UI.lnk": '-Page "today"',
        "ACA 4 Body.lnk": '-Page "body"',
        "ACA 5 Feedback.lnk": '-Page "feedback"',
        "ACA 6 Review.lnk": '-Page "review"',
        "ACA 7 Data Backup Export.lnk": '-Page "data"',
    }
    for shortcut_name, expected_target in expected_shortcuts.items():
        assert shortcut_name in script
        assert expected_target in script

    assert "WScript.Shell" in script
    assert "CreateShortcut" in script
    assert "open_accurate_intake_desktop_page.ps1" in script
    assert "workspace_data\\local_dogfood" in script
    assert "local_debug_token.txt" in script
    assert "local_debug_token=" not in script
    assert "/static/accurate-intake" not in script


def test_self_use_runbook_documents_desktop_launcher_without_readiness_claim() -> None:
    runbook = Path("docs/quality/ACCURATE_INTAKE_MVP_SELF_USE_RUNBOOK.md").read_text(encoding="utf-8-sig")

    assert "run_accurate_intake_desktop_dogfood_launcher.py" in runbook
    assert "open_accurate_intake_desktop_page.ps1" in runbook
    assert "create_accurate_intake_desktop_shortcuts.ps1" in runbook
    assert "workspace_data/local_dogfood/accurate_intake.sqlite3" in runbook
    assert "/accurate-intake" in runbook
    assert "/static/accurate-intake-desktop.html" in runbook
    assert "X-Local-Debug-Token" in runbook
    assert "provider preflight" in runbook
    assert "does not approve private self-use" in runbook


def test_desktop_entry_page_displays_sanitized_provider_preflight() -> None:
    html = Path("static/accurate-intake-desktop.html").read_text(encoding="utf-8")

    assert 'data-provider-preflight-source="/ping"' in html
    assert 'id="manager-provider-status"' in html
    assert 'id="search-provider-status"' in html
    assert 'id="extract-provider-status"' in html
    assert "function renderProviderPreflight(payload)" in html
    assert "base_url" not in html
    assert "timeout_seconds" not in html
