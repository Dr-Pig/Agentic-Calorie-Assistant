from __future__ import annotations

import os
import secrets
import time
from pathlib import Path
from typing import Any

import pytest

from app.database import get_or_create_user
from app.runtime.interface.local_debug_auth import LOCAL_DEBUG_API_TOKEN_ENV
from scripts.run_accurate_intake_browser_shell_smoke import (
    BrowserSmokeDependencyMissing,
    _build_app,
    _free_port,
    _load_sync_playwright,
    _restore_runtime,
    _run_uvicorn_in_thread,
    _seed_body_plan,
    _session_factory,
    _wait_for_http,
)
from scripts.run_accurate_intake_desktop_dogfood_launcher import add_desktop_dogfood_entry_routes
from scripts.run_accurate_intake_mvp_manager_style_smoke import DeterministicSelfUseManagerProvider


def _static_page_url(base_url: str, page: str, *, user_id: str, local_date: str) -> str:
    return f"{base_url}/static/accurate-intake-{page}.html?user_id={user_id}&local_date={local_date}"


def _local_debug_session_cookie_established(page: Any) -> bool:
    status = page.evaluate(
        """async () => {
          const response = await fetch("/accurate-intake/local-debug-session");
          return response.status;
        }"""
    )
    return status == 200


def _browser_module() -> Any:
    try:
        return _load_sync_playwright()
    except BrowserSmokeDependencyMissing as exc:
        pytest.skip(str(exc))


def test_direct_static_operator_pages_reconnect_through_friendly_routes(tmp_path: Path) -> None:
    playwright_module = _browser_module()
    user_id = "static-session-reconnect-user"
    local_date = "2026-05-12"
    db_path = tmp_path / "static-session-reconnect.sqlite3"
    engine, SessionLocal = _session_factory(db_path)
    provider = DeterministicSelfUseManagerProvider()
    db = SessionLocal()
    app = _build_app(SessionLocal, provider)
    add_desktop_dogfood_entry_routes(app)
    port = _free_port()
    previous_debug_token = os.environ.get(LOCAL_DEBUG_API_TOKEN_ENV)
    os.environ[LOCAL_DEBUG_API_TOKEN_ENV] = secrets.token_urlsafe(24)
    server, thread = _run_uvicorn_in_thread(app, port=port)
    try:
        base_url = f"http://127.0.0.1:{port}"
        _wait_for_http(f"{base_url}/static/accurate-intake-data.html")
        get_or_create_user(db, user_id)
        _seed_body_plan(db, user_external_id=user_id, local_date=local_date)

        with playwright_module() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                expectations = {
                    "data": ('[data-surface-role="local-data-hygiene"]', "#hygiene-status"),
                    "feedback": ('[data-surface-role="dogfood-feedback"]', "#feedback-status"),
                    "review": ('[data-surface-role="dogfood-review-queue"]', "#review-status"),
                }
                for page_name, (surface_selector, ready_selector) in expectations.items():
                    context = browser.new_context(viewport={"width": 1280, "height": 900})
                    page = context.new_page()
                    try:
                        responses: list[tuple[int, str]] = []
                        page.on("response", lambda response: responses.append((response.status, response.url)))
                        page.goto(
                            _static_page_url(base_url, page_name, user_id=user_id, local_date=local_date),
                            wait_until="networkidle",
                            timeout=15000,
                        )
                        page.wait_for_selector(surface_selector, timeout=15000)
                        assert any(
                            status == 307
                            and f"/accurate-intake/{page_name}" in url
                            and "reconnect_attempted=1" in url
                            for status, url in responses
                        ), responses
                        assert f"/static/accurate-intake-{page_name}.html" in page.url
                        assert _local_debug_session_cookie_established(page) is True
                        assert "local_debug_token=" not in page.url
                        assert page.evaluate(
                            """() => typeof window.LOCAL_DEBUG_API_TOKEN === "undefined"
                              || window.LOCAL_DEBUG_API_TOKEN === "" """
                        )
                        if page_name == "data":
                            page.wait_for_function(
                                """(selector) => document.querySelector(selector)?.textContent?.trim()
                                  && document.querySelector(selector)?.textContent?.trim() !== "--" """,
                                arg=ready_selector,
                                timeout=15000,
                            )
                    finally:
                        page.close()
                        context.close()
            finally:
                browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        _restore_runtime(app)
        if previous_debug_token is None:
            os.environ.pop(LOCAL_DEBUG_API_TOKEN_ENV, None)
        else:
            os.environ[LOCAL_DEBUG_API_TOKEN_ENV] = previous_debug_token
        db.close()
        engine.dispose()
        time.sleep(0.1)
