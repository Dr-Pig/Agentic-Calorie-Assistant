from __future__ import annotations

import json
from pathlib import Path

from scripts.run_accurate_intake_local_web_shell_smoke import (
    _build_test_client,
    _close_test_client,
    build_local_web_shell_bridge_report,
    main,
)


def test_local_web_shell_bridge_smoke_closes_static_to_runtime_loop(tmp_path: Path) -> None:
    report = build_local_web_shell_bridge_report(db_path=tmp_path / "web-shell.sqlite3")

    assert report["route_bridge_id"] == "accurate_intake_local_web_shell_route_bridge_v1"
    assert report["status"] == "pass"
    assert report["claim_scope"] == "local_deterministic_web_shell_route_bridge_smoke"
    assert report["evidence_scope"] == "server_route_compatibility_not_browser_execution"
    assert report["static_shell"]["ok"] is True
    assert report["static_shell"]["contains_shell_id"] is True
    assert report["static_shell"]["contains_frontend_non_owner_marker"] is True
    assert report["backend_local_date_source"] == "today_current_budget"
    assert report["frontend_semantic_owner"] is False
    assert report["browser_executed"] is False
    assert report["browser_execution_required"] is False
    assert report["deferred_evidence"] == ["browser_executed_fetch_sequence"]
    assert report["provider"]["live_llm_invoked"] is False
    assert report["manual_target"]["live_llm_invoked"] is False
    assert report["manual_target"]["production_selected"] is False
    assert report["estimate"]["has_payload"] is True
    assert report["today_after_estimate"]["consumed_kcal"] > 0
    assert report["debug"]["read_only"] is True
    assert report["debug"]["same_truth_status"] == "pass"
    assert report["chat_history"]["ok"] is True
    assert report["chat_history"]["source"] == "sqlite_message_buffer"
    assert report["chat_history"]["frontend_semantic_owner"] is False
    assert report["chat_history"]["message_count"] >= 2
    assert report["chat_history"]["runtime_turn_trace_present"] is True
    assert report["chat_history"]["context_snapshot_present"] is True
    assert report["chat_history"]["trace_chain_complete"] is True


def test_local_web_shell_bridge_uses_backend_date_for_followup_surfaces(tmp_path: Path) -> None:
    report = build_local_web_shell_bridge_report(db_path=tmp_path / "web-shell.sqlite3")

    backend_date = report["backend_local_date"]
    assert backend_date
    assert report["initial_budget"]["local_date"] == backend_date
    assert report["today_after_estimate"]["local_date"] == backend_date


def test_local_web_shell_bridge_preserves_non_claims(tmp_path: Path) -> None:
    report = build_local_web_shell_bridge_report(db_path=tmp_path / "web-shell.sqlite3")

    assert report["live_llm_invoked"] is False
    assert report["production_db_used"] is False
    assert report["product_readiness_claimed"] is False
    assert report["private_self_use_approved"] is False
    assert report["production_selected"] is False
    assert report["browser_executed"] is False
    assert {
        "product_ready",
        "rollout_ready",
        "live_llm_ready",
        "web_ready",
        "production_db_ready",
    } <= set(report["not_claiming"])
    assert report["chat_history"]["long_term_memory_used"] is False
    assert report["chat_history"]["proactive_or_rescue_used"] is False


def test_local_web_shell_bridge_client_uses_request_scoped_db_sessions() -> None:
    from app.database import get_db
    from scripts.run_accurate_intake_mvp_manager_style_smoke import DeterministicSelfUseManagerProvider

    created: list[FakeSession] = []

    class FakeSession:
        def __init__(self) -> None:
            self.closed = False

        def close(self) -> None:
            self.closed = True

    def fake_session_factory() -> FakeSession:
        session = FakeSession()
        created.append(session)
        return session

    client = _build_test_client(fake_session_factory, DeterministicSelfUseManagerProvider())  # type: ignore[arg-type]
    try:
        override_get_db = client.app.dependency_overrides[get_db]
        first_dependency = override_get_db()
        second_dependency = override_get_db()
        first_session = next(first_dependency)
        second_session = next(second_dependency)

        assert first_session is created[0]
        assert second_session is created[1]
        assert first_session is not second_session
        for dependency in (first_dependency, second_dependency):
            try:
                next(dependency)
            except StopIteration:
                pass
            else:
                raise AssertionError("dependency generator should stop after yielding one session")
        assert first_session.closed is True
        assert second_session.closed is True
    finally:
        _close_test_client(client)


def test_local_web_shell_bridge_cli_writes_artifact(tmp_path: Path, capsys) -> None:
    output_path = tmp_path / "bridge.json"
    db_path = tmp_path / "web-shell.sqlite3"

    exit_code = main(["--db-path", str(db_path), "--output", str(output_path)])
    printed = json.loads(capsys.readouterr().out)
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact == printed
    assert artifact["status"] == "pass"


def test_local_web_shell_bridge_restores_provider_globals_if_client_setup_fails(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from app.composition import intake_routes
    from scripts import run_accurate_intake_local_web_shell_smoke as module

    original_manager = intake_routes.manager_provider
    original_search = intake_routes.search_provider
    original_extract = intake_routes.extract_provider

    def fail_test_client(*_: object, **__: object) -> object:
        raise RuntimeError("forced_client_setup_failure")

    monkeypatch.setattr(module, "TestClient", fail_test_client)

    try:
        module.build_local_web_shell_bridge_report(db_path=tmp_path / "web-shell.sqlite3")
    except RuntimeError as exc:
        assert str(exc) == "forced_client_setup_failure"
    else:
        raise AssertionError("expected forced_client_setup_failure")

    assert intake_routes.manager_provider is original_manager
    assert intake_routes.search_provider is original_search
    assert intake_routes.extract_provider is original_extract
